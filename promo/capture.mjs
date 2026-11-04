// Pass 1 of the promo: run the real PaperSensei (the API with the scripted model, and the Vite UI), drive it like a
// reader would, and save DOM snapshots of each moment to promo/out/snaps. Pass 2 (kit/render.mjs) films them.
//
//   cd promo && pnpm install && node capture.mjs
import { rmSync } from "node:fs";
import { resolve } from "node:path";
import { freePort, launch, serve, sleep, snapper, until } from "./kit/snap.mjs";

const ROOT = resolve(import.meta.dirname, "..");
const SNAPS = resolve(import.meta.dirname, "out/snaps");
rmSync(SNAPS, { recursive: true, force: true });
const data = resolve(import.meta.dirname, "out/data");
rmSync(data, { recursive: true, force: true });

const api = await freePort();
const web = await freePort();
const stopApi = await serve("uv", ["run", "papersensei", "serve", "--host", "127.0.0.1", "--port", String(api)], {
  cwd: resolve(ROOT, "backend"),
  env: { PAPERSENSEI_LLM: "scripted", PAPERSENSEI_SCRIPTED_DELAY: "0.08", PAPERSENSEI_DATA_DIR: data },
  url: `http://127.0.0.1:${api}/api/health`,
});
const stopWeb = await serve("pnpm", ["exec", "vite", "--host", "127.0.0.1", "--port", String(web), "--strictPort"], {
  cwd: resolve(ROOT, "frontend"),
  env: { PAPERSENSEI_API: `http://127.0.0.1:${api}` },
  url: `http://127.0.0.1:${web}/`,
});

const { browser, page } = await launch();
// Day reading is the default look; headless Chrome can report a dark colour scheme.
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
await page.goto(`http://127.0.0.1:${web}/`);
await page.evaluate(() => (localStorage.clear(), localStorage.setItem("papersensei.theme", "day")));
await page.reload();
await until(page, () => document.querySelector(".library .sample"));
if ((await page.evaluate(() => document.documentElement.dataset.theme)) !== "day") await page.click(".theme");
await until(page, () => document.documentElement.dataset.theme === "day");
await sleep(500);
const shot = snapper(page, SNAPS);
const scrollTo = async (sel, block = "start", offset = 0) => {
  await page.evaluate(
    (sel, block, offset) => {
      const el = document.querySelector(sel);
      const r = el.getBoundingClientRect();
      const top = block === "center" ? r.top + scrollY - (innerHeight - r.height) / 2 : r.top + scrollY - offset;
      window.scrollTo({ top: Math.max(0, top), behavior: "instant" });
    },
    sel,
    block,
    offset,
  );
  await sleep(300);
};

// The library: drop a PDF, paste an arXiv link, or open the sample.
await shot("library");

// Open the sample and film the build: the curriculum, then lessons as the parallel writers finish.
await page.click(".library .sample");
await until(page, () => document.querySelector(".paper"));
for (let i = 0; i < 60; i++) {
  await shot(`build-${String(i).padStart(2, "0")}`);
  const done = await page.evaluate(() => document.querySelectorAll(".syllabus i").length > 0 && [...document.querySelectorAll(".syllabus i")].every((x) => x.textContent.startsWith("Read")) && document.querySelector(".glossary") && /verified/.test(document.querySelector(".overview .kicker")?.textContent ?? ""));
  if (done) break;
  await sleep(250);
}
await sleep(600);
await shot("build-done");
await scrollTo(".overview h3 + .glossary", "start", 200);
await shot("glossary");
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));

// Lesson 3: the walkthrough, a glossary term opened, the evidence in the margin.
await page.click(".toc-item:nth-of-type(5)");
await until(page, () => document.querySelector(".lesson h1"));
await sleep(900);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
await sleep(300);
await shot("lesson");
// Hover a glossary term. Hover is lost in a snapshot, so pin the tooltip open the way :hover shows it.
await page.hover(".prose .term");
await sleep(300);
await page.evaluate(() => {
  const t = document.querySelector(".prose .term");
  t.style.background = "linear-gradient(transparent 20%, var(--hl-strong) 20%)";
  Object.assign(t.querySelector(".tip").style, { opacity: "1", transform: "translateX(-50%)" });
});
await shot("term");
await page.evaluate(() => {
  const t = document.querySelector(".prose .term");
  t.style.background = "";
  t.querySelector(".tip").removeAttribute("style");
});
await page.mouse.move(10, 600);

// The diagram and the key points.
await scrollTo(".lesson .diagram", "start", 330);
await shot("diagram");

// The quiz: pick the right answer.
await scrollTo(".lesson .quiz", "center");
await shot("quiz");
await page.click(".quiz .option:nth-child(1)");
await sleep(500);
await shot("quiz-done");

// Explain it again for an expert.
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
await sleep(300);
await page.click(".levels button:nth-of-type(3)");
await sleep(60);
await shot("rewrite-busy");
await until(page, () => !document.querySelector(".lesson.rewriting"));
await sleep(700);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
await sleep(300);
await shot("rewrite-done");

// The tutor: a question about the paper, answered with page citations.
await page.click(".ask-fab");
await until(page, () => document.querySelector(".tutor .starter"));
await sleep(600);
await shot("tutor");
async function ask(prefix, question) {
  await page.click(".tutor input");
  await page.keyboard.type(question, { delay: 6 });
  await page.keyboard.press("Enter");
  await sleep(100);
  let i = 0;
  let last = "";
  for (; i < 60; i++) {
    await shot(`${prefix}-${String(i).padStart(2, "0")}`);
    // Streaming is over when the answer has text and stops growing between two looks.
    const text = await page.evaluate(() => [...document.querySelectorAll(".tutor .answer")].pop()?.textContent ?? "");
    const done = text && !text.includes("reading the paper") && text === last;
    last = text;
    if (done) break;
    await sleep(250);
  }
  await sleep(800);
  await shot(`${prefix}-done`);
  console.log(`${prefix}: ${i + 1} frames`);
}
await ask("ask", "Why does reciprocal rank fusion ignore raw scores?");
await page.click(".tutor .answer .pg");
await sleep(500);
await shot("cite");
await ask("off", "Who won the World Cup in 2022?");

// Night reading.
await page.click(".theme");
await sleep(600);
await shot("night");
await page.click(".theme");
await sleep(400);

// Back to the library: the paper is on the shelf.
await page.click(".tutor .close");
await page.click(".toc .back");
await until(page, () => document.querySelector(".shelf .card"));
await sleep(600);
await scrollTo(".shelf", "start", 300);
await shot("shelf");

await browser.close();
stopWeb();
stopApi();
console.log(`${shot.names.length} snapshots in promo/out/snaps`);
process.exit(0);
