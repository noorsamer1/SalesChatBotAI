export default function TextMessage({ data, fallbackText }) {
    return (
        <span>
<<<<<<< HEAD
            {data?.text || fallbackText || "⚠️ No content"}
=======
            {/* Try template, then text, then fallback */}
            {data?.template || data?.text || fallbackText || "⚠️ No content"}
>>>>>>> master
        </span>
    );
}
