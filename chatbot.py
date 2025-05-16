from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import requests
import os
import json
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq as Groq
from langchain.chains import RetrievalQA
from bs4 import BeautifulSoup
import logging
import time
from langchain.schema import Document
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urljoin
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Web Extension RAG Backend")

# Add CORS middleware to allow requests from extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not found in environment variables!")

# Default Groq model
DEFAULT_GROQ_MODEL = "llama3-70b-8192"

# Pydantic models
class CrawlRequest(BaseModel):
    url: str
    selector_config: Optional[Dict[str, str]] = None
    use_selenium: Optional[bool] = True
    wait_time: Optional[int] = 5
    max_depth: Optional[int] = 3
    max_pages: Optional[int] = 50
    selenium_fallback: Optional[bool] = False

class ChatRequest(BaseModel):
    url: str
    query: str
    model: Optional[str] = Field(default=DEFAULT_GROQ_MODEL)

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

# In-memory storage for vector databases (in production, use persistent storage)
vector_stores = {}

def setup_selenium_driver():
    """Set up and return a headless Chrome browser for Selenium"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

async def fetch_page_with_selenium(url: str, wait_time: int = 5):
    """Fetch page content using Selenium to bypass JavaScript checks"""
    driver = None
    try:
        driver = setup_selenium_driver()
        driver.get(url)
        
        # Wait for JavaScript to load content
        time.sleep(wait_time)
        
        # Get the page source after JavaScript execution
        page_content = driver.page_source
        return page_content
    
    except Exception as e:
        logger.error(f"Error fetching with Selenium: {str(e)}")
        return None
    
    finally:
        if driver:
            driver.quit()

@app.post("/crawl", status_code=200)
async def crawl_website(request: CrawlRequest):
    """
    Crawls the specified website using depth-first search and creates a RAG pipeline 
    with the extracted content.
    """
    try:
        base_url = request.url
        max_depth = 1
        max_pages = 25
        
        logger.info(f"Crawling website: {base_url} with max depth {max_depth} and max pages {max_pages}")
        
        # Store visited URLs to avoid cycles
        visited_urls = set()
        # Store extracted documents
        documents = []
        # URLs to visit with their depth
        url_stack = [(base_url, 0)]  # (url, depth)
        
        # Parse the base URL to get domain for staying within same site
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        
        while url_stack and len(visited_urls) < max_pages:
            current_url, current_depth = url_stack.pop()
            
            # Skip if already visited or exceeds max depth
            if current_url in visited_urls or current_depth > max_depth:
                continue
                
            logger.info(f"Processing {current_url} (depth: {current_depth})")
            visited_urls.add(current_url)
            
            try:
                # Fetch page content
                page_content = ""
                if request.use_selenium:
                    page_content = await fetch_page_with_selenium(current_url, request.wait_time)
                    if not page_content:
                        logger.warning(f"Failed to fetch content for {current_url} with Selenium")
                        continue
                else:
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        }
                        response = requests.get(current_url, headers=headers, timeout=10)
                        response.raise_for_status()
                        page_content = response.text
                        
                        if "Just a moment" in page_content or "Enable JavaScript and cookies" in page_content:
                            logger.warning(f"Detected Cloudflare protection at {current_url}. Will attempt Selenium if configured.")
                            if request.selenium_fallback:
                                page_content = await fetch_page_with_selenium(current_url, request.wait_time)
                    except Exception as e:
                        logger.warning(f"Failed to fetch {current_url}: {str(e)}")
                        continue
                
                # Parse the content
                soup = BeautifulSoup(page_content, 'html.parser')
                
                # Extract text and create document
                text_content = soup.get_text(strip=True)
                doc_metadata = {
                    "source": current_url,
                    "depth": current_depth,
                    "title": soup.title.text if soup.title else "No title",
                    "crawl_time": datetime.now().isoformat()
                }
                
                # Skip if page has too little content
                if len(text_content) > 100:  # Minimum content threshold
                    documents.append(Document(page_content=text_content, metadata=doc_metadata))
                
                # Apply custom extraction if selectors are provided
                if request.selector_config:
                    enhanced_documents = await enhance_documents_with_selectors(
                        current_url, 
                        soup,
                        request.selector_config,
                        current_depth
                    )
                    if enhanced_documents:
                        documents.extend(enhanced_documents)
                
                # Only follow links if not at max depth
                if current_depth < max_depth:
                    # Find all links on the page
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        # logger.info(f"new link : {href}")

                        # Skip empty links, anchors, or javascript
                        if not href or href.startswith('#') or href.startswith('javascript:'):
                            continue
                            
                        # Handle relative URLs
                        if not href.startswith(('http://', 'https://')):
                            # Convert relative to absolute URL
                            next_url = urljoin(current_url, href)
                        else:
                            next_url = href
                        
                        # Parse the URL to check domain
                        parsed_url = urlparse(next_url)
                        
                        # Only crawl links within the same domain
                        # parsed_url.netloc == base_domain and
                        if next_url not in visited_urls:
                            url_stack.append((next_url, current_depth + 1))
            
            except Exception as e:
                logger.error(f"Error processing {current_url}: {str(e)}")
                continue
                
        logger.info(f"Crawling completed. Processed {len(visited_urls)} pages, extracted {len(documents)} documents.")
        
        if not documents:
            logger.warning("No documents were extracted during crawling.")
            return {"status": "warning", "message": "Crawling completed but no content was extracted"}
            
        # Process documents for RAG
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        
        # Create embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Create vector store
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # Store the vector store in memory (indexed by URL)
        vector_stores[base_url] = vector_store
        
        return {
            "status": "success", 
            "message": f"Successfully processed {base_url}", 
            "chunks_count": len(chunks),
            "pages_crawled": len(visited_urls),
            "documents_extracted": len(documents),
            "extraction_method": "dfs_crawler",
            "content_preview": documents[0].page_content[:200] + "..." if documents else ""
        }
    
    except Exception as e:
        logger.error(f"Error crawling website: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing the website: {str(e)}")

async def enhance_documents_with_selectors(url: str, soup: BeautifulSoup, selector_config: Dict[str, str], depth: int):
    """Helper function to extract specific content using selectors from an already fetched page"""
    try:
        enhanced_docs = []
        
        for content_type, selector in selector_config.items():
            elements = soup.select(selector)
            for element in elements:
                text_content = element.get_text(strip=True)
                if text_content:  # Only add if content is not empty
                    enhanced_docs.append(Document(
                        page_content=text_content,
                        metadata={
                            "source": url,
                            "content_type": content_type,
                            "depth": depth,
                            "crawl_time": datetime.now().isoformat()
                        }
                    ))
        
        return enhanced_docs
    except Exception as e:
        logger.error(f"Error enhancing documents: {str(e)}")
        return None

@app.post("/chat", response_model=ChatResponse)
async def chat_with_website(request: ChatRequest):
    """
    Enables chat functionality with the content of a previously crawled website.
    """
    url = request.url
    query = request.query
    model = request.model or DEFAULT_GROQ_MODEL
    
    if url not in vector_stores:
        raise HTTPException(status_code=404, detail=f"Website {url} has not been crawled yet.")
    
    try:
        # Initialize Groq LLM
        if not GROQ_API_KEY:
            raise HTTPException(status_code=500, detail="GROQ API key not configured")
        
        # Create Groq LLM with required model parameter
        llm = Groq(
            api_key=GROQ_API_KEY,
            model=model
        )
        
        # Setup retriever
        retriever = vector_stores[url].as_retriever(search_kwargs={"k": 3})
        
        # Create prompt template
        template = """
        You are an AI assistant that answers questions based on the content of a specific webpage.
        Use the following context to answer the question:
        
        {context}
        
        Question: {question}
        
        Provide a brief answer based solely on the provided context.
        If the context does not provide enough information, indicate that no answer could be determined.
        """
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
        
        # Create QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        
        # Get answer
        result = qa_chain({"query": query})
        
        # Extract sources
        sources = []
        if "source_documents" in result:
            sources = [doc.metadata.get("source", "unknown") for doc in result["source_documents"]]
        
        return ChatResponse(
            answer=result.get("result", "No answer found."),
            sources=sources
        )
    
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.delete("/clear/{url}")
async def clear_website_data(url: str):
    """Clear the vector store for a specific URL"""
    # if url in vector_stores:
    #     del vector_stores[url]
    #     return {"status": "success", "message": f"Data for {url} cleared successfully"}
    # raise HTTPException(status_code=404, detail=f"No data found for {url}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
