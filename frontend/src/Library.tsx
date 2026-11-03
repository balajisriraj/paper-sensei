import { useEffect, useRef, useState } from "react";
import { api, type Level, type PaperSummary } from "./api";
import { navigate } from "./router";

const LEVELS: [Level, string, string][] = [
  ["beginner", "New to this", "Every term defined"],
  ["practitioner", "Practitioner", "How it works, when to use it"],
  ["expert", "Expert", "What's new and its limits"],
];

export function Library() {
  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [level, setLevel] = useState<Level>(() => (localStorage.getItem("papersensei.level") as Level) ?? "beginner");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const file = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.list().then(setPapers).catch(() => setError("The PaperSensei API isn't reachable."));
  }, []);
  useEffect(() => {
    localStorage.setItem("papersensei.level", level);
  }, [level]);

  const start = async (label: string, go: () => Promise<{ id: string }>) => {
    setBusy(label);
    setError(null);
    try {
      navigate(`/paper/${(await go()).id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  };

  const upload = (f: File | undefined) => f && start("upload", () => api.upload(f, level));

  return (
    <main className="library">
      <section className="masthead">
        <p className="kicker">A tutor for research papers</p>
        <h1>
          Understand any paper <em>in an evening.</em>
        </h1>
        <p className="lede">
          Drop in a paper. PaperSensei reads every page, writes you a short course with diagrams and quizzes, checks
          every quote against the text, and answers your questions with the page it came from.
        </p>
      </section>

      <section className="intake">
        <div
          className={`drop ${drag ? "over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            upload(e.dataTransfer.files[0]);
          }}
          onClick={() => file.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && file.current?.click()}
        >
          <input ref={file} type="file" accept="application/pdf" hidden onChange={(e) => upload(e.target.files?.[0])} />
          <span className="sheet" aria-hidden="true" />
          <b>{busy === "upload" ? "Reading…" : "Drop a PDF here"}</b>
          <span>or click to choose one, up to 40 pages</span>
        </div>

        <form
          className="arxiv"
          onSubmit={(e) => {
            e.preventDefault();
            if (url.trim()) start("arxiv", () => api.arxiv(url, level));
          }}
        >
          <label htmlFor="arxiv">Or paste an arXiv link</label>
          <div>
            <input id="arxiv" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://arxiv.org/abs/1706.03762" />
            <button className="btn" disabled={!url.trim() || !!busy}>
              {busy === "arxiv" ? "Fetching…" : "Learn it"}
            </button>
          </div>
        </form>

        <fieldset className="level">
          <legend>Teach me as</legend>
          {LEVELS.map(([value, label, hint]) => (
            <label key={value} className={level === value ? "on" : ""}>
              <input type="radio" name="level" value={value} checked={level === value} onChange={() => setLevel(value)} />
              <b>{label}</b>
              <span>{hint}</span>
            </label>
          ))}
        </fieldset>

        <button className="sample" disabled={!!busy} onClick={() => start("sample", () => api.sample(level))}>
          {busy === "sample" ? "Opening…" : "No paper handy? Try the sample on hybrid retrieval →"}
        </button>
        {error && <p className="notice">{error}</p>}
      </section>

      {papers.length > 0 && (
        <section className="shelf">
          <h2>Your shelf</h2>
          <ul>
            {papers.map((p) => (
              <li key={p.id}>
                <button className="card" onClick={() => navigate(`/paper/${p.id}`)}>
                  <span className={`status ${p.status}`}>{p.status === "ready" ? `${p.lessons} lessons` : p.status}</span>
                  <b>{p.title}</b>
                  <span className="meta">
                    {p.pages} pages · {p.level}
                    {p.grounding !== null && ` · ${Math.round(p.grounding * 100)}% verified`}
                  </span>
                </button>
                <button
                  className="remove"
                  aria-label={`Remove ${p.title}`}
                  onClick={() => api.remove(p.id).then(() => setPapers((ps) => ps.filter((x) => x.id !== p.id)))}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="colophon">
        Built with Claude, LangGraph and FastAPI. Part of <a href="https://balajisriraj.com/#lab">Balaji's Lab</a>.
      </footer>
    </main>
  );
}
