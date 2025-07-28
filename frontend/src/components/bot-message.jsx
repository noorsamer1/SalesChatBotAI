import TextMessage from './text-message';
import ChartMessage from './chart-message';
import TableMessage from './table-message';

export default function BotMessage({ data }) {
    /**
     * Expects `data` to be an array of response blocks,
     * each block having a `type` like 'text', 'table', or 'chart'.
     */

    if (!Array.isArray(data)) {
        console.error('BotMessage expected an array but got:', data);
        return <span>⚠️ Invalid bot message format.</span>;
    }

    return (
        <div>
            {data.map((block, index) => {
                switch (block.type) {
                    case 'text':
                        return (
                            <div key={index} style={{ marginBottom: '10px' }}>
                                <TextMessage data={block} />
                            </div>
                        );
                    case 'table':
                        return (
                            <div key={index} style={{ marginBottom: '10px' }}>
                                <TableMessage data={block} />
                            </div>
                        );
                    case 'chart':
                        return (
                            <div key={index} style={{ marginBottom: '10px' }}>
                                <ChartMessage data={block} />
                            </div>
                        );
                    case 'smart_suggestions':
                        return (
                            <div key={index} style={{ marginBottom: '10px' }}>
                                <div className="smart-suggestions">
                                    <div className="suggestions-header">
                                        <span className="suggestions-icon">💡</span>
                                        <span className="suggestions-title">SMART SUGGESTIONS:</span>
                                    </div>
                                    <ul className="suggestions-list">
                                        {block.suggestions.map((suggestion, i) => (
                                            <li key={i} className="suggestion-item">{suggestion}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        );
                    default:
                        return (
                            <div key={index} style={{ marginBottom: '10px' }}>
                                <span>⚠️ Unsupported block type: {block.type}</span>
                            </div>
                        );
                }
            })}
        </div>
    );
}
