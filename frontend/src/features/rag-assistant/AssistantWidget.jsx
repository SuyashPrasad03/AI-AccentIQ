import { useState, useRef, useEffect } from "react";
import { askAssistant } from "../../api/assistant.js";

export function AssistantWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;
    setMessages((p) => [...p, { role: "user", text: q }]);
    setInput(""); setLoading(true);
    try {
      const data = await askAssistant(q);
      setMessages((p) => [...p, { role: "assistant", text: data.answer }]);
    } catch (_e) { setMessages((p) => [...p, { role: "assistant", text: "Something went wrong." }]); }
    finally { setLoading(false); }
  };

  return (
    <>
      <button
        className="fixed bottom-5 right-5 z-[300] w-12 h-12 rounded-full bg-secondary text-white
                   flex items-center justify-center shadow-lg text-lg hover:scale-110 transition-transform"
        onClick={() => setOpen(!open)}
      >{open ? "✕" : "💬"}</button>

      {open && (
        <div className="fixed bottom-20 right-5 z-[300] w-[360px] max-h-[500px] bg-bg rounded-[var(--radius-card)]
                        shadow-lg border border-card-border flex flex-col overflow-hidden animate-slide-up">
          <div className="px-5 py-3.5 border-b border-card-border">
            <h3 className="font-bold text-sm text-ink">App Assistant</h3>
            <p className="text-[11px] text-ink-faint">I help with questions about this app</p>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-2.5 min-h-[200px] max-h-[330px]">
            {messages.length === 0 && (
              <div className="text-xs text-ink-faint py-4 text-center">
                <p className="mb-1.5">Try asking:</p>
                <p className="italic">"How is my score calculated?"</p>
                <p className="italic">"What happens to my audio?"</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`max-w-[85%] px-3.5 py-2.5 rounded-[var(--radius-lg)] text-sm leading-relaxed
                ${msg.role === "user" ? "bg-secondary text-white self-end" : "bg-bg-soft text-ink self-start"}`}>
                {msg.text}
              </div>
            ))}
            {loading && <div className="bg-bg-soft text-ink-faint self-start px-3.5 py-2.5 rounded-[var(--radius-lg)] text-sm italic">Thinking…</div>}
            <div ref={endRef} />
          </div>
          <form className="flex gap-2 px-4 py-3 border-t border-card-border" onSubmit={handleSend}>
            <input type="text" className="flex-1 px-3.5 py-2.5 text-sm rounded-pill border border-card-border bg-bg-soft focus:outline-none focus:border-primary placeholder:text-ink-faint"
              value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about the app…" disabled={loading} />
            <button type="submit" className="btn-primary !px-4 !py-2 !text-xs" disabled={loading || !input.trim()}>Send</button>
          </form>
        </div>
      )}
    </>
  );
}
