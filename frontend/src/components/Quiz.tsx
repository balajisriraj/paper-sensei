import { useState } from "react";
import type { Lesson } from "../api";

export function Quiz({ quiz, onAnswer }: { quiz: Lesson["quiz"]; onAnswer: (correct: boolean) => void }) {
  const [picked, setPicked] = useState<number | null>(null);
  const done = picked !== null;
  return (
    <section className="quiz">
      <h3>Check your understanding</h3>
      <p className="q">{quiz.question}</p>
      <div className="options">
        {quiz.options.map((option, i) => {
          const state = !done ? "" : i === quiz.answer ? "right" : i === picked ? "wrong" : "dim";
          return (
            <button
              key={i}
              className={`option ${state}`}
              disabled={done}
              onClick={() => {
                setPicked(i);
                onAnswer(i === quiz.answer);
              }}
            >
              <span className="letter">{"ABCD"[i]}</span>
              {option}
            </button>
          );
        })}
      </div>
      {done && (
        <p className={`explain ${picked === quiz.answer ? "ok" : "no"}`}>
          <b>{picked === quiz.answer ? "Exactly." : "Not quite."}</b> {quiz.explanation}
          {picked !== quiz.answer && (
            <button className="link" onClick={() => setPicked(null)}>
              Try again
            </button>
          )}
        </p>
      )}
    </section>
  );
}
