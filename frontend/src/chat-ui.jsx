import React, { 
    useState, 
    useEffect, 
    useRef 
} from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
} from '@tanstack/react-table';
import Plot from 'react-plotly.js';
import './chat-ui.css';
import { v4 as uuidv4 } from 'uuid';

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

            const botMessage = {
                id: uuidv4(),
                type: 'bot',
                data,
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
                                {msg.data?.type === "chart" && msg.data.chart_data ? (
                                    <Plot
                                        data={[
                                            msg.data.kind === "pie"
                                                ? {
                                                    type: "pie",
                                                    labels: msg.data.chart_data.labels,
                                                    values: msg.data.chart_data.values,
                                                }
                                                : {
                                                    type: msg.data.kind || "bar",
                                                    x: msg.data.chart_data.labels,
                                                    y: msg.data.chart_data.values,
                                                    mode: msg.data.kind === "line" ? "lines+markers" : undefined,
                                                },
                                        ]}
                                        layout={{
                                            title: msg.data.title || "Chart",
                                            ...(msg.data.kind !== "pie" && {
                                                xaxis: { title: msg.data.chart_data.x_axis || "" },
                                                yaxis: { title: msg.data.chart_data.y_axis || "" },
                                            }),
                                            autosize: true,
                                            plot_bgcolor: "#111827",
                                            paper_bgcolor: "#374151",
                                            font: { color: "#ffffff" },
                                        }}
                                        style={{ width: "100%", height: "100%" }}
                                    />
                                ) : msg.data?.type === "table" ? (
                                    <TableRender tableData={msg.data.table_data} title={msg.data.title} />
                                ) : (
                                    <span>{msg.data?.text || msg.text}</span>
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

// Fixed TableRender component to work with the corrected backend data structure
function TableRender({ tableData, title }) {
  if (!tableData || !tableData.columns || !tableData.rows) {
    return <div>No table data available</div>;
  }

  const columns = tableData.columns.map((col, idx) => ({
    accessorKey: `col_${idx}`,
    header: col,
    cell: info => info.getValue(),
  }));

  const data = tableData.rows.map(row =>
    Object.fromEntries(row.map((val, idx) => [`col_${idx}`, val]))
  );

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="table-container">
      <h3 style={{ marginBottom: '10px', fontWeight: 'bold' }}>{title}</h3>
      <table className="chatbot-table">
        <thead>
          {table.getHeaderGroups().map(headerGroup => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map(header => (
                <th key={header.id}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map(row => (
            <tr key={row.id}>
              {row.getVisibleCells().map(cell => (
                <td key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {tableData.paginated && (
        <div className="pagination">
          Page {tableData.page} of {tableData.total_pages} (Total: {tableData.total_rows} rows)
        </div>
      )}
    </div>
  );
}