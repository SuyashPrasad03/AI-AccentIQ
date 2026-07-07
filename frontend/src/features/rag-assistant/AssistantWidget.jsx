import { useState, useRef, useEffect } from "react";
import { askAssistant } from "../../api/assistant.js";

/**
 * AssistantWidget — floating chat widget available on every page.
 * Answers only questions about the app (RAG-grounded, refuses out-of-scope).
 */
export function AssistantWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const data = await askAssistant(question);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.answer, sources: data.sources, refused: data.refused },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, something went wrong. Please try again.", refused: false },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Toggle button */}
      <button
        className="assistant-fab"
        onClick={() => setOpen(!open)}
        aria-label={open ? "Close assistant" : "Open assistant"}
      >
        {open ? "✕" : "💬"}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="assistant-panel" role="dialog" aria-label="App assistant">
          <div className="assistant-header">
            <h3>App Assistant</h3>
            <span className="assistant-scope">I can only help with questions about this app</span>
          </div>

          <div className="assistant-messages">
            {messages.length === 0 && (
              <div className="assistant-empty">
                <p>Ask me anything about:</p>
                <ul>
                  <li>How scoring works</li>
                  <li>Privacy &amp; data handling</li>
                  <li>How to use features</li>
                  <li>Troubleshooting issues</li>
                </ul>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`assistant-msg msg-${msg.role}`}>
                <p>{msg.text}</p>
                {msg.sources && msg.sources.length > 0 && (
                  <span className="msg-sources">
                    Sources: {msg.sources.join(", ")}
                  </span>
                )}
              </div>
            ))}

            {loading && (
              <div className="assistant-msg msg-assistant">
                <span className="assistant-typing">Thinking…</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <form className="assistant-input-row" onSubmit={handleSend}>
            <input
              type="text"
              className="assistant-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about the app…"
              disabled={loading}
              aria-label="Type your question"
            />
            <button className="btn btn-primary assistant-send" type="submit" disabled={loading || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
