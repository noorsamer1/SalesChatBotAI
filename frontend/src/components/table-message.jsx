import React from 'react';

export default function TableMessage({ data }) {
    const { title, columns: columnNames, rows } = data;

    if (!columnNames || !rows) {
        return (
            <div style={{ 
                padding: '20px', 
                background: '#f59e0b',
                borderRadius: '8px',
                color: '#ffffff'
            }}>
                ⚠️ No table data available.
            </div>
        );
    }

    // Simple HTML table instead of TanStack (to avoid import issues)
    return (
        <div style={{ marginBottom: '20px' }}>
            <h4 style={{ marginBottom: '10px', color: '#ffffff' }}>{title}</h4>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ 
                    width: "100%", 
                    borderCollapse: "collapse", 
                    backgroundColor: '#1f2937',
                    color: '#ffffff'
                }}>
                    <thead>
                        <tr style={{ backgroundColor: '#374151' }}>
                            {columnNames.map((colName, idx) => (
                                <th
                                    key={idx}
                                    style={{ 
                                        border: "1px solid #4b5563", 
                                        padding: "12px 8px", 
                                        textAlign: "left",
                                        fontWeight: 'bold'
                                    }}
                                >
                                    {colName}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row, rowIdx) => (
                            <tr 
                                key={rowIdx}
                                style={{ 
                                    backgroundColor: rowIdx % 2 === 0 ? '#1f2937' : '#111827' 
                                }}
                            >
                                {row.map((cell, cellIdx) => (
                                    <td 
                                        key={cellIdx} 
                                        style={{ 
                                            border: "1px solid #4b5563", 
                                            padding: "8px",
                                            textAlign: typeof cell === 'number' ? 'right' : 'left'
                                        }}
                                    >
                                        {cell === null || cell === undefined ? '' : String(cell)}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}