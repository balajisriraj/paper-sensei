import { useState } from "react";
import { api, type Lesson, type Level, type Term } from "../api";
import { Diagram } from "./Diagram";
import { Prose } from "./Prose";
import { Quiz } from "./Quiz";

const LEVELS: [Level, string][] = [
  ["beginner", "New to this"],
  ["practitioner", "Practitioner"],
  ["expert", "Expert"],
];

export function LessonView({
  paperId,
  lesson,
  total,
  terms,
  onReplace,
  onAnswer,
  onNext,
}: {
  paperId: string;
  lesson: Lesson;
  total: number;
  terms: Term[];
  onReplace: (lesson: Lesson) => void;
  onAnswer: (correct: boolean) => void;
  onNext?: () => void;
}) {
  const [busy, setBusy] = useState<Level | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rewrite = async (level: Level) => {
    setBusy(level);
    setError(null);
    try {
      onReplace(await api.rewrite(paperId, lesson.index, level));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const verified = lesson.quote_checks.filter((c) => c.verified).length;

  return (
    <div className="spread">
      <article className={`lesson ${busy ? "rewriting" : ""}`} key={`${lesson.index}-${lesson.level}`}>
        <p className="kicker">
          Lesson {lesson.index + 1} of {total} · {lesson.sections.map((s) => `${s.title} (p.${s.page})`).join(", ")}
        </p>
        <h1>{lesson.title}</h1>
        <p className="goal">{lesson.plan.goal}</p>

        <div className="levels" role="group" aria-label="Explain again for">
          <span>Explain for</span>
          {LEVELS.map(([value, label]) => (
            <button key={value} className={lesson.level === value ? "on" : ""} disabled={!!busy || lesson.level === value} onClick={() => rewrite(value)}>
              {busy === value ? "Rewriting…" : label}
            </button>
          ))}
        </div>
        {error && <p className="notice">{error}</p>}

        <div className="prose">
          <Prose text={lesson.walkthrough} terms={terms} />
        </div>

        <aside className="analogy">
          <span>In other words</span>
          <p>{lesson.analogy}</p>
        </aside>

        <Diagram spec={lesson.diagram} />

        <section className="remember">
          <h3>Remember</h3>
          <ol>
            {lesson.key_points.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ol>
        </section>

        <Quiz key={lesson.quiz.question} quiz={lesson.quiz} onAnswer={onAnswer} />

        {onNext && (
          <button className="next" onClick={onNext}>
            Next lesson →
          </button>
        )}
      </article>

      <aside className="margin" aria-label="Evidence from the paper">
        <h4>From the paper</h4>
        <p className="score">
          {verified} of {lesson.quote_checks.length} quotes found in the text
          {lesson.attempts > 1 && <em> · rewritten once to fix its quotes</em>}
        </p>
        {lesson.quote_checks.map((c, i) => (
          <figure key={i} className={`note ${c.verified ? "ok" : "miss"}`}>
            <blockquote>{c.text}</blockquote>
            <figcaption>{c.verified ? `✓ page ${c.page}` : "✗ not found in the paper"}</figcaption>
          </figure>
        ))}
      </aside>
    </div>
  );
}
