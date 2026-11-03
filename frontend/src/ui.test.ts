import { describe, expect, it } from "vitest";
import type { Paper } from "./api";
import { layout } from "./components/Diagram";
import { fold } from "./components/Tutor";
import { applyBuild } from "./PaperView";

describe("diagram layout", () => {
  const n = (id: string) => ({ id, label: id, detail: "" });
  it("places nodes in columns by longest path", () => {
    const { pos } = layout([n("a"), n("b"), n("c"), n("d")], [
      { source: "a", target: "b", label: "" },
      { source: "a", target: "c", label: "" },
      { source: "b", target: "d", label: "" },
      { source: "c", target: "d", label: "" },
    ]);
    expect(pos.get("a")!.x).toBe(0);
    expect(pos.get("b")!.x).toBe(pos.get("c")!.x);
    expect(pos.get("d")!.x).toBeGreaterThan(pos.get("b")!.x);
  });
  it("survives cycles and dangling edges", () => {
    const { pos, edges } = layout([n("a"), n("b")], [
      { source: "a", target: "b", label: "" },
      { source: "b", target: "a", label: "" },
      { source: "a", target: "ghost", label: "" },
    ]);
    expect(pos.size).toBe(2);
    expect(edges).toHaveLength(2);
  });
});

describe("tutor fold", () => {
  it("merges text and keeps citations in place", () => {
    let s = fold([], { type: "text", text: "Fusion " });
    s = fold(s, { type: "text", text: "uses ranks." });
    s = fold(s, { type: "citation", passage: 6, page: 1, section: "3 Method", cited_text: "Ranks are comparable.", verified: true });
    s = fold(s, { type: "text", text: " More." });
    expect(s.map((x) => x.kind)).toEqual(["text", "cite", "text"]);
    expect(s[0]).toEqual({ kind: "text", text: "Fusion uses ranks." });
  });
});

describe("build events", () => {
  it("keeps lessons ordered as they arrive out of order", () => {
    const base = { lessons: [], status: "building" } as unknown as Paper;
    const lesson = (index: number) => ({ index }) as Paper["lessons"][number];
    const retrying = new Set<number>([1]);
    let p = applyBuild(base, { type: "lesson", lesson: lesson(1) }, retrying);
    p = applyBuild(p, { type: "lesson", lesson: lesson(0) }, retrying);
    p = applyBuild(p, { type: "done", lessons: 2, grounding: 1 }, retrying);
    expect(p.lessons.map((l) => l.index)).toEqual([0, 1]);
    expect(p.status).toBe("ready");
    expect(retrying.size).toBe(0);
  });
});
