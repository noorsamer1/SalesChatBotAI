import React, { useState, useEffect, useRef } from "react";
import "../styles/chat-ui.css";
import BotMessage from "./bot-message.jsx";
import AnalyticsDashboard from "./AnalyticsDashboard.jsx";

function generateChatName(idx) {
  return idx === 0 ? "New Chat" : `Chat ${idx + 1}`;
}

export default function ChatUI({ user, onLogout }) {
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const [messageCache, setMessageCache] = useState(new Map()); // Cache for messages
  const [showAnalytics, setShowAnalytics] = useState(false);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initial fetch of chats - make it more robust
  useEffect(() => {
    async function fetchChats() {
      const token = localStorage.getItem("futuretec_token");
      if (!token) {
        console.log("No token found, skipping chat fetch");
        return;
      }

      try {
        console.log("Fetching chats for user..."); // Debug log
        const res = await fetch("http://localhost:8845/chat/conversations", {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (!res.ok) {
          console.error("Failed to fetch chats, status:", res.status);
          if (res.status === 401) {
            // Token might be invalid, logout
            localStorage.removeItem("futuretec_token");
            onLogout();
            return;
          }
          throw new Error("Failed to fetch chats");
        }
        
        const data = await res.json();
        console.log("Fetched chats:", data); // Debug log
        setChats(data);
        if (data.length > 0) {
          setActiveChatId(data[0].id);
        } else {
          console.log("No conversations found for user");
        }
      } catch (err) {
        console.error("Error fetching chats:", err);
      }
    }
    
    // Add a small delay to ensure token is available
    setTimeout(fetchChats, 100);
  }, [user, onLogout]);

  // Load messages for active chat with proper caching and ordering
  useEffect(() => {
    if (!activeChatId) {
      setMessages([]);
      return;
    }
    
    // Check cache first
    if (messageCache.has(activeChatId)) {
      const cachedMessages = messageCache.get(activeChatId);
      setMessages(cachedMessages);
      return;
    }

    // Fetch from backend with proper error handling
    async function fetchMessages() {
      try {
        const res = await fetch(
          `http://localhost:8845/chat/conversations/${activeChatId}/messages`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
            },
          }
        );
        
        if (!res.ok) {
          if (res.status === 404) {
            // Chat doesn't exist or no messages
            setMessages([]);
            return;
          }
          throw new Error(`Failed to fetch messages: ${res.status}`);
        }
        
        const data = await res.json();
        
        // Transform backend messages to frontend format with proper ordering
        const transformedMessages = data
          .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)) // Sort by timestamp
          .map(msg => {
            let content = msg.content;
            
            // Handle bot messages that might have parsing issues
            if (msg.sender === "bot") {
              if (typeof content === "string") {
                try {
                  // Try to parse if it's a JSON string
                  content = JSON.parse(content);
                } catch (e) {
                  console.warn("Failed to parse bot message content:", content);
                  // If parsing fails, wrap as text message
                  content = [{ type: "text", text: content }];
                }
              } else if (!Array.isArray(content) && typeof content === "object" && content !== null) {
                // If it's an object but not an array, wrap it
                content = [content];
              } else if (!content) {
                // If content is null/undefined, provide fallback
                content = [{ type: "text", text: "Message content unavailable" }];
              }
            }
            
            return {
              id: msg.id,
              sender: msg.sender,
              content: content,
              timestamp: msg.timestamp
            };
          });
        
        console.log("Transformed messages for chat", activeChatId, ":", transformedMessages);
        
        // Update messages state
        setMessages(transformedMessages);
        
        // Cache the messages
        setMessageCache(prev => new Map(prev.set(activeChatId, transformedMessages)));
        
      } catch (err) {
        console.error("Error loading messages:", err);
        setMessages([]);
        
        // Cache empty array to prevent repeated failed requests
        setMessageCache(prev => new Map(prev.set(activeChatId, [])));
      }
    }
    
    fetchMessages();
  }, [activeChatId]);

  // Update cache when messages change
  useEffect(() => {
    if (activeChatId && messages.length >= 0) {
      setMessageCache(prev => new Map(prev.set(activeChatId, messages)));
    }
  }, [messages, activeChatId]);

  // Manual refresh chats function for debugging
