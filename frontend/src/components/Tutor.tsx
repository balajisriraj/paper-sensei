import { useEffect, useRef, useState } from "react";
import { api, type Citation, type Level, type TutorEvent } from "../api";

export type Segment = { kind: "text"; text: string } | ({ kind: "cite" } & Citation);
type Message = { role: "user" | "assistant"; segments: Segment[]; streaming?: boolean; error?: boolean };

const plain = (m: Message) => m.segments.map((s) => (s.kind === "text" ? s.text : "")).join("");

/** Fold a tutor event into the answer's segments: text runs, each followed by the citations that back it. */
export function fold(segments: Segment[], e: TutorEvent): Segment[] {
  if (e.type === "text") {
    const last = segments[segments.length - 1];
    return last?.kind === "text" ? [...segments.slice(0, -1), { kind: "text", text: last.text + e.text }] : [...segments, { kind: "text", text: e.text }];
  }
  if (e.type === "citation") {
    const { type: _type, ...c } = e;
    return [...segments, { kind: "cite", ...c }];
  }
  if (e.type === "error") return [...segments, { kind: "text", text: e.message }];
  return segments;
}

const STARTERS = ["What problem does this paper solve?", "Explain the method like I'm new to this.", "What are the limitations?"];

export function Tutor({ paperId, level, onClose }: { paperId: string; level: Level; onClose: () => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const busy = messages.some((m) => m.streaming);

  useEffect(() => {
    end.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages]);
  useEffect(() => () => abort.current?.abort(), []);

  const ask = async (question: string) => {
    if (!question.trim() || busy) return;
    const history = messages.filter((m) => !m.error).map((m) => ({ role: m.role, content: plain(m) }));
    setMessages((ms) => [...ms, { role: "user", segments: [{ kind: "text", text: question }] }, { role: "assistant", segments: [], streaming: true }]);
    setDraft("");
    abort.current = new AbortController();
    const update = (fn: (m: Message) => Message) => setMessages((ms) => [...ms.slice(0, -1), fn(ms[ms.length - 1])]);
    try {
      await api.ask(paperId, { question, history, level }, (e) => update((m) => ({ ...m, segments: fold(m.segments, e), error: m.error || e.type === "error" })), abort.current.signal);
    } catch (err) {
      if ((err as Error).name !== "AbortError") update((m) => ({ ...m, error: true, segments: [{ kind: "text", text: "The tutor is unreachable right now." }] }));
    } finally {
      update((m) => ({ ...m, streaming: false }));
    }
  };

  return (
    <aside className="tutor" aria-label="Tutor">
      <header>
        <div>
          <span className="kicker">Tutor</span>
          <h2>Ask the sensei</h2>
        </div>
        <button className="close" onClick={onClose} aria-label="Close tutor">
          ×
        </button>
      </header>
      <div className="log">
        {messages.length === 0 && (
          <div className="starter">
            <p>Every answer cites the page it came from. If the paper doesn't say, I'll tell you.</p>
            {STARTERS.map((s) => (
              <button key={s} onClick={() => ask(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <p key={i} className="you">
              {plain(m)}
            </p>
          ) : (
            <div key={i} className={`answer ${m.error ? "err" : ""}`}>
              {m.segments.length === 0 && <span className="pen">reading the paper…</span>}
              <p>
                {m.segments.map((s, j) =>
                  s.kind === "text" ? (
                    <span key={j}>{s.text}</span>
                  ) : (
                    <button
                      key={j}
                      className={`pg ${s.verified ? "" : "unverified"} ${open === `${i}-${j}` ? "on" : ""}`}
                      onClick={() => setOpen(open === `${i}-${j}` ? null : `${i}-${j}`)}
                      title={s.verified ? "Quoted from the paper" : "Could not match this quote to the paper"}
                    >
                      p.{s.page}
                    </button>
                  ),
                )}
              </p>
              {m.segments.map((s, j) =>
                s.kind === "cite" && open === `${i}-${j}` ? (
                  <blockquote key={`q${j}`}>
                    “{s.cited_text.trim()}”<cite>{s.section} · page {s.page}{s.verified ? " · verified" : ""}</cite>
                  </blockquote>
                ) : null,
              )}
            </div>
          ),
        )}
        <div ref={end} />
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(draft);
        }}
      >
        <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Ask about this paper…" maxLength={1500} aria-label="Question" />
        <button type="submit" disabled={!draft.trim() || busy}>
          Ask
        </button>
      </form>
    </aside>
  );
}
