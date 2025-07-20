import React, { useState, useEffect } from 'react';

export default function ChartMessage({ data }) {
    const [Plot, setPlot] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadPlotly = async () => {
            try {
                // Try multiple import strategies
                let PlotlyComponent;
                
                try {
                    // First, try the default import
                    PlotlyComponent = await import('react-plotly.js');
                    setPlot(() => PlotlyComponent.default);
                } catch (err) {
                    console.warn('react-plotly.js not available, trying CDN approach');
                    
                    // Fallback: Use Chart.js or simple canvas chart
                    const chartFallback = () => SimpleChart;
                    setPlot(chartFallback);
                }
                
                setLoading(false);
            } catch (err) {
                console.error('Failed to load any chart library:', err);
                setError('Chart library failed to load');
                setLoading(false);
            }
        };

        loadPlotly();
    }, []);

    // Simple fallback chart component using HTML5 Canvas
    const SimpleChart = ({ data: plotData, layout }) => {
        const canvasRef = React.useRef(null);
        
        React.useEffect(() => {
            const canvas = canvasRef.current;
            if (!canvas || !plotData || !plotData[0]) return;
            
            const ctx = canvas.getContext('2d');
            const { x, y, type } = plotData[0];
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Set styles
            ctx.fillStyle = '#ffffff';
            ctx.strokeStyle = '#667eea';
            ctx.lineWidth = 2;
            
            if (type === 'bar' && x && y) {
                drawBarChart(ctx, x, y, canvas.width, canvas.height);
            } else if (type === 'line' && x && y) {
                drawLineChart(ctx, x, y, canvas.width, canvas.height);
            }
        }, [plotData, layout]);
        
        const drawBarChart = (ctx, labels, values, width, height) => {
            const margin = 40;
            const chartWidth = width - 2 * margin;
            const chartHeight = height - 2 * margin;
            const barWidth = chartWidth / labels.length * 0.8;
            const maxValue = Math.max(...values);
            
            labels.forEach((label, i) => {
                const barHeight = (values[i] / maxValue) * chartHeight;
                const x = margin + i * (chartWidth / labels.length);
                const y = height - margin - barHeight;
                
                // Draw bar
                ctx.fillStyle = '#667eea';
                ctx.fillRect(x, y, barWidth, barHeight);
                
                // Draw label
                ctx.fillStyle = '#ffffff';
                ctx.font = '12px Inter';
                ctx.textAlign = 'center';
                ctx.fillText(label, x + barWidth/2, height - 10);
                
                // Draw value
                ctx.fillText(values[i].toFixed(1), x + barWidth/2, y - 5);
            });
        };
        
        const drawLineChart = (ctx, labels, values, width, height) => {
            const margin = 40;
            const chartWidth = width - 2 * margin;
            const chartHeight = height - 2 * margin;
            const maxValue = Math.max(...values);
            
            ctx.beginPath();
            values.forEach((value, i) => {
                const x = margin + (i / (values.length - 1)) * chartWidth;
                const y = height - margin - (value / maxValue) * chartHeight;
                
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
                
                // Draw point
                ctx.fillStyle = '#667eea';
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, 2 * Math.PI);
                ctx.fill();
                ctx.beginPath();
            });
            
            ctx.strokeStyle = '#667eea';
            ctx.stroke();
        };
        
        return (
            <canvas 
                ref={canvasRef} 
                width={600} 
                height={400}
                style={{ 
                    backgroundColor: '#1f2937',
                    borderRadius: '8px',
                    maxWidth: '100%'
                }}
            />
        );
    };

    if (loading) {
        return (
            <div style={{ 
                padding: '20px', 
                textAlign: 'center',
                background: '#1f2937',
                borderRadius: '8px',
                color: '#ffffff'
            }}>
                <div style={{ 
                    display: 'inline-block',
                    width: '20px',
                    height: '20px',
                    border: '2px solid #667eea',
                    borderTop: '2px solid transparent',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                }} />
                <p style={{ marginTop: '10px' }}>Loading chart...</p>
            </div>
        );
    }

    if (error || !Plot) {
        return (
            <div style={{ 
                padding: '20px', 
                background: '#ef4444',
                borderRadius: '8px',
                color: '#ffffff'
            }}>
                ⚠️ {error || 'Chart component unavailable'}
                <br />
                <small>Using fallback chart renderer</small>
            </div>
        );
    }

    // Validate and prepare chart data
    const { chart_data, kind, title } = data;

    if (!chart_data || !chart_data.labels || !chart_data.values) {
        return (
            <div style={{ 
                padding: '20px', 
                background: '#f59e0b',
                borderRadius: '8px',
                color: '#ffffff'
            }}>
                ⚠️ Invalid chart data structure
                <br />
                <small>Expected: chart_data.labels and chart_data.values</small>
            </div>
        );
    }

    // Prepare data for Plotly or fallback
    const plotData = kind === "pie" ? [{
        type: "pie",
        labels: chart_data.labels,
        values: chart_data.values,
        hole: 0.3, // Donut chart
        marker: {
            colors: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
        }
    }] : [{
        type: kind === "line" ? "scatter" : "bar",
        x: chart_data.labels,
        y: chart_data.values,
        mode: kind === "line" ? "lines+markers" : undefined,
        marker: {
            color: '#667eea'
        },
        line: kind === "line" ? {
            color: '#667eea',
            width: 3
        } : undefined
    }];

    const layout = {
        title: {
            text: title || "Chart",
            font: { color: "#ffffff", size: 18, family: "Inter, sans-serif" },
            pad: { t: 20 }
        },
        ...(kind !== "pie" && {
            xaxis: { 
                title: {
                    text: chart_data.x_axis || "Period",
                    font: { color: "#e5e7eb", size: 14 }
                },
                tickfont: { color: "#d1d5db", size: 11 },
                tickangle: kind === "line" ? -45 : 0, // Rotate labels for time series
                gridcolor: "#374151",
                linecolor: "#4b5563",
                showgrid: true,
                zeroline: false,
                tickmode: kind === "line" ? "linear" : "array"
            },
            yaxis: { 
                title: {
                    text: chart_data.y_axis || "Sales (KWD)",
                    font: { color: "#e5e7eb", size: 14 }
                },
                tickfont: { color: "#d1d5db", size: 11 },
                tickformat: ",.0f", // Format numbers with commas
                gridcolor: "#374151",
                linecolor: "#4b5563",
                showgrid: true,
                zeroline: false
            },
        }),
        autosize: true,
        plot_bgcolor: "#1f2937",
        paper_bgcolor: "#111827",
        font: { color: "#ffffff", family: "Inter, sans-serif" },
        margin: { t: 80, r: 60, b: 80, l: 80 }, // Better margins for readability
        showlegend: kind === "pie",
        hovermode: "x unified", // Better hover experience
        // Professional gridlines and styling
        annotations: kind === "line" ? [{
            text: "Peak Performance",
            x: chart_data.labels[chart_data.values.indexOf(Math.max(...chart_data.values))],
            y: Math.max(...chart_data.values),
            arrowhead: 2,
            arrowsize: 1,
            arrowwidth: 2,
            arrowcolor: "#10b981",
            font: { color: "#10b981", size: 12 },
            bgcolor: "rgba(16, 185, 129, 0.1)",
            bordercolor: "#10b981",
            borderwidth: 1
        }] : []
    };

    const config = { 
        responsive: true,
        displayModeBar: false,
        doubleClick: 'reset',
        scrollZoom: false
    };

    return (
        <div style={{ width: "100%", minHeight: "400px", marginBottom: "20px" }}>
            <h4 style={{ marginBottom: '10px', color: '#ffffff' }}>
                {title || "Chart"}
            </h4>
            
            {Plot === SimpleChart ? (
                <SimpleChart data={plotData} layout={layout} />
            ) : (
                <Plot 
                    data={plotData} 
                    layout={layout} 
                    style={{ width: "100%", height: "400px" }}
                    config={config}
                />
            )}
            
            {/* Add CSS animation for loading spinner */}
            <style jsx>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}