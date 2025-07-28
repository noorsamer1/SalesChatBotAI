import React, { useState, useEffect, useRef } from "react";
import "../styles/chat-ui.css";
import BotMessage from "./bot-message.jsx";
import StreamingMessage from "./StreamingMessage.jsx"; // 🆕 Import streaming component
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
  const [isWelcomeMode, setIsWelcomeMode] = useState(true); // 🆕 NEW: Welcome state like ChatGPT
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [chatToDelete, setChatToDelete] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false); // 🆕 Prevent duplicate submissions
  const [isStreaming, setIsStreaming] = useState(false); // 🆕 Streaming state
  const [streamingQuery, setStreamingQuery] = useState(""); // 🆕 Current streaming query
  const [useStreaming, setUseStreaming] = useState(false); // 🆕 DISABLE streaming temporarily
  const [isMobile, setIsMobile] = useState(false); // 📱 Mobile detection
  const [sidebarOpen, setSidebarOpen] = useState(false); // 📱 Mobile sidebar state

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // 📱 Mobile detection and responsive handling
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      // Auto-close sidebar on desktop
      if (!mobile) {
        setSidebarOpen(false);
      }
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

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
            console.log("Unauthorized, redirecting to login");
            localStorage.removeItem("futuretec_token");
            window.location.href = "/";
            return;
          }
          throw new Error(`HTTP ${res.status}`);
        }
        
        const data = await res.json();
        console.log("Fetched chats:", data.length); // Debug log
        setChats(data);
        
        // Only set welcome mode if no chats exist
        if (data.length === 0) {
          setIsWelcomeMode(true);
        }
      } catch (error) {
        console.error("Error fetching chats:", error);
      }
    }
    
    fetchChats();
  }, []);

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

 

  // Always create a new chat in the backend when New Chat is clicked
  async function handleNewChat() {
    try {
      const res = await fetch("http://localhost:8845/chat/conversations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
        },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error("Failed to create new chat");
      const data = await res.json();
      const newChat = { id: data.id, title: data.title || "New Chat", created_at: new Date().toISOString() };
      setChats(prevChats => [newChat, ...prevChats]);
      setActiveChatId(newChat.id);
      setMessages([]);
      setIsWelcomeMode(false);
    } catch (err) {
      alert("Error: Could not create a new chat.");
    }
  }

  // Delete chat with confirm
  async function handleDeleteChat(chatId) {
    // Show custom modal instead of browser confirm
    setChatToDelete(chatId);
    setShowDeleteModal(true);
  }

  // Confirm delete from modal
  async function confirmDeleteChat() {
    if (!chatToDelete) return;
    
    try {
      // Delete from backend first
      const res = await fetch(`http://localhost:8845/chat/conversations/${chatToDelete}`, {
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
        newCache.delete(chatToDelete);
        return newCache;
      });
      
      // If backend deletion successful, update frontend
      setChats(prevChats => {
        const updated = prevChats.filter((c) => c.id !== chatToDelete);
        
        // Update active chat if we're deleting the current one
        if (activeChatId === chatToDelete) {
          const nextChat = updated[0];
          setActiveChatId(nextChat?.id ?? null);
          setMessages(nextChat ? messageCache.get(nextChat.id) || [] : []);
          // If no chats left, go to welcome mode
          if (updated.length === 0) {
            setIsWelcomeMode(true);
          }
        }
        
        return updated;
      });
      
      // Close modal
      setShowDeleteModal(false);
      setChatToDelete(null);
      
    } catch (err) {
      console.error("Error deleting chat:", err);
      alert("Error: Could not delete chat. Please try again.");
      setShowDeleteModal(false);
      setChatToDelete(null);
    }
  }

  // Cancel delete from modal
  function cancelDeleteChat() {
    setShowDeleteModal(false);
    setChatToDelete(null);
  }

  // Select and load a chat
  async function handleSelectChat(chatId) {
    if (chatId === activeChatId) return;
    
    setActiveChatId(chatId);
    setIsWelcomeMode(false); // 🆕 Exit welcome mode when selecting a chat
    setLoading(true);

    // Use cached messages if available
    if (messageCache.has(chatId)) {
      setMessages(messageCache.get(chatId));
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(
        `http://localhost:8845/chat/conversations/${chatId}/messages`,
        {
          headers: { Authorization: `Bearer ${localStorage.getItem("futuretec_token")}` }
        }
      );
      if (!res.ok) throw new Error("Failed to load messages");
      const data = await res.json();
      
      setMessages(data);
      
      // Cache the messages
      setMessageCache(prev => new Map(prev.set(chatId, data)));
      
    } catch (err) {
      console.error("Failed to load messages", err);
      alert("Error: Could not load messages for this chat.");
      setMessages([]);
    }
    setLoading(false);
  }

  // 🌊 NEW: Streaming message handler
  async function handleStreamingSend(trimmed) {
    let chatId = activeChatId;
    
    // Create chat if needed
    if (!chatId) {
      try {
        const res = await fetch("http://localhost:8845/chat/conversations", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
          },
          body: JSON.stringify({}),
        });
        if (!res.ok) throw new Error("Failed to create new chat");
        const data = await res.json();
        const newChat = { id: data.id, title: data.title || "New Chat", created_at: new Date().toISOString() };
        setChats(prevChats => [newChat, ...prevChats]);
        setActiveChatId(newChat.id);
        setMessages([]);
        setIsWelcomeMode(false);
        chatId = newChat.id;
      } catch (err) {
        alert("Error: Could not create a new chat.");
        setIsSubmitting(false);
        return;
      }
    } else {
      setIsWelcomeMode(false);
    }
    
    // Clear input and add user message
    setInputValue("");
    const userMessage = { 
      id: `user-${Date.now()}`, 
      sender: "user", 
      content: trimmed,
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);
    
    // Start streaming
    setIsStreaming(true);
    setStreamingQuery(trimmed);
    setIsSubmitting(false); // Release lock for streaming
  }

  // Handle streaming completion
  function handleStreamingComplete(result) {
    setIsStreaming(false);
    setStreamingQuery("");
    
    // Add bot message to the conversation
    const botMessage = {
      id: `bot-${Date.now()}`,
      sender: "bot",
      content: result.data || result.text,
      timestamp: new Date().toISOString()
    };
    
    setMessages((prev) => [...prev, botMessage]);
  }

  // Handle streaming error
  function handleStreamingError(error) {
    setIsStreaming(false);
    setStreamingQuery("");
    setIsSubmitting(false);
    
    console.error("Streaming error:", error);
    alert(`Streaming failed: ${error}`);
  }

  // Auto-create a chat if needed before sending a message
  async function handleSend() {
    const trimmed = inputValue.trim();
    if (!trimmed || loading || isSubmitting || isStreaming) return; // 🆕 Prevent duplicate submissions
    
    // 🆕 Lock submission to prevent duplicates
    setIsSubmitting(true);
    
    // 🌊 NEW: Use streaming if enabled
    if (useStreaming) {
      await handleStreamingSend(trimmed);
      return;
    }
    
    let chatId = activeChatId;
    if (!chatId) {
      // No active chat, create one first
      try {
        const res = await fetch("http://localhost:8845/chat/conversations", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
          },
          body: JSON.stringify({}),
        });
        if (!res.ok) throw new Error("Failed to create new chat");
        const data = await res.json();
        const newChat = { id: data.id, title: data.title || "New Chat", created_at: new Date().toISOString() };
        setChats(prevChats => [newChat, ...prevChats]);
        setActiveChatId(newChat.id);
        setMessages([]);
        setIsWelcomeMode(false);
        chatId = newChat.id;
      } catch (err) {
        alert("Error: Could not create a new chat.");
        setIsSubmitting(false); // 🆕 Release lock on error
        return;
      }
    } else {
      setIsWelcomeMode(false);
    }
    setLoading(true);
    setInputValue("");
    const tempUserMsgId = `temp-user-${Date.now()}`;
    const userMessage = { 
      id: tempUserMsgId, 
      sender: "user", 
      content: trimmed,
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);
    try {
      const res = await fetch(
        `http://localhost:8845/chat/conversations/${chatId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("futuretec_token")}`,
          },
          body: JSON.stringify({ content: trimmed })
        }
      );
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Server error: ${res.status} - ${errorText}`);
      }
      const data = await res.json();
      setMessages((prev) => {
        const withoutTemp = prev.filter(msg => msg.id !== tempUserMsgId);
        return [
          ...withoutTemp,
          data.user_message,
          data.bot_message
        ];
      });
      if (data.conversation_title) {
        setChats(prevChats => 
          prevChats.map(chat => 
            chat.id === chatId 
              ? { ...chat, title: data.conversation_title }
              : chat
          )
        );
      }
      setIsTyping(false);
      setLoading(false);
      setIsSubmitting(false); // 🆕 Release lock on success
    } catch (err) {
      setIsTyping(false);
      setLoading(false);
      setIsSubmitting(false); // 🆕 Release lock on error
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
    if (e.key === "Enter" && !e.shiftKey && !isSubmitting) { // 🆕 Check submission lock
      e.preventDefault();
      handleSend();
    }
  }

  // Get active chat title
  const getActiveChatTitle = () => {
    const activeChat = chats.find(c => c.id === activeChatId);
    return activeChat?.title || "Sales AI Chatbot";
  };

  // Add this helper to send a suggestion immediately
  function handleSuggestionSend(suggestion) {
    setInputValue(suggestion);
    setTimeout(() => {
      handleSend();
    }, 0);
  }

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
          
          <button 
            className={`clear-memory ${useStreaming ? 'active' : ''}`} 
            onClick={() => setUseStreaming(!useStreaming)}
            title="Toggle streaming mode"
          >
            <span className="btn-icon">🌊</span>
            {useStreaming ? 'Streaming ON' : 'Streaming OFF'}
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
        ) : isWelcomeMode ? (
          // Welcome Mode
          <div className="welcome-container">
            <div className="welcome-content">
              <div className="welcome-header">
                <div className="welcome-icon">🤖</div>
                <h1 className="welcome-title">FutureTec Sales AI</h1>
                <p className="welcome-subtitle">
                  Powered by advanced AI • Ready to analyze your sales data
                </p>
              </div>
              
              <div className="welcome-features">
                <div className="feature-grid">
                  <div className="feature-card">
                    <span className="feature-icon">📊</span>
                    <h3>Smart Analytics</h3>
                    <p>Get instant insights from your sales data</p>
                  </div>
                  <div className="feature-card">
                    <span className="feature-icon">🎨</span>
                    <h3>Smart Visualization</h3>
                    <p>Auto-generated charts and tables</p>
                  </div>
                  <div className="feature-card">
                    <span className="feature-icon">⚡</span>
                    <h3>Real-time Streaming</h3>
                    <p>Progressive response loading</p>
                  </div>
                  <div className="feature-card">
                    <span className="feature-icon">🧠</span>
                    <h3>Business Intelligence</h3>
                    <p>Proactive insights and alerts</p>
                  </div>
                </div>
              </div>
              
              <div className="welcome-suggestions">
                <h3>Try asking:</h3>
                <div className="suggestion-chips">
                  <button 
                    className="suggestion-chip"
                    onClick={() => handleSuggestionSend("Show me division sales breakdown")}
                  >
                    📊 Division Sales Breakdown
                  </button>
                  <button 
                    className="suggestion-chip"
                    onClick={() => handleSuggestionSend("Top 10 customers by revenue")}
                  >
                    👥 Top Customers
                  </button>
                  <button 
                    className="suggestion-chip"
                    onClick={() => handleSuggestionSend("Sales performance by month")}
                  >
                    📈 Monthly Performance
                  </button>
                  <button 
                    className="suggestion-chip"
                    onClick={() => handleSuggestionSend("Product analysis with profit margins")}
                  >
                    🏷️ Product Analysis
                  </button>
                </div>
              </div>
            </div>
            
            {/* Always show the chat input bar, centered in welcome mode */}
            <div className="chatbot-input welcome-input-center">
              <div className="input-bar">
                <textarea
                  className="message-input"
                  placeholder="Ask me about your sales data, analytics, or reports..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                  aria-label="Message input"
                  autoComplete="off"
                  rows={1}
                  style={{ resize: "none" }}
                />
                <button
                  className="send-button"
                  onClick={handleSend}
                  aria-label="Send message"
                  disabled={loading || isSubmitting || !inputValue.trim()} // 🆕 Include isSubmitting
                >
                  {loading || isSubmitting ? "⏳" : "🚀"} {/* 🆕 Show loading for both states */}
                </button>
              </div>
            </div>
          </div>
        ) : (
          // Chat Mode
          <>
            <header className="header">
              <div className="header-content">
                <span className="header-icon">🤖</span>
                <div className="header-text">
                  <h1 className="header-title">{getActiveChatTitle()}</h1>
                  <p className="header-subtitle">
                    Powered by FutureTec AI • {isTyping ? "Typing..." : "Ready to help"}
                  </p>
                </div>
              </div>
            </header>

            <section className="main">
              {messages.map((msg) => (
                <div
                  key={`${msg.id}-${msg.timestamp}`}
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
              
              {/* 🌊 NEW: Streaming component */}
              {isStreaming && streamingQuery && activeChatId && (
                <div className="message bot">
                  <div className="message-avatar">🤖</div>
                  <div className="bubble">
                    <StreamingMessage
                      query={streamingQuery}
                      conversationId={activeChatId}
                      onComplete={handleStreamingComplete}
                      onError={handleStreamingError}
                    />
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </section>

            {/* Always show the chat input bar at the bottom in chat mode */}
            <div className="chatbot-input">
              <div className="input-bar">
                <textarea
                  className="message-input"
                  placeholder="Ask me about your sales data, analytics, or reports..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                  aria-label="Message input"
                  autoComplete="off"
                  rows={1}
                  style={{ resize: "none" }}
                />
                <button
                  className="send-button"
                  onClick={handleSend}
                  aria-label="Send message"
                  disabled={loading || isSubmitting || !inputValue.trim()} // 🆕 Include isSubmitting
                >
                  {loading || isSubmitting ? "⏳" : "🚀"} {/* 🆕 Show loading for both states */}
                </button>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Confirm Deletion</h2>
            <p>Are you sure you want to delete this chat?</p>
            <div className="modal-actions">
              <button className="modal-btn cancel-btn" onClick={cancelDeleteChat}>
                Cancel
              </button>
              <button className="modal-btn confirm-btn" onClick={confirmDeleteChat}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}