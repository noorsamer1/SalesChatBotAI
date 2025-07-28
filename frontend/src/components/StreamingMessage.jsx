import React, { useState, useEffect, useRef } from 'react';
import BotMessage from './bot-message.jsx';

export default function StreamingMessage({ 
  query, 
  conversationId, 
  onComplete, 
  onError 
}) {
  const [streamingText, setStreamingText] = useState("");
  const [currentStatus, setCurrentStatus] = useState("Connecting...");
  const [isStreaming, setIsStreaming] = useState(true);
  const [structuredData, setStructuredData] = useState([]);
  const [complexity, setComplexity] = useState(1);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    const token = localStorage.getItem("futuretec_token");
    if (!token) {
      onError("Authentication required");
      return;
    }

    // Create EventSource for streaming
    const streamUrl = `http://localhost:8845/chat/conversations/${conversationId}/messages/stream?content=${encodeURIComponent(query)}&token=${token}`;
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log("[STREAMING] Connection opened");
      setCurrentStatus("Connected to AI...");
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleStreamData(data);
      } catch (error) {
        console.error("[STREAMING] Parse error:", error);
      }
    };

    eventSource.onerror = (error) => {
      console.error("[STREAMING] EventSource error:", error);
      setCurrentStatus("Connection error");
      eventSource.close();
      onError("Streaming connection failed");
    };

    // Cleanup
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [query, conversationId]);

  const handleStreamData = (data) => {
    switch (data.type) {
      case "stream_start":
        setCurrentStatus(data.status);
        setComplexity(data.complexity || 1);
        break;

      case "text_token":
        // Filter out JSON completely - only show meaningful text
        const token = data.token;
        const accumulated = data.accumulated;
        
        // Skip if we're in JSON mode
        if (accumulated.includes('```json') || 
            accumulated.includes('[{') || 
            accumulated.includes('"type"') ||
            accumulated.includes('"template"') ||
            accumulated.includes('"value_code"') ||
            accumulated.includes('```')) {
          return; // Don't update streaming text
        }
        
        // Only show if it looks like meaningful text
        if (token && !token.includes('{') && !token.includes('}') && !token.includes('[') && !token.includes(']')) {
          setStreamingText(accumulated);
        }
        break;

      case "parsing_start":
        setCurrentStatus(data.status);
        // Clear the streaming text since we're now processing structured data
        setStreamingText("");
        break;

      case "text_complete":
        // Text block completed, add to structured data
        setStructuredData(prev => {
          const newData = [...prev];
          newData[data.index] = {
            type: "text",
            template: data.content
          };
          return newData;
        });
        break;

      case "sql_start":
        setCurrentStatus(`Executing ${data.data_type} query: ${data.title}`);
        setStructuredData(prev => {
          const newData = [...prev];
          newData[data.index] = {
            type: data.data_type,
            title: data.title,
            loading: true
          };
          return newData;
        });
        break;

      case "table_data":
        setStructuredData(prev => {
          const newData = [...prev];
          newData[data.index] = {
            ...newData[data.index],
            ...data.data,
            loading: false
          };
          return newData;
        });
        break;

      case "chart_data":
        setStructuredData(prev => {
          const newData = [...prev];
          newData[data.index] = {
            ...newData[data.index],
            ...data.data,
            loading: false
          };
          return newData;
        });
        break;

      case "sql_error":
        setStructuredData(prev => {
          const newData = [...prev];
          newData[data.index] = {
            type: "error",
            error: data.error,
            loading: false
          };
          return newData;
        });
        break;

      case "stream_complete":
        setCurrentStatus(data.status);
        setIsStreaming(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
        onComplete({
          text: streamingText,
          data: structuredData
        });
        break;

      case "stream_error":
        setCurrentStatus("Error occurred");
        setIsStreaming(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
        onError(data.error);
        break;

      default:
        console.log("[STREAMING] Unknown data type:", data.type);
    }
  };

  return (
    <div className="streaming-message">
      {/* Streaming status */}
      <div className="streaming-status">
        <div className="status-indicator">
          {isStreaming ? (
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : (
            <span className="complete-icon">✅</span>
          )}
        </div>
        <span className="status-text">{currentStatus}</span>
        {complexity > 1 && (
          <span className="complexity-badge">
            Complexity: {complexity}/5
          </span>
        )}
      </div>

      {/* Streaming text with cursor */}
      {streamingText && (
        <div className="streaming-text">
          <span>{streamingText}</span>
          {isStreaming && <span className="typing-cursor">|</span>}
        </div>
      )}

      {/* Structured data blocks */}
      <div className="structured-data">
        {structuredData.map((block, index) => {
          if (!block) return null;

          if (block.type === "text") {
            return (
              <div key={index} className="text-block">
                {block.template}
              </div>
            );
          }

          if (block.type === "error") {
            return (
              <div key={index} className="error-block">
                <span className="error-icon">❌</span>
                <span>Error: {block.error}</span>
              </div>
            );
          }

          if (block.loading) {
            return (
              <div key={index} className="loading-block">
                <div className="loading-skeleton">
                  <div className="skeleton-header"></div>
                  <div className="skeleton-content"></div>
                </div>
                <span>Loading {block.type}...</span>
              </div>
            );
          }

          // Render completed structured data using existing BotMessage
          return (
            <div key={index} className="data-block">
              <BotMessage data={[block]} />
            </div>
          );
        })}
      </div>
    </div>
  );
} 