import { useState, useEffect } from 'react';
import { MessageSquare, Moon, Sun } from 'lucide-react';
import { useLocation } from 'react-router-dom';

export default function FormHelper() {
	const [messages, setMessages] = useState([
		{ text: 'Hi! I’m here to help you fill the form. 😊', sender: 'bot' },
	]);
	const [input, setInput] = useState('');
	const [isDark, setIsDark] = useState(false);
	const [isLoading, setIsLoading] = useState(false); // New loading state
	const { state } = useLocation();
	const extra_url = state?.extra_url;
	// const [BASE_URL, setBASE_URL] = useState('');
	// 	useEffect(() => {
	// 		fetch('config.json')
	// 			.then((res) => res.json())
	// 			.then((config) => {
	// 				setBASE_URL(config.API_BASE_URL);
	// 			})
	// 			.catch((err) => {
	// 				console.error('Failed to load config.json', err);
	// 				setError('Could not load API configuration.');
	// 			});
	// 	}, []);

	useEffect(() => {
		const savedTheme = localStorage.getItem('theme');
		if (savedTheme === 'dark') {
			document.documentElement.classList.add('dark');
			setIsDark(true);
		}
	}, []);   
	      
	const toggleDarkMode = () => {
		const html = document.documentElement;
		if (html.classList.contains('dark')) {
			html.classList.remove('dark');
			localStorage.setItem('theme', 'light');
			setIsDark(false);
		} else {
			html.classList.add('dark');
			localStorage.setItem('theme', 'dark');
			setIsDark(true);
		}
	};

	const appendMessage = (text, sender) => {
		setMessages((prev) => [...prev, { text, sender }]);
	};

	const getCurrentTabUrl = () =>
		new Promise((resolve, reject) => {
			try {
				chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
					resolve(tabs[0].url);
				});
			} catch (err) {
				reject(err);
			}
		});


	const handleSend = async () => {
		if (!input.trim()) return;
		appendMessage(input, 'user');

		try {
			setIsLoading(true);
			const currentUrl = await getCurrentTabUrl();
			
			const res = await fetch(`http://localhost:8000/chat`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ query: input, url: currentUrl,extra_url }),
			});
			const data = await res.json();
			appendMessage(data.response || data.answer || 'Sorry, I couldn’t understand that.', 'bot');
		} catch (err) {
			appendMessage('Error contacting backend.', 'bot');
		}
		finally {
            setIsLoading(false);
        }
		setInput('');
	};

	const LoadingDots = () => (
        <div className="flex space-x-1 px-4 py-2 rounded-xl bg-blue-100 dark:bg-blue-900 text-gray-800 dark:text-gray-100 self-start">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
    );

	return (
		<div className="h-screen w-full flex items-center justify-center bg-gradient-to-br from-[#eef2f3] to-[#cfd9df] dark:from-gray-800 dark:to-gray-700 p-4">
			<div className="flex flex-col h-full max-h-[700px] w-full max-w-md bg-white dark:bg-gray-800 rounded-3xl shadow-2xl p-6 relative">
				<button
					onClick={toggleDarkMode}
					className="absolute top-4 right-4 p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition"
					aria-label="Toggle Theme"
				>
					{isDark ? <Sun className="text-yellow-400" /> : <Moon className="text-gray-800" />}
				</button>

				<div className="flex items-center text-blue-600 dark:text-blue-300 text-lg font-semibold mb-4">
					<MessageSquare className="mr-2" />
					Context Aware Assistant
				</div>

				<div className="flex-grow overflow-y-auto space-y-2 p-4 bg-white dark:bg-gray-900 rounded-xl shadow-inner border border-gray-200 dark:border-gray-700 mb-4">
					{messages.map((msg, i) => (
						<div
							key={i}
							className={`text-sm px-4 py-2 rounded-xl max-w-[80%] ${
								msg.sender === 'bot'
									? 'bg-blue-100 dark:bg-blue-900 text-gray-800 dark:text-gray-100 self-start'
									: 'bg-green-100 dark:bg-green-900 text-gray-800 dark:text-gray-100 self-end ml-auto'
							}`}
						>
							{msg.text}
						</div>
					))}
					{isLoading && <LoadingDots />}
				</div>

				<div className="flex gap-2 mb-3">
					<input
						type="text"
						value={input}
						onChange={(e) => setInput(e.target.value)}
						placeholder="Type your message..."
						className="flex-grow px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-gray-900 dark:text-white"
					/>
					<button
						onClick={handleSend}
						className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-xl transition-all"
					>
						Send
					</button>
				</div>
			</div>
		</div>
	);
}
