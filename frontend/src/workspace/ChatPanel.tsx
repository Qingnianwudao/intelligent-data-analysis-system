import { FormEvent, useEffect, useRef, useState } from "react";
import { useWorkspace } from "./WorkspaceContext";

export function ChatPanel() {
  const { messages, sendMessage, sending } = useWorkspace();
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void sendMessage(draft);
    setDraft("");
  }

  return (
    <section className="panel chat-panel">
      <div className="panel-header">
        <h2>问答</h2>
      </div>
      <div className="message-list">
        {messages.length === 0 ? (
          <p className="empty-hint">输入问题后发送，右侧图表将使用后端返回的 columns / rows 更新。</p>
        ) : null}
        {messages.map((m) => (
          <div
            key={m.id}
            className={m.role === "user" ? "bubble user" : "bubble assistant"}
          >
            <span className="bubble-role">{m.role === "user" ? "你" : "助手"}</span>
            <p className="bubble-text">{m.content}</p>
            {m.role === "assistant" && m.sql ? (
              <details className="sql-block">
                <summary>SQL</summary>
                <pre>{m.sql}</pre>
              </details>
            ) : null}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input-row" onSubmit={onSubmit}>
        <textarea
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="用自然语言描述你的分析需求…"
          disabled={sending}
        />
        <button
          type="submit"
          className="btn-primary"
          disabled={!draft.trim() || sending}
        >
          {sending ? "发送中…" : "发送"}
        </button>
      </form>
    </section>
  );
}
