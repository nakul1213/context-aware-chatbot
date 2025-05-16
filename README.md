# 🧠 Context-Aware Chatbot Browser Extension

A dynamic, form-filling assistant that understands webpage content in real-time using Retrieval-Augmented Generation (RAG). Built with FastAPI, FAISS, HuggingFace, and Groq’s LLaMA 3, and delivered via a sleek Vite + React browser extension UI.

## ✨ Features

- 💬 Chatbot overlays on any webpage
- 🕸️ Backend crawler (Selenium optional) extracts and indexes webpage content
- 🧠 RAG pipeline using FAISS + HuggingFace embeddings
- 🤖 LLaMA 3 (via Groq) for context-aware responses
- ⚡ Fast, lightweight UI using Vite + React

## 📦 Tech Stack

- **Frontend**: React, Vite, Tailwind (optional)
- **Backend**: FastAPI, FAISS, HuggingFace Transformers, Groq API
- **Crawling**: Requests / BeautifulSoup (+ optional Selenium)
- **Browser Extension**: Manifest v3 compatible


# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
