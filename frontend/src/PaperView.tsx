import { useEffect, useState } from "react";
import { api, type BuildEvent, type Lesson, type Paper } from "./api";
import { LessonView } from "./components/LessonView";
import { Tutor } from "./components/Tutor";
import { navigate } from "./router";

type Progress = Record<number, boolean>; // lesson index -> answered correctly

/** Apply one build event to the paper as it streams in. */
export function applyBuild(paper: Paper, e: BuildEvent, retrying: Set<number>): Paper {
  switch (e.type) {
    case "plan":
      return { ...paper, plan: e.plan, title: e.plan.title };
    case "lesson_retry":
      retrying.add(e.index);
      return paper;
    case "lesson": {
      retrying.delete(e.lesson.index);
      const lessons = [...paper.lessons.filter((l) => l.index !== e.lesson.index), e.lesson].sort((a, b) => a.index - b.index);
      return { ...paper, lessons };
    }
    case "glossary":
      return { ...paper, glossary: e.terms };
    case "done":
      return { ...paper, status: "ready", grounding: e.grounding };
    case "error":
      return { ...paper, status: "failed", error: e.message };
    default:
      return paper;
  }
}

export function PaperView({ id }: { id: string }) {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [missing, setMissing] = useState(false);
  const [current, setCurrent] = useState(-1); // -1 is the overview
  const [tutor, setTutor] = useState(false);
  const [retrying] = useState(() => new Set<number>());
  const [progress, setProgress] = useState<Progress>(() => JSON.parse(localStorage.getItem(`papersensei.progress.${id}`) ?? "{}"));

  useEffect(() => {
    const ctrl = new AbortController();
    api
      .get(id)
      .then((p) => {
        setPaper(p);
        if (p.status === "building") {
          api.events(id, (e) => setPaper((cur) => (cur ? applyBuild(cur, e, retrying) : cur)), ctrl.signal).catch(() => {});
        }
      })
      .catch(() => setMissing(true));
    return () => ctrl.abort();
  }, [id, retrying]);

  useEffect(() => {
    localStorage.setItem(`papersensei.progress.${id}`, JSON.stringify(progress));
  }, [id, progress]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [current]);

  if (missing)
    return (
      <main className="empty-page">
        <h1>That paper isn't on the shelf.</h1>
        <button className="btn" onClick={() => navigate("/")}>
          Back to the library
        </button>
      </main>
    );
  if (!paper) return <main className="empty-page pen">Opening the paper…</main>;

  const plan = paper.plan;
  const planned = plan?.lessons ?? [];
  const lesson = paper.lessons.find((l) => l.index === current);
  const answered = Object.keys(progress).length;

  return (
    <div className={`paper ${tutor ? "with-tutor" : ""}`}>
      <nav className="toc" aria-label="Lessons">
        <button className="back" onClick={() => navigate("/")}>
          ← Library
        </button>
        <button className={`toc-item ${current === -1 ? "on" : ""}`} onClick={() => setCurrent(-1)}>
          <span className="num">§</span>Overview
        </button>
        {planned.map((lp, i) => {
          const ready = paper.lessons.some((l) => l.index === i);
          return (
            <button key={i} className={`toc-item ${current === i ? "on" : ""} ${ready ? "" : "pending"}`} disabled={!ready} onClick={() => setCurrent(i)}>
              <span className="num">{progress[i] ? "✓" : i + 1}</span>
              {lp.title}
              {!ready && <i className="dots">{retrying.has(i) ? "checking quotes" : "writing"}</i>}
            </button>
          );
        })}
        {!plan && paper.status === "building" && <p className="pen small">Designing the curriculum…</p>}
        {planned.length > 0 && (
          <div className="meter" aria-label={`${answered} of ${planned.length} quizzes done`}>
            <span style={{ width: `${(answered / planned.length) * 100}%` }} />
          </div>
        )}
      </nav>

      <main className="reader">
        {current === -1 || !lesson ? (
          <Overview paper={paper} onStart={(i) => setCurrent(i)} />
        ) : (
          <LessonView
            paperId={paper.id}
            lesson={lesson}
            total={planned.length}
            terms={paper.glossary ?? []}
            onReplace={(l: Lesson) => setPaper({ ...paper, lessons: paper.lessons.map((x) => (x.index === l.index ? l : x)) })}
            onAnswer={(ok) => ok && setProgress((p) => ({ ...p, [lesson.index]: true }))}
            onNext={paper.lessons.some((l) => l.index === current + 1) ? () => setCurrent(current + 1) : undefined}
          />
        )}
      </main>

      {tutor ? (
        <Tutor paperId={paper.id} level={paper.level} onClose={() => setTutor(false)} />
      ) : (
        <button className="ask-fab" onClick={() => setTutor(true)} disabled={paper.status === "failed"}>
          Ask the sensei
        </button>
      )}
    </div>
  );
}

function Overview({ paper, onStart }: { paper: Paper; onStart: (i: number) => void }) {
  const plan = paper.plan;
  return (
    <article className="overview">
      <p className="kicker">
        {paper.pages} pages · {paper.filename}
        {paper.grounding !== null && ` · ${Math.round(paper.grounding * 100)}% of quotes verified`}
      </p>
      <h1>{plan?.title ?? paper.title}</h1>
      {paper.status === "failed" && <p className="notice">{paper.error}</p>}
      {plan ? (
        <>
          <p className="tldr">{plan.tldr}</p>
          <p className="why">
            <b>Why it matters.</b> {plan.why_it_matters}
          </p>
          <div className="prereq">
            <span>Before you start</span>
            {plan.prerequisites.map((p) => (
              <em key={p}>{p}</em>
            ))}
          </div>
          <h3>Your lessons</h3>
          <ol className="syllabus">
            {plan.lessons.map((lp, i) => {
              const ready = paper.lessons.some((l) => l.index === i);
              return (
                <li key={i}>
                  <button disabled={!ready} onClick={() => onStart(i)}>
                    <b>{lp.title}</b>
                    <span>{lp.goal}</span>
                    <i>{ready ? "Read →" : "Writing…"}</i>
                  </button>
                </li>
              );
            })}
          </ol>
          {paper.glossary && paper.glossary.length > 0 && (
            <>
              <h3>Glossary</h3>
              <dl className="glossary">
                {paper.glossary.map((t) => (
                  <div key={t.term}>
                    <dt>{t.term}</dt>
                    <dd>{t.definition}</dd>
                  </div>
                ))}
              </dl>
            </>
          )}
          <p className="pdf-link">
            <a href={`/api/papers/${paper.id}/pdf`} target="_blank" rel="noreferrer">
              Open the original PDF ↗
            </a>
          </p>
        </>
      ) : (
        <div className="building">
          <p className="pen">Reading every page and designing your curriculum.</p>
          <p className="small">Lessons appear one by one as they're written and fact-checked against the paper.</p>
        </div>
      )}
    </article>
  );
}
