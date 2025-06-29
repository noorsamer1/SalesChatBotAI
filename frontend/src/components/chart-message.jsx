import Plot from 'react-plotly.js';

export default function ChartMessage({ data }) {
    const { chart_data, kind, title } = data;

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
    };

    return <Plot data={plotData} layout={layout} style={{ width: "100%", height: "100%" }} />;
}
