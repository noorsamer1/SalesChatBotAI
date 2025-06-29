import React, { useState, useEffect, useRef } from 'react';
import './chat-ui.css';
import { v4 as uuidv4 } from 'uuid';
import TextMessage from './components/text-message';
import ChartMessage from './components/chart-message';
import TableMessage from './components/table-message';

// ########################################// ########################################
// # ⚠️ original before the components where made is available in Downloads Folder ⚠️
// ########################################// ########################################


export default function ChatUI() {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState("");
    const intervalRef = useRef(null);

    const handleSend = () => {
        const trimmed = inputValue.trim();
        if (!trimmed) return;
        setInputValue("");
        giveResponse(trimmed);
    };

    const giveResponse = async (userInput) => {
        setMessages(prev => [...prev, { id: uuidv4(), type: 'user', text: userInput }]);

        try {
            const res = await fetch("http://localhost:8000/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: userInput }),
            });

            const data = await res.json();
            console.log("Received from backend:", data);

            // Standardize message format for rendering
            const botMessage = {
                id: uuidv4(),
                type: 'bot',
                data,  // this will include text or chart or table
            };

            setMessages(prev => [...prev, botMessage]);

        } catch (err) {
            console.error("Backend error:", err);
            setMessages(prev => [...prev, {
                id: uuidv4(),
                type: 'bot',
                data: { type: 'text', text: "⚠️ Error: Could not connect to backend." }
            }]);
        }
    };


    useEffect(() => {
        return () => clearInterval(intervalRef.current);
    }, []);

    return (
        <div className='base'>
            <aside className="sidebar">
                <button
                    className="clear-memory"
                    onClick={() => setMessages([])}
                    aria-label="Clear chat history"
                >
                    ⟲ Clear History
                </button>
            </aside>

            <main className="main-container">
                <header className="header">
                    <h1>💬 Data Analysis Chatbot</h1>
                </header>

                <section className="main">
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            style={{
                                display: 'flex',
                                justifyContent: msg.type === 'user' ? 'flex-end' : 'flex-start',
                                margin: '10px 0',
                            }}
                        >
                            <div
                                style={{
                                    background: msg.type === 'user' ? '#2563eb' : '#374151',
                                    color: 'white',
                                    padding: '10px 15px',
                                    borderRadius: '12px',
                                    maxWidth: '60%',
                                    textAlign: 'left',
                                }}
                            >
                                {msg.type === 'user' ? (
                                    <span>{msg.text}</span>
                                ) : msg.data?.type === "chart" ? (
                                    <ChartMessage data={msg.data} />
                                ) : msg.data?.type === "table" ? (
                                    <TableMessage data={msg.data} />
                                ) : (
                                    <TextMessage data={msg.data} />
                                )}
                            </div>
                        </div>
                    ))}
                </section>


                <footer className="chatbot-input">
                    <div className="input-bar">
                        <input 
                            type="text"
                            className="message-input"
                            placeholder="Type your question..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
                            aria-label="Message input"
                        />
                        <button
                            className="send-button"
                            onClick={handleSend}
                            aria-label="Send message"
                        >
                            ▶
                        </button>
                    </div>
                </footer>
            </main>
        </div>
    );
}