//   async function handleRefreshChats() {
//     const token = localStorage.getItem("futuretec_token");
//     if (!token) {
//       alert("No token found");
//       return;
//     }

//     try {
//       console.log("Manually refreshing chats...");
//       const res = await fetch("http://localhost:8845/chat/conversations", {
//         headers: { Authorization: `Bearer ${token}` }
//       });
      
//       if (!res.ok) {
//         console.error("Refresh failed, status:", res.status);
//         alert(`Refresh failed: ${res.status}`);
//         return;
//       }
      
//       const data = await res.json();
//       console.log("Manually fetched chats:", data);
//       setChats(data);
      
//       // Clear message cache
//       setMessageCache(new Map());
      
//       if (data.length > 0) {
//         setActiveChatId(data[0].id);
//       }
//     } catch (err) {
//       console.error("Error refreshing chats:", err);
//       alert("Error refreshing chats");
//     }
//   }

  // Create new chat by calling backend to get real conversation ID
  async function handleNewChat() {
    try {
      const res = await fetch("http://localhost:8845/chat/conversations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
        },
        body: JSON.stringify({ title: "New Chat" }),
      });
      if (!res.ok) throw new Error("Failed to create new chat");
      const data = await res.json();
      const newChat = { id: data.id, title: data.title, created_at: new Date().toISOString() };
      
      setChats(prevChats => [newChat, ...prevChats]);
      setActiveChatId(newChat.id);
      setMessages([]);
      
      // Initialize empty cache for new chat
      setMessageCache(prev => new Map(prev.set(newChat.id, [])));
      
    } catch (err) {
      console.error("Failed to create new chat", err);
      alert("Error: Could not create a new chat.");
    }
  }

  // Delete chat with confirm
  async function handleDeleteChat(chatId) {
    if (!window.confirm("Delete this chat?")) return;
    
    try {
      // Delete from backend first
      const res = await fetch(`http://localhost:8845/chat/conversations/${chatId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
        },
      });
      
      if (!res.ok) {
        throw new Error("Failed to delete chat from server");
      }
      
      // Remove from cache
      setMessageCache(prev => {
        const newCache = new Map(prev);
        newCache.delete(chatId);
        return newCache;
      });
      
      // If backend deletion successful, update frontend
      setChats(prevChats => {
        const updated = prevChats.filter((c) => c.id !== chatId);
        
        // Update active chat if we're deleting the current one
        if (activeChatId === chatId) {
          const nextChat = updated[0];
          setActiveChatId(nextChat?.id ?? null);
          setMessages(nextChat ? messageCache.get(nextChat.id) || [] : []);
        }
        
        return updated;
      });
      
    } catch (err) {
      console.error("Error deleting chat:", err);
      alert("Error: Could not delete chat. Please try again.");
    }
  }

  // Select chat from sidebar with proper state management
  function handleSelectChat(chatId) {
    if (chatId === activeChatId) return; // No need to reload same chat
    
    setActiveChatId(chatId);
    
    // Load messages from cache or trigger useEffect to fetch
    if (messageCache.has(chatId)) {
      setMessages(messageCache.get(chatId));
    } else {
      setMessages([]); // Will trigger fetch in useEffect
    }
  }

  // Typing indicator simulation
  const showTypingIndicator = () => {
    setIsTyping(true);
    setTimeout(() => setIsTyping(false), 3000);
  };

  // Send user message to backend, handle bot reply
  async function handleSend() {
    const trimmed = inputValue.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setInputValue("");

    // Add user message locally with temporary ID for React keys
    const tempUserMsgId = `temp-user-${Date.now()}`;
    const userMessage = { 
      id: tempUserMsgId, 
      sender: "user", 
      content: trimmed,
      timestamp: new Date().toISOString()
    };
    
    setMessages((prev) => [...prev, userMessage]);

    // Show typing indicator
    setIsTyping(true);

    try {
      // Add 60-second timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);

      const res = await fetch(
        `http://localhost:8845/chat/conversations/${activeChatId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
          },
          body: JSON.stringify({ content: trimmed }),
          signal: controller.signal
        }
      );
      
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Server error: ${res.status} - ${errorText}`);
      }
      
      const data = await res.json();
      
      // Remove temp user message and add real ones with backend IDs
      setMessages((prev) => {
        const withoutTemp = prev.filter(msg => msg.id !== tempUserMsgId);
        
        // Add real user message with backend ID
        const realUserMessage = {
          id: data.user_message.id,
          sender: "user",
          content: data.user_message.content,
          timestamp: data.user_message.timestamp
        };
        
        // Add real bot message with backend ID
        const realBotMessage = {
          id: data.bot_message.id,
          sender: "bot",
          content: data.bot_message.content,
          timestamp: data.bot_message.timestamp
        };
        
        // Sort messages by timestamp to maintain order
        const newMessages = [...withoutTemp, realUserMessage, realBotMessage]
          .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        return newMessages;
      });

      // Update chat title if this was the first message
      const currentChat = chats.find(c => c.id === activeChatId);
      if (currentChat && (currentChat.title === "New Chat" || !currentChat.title)) {
        setChats(prev => prev.map(c => 
          c.id === activeChatId 
            ? { ...c, title: data.bot_message.content?.[0]?.template?.substring(0, 50) || "Chat" }
            : c
        ));
      }

    } catch (err) {
      console.error("Error sending message:", err);
      
      // Remove temp user message and show error
      setMessages((prev) => {
        const withoutTemp = prev.filter(msg => msg.id !== tempUserMsgId);
        
        let errorMsg = "⚠️ Error: Could not connect to backend.";
        
        if (err.name === 'AbortError') {
          errorMsg = "⚠️ Request timed out. Please try a simpler question.";
        } else if (err.message.includes('Server error')) {
          errorMsg = `⚠️ ${err.message}`;
        }
        
        return [...withoutTemp, {
          id: `error-${Date.now()}`,
          sender: "bot",
          content: [{ type: "text", text: errorMsg }],
          timestamp: new Date().toISOString()
        }];
      });
    } finally {
      setLoading(false);
      setIsTyping(false);
    }
  }

  // Handle logout properly
  async function handleLogout() {
    try {
      // Call backend logout endpoint
      const res = await fetch("http://localhost:8845/auth/logout", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
        },
      });
      
      if (res.ok) {
        // Clear token from localStorage
        localStorage.removeItem("futuretec_token");
        
        // Clear all chat state
        setChats([]);
        setMessages([]);
        setActiveChatId(null);
        setMessageCache(new Map());
        
        // Call parent logout handler
        if (onLogout) {
          onLogout();
        } else {
          window.location.href = "/";
        }
      } else {
        console.error("Logout failed on backend");
        // Still proceed with frontend logout
        localStorage.removeItem("futuretec_token");
        if (onLogout) {
          onLogout();
        } else {
          window.location.href = "/";
        }
      }
    } catch (err) {
      console.error("Error during logout:", err);
      // Still proceed with frontend logout even if backend fails
      localStorage.removeItem("futuretec_token");
      if (onLogout) {
        onLogout();
      } else {
        window.location.href = "/";
      }
    }
  }

  // Send on Enter key press
  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // Get active chat title
  const getActiveChatTitle = () => {
    const activeChat = chats.find(c => c.id === activeChatId);
    return activeChat?.title || "Sales AI Chatbot";
  };

  return (
    <div className="base">
      <aside className="sidebar">
        <div className="sidebar-header">
          <img
            src="/futuretec-logo.png"
            alt="FutureTec"
            className="logo"
          />
          <div className="user-badge" title={user}>
            <span className="user-icon">👤</span>
            <span className="username">{user}</span>
          </div>
        </div>
        
        <div className="sidebar-controls">
          <button className="clear-memory" onClick={handleNewChat}>
            <span className="btn-icon">✨</span>
            New Chat
          </button>
          
          <button 
            className={`clear-memory analytics-btn ${showAnalytics ? 'active' : ''}`} 
            onClick={() => setShowAnalytics(!showAnalytics)}
          >
            <span className="btn-icon">📊</span>
            Analytics Dashboard
          </button>
          {/* <button 
            className="clear-memory refresh-btn" 
            onClick={handleRefreshChats}
            title="Refresh conversations"
          >
            <span className="btn-icon">🔄</span>
            Refresh
          </button> */}
        </div>

        <div className="chat-list">
          {chats.map((chat) => (
            <div
              key={chat.id}
              className={`chat-list-item${chat.id === activeChatId ? " selected" : ""}`}
              onClick={() => handleSelectChat(chat.id)}
            >
              <div className="chat-info">
                <span className="chat-icon">💬</span>
                <span className="chat-title">
                  {chat.title}
                </span>
              </div>
              <button
                className="delete-chat"
                title="Delete chat"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteChat(chat.id);
                }}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
        
        <div className="sidebar-footer">
          <button className="logout-btn" onClick={handleLogout}>
            <span className="btn-icon">🚪</span>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-container">
        {showAnalytics ? (
          <AnalyticsDashboard />
        ) : (
          <>
            <header className="header">
              <div className="header-content">
                <span className="header-icon">🤖</span>
                <div className="header-text">
                  <h1 className="header-title">{getActiveChatTitle()}</h1>
                  <p className="header-subtitle">
                    Powered by Joud AI • {isTyping ? "Typing..." : "Ready to help"}
                  </p>
                </div>
              </div>
            </header>

        <section className="main">
          {messages.length === 0 && (
            <div className="welcome-message">
              <div className="welcome-content">
                <h2>Welcome to Joud Sales AI</h2>
                <p>Ask me anything about your sales data, analytics, or performance metrics.</p>
                <div className="quick-actions">
                  <button 
                    className="quick-action-btn"
                    onClick={() => setInputValue("Show me top 5 customers by sales")}
                  >
                    📊 Top Customers
                  </button>
                  <button 
                    className="quick-action-btn"
                    onClick={() => setInputValue("Generate sales report for this month")}
                  >
                    📈 Sales Report
                  </button>
                  <button 
                    className="quick-action-btn"
                    onClick={() => setInputValue("Show revenue trends over time")}
                  >
                    💰 Revenue Trends
                  </button>
                </div>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={`${msg.id}-${msg.timestamp}`} // More unique key
              className={`message ${msg.sender === "user" ? "user" : "bot"}`}
            >
              <div className="message-avatar">
                {msg.sender === "user" ? "👤" : "🤖"}
              </div>
              <div className="bubble">
                {msg.sender === "user" ? (
                  <span className="user-message">{msg.content}</span>
                ) : (
                  <BotMessage data={msg.content} />
                )}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="message bot typing-indicator">
              <div className="message-avatar">🤖</div>
              <div className="bubble">
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </section>

                  <footer className="chatbot-input">
            <div className="input-bar">
              <input
                type="text"
                className="message-input"
                placeholder={loading ? "Processing your request..." : "Ask me about sales data, analytics, or reports..."}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                aria-label="Message input"
                autoComplete="off"
              />
              <button 
                className="send-button"
                onClick={handleSend}
                aria-label="Send message"
                disabled={loading || !inputValue.trim()}
              >
                {loading ? "⏳" : "🚀"}
              </button>
            </div>
          </footer>
          </>
        )}
      </main>
    </div>
  );
}