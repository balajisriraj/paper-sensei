export type Level = "beginner" | "practitioner" | "expert";

export type Node = { id: string; label: string; detail: string };
export type Edge = { source: string; target: string; label: string };
export type Diagram = {
  title: string;
  kind: "flow" | "compare";
  nodes: Node[];
  edges: Edge[];
  left_title: string;
  right_title: string;
  rows: { label: string; left: string; right: string }[];
};
export type QuoteCheck = { text: string; verified: boolean; passage: number | null; page: number | null; score: number };
export type LessonPlan = { title: string; goal: string; sections: string[] };

export type Lesson = {
  index: number;
  plan: LessonPlan;
  level: Level;
  title: string;
  walkthrough: string;
  key_points: string[];
  analogy: string;
  diagram: Diagram;
  quiz: { question: string; options: string[]; answer: number; explanation: string };
  quotes: { text: string; supports: string }[];
  quote_checks: QuoteCheck[];
  sections: { title: string; page: number }[];
  grounding: number;
  attempts: number;
  ms: number;
};

export type Plan = { title: string; tldr: string; why_it_matters: string; prerequisites: string[]; lessons: LessonPlan[] };
export type Term = { term: string; definition: string; section: string };

export type Paper = {
  id: string;
  title: string;
  filename: string;
  status: "building" | "ready" | "failed";
  level: Level;
  error: string | null;
  pages: number;
  plan: Plan | null;
  glossary: Term[] | null;
  lessons: Lesson[];
  grounding: number | null;
  parsed: { passages: { id: number; section: string; page: number; text: string }[] };
};

export type PaperSummary = Pick<Paper, "id" | "title" | "filename" | "status" | "level" | "pages" | "grounding"> & {
  lessons: number;
  created_at: string;
};

export type BuildEvent =
  | { type: "step"; step: string; status: string }
  | { type: "plan"; plan: Plan; ms: number }
  | { type: "lesson_started"; index: number; title: string }
  | { type: "lesson_retry"; index: number; grounding: number }
  | { type: "lesson"; lesson: Lesson }
  | { type: "glossary"; terms: Term[] }
  | { type: "done"; lessons: number; grounding: number }
  | { type: "error"; message: string };

export type Citation = { passage: number; page: number; section: string; cited_text: string; verified: boolean };
export type TutorEvent =
  | { type: "text"; text: string }
  | ({ type: "citation" } & Citation)
  | { type: "done"; citations: number; verified: number }
  | { type: "error"; message: string };

/** Split an SSE stream into parsed `data:` payloads; returns the unconsumed remainder. */
export function parseSSE<T>(buffer: string, emit: (event: T) => void): string {
  const frames = buffer.split(/\r?\n\r?\n/);
  const rest = frames.pop() ?? "";
  for (const frame of frames) {
    const data = frame
      .split(/\r?\n/)
      .filter((l) => l.startsWith("data:"))
      .map((l) => l.slice(5).trimStart())
      .join("\n");
    if (data) emit(JSON.parse(data) as T);
  }
  return rest;
}

async function stream<T>(res: Response, onEvent: (e: T) => void): Promise<void> {
  if (!res.ok || !res.body) throw new Error(await errorText(res));
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer = parseSSE(buffer + value, onEvent);
  }
  parseSSE(buffer + "\n\n", onEvent);
}

async function errorText(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await errorText(res));
  return (await res.json()) as T;
}

const post = (url: string, body: unknown, signal?: AbortSignal) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });

export const api = {
  health: () => fetch("/api/health").then(json<{ llm: string; model: string }>),
  list: () => fetch("/api/papers").then(json<PaperSummary[]>),
  get: (id: string) => fetch(`/api/papers/${id}`).then(json<Paper>),
  remove: (id: string) => fetch(`/api/papers/${id}`, { method: "DELETE" }).then(json<{ deleted: boolean }>),
  sample: (level: Level) => post("/api/papers/sample", { level }).then(json<{ id: string }>),
  arxiv: (url: string, level: Level) => post("/api/papers/arxiv", { url, level }).then(json<{ id: string }>),
  upload: (file: File, level: Level) => {
    const form = new FormData();
    form.append("file", file);
    form.append("level", level);
    return fetch("/api/papers", { method: "POST", body: form }).then(json<{ id: string }>);
  },
  rewrite: (id: string, index: number, level: Level) =>
    post(`/api/papers/${id}/lessons/${index}/rewrite`, { level }).then(json<Lesson>),
  events: (id: string, onEvent: (e: BuildEvent) => void, signal: AbortSignal) =>
    fetch(`/api/papers/${id}/events`, { signal }).then((res) => stream(res, onEvent)),
  ask: (
    id: string,
    body: { question: string; history: { role: string; content: string }[]; level: Level },
    onEvent: (e: TutorEvent) => void,
    signal: AbortSignal,
  ) => post(`/api/papers/${id}/ask`, body, signal).then((res) => stream(res, onEvent)),
};
