export default function TextMessage({ data, fallbackText }) {
    return (
        <span>
            {/* Try template, then text, then fallback */}
            {data?.template || data?.text || fallbackText || "⚠️ No content"}
        </span>
    );
}
