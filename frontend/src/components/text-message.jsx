export default function TextMessage({ data, fallbackText }) {
    const content = data?.template || data?.text || fallbackText || "⚠️ No content";
    const isStreaming = data?.streaming === true;
    
    return (
        <span 
            className={isStreaming ? "text-streaming streaming-text" : ""}
            data-streaming={isStreaming}
        >
            {content}
            {isStreaming && (
                <span 
                    className="streaming-cursor"
                    style={{
                        display: 'inline-block',
                        width: '2px',
                        height: '1.2em',
                        background: '#06b6d4',
                        marginLeft: '2px',
                        animation: 'blinkingCursor 1.2s infinite',
                        verticalAlign: 'text-top'
                    }}
                />
            )}
        </span>
    );
}
