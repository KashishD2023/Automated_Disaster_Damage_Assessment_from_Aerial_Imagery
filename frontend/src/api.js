
const API_BASE = process.env.REACT_APP_API_BASE || "http://127.0.0.1:8000";

export async function sendChat(message, session_id = null) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Request failed");
  }

  return res.json();
}