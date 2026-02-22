import { useState } from "react";
import { sendChat } from "./api";

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState([]);

  async function onSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    setMsgs((m) => [...m, { who: "You", text }]);
    setInput("");

    try {
      const data = await sendChat(text);
      setMsgs((m) => [...m, { who: "Bot", text: data.response }]);
    } catch (err) {
      setMsgs((m) => [...m, { who: "Bot", text: "Error: " + err.message }]);
    }
  }

  return (
    <div style={{ maxWidth: 650, margin: "40px auto" }}>
      <h2>Chat</h2>

      <div style={{ border: "1px solid #ccc", padding: 12, minHeight: 300 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ margin: "8px 0" }}>
            <b>{m.who}:</b> {m.text}
          </div>
        ))}
      </div>

      <form onSubmit={onSend} style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type..."
          style={{ flex: 1, padding: 10 }}
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}