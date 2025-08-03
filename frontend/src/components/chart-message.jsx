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
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Check if this is multi-series data
            const isMultiSeries = plotData.length > 1 && plotData[0].mode === "lines+markers";
            
            if (isMultiSeries) {
                // Multi-series line chart
                drawMultiSeriesLineChart(ctx, plotData, canvas.width, canvas.height);
            } else {
                // Single series chart
                const { x, y, type } = plotData[0];
                
                // Set styles
                ctx.fillStyle = '#ffffff';
                ctx.strokeStyle = '#667eea';
                ctx.lineWidth = 2;
                
                if (type === 'bar' && x && y) {
                    drawBarChart(ctx, x, y, canvas.width, canvas.height);
                } else if ((type === 'scatter' || type === 'line') && x && y) {
                    drawLineChart(ctx, x, y, canvas.width, canvas.height, '#667eea');
                }
            }
        }, [plotData, layout]);
        
        const drawMultiSeriesLineChart = (ctx, plotData, width, height) => {
            const margin = 60; // More margin for legend
            const chartWidth = width - 2 * margin;
            const chartHeight = height - 2 * margin;
            
            // Get all values to find max
            const allValues = plotData.flatMap(series => series.y);
            const maxValue = Math.max(...allValues);
            const minValue = Math.min(...allValues);
            const valueRange = maxValue - minValue;
            
            const labels = plotData[0].x;
            
            // Draw each series
            plotData.forEach((series, seriesIndex) => {
                const color = series.line?.color || '#667eea';
                
                // Draw line
                ctx.beginPath();
                ctx.strokeStyle = color;
                ctx.lineWidth = 3;
                
                series.y.forEach((value, i) => {
                    const x = margin + (i / (series.y.length - 1)) * chartWidth;
                    const y = height - margin - ((value - minValue) / valueRange) * chartHeight;
                    
                    if (i === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                });
                
                ctx.stroke();
                
                // Draw points
                ctx.fillStyle = color;
                series.y.forEach((value, i) => {
                    const x = margin + (i / (series.y.length - 1)) * chartWidth;
                    const y = height - margin - ((value - minValue) / valueRange) * chartHeight;
                    
                    ctx.beginPath();
                    ctx.arc(x, y, 4, 0, 2 * Math.PI);
                    ctx.fill();
                });
                
                // Draw legend
                const legendY = 20 + seriesIndex * 25;
                ctx.fillStyle = color;
                ctx.fillRect(20, legendY, 15, 15);
                ctx.fillStyle = '#ffffff';
                ctx.font = '14px Inter';
                ctx.fillText(series.name, 45, legendY + 12);
            });
            
            // Draw x-axis labels
            ctx.fillStyle = '#ffffff';
            ctx.font = '12px Inter';
            ctx.textAlign = 'center';
            labels.forEach((label, i) => {
                const x = margin + (i / (labels.length - 1)) * chartWidth;
                ctx.save();
                ctx.translate(x, height - 10);
                ctx.rotate(-Math.PI / 4); // 45 degree rotation
                ctx.fillText(label, 0, 0);
                ctx.restore();
            });
            
            // Draw y-axis labels
            ctx.textAlign = 'right';
            for (let i = 0; i <= 5; i++) {
                const value = minValue + (valueRange * i / 5);
                const y = height - margin - (i / 5) * chartHeight;
                ctx.fillText(value.toFixed(0), margin - 10, y + 4);
            }
        };
        
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
        
        const drawLineChart = (ctx, labels, values, width, height, color = '#667eea') => {
            const margin = 40;
            const chartWidth = width - 2 * margin;
            const chartHeight = height - 2 * margin;
            const maxValue = Math.max(...values);
            
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            
            values.forEach((value, i) => {
                const x = margin + (i / (values.length - 1)) * chartWidth;
                const y = height - margin - (value / maxValue) * chartHeight;
                
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
                
                // Draw point
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, 2 * Math.PI);
                ctx.fill();
                ctx.beginPath();
            });
            
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

    if (!chart_data || !chart_data.labels) {
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

    // 🚀 NEW: Handle multi-series data for year-over-year comparisons
    const isMultiSeries = chart_data.multi_series && chart_data.series;
    
    // Prepare data for Plotly or fallback
    let plotData;
    
    if (isMultiSeries) {
        // Multi-series line chart (e.g., 2023 vs 2024)
        plotData = chart_data.series.map(series => ({
            type: "scatter",
            mode: "lines+markers",
            name: series.name,
            x: chart_data.labels,
            y: series.values,
            line: {
                color: series.color,
                width: 3
            },
            marker: {
                color: series.color,
                size: 6
            }
        }));
    } else if (kind === "pie") {
        // Traditional pie chart with improved formatting
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#42a5f5', '#26c6da', '#66bb6a', '#ffa726', '#ab47bc'];
        
        // Special color for "Others" category
        const pieColors = chart_data.labels.map((label, index) => {
            if (label === "Others") {
                return '#6b7280'; // Gray color for Others
            }
            return colors[index % colors.length];
        });
        
        plotData = [{
            type: "pie",
            labels: chart_data.labels,
            values: chart_data.values,
            hole: 0, // No hole for pie
            marker: {
                colors: pieColors
            },
            textinfo: 'label+percent',
            textposition: 'outside',
            textfont: { size: 10, color: "#ffffff" },
            outsidetextfont: { size: 10, color: "#ffffff" },
            pull: 0.01, // Slight pull for better separation
            rotation: 0,
            hoverinfo: 'label+percent+value',
            hovertemplate: '<b>%{label}</b><br>Value: %{value:,.0f}<br>Share: %{percent:.1f}%<extra></extra>'
        }];
    } else if (kind === "donut") {
        // Modern donut chart (professional)
        plotData = [{
            type: "pie",
            labels: chart_data.labels,
            values: chart_data.values,
            hole: 0.4, // Professional donut hole
            marker: {
                colors: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#42a5f5', '#26c6da', '#66bb6a']
            },
            textinfo: 'label+percent',
            textposition: 'outside'
        }];
    } else if (kind === "horizontal_bar") {
        // Horizontal bar chart for long labels
        plotData = [{
            type: "bar",
            orientation: 'h',
            x: chart_data.values,
            y: chart_data.labels,
            marker: {
                color: '#667eea'
            }
        }];
    } else if (kind === "stacked_bar" && Array.isArray(chart_data.y)) {
        // Stacked bar chart for breakdowns
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'];
        plotData = chart_data.y.map((series, index) => ({
            type: "bar",
            name: series.replace(/_/g, ' ').toUpperCase(),
            x: chart_data.labels,
            y: chart_data.values[series] || [],
            marker: {
                color: colors[index % colors.length]
            }
        }));
    } else if (kind === "waterfall") {
        // Waterfall chart for change analysis
        plotData = [{
            type: "waterfall",
            orientation: "v",
            x: chart_data.labels,
            y: chart_data.values,
            connector: { line: { color: "rgb(63, 63, 63)" } },
            increasing: { marker: { color: "#10b981" } },
            decreasing: { marker: { color: "#ef4444" } },
            totals: { marker: { color: "#667eea" } }
        }];
    } else if (kind === "gauge") {
        // Gauge chart for KPIs
        plotData = [{
            type: "indicator",
            mode: "gauge+number+delta",
            value: chart_data.values[0] || 0,
            domain: { x: [0, 1], y: [0, 1] },
            title: { text: chart_data.labels[0] || "KPI" },
            gauge: {
                axis: { range: [null, 100] },
                bar: { color: "#667eea" },
                steps: [
                    { range: [0, 50], color: "#ef4444" },
                    { range: [50, 80], color: "#f59e0b" },
                    { range: [80, 100], color: "#10b981" }
                ],
                threshold: {
                    line: { color: "#dc2626", width: 4 },
                    thickness: 0.75,
                    value: 90
                }
            }
        }];
    } else if (kind === "heatmap") {
        // Heatmap for performance matrices
        plotData = [{
            type: "heatmap",
            z: chart_data.matrix || [[1, 2, 3], [4, 5, 6], [7, 8, 9]], // 2D array
            x: chart_data.x_labels || chart_data.labels,
            y: chart_data.y_labels || ['Category A', 'Category B', 'Category C'],
            colorscale: [
                [0, '#1f2937'], [0.5, '#667eea'], [1, '#10b981']
            ],
            showscale: true
        }];
    } else if (kind === "multi_line" && Array.isArray(chart_data.y)) {
        // Multi-line chart for multiple metrics
        const colors = ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
        plotData = chart_data.y.map((metric, index) => ({
            type: "scatter",
            mode: "lines+markers",
            name: metric.replace(/_/g, ' ').toUpperCase(),
            x: chart_data.labels,
            y: chart_data.values[metric] || [],
            line: {
                color: colors[index % colors.length],
                width: 3
            },
            marker: {
                color: colors[index % colors.length],
                size: 6
            }
        }));
    } else {
        // Single-series bar/line chart (fallback)
        plotData = [{
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
    }

    // Dynamic layout based on chart type
    let layout = {
        title: {
            text: title || "Chart",
            font: { color: "#ffffff", size: 18, family: "Inter, sans-serif" },
            pad: { t: 20 }
        },
        autosize: true,
        plot_bgcolor: "#1f2937",
        paper_bgcolor: "#111827",
        font: { color: "#ffffff", family: "Inter, sans-serif" },
        margin: { t: 80, r: 60, b: 80, l: 80 }
    };

    // Chart-specific layout configurations
    if (kind === "gauge") {
        // Gauge charts need minimal layout
        layout.showlegend = false;
        layout.margin = { t: 40, r: 40, b: 40, l: 40 };
    } else if (kind === "pie" || kind === "donut") {
        // Pie/donut charts don't need axes
        layout.showlegend = true;
        layout.legend = {
            orientation: "v",
            x: 1.02,
            y: 0.5,
            xanchor: "left",
            yanchor: "middle",
            bgcolor: "rgba(31, 41, 55, 0.9)",
            bordercolor: "#4b5563",
            borderwidth: 1,
            font: { color: "#ffffff", size: 11 }
        };
        // Increase top margin to prevent title overlap
        layout.margin = { t: 100, r: 200, b: 80, l: 80 };
        // Ensure title is visible and properly positioned
        layout.title = {
            text: title || "Chart",
            font: { color: "#ffffff", size: 18, family: "Inter, sans-serif" },
            pad: { t: 20, b: 20 },
            x: 0.5,
            y: 0.95,
            xanchor: "center",
            yanchor: "top"
        };
        // Configure pie chart to prevent line overlap
        if (kind === "pie") {
            layout.pie = {
                textinfo: "label+percent",
                textposition: "outside",
                textfont: { size: 10, color: "#ffffff" },
                outsidetextfont: { size: 10, color: "#ffffff" },
                pull: 0.01, // Slight pull for better separation
                rotation: 0
            };
            // Increase right margin for legend and prevent line overlap
            layout.margin.r = 250;
            // Configure hover template to show more info
            layout.hoverlabel = {
                bgcolor: "rgba(31, 41, 55, 0.9)",
                bordercolor: "#4b5563",
                font: { color: "#ffffff", size: 12 }
            };
        }
    } else if (kind === "heatmap") {
        // Heatmap specific layout
        layout.xaxis = {
            title: { text: "Categories", font: { color: "#e5e7eb", size: 14 } },
            tickfont: { color: "#d1d5db", size: 11 },
            side: "bottom"
        };
        layout.yaxis = {
            title: { text: "Metrics", font: { color: "#e5e7eb", size: 14 } },
            tickfont: { color: "#d1d5db", size: 11 }
        };
        layout.showlegend = false;
    } else if (kind === "horizontal_bar") {
        // Horizontal bar charts swap x/y axes
        layout.xaxis = {
            title: {
                text: chart_data.y_axis || "Sales (KWD)",
                font: { color: "#e5e7eb", size: 14 }
            },
            tickfont: { color: "#d1d5db", size: 11 },
            tickformat: ",.0f",
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: true,
            zeroline: false
        };
        layout.yaxis = {
            title: {
                text: chart_data.x_axis || "Categories",
                font: { color: "#e5e7eb", size: 14 }
            },
            tickfont: { color: "#d1d5db", size: 11 },
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: false,
            zeroline: false
        };
        layout.margin.l = 150; // More left margin for long labels
        layout.showlegend = false;
    } else if (kind === "stacked_bar" || kind === "multi_line") {
        // Multi-series charts need legends and proper axes
        layout.xaxis = {
            title: {
                text: chart_data.x_axis || "Period",
                font: { color: "#e5e7eb", size: 14 }
            },
            tickfont: { color: "#d1d5db", size: 11 },
            tickangle: kind === "multi_line" ? -45 : 0,
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: true,
            zeroline: false
        };
        layout.yaxis = {
            title: {
                text: chart_data.y_axis || "Value (KWD)",
                font: { color: "#e5e7eb", size: 14 }
            },
            tickfont: { color: "#d1d5db", size: 11 },
            tickformat: ",.0f",
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: true,
            zeroline: false
        };
        layout.barmode = kind === "stacked_bar" ? "stack" : undefined;
        layout.showlegend = true;
        layout.legend = {
            x: 1.02,
            y: 1,
            xanchor: "left",
            yanchor: "top",
            bgcolor: "rgba(31, 41, 55, 0.9)",
            bordercolor: "#4b5563",
            borderwidth: 1,
            font: { color: "#ffffff", size: 12 },
            orientation: "v"
        };
        layout.hovermode = "x unified";
    } else if (kind === "waterfall") {
        // Waterfall charts need special formatting
        layout.xaxis = {
            title: { text: "Changes", font: { color: "#e5e7eb", size: 14 } },
            tickfont: { color: "#d1d5db", size: 11 },
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: true
        };
        layout.yaxis = {
            title: { text: "Impact (KWD)", font: { color: "#e5e7eb", size: 14 } },
            tickfont: { color: "#d1d5db", size: 11 },
            tickformat: ",.0f",
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: true
        };
        layout.showlegend = false;
    } else {
        // Standard bar/line charts
        layout.xaxis = {
            title: {
                text: chart_data.x_axis || "Period",
                font: { color: "#e5e7eb", size: 14 }
            },
            tickfont: { color: "#d1d5db", size: 11 },
            tickangle: kind === "line" ? -45 : 0,
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: true,
            zeroline: false,
            tickmode: kind === "line" ? "linear" : "array"
        };
        layout.yaxis = {
            title: {
                text: chart_data.y_axis || "Sales (KWD)",
                font: { color: "#e5e7eb", size: 14 }
            },
            tickfont: { color: "#d1d5db", size: 11 },
            tickformat: ",.0f",
            gridcolor: "#374151",
            linecolor: "#4b5563",
            showgrid: true,
            zeroline: false
        };
        layout.showlegend = isMultiSeries;
        layout.legend = isMultiSeries ? {
            x: 1.02,
            y: 1,
            xanchor: "left",
            yanchor: "top",
            bgcolor: "rgba(31, 41, 55, 0.9)",
            bordercolor: "#4b5563",
            borderwidth: 1,
            font: { color: "#ffffff", size: 12 },
            orientation: "v"
        } : undefined;
        layout.hovermode = "x unified";
        
        // Enhanced annotations for single-series line charts
        if (kind === "line" && !isMultiSeries && chart_data.values) {
            layout.annotations = [{
                text: "Peak",
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
            }];
        }
    }

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