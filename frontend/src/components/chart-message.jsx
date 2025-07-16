import React, { useState, useEffect } from 'react';

export default function ChartMessage({ data }) {
    const [Plot, setPlot] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Dynamically import Plotly to avoid blocking
        const loadPlotly = async () => {
            try {
                const PlotlyComponent = await import('react-plotly.js');
                setPlot(() => PlotlyComponent.default);
                setLoading(false);
            } catch (err) {
                console.error('Failed to load Plotly:', err);
                setError('Chart library failed to load');
                setLoading(false);
            }
        };

        loadPlotly();
    }, []);

    if (loading) {
        return (
            <div style={{ 
                padding: '20px', 
                textAlign: 'center',
                background: '#1f2937',
                borderRadius: '8px',
                color: '#ffffff'
            }}>
                Loading chart...
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
            </div>
        );
    }

    const { chart_data, kind, title } = data;

    // Validate chart data
    if (!chart_data || !chart_data.labels || !chart_data.values) {
        return (
            <div style={{ 
                padding: '20px', 
                background: '#f59e0b',
                borderRadius: '8px',
                color: '#ffffff'
            }}>
                ⚠️ Invalid chart data
            </div>
        );
    }

    const plotData = kind === "pie" ? [{
        type: "pie",
        labels: chart_data.labels,
        values: chart_data.values,
    }] : [{
        type: kind || "bar",
        x: chart_data.labels,
        y: chart_data.values,
        mode: kind === "line" ? "lines+markers" : undefined,
    }];

    const layout = {
        title: title || "Chart",
        ...(kind !== "pie" && {
            xaxis: { title: chart_data.x_axis || "" },
            yaxis: { title: chart_data.y_axis || "" },
        }),
        autosize: true,
        plot_bgcolor: "#1f2937",
        paper_bgcolor: "#111827",
        font: { color: "#ffffff" },
        margin: { t: 50, r: 50, b: 50, l: 50 }
    };

    return (
        <div style={{ width: "100%", minHeight: "400px" }}>
            <Plot 
                data={plotData} 
                layout={layout} 
                style={{ width: "100%", height: "400px" }}
                config={{ responsive: true }}
            />
        </div>
    );
}