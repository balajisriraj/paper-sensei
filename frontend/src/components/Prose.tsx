import { Fragment, type ReactNode } from "react";
import type { Term } from "../api";

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Paragraphs with **bold**, *italic* and glossary terms (first use per paragraph) as hoverable definitions. */
export function Prose({ text, terms = [] }: { text: string; terms?: Term[] }) {
  const byWord = new Map(terms.map((t) => [t.term.toLowerCase(), t]));
  const pattern = terms.length
    ? new RegExp(`\\b(${[...terms].sort((a, b) => b.term.length - a.term.length).map((t) => escape(t.term)).join("|")})\\b`, "gi")
    : null;

  const inline = (chunk: string, used: Set<string>, key: string): ReactNode[] =>
    chunk.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) => {
      if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={`${key}${i}`}>{part.slice(2, -2)}</strong>;
      if (/^\*[^*]+\*$/.test(part)) return <em key={`${key}${i}`}>{part.slice(1, -1)}</em>;
      if (!pattern) return <Fragment key={`${key}${i}`}>{part}</Fragment>;
      return part.split(pattern).map((bit, j) => {
        const term = byWord.get(bit.toLowerCase());
        if (!term || used.has(term.term)) return <Fragment key={`${key}${i}-${j}`}>{bit}</Fragment>;
        used.add(term.term);
        return (
          <span key={`${key}${i}-${j}`} className="term" tabIndex={0}>
            {bit}
            <span className="tip" role="tooltip">
              <b>{term.term}</b>
              {term.definition}
            </span>
          </span>
        );
      });
    });

  return (
    <>
      {text
        .trim()
        .split(/\n\s*\n/)
        .map((block, i) => {
          const used = new Set<string>();
          const lines = block.split("\n");
          if (lines.every((l) => /^\s*[-*] /.test(l)))
            return (
              <ul key={i}>
                {lines.map((l, j) => (
                  <li key={j}>{inline(l.replace(/^\s*[-*] /, ""), used, `${i}-${j}-`)}</li>
                ))}
              </ul>
            );
          return <p key={i}>{inline(block.replace(/\n/g, " "), used, `${i}-`)}</p>;
        })}
    </>
  );
}
