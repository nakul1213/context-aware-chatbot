import React, { useState,useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
	const navigate = useNavigate();
	const [extra_url, setextraUrl] = useState('');
	const [loading, setLoading] = useState(false);
	const [loading2, setLoading2] = useState(false);
	const [error, setError] = useState('');
	// const [BASE_URL, setBASE_URL] = useState('');
	// useEffect(() => {
	// 	fetch('config.json')
	// 		.then((res) => res.json())
	// 		.then((config) => {
	// 			setBASE_URL(config.API_BASE_URL);
	// 		})
	// 		.catch((err) => {
	// 			console.error('Failed to load config.json', err);
	// 			setError('Could not load API configuration.');
	// 		});
	// }, []);
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

	const handleCrawl = async () => {
		const url = await getCurrentTabUrl();
		console.log('Current URL:', url); // Debugging line
		if (!extra_url.trim()) {
			setError('Please enter a valid URL');
			return;
		}
		setLoading(true);
		setError('');
		try {
			// console.log(BASE_URL)
			const response = await fetch(`http://localhost:8000/crawl`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ extra_url, url }),
			});
			const data = await response.json();
			console.log('Crawl success:', data);
			navigate('/home', {
				state: {
				  extra_url
				}
			  });
		} catch (err) {
			setError('Crawl failed. Check console for details.');
			console.error(err);
		}
		setLoading(false);
	};
	const handleSkip = async () => {
		const url = await getCurrentTabUrl();
		console.log('Current URL:', url); // Debugging line

		setLoading2(true);
		setError('');
		try {
			// console.log(BASE_URL)
			const response = await fetch(`http://localhost:8000/crawl`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url }),
			});
			const data = await response.json();
			console.log('Crawl success:', data);
			navigate('/home');
		} catch (err) {
			setError('Crawl failed. Check console for details.');
			console.error(err);
		}
		setLoading2(false);
	};

	return (
		<div className="relative max-w-3xl p-6 m-auto min-h-screen bg-contain bg-no-repeat bg-[url('assets/chatbot.jpg')] flex flex-col justify-center items-center">
			<div className="bg-white bg-opacity-80 dark:bg-black/60 p-6 rounded-2xl shadow-xl w-full max-w-md mt-56">
				<h2 className="text-xl font-semibold mb-4 text-center text-purple-700 dark:text-purple-300">
					Enter Website to Crawl
				</h2>
				<input
					type="text"
					value={extra_url}
					onChange={(e) => setextraUrl(e.target.value)}
					placeholder="https://example.com"
					className="w-full p-3 rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-purple-400 mb-3 dark:bg-gray-800 dark:text-white"
				/>
				{error && <p className="text-red-500 text-sm mb-2">{error}</p>}
				<button
					onClick={handleCrawl}
					className="w-full bg-purple-500 text-white font-semibold py-3 rounded-lg hover:bg-purple-600 transition duration-200"
					disabled={loading}
				>
					{loading ? 'Crawling...' : 'Crawl Website'}
				</button>
			</div>

			<button
				onClick={handleSkip}
				className={`
					w-full relative overflow-hidden
					bg-gradient-to-r from-purple-500 to-purple-600
					text-white font-semibold py-3 rounded-lg
					hover:from-purple-600 hover:to-purple-700
					active:from-purple-700 active:to-purple-800
					transition-all duration-200
					shadow-lg hover:shadow-purple-500/30
					mt-16
					${loading2 ? 'opacity-70 cursor-not-allowed' : ''}
				`}
				disabled={loading2}
				>
				{/* Ripple effect */}
				<span className="absolute inset-0 bg-white opacity-0 group-active:opacity-10 transition-opacity duration-300"></span>
				
				{/* Button content */}
				<span className="relative flex items-center justify-center gap-2">
					{loading2 ? (
					<>
						<svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
						<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Processing...
					</>
					) : (
					<>
						<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
						</svg>
						Skip and chat with me
					</>
					)}
				</span>
</button>
		</div>
	);
}
