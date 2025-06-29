export default function TextMessage({ data, fallbackText }) {
    return (
        <span>
            {data?.text || fallbackText || "⚠️ No content"}
        </span>
    );
}
