import React, { useState } from 'react';

export default function TableMessage({ data }) {
    const { title, columns: columnNames, rows } = data;
    const [showAll, setShowAll] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [rowsPerPage, setRowsPerPage] = useState(10);

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

    // Helper function to get the maximum value for progress bars
    const getMaxValue = (columnIndex) => {
        return Math.max(...rows.map(row => {
            const value = parseFloat(String(row[columnIndex]).replace(/,/g, ''));
            return isNaN(value) ? 0 : value;
        }));
    };

    // Helper function to determine if column is numeric
    const isNumericColumn = (columnIndex) => {
        const sampleValue = rows[0]?.[columnIndex];
        if (!sampleValue) return false;
        const cleanValue = String(sampleValue).replace(/,/g, '');
        return !isNaN(parseFloat(cleanValue));
    };

    // Helper function to format ranking
    const getRankIcon = (index) => {
        switch(index) {
            case 0: return '🥇';
            case 1: return '🥈';
            case 2: return '🥉';
            default: return `${index + 1}.`;
        }
    };

    // Enhanced HTML table with modern styling
    return (
        <div style={{ marginBottom: '20px' }}>
            <h4 style={{ 
                marginBottom: '15px', 
                color: '#ffffff',
                fontSize: '18px',
                fontWeight: '600'
            }}>
                {title}
            </h4>
            
            <div style={{ 
                overflowX: 'auto',
                borderRadius: '12px',
                border: '1px solid #374151',
                background: 'linear-gradient(135deg, #1f2937 0%, #111827 100%)'
            }}>
                <table style={{ 
                    width: "100%", 
                    borderCollapse: "collapse", 
                    backgroundColor: 'transparent',
                    color: '#ffffff'
                }}>
                    <thead>
                        <tr style={{ 
                            background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                        }}>
                            <th style={{
                                padding: "12px 16px",
                                textAlign: "center",
                                fontWeight: 'bold',
                                fontSize: '14px',
                                color: '#ffffff',
                                borderRight: '1px solid rgba(255,255,255,0.1)'
                            }}>
                                #
                            </th>
                            {columnNames.map((colName, idx) => (
                                <th
                                    key={idx}
                                    style={{ 
                                        padding: "12px 16px", 
                                        textAlign: isNumericColumn(idx) ? "right" : "left",
                                        fontWeight: 'bold',
                                        fontSize: '14px',
                                        color: '#ffffff',
                                        borderRight: idx < columnNames.length - 1 ? '1px solid rgba(255,255,255,0.1)' : 'none'
                                    }}
                                >
                                    {colName.replace(/_/g, ' ').toUpperCase()}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {(() => {
                            // Calculate pagination
                            const totalRows = rows.length;
                            const startIndex = showAll ? 0 : (currentPage - 1) * rowsPerPage;
                            const endIndex = showAll ? totalRows : Math.min(startIndex + rowsPerPage, totalRows);
                            const displayRows = rows.slice(startIndex, endIndex);
                            
                            return displayRows.map((row, displayIdx) => {
                                const actualRowIdx = showAll ? displayIdx : startIndex + displayIdx;
                                const isTopPerformer = actualRowIdx < 3;
                            return (
                                <tr 
                                    key={actualRowIdx}
                                    style={{ 
                                        backgroundColor: actualRowIdx % 2 === 0 ? 'rgba(31, 41, 55, 0.8)' : 'rgba(17, 24, 39, 0.8)',
                                        borderBottom: '1px solid #374151',
                                        transition: 'all 0.2s ease',
                                        cursor: 'default'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.backgroundColor = 'rgba(79, 70, 229, 0.1)';
                                        e.currentTarget.style.transform = 'scale(1.01)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.backgroundColor = actualRowIdx % 2 === 0 ? 'rgba(31, 41, 55, 0.8)' : 'rgba(17, 24, 39, 0.8)';
                                        e.currentTarget.style.transform = 'scale(1)';
                                    }}
                                >
                                    {/* Ranking Column */}
                                    <td style={{
                                        padding: "12px 16px",
                                        textAlign: "center",
                                        fontWeight: 'bold',
                                        fontSize: '16px',
                                        borderRight: '1px solid #374151',
                                        background: isTopPerformer ? 'linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(217, 119, 6, 0.2) 100%)' : 'transparent'
                                    }}>
                                        {getRankIcon(actualRowIdx)}
                                    </td>
                                    
                                    {/* Data Columns */}
                                    {row.map((cell, cellIdx) => {
                                        const isNumeric = isNumericColumn(cellIdx);
                                        const maxValue = isNumeric ? getMaxValue(cellIdx) : 0;
                                        const numericValue = isNumeric ? parseFloat(String(cell).replace(/,/g, '')) : 0;
                                        const percentage = isNumeric && maxValue > 0 ? (numericValue / maxValue) * 100 : 0;
                                        
                                        return (
                                            <td 
                                                key={cellIdx} 
                                                style={{ 
                                                    padding: "12px 16px",
                                                    textAlign: isNumeric ? 'right' : 'left',
                                                    borderRight: cellIdx < row.length - 1 ? '1px solid #374151' : 'none',
                                                    position: 'relative',
                                                    fontWeight: isNumeric ? '600' : '400',
                                                    fontSize: '14px'
                                                }}
                                            >
                                                {/* Progress Bar Background for Numeric Values */}
                                                {isNumeric && (
                                                    <div style={{
                                                        position: 'absolute',
                                                        top: 0,
                                                        left: 0,
                                                        right: 0,
                                                        bottom: 0,
                                                        background: `linear-gradient(to right, rgba(79, 70, 229, 0.15) 0%, rgba(79, 70, 229, 0.15) ${percentage}%, transparent ${percentage}%, transparent 100%)`,
                                                        borderRadius: '4px'
                                                    }} />
                                                )}
                                                
                                                {/* Cell Content */}
                                                <span style={{ 
                                                    position: 'relative', 
                                                    zIndex: 1,
                                                    color: isNumeric ? '#e5e7eb' : '#d1d5db'
                                                }}>
                                                    {cell === null || cell === undefined ? '' : String(cell)}
                                                </span>
                                                
                                                                                                 {/* Performance Indicator for Top Values */}
                                                 {isNumeric && actualRowIdx === 0 && (
                                                     <span style={{
                                                         marginLeft: '8px',
                                                         fontSize: '12px',
                                                         color: '#10b981',
                                                         fontWeight: 'bold'
                                                     }}>
                                                         👑
                                                     </span>
                                                 )}
                                                 
                                                 {/* Risk Status Indicators for Business Intelligence */}
                                                 {!isNumeric && String(cell).includes('🔴') && (
                                                     <span style={{
                                                         marginLeft: '8px',
                                                         padding: '2px 6px',
                                                         backgroundColor: 'rgba(239, 68, 68, 0.2)',
                                                         borderRadius: '4px',
                                                         fontSize: '10px',
                                                         fontWeight: 'bold',
                                                         border: '1px solid rgba(239, 68, 68, 0.5)'
                                                     }}>
                                                         HIGH RISK
                                                     </span>
                                                 )}
                                                 
                                                 {!isNumeric && String(cell).includes('🟡') && (
                                                     <span style={{
                                                         marginLeft: '8px',
                                                         padding: '2px 6px',
                                                         backgroundColor: 'rgba(245, 158, 11, 0.2)',
                                                         borderRadius: '4px',
                                                         fontSize: '10px',
                                                         fontWeight: 'bold',
                                                         border: '1px solid rgba(245, 158, 11, 0.5)'
                                                     }}>
                                                         MONITOR
                                                     </span>
                                                 )}
                                                 
                                                 {!isNumeric && String(cell).includes('🟢') && (
                                                     <span style={{
                                                         marginLeft: '8px',
                                                         padding: '2px 6px',
                                                         backgroundColor: 'rgba(34, 197, 94, 0.2)',
                                                         borderRadius: '4px',
                                                         fontSize: '10px',
                                                         fontWeight: 'bold',
                                                         border: '1px solid rgba(34, 197, 94, 0.5)'
                                                     }}>
                                                         HEALTHY
                                                     </span>
                                                 )}
                                            </td>
                                        );
                                    })}
                                </tr>
                            );
                        });
                        })()}
                    </tbody>
                </table>
            </div>
            
            {/* Pagination Controls */}
            {rows.length > 10 && (
                <div style={{
                    marginTop: '15px',
                    padding: '10px 16px',
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '10px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ 
                            fontSize: '12px', 
                            color: '#94a3b8',
                            fontWeight: '500'
                        }}>
                            Showing {showAll ? rows.length : Math.min(rowsPerPage, rows.length)} of {rows.length} rows
                        </span>
                        
                        {!showAll && (
                            <select
                                value={rowsPerPage}
                                onChange={(e) => {
                                    setRowsPerPage(parseInt(e.target.value));
                                    setCurrentPage(1);
                                }}
                                style={{
                                    background: 'rgba(31, 41, 55, 0.8)',
                                    border: '1px solid #374151',
                                    borderRadius: '4px',
                                    padding: '4px 8px',
                                    color: '#e5e7eb',
                                    fontSize: '11px'
                                }}
                            >
                                <option value={10}>10 per page</option>
                                <option value={25}>25 per page</option>
                                <option value={50}>50 per page</option>
                            </select>
                        )}
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {!showAll && rows.length > rowsPerPage && (
                            <>
                                <button
                                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                    disabled={currentPage === 1}
                                    style={{
                                        background: currentPage === 1 ? 'rgba(75, 85, 99, 0.5)' : 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                                        border: 'none',
                                        borderRadius: '4px',
                                        padding: '6px 12px',
                                        color: currentPage === 1 ? '#6b7280' : 'white',
                                        fontSize: '11px',
                                        cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    ← Previous
                                </button>
                                
                                <span style={{ 
                                    fontSize: '11px', 
                                    color: '#94a3b8',
                                    padding: '0 8px'
                                }}>
                                    {currentPage} of {Math.ceil(rows.length / rowsPerPage)}
                                </span>
                                
                                <button
                                    onClick={() => setCurrentPage(Math.min(Math.ceil(rows.length / rowsPerPage), currentPage + 1))}
                                    disabled={currentPage >= Math.ceil(rows.length / rowsPerPage)}
                                    style={{
                                        background: currentPage >= Math.ceil(rows.length / rowsPerPage) ? 'rgba(75, 85, 99, 0.5)' : 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                                        border: 'none',
                                        borderRadius: '4px',
                                        padding: '6px 12px',
                                        color: currentPage >= Math.ceil(rows.length / rowsPerPage) ? '#6b7280' : 'white',
                                        fontSize: '11px',
                                        cursor: currentPage >= Math.ceil(rows.length / rowsPerPage) ? 'not-allowed' : 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    Next →
                                </button>
                            </>
                        )}
                        
                        <button
                            onClick={() => {
                                setShowAll(!showAll);
                                setCurrentPage(1);
                            }}
                            style={{
                                background: showAll ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                border: 'none',
                                borderRadius: '6px',
                                padding: '6px 12px',
                                color: 'white',
                                fontSize: '11px',
                                cursor: 'pointer',
                                fontWeight: '600',
                                transition: 'all 0.2s ease'
                            }}
                            onMouseEnter={(e) => {
                                e.target.style.transform = 'scale(1.05)';
                            }}
                            onMouseLeave={(e) => {
                                e.target.style.transform = 'scale(1)';
                            }}
                        >
                            {showAll ? '📄 Show Pages' : '📋 Show All'}
                        </button>
                    </div>
                </div>
            )}
            
            {/* Summary Footer with Actions */}
            <div style={{
                marginTop: '10px',
                padding: '8px 16px',
                backgroundColor: 'rgba(17, 24, 39, 0.5)',
                borderRadius: '8px',
                fontSize: '12px',
                color: '#9ca3af',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <span>
                    Showing {rows.length} results
                    {/* Return Intelligence Summary */}
                    {columnNames.some(col => col.toLowerCase().includes('return_rate')) && (
                        <span style={{ 
                            marginLeft: '10px', 
                            padding: '2px 6px',
                            backgroundColor: 'rgba(79, 70, 229, 0.2)',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: 'bold'
                        }}>
                            📊 RETURN INTELLIGENCE ENABLED
                        </span>
                    )}
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                        onClick={() => {
                            // Copy table data as CSV
                            const csvContent = [
                                columnNames.join(','),
                                ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
                            ].join('\n');
                            navigator.clipboard.writeText(csvContent);
                            // Show temporary feedback
                            const btn = event.target;
                            const originalText = btn.textContent;
                            btn.textContent = '✓ Copied!';
                            btn.style.color = '#10b981';
                            setTimeout(() => {
                                btn.textContent = originalText;
                                btn.style.color = '#9ca3af';
                            }, 2000);
                        }}
                        style={{
                            background: 'none',
                            border: '1px solid #374151',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            color: '#9ca3af',
                            fontSize: '11px',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.borderColor = '#6366f1';
                            e.target.style.color = '#e5e7eb';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.borderColor = '#374151';
                            e.target.style.color = '#9ca3af';
                        }}
                    >
                        📋 Copy CSV
                    </button>
                    <button
                        onClick={() => {
                            // Copy as formatted text
                            const textContent = [
                                title,
                                '='.repeat(title.length),
                                '',
                                columnNames.join('\t'),
                                '-'.repeat(columnNames.join('\t').length),
                                ...rows.map(row => row.join('\t'))
                            ].join('\n');
                            navigator.clipboard.writeText(textContent);
                            // Show temporary feedback
                            const btn = event.target;
                            const originalText = btn.textContent;
                            btn.textContent = '✓ Copied!';
                            btn.style.color = '#10b981';
                            setTimeout(() => {
                                btn.textContent = originalText;
                                btn.style.color = '#9ca3af';
                            }, 2000);
                        }}
                        style={{
                            background: 'none',
                            border: '1px solid #374151',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            color: '#9ca3af',
                            fontSize: '11px',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.borderColor = '#6366f1';
                            e.target.style.color = '#e5e7eb';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.borderColor = '#374151';
                            e.target.style.color = '#9ca3af';
                        }}
                    >
                        📄 Copy Text
                    </button>
                </div>
            </div>
        </div>
    );
}