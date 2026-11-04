// PaperSensei's promo: the problem, the product, then each feature given room on the real UI (DOM snapshots from
// capture.mjs), and what's under the hood. 96 bpm; shots are counted in beats.
import { big, chips, eyebrow, grad, makeFilm, stream, sub } from "./kit/film";

// The app's own tokens (frontend/src/styles.css): warm paper, ink, a vermilion pen and a highlighter.
const PAPER = "#f4efe4";
const INK = "#1e1b16";
const PEN = "#c8411b";
const SERIF = `"Iowan Old Style", "Palatino Linotype", Palatino, Charter, Georgia, serif`;
const SANS = `-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, "Helvetica Neue", Arial, sans-serif`;

// The seal from the app bar, large.
const logo = `<div class="seal-xl"><span>PS</span></div>`;
const { word, ui, run, BEAT } = makeFilm({
  name: "paper-sensei",
  style: "study",
  bpm: 96,
  bgs: {
    light: [PAPER, INK],
    dark: ["#12141a", "#ece4d4"],
    pen: [PEN, "#fff4ea"],
  },
  grad: "linear-gradient(92deg, #c8411b 0%, #db5a1f 50%, #e3901a 100%)",
  font: SERIF,
  stage: "radial-gradient(1300px 800px at 50% 42%, #fbf7ee, #e6dcc6)",
  caption: { bg: "rgba(255, 252, 245, .94)", ink: INK, shadow: "0 22px 50px -22px rgba(60, 40, 10, .55), 0 0 0 1px rgba(60, 40, 10, .12)" },
  logo,
  css: `
    #type .w { font-weight: 600; letter-spacing: -.025em; }
    #type .w em { font-style: italic; font-weight: 500; }
    #type .sub { font-family: ${SERIF}; font-style: italic; opacity: .72; }
    #type .eyebrow { font-family: ${SANS}; font-size: 24px; letter-spacing: .22em; color: ${PEN}; opacity: 1; }
    #type[data-bg=dark] .eyebrow { color: #ff8a5c; }
    #type[data-bg=pen] .eyebrow { color: #fff4ea; opacity: .8; }
    #type .chips span { font-family: ${SANS}; font-size: 27px; border-width: 1.5px; border-radius: 6px; background: #fffcf5; }
    #type[data-bg=pen] .grad { -webkit-text-fill-color: #fff4ea; }
    #type[data-bg=dark] .grad { background: linear-gradient(92deg, #ff8a5c, #ffd60a); -webkit-background-clip: text; background-clip: text; }
    .hl { background: linear-gradient(transparent 58%, rgba(255, 214, 10, .55) 58%); padding: 0 .06em; }
    .seal-xl { width: 150px; height: 150px; margin: 0 auto 6px; display: grid; place-items: center; background: ${PEN}; border-radius: 26px; transform: rotate(-4deg);
      box-shadow: inset 0 0 0 10px ${PEN}, inset 0 0 0 14px #fff4ea88, 0 30px 70px -26px rgba(200, 65, 27, .75); }
    .seal-xl span { font: 700 58px ${SERIF}; color: #fff4ea; letter-spacing: .02em; }
    #caption { border-radius: 10px; }
    #caption .eyebrow { font-family: ${SANS}; }
    #caption .title { font-weight: 600; letter-spacing: -.012em; }
    #camera.window { border-radius: 14px; box-shadow: 0 60px 130px -40px rgba(60, 40, 10, .55), 0 0 0 1px rgba(60, 40, 10, .14); }
    #ring { border-radius: 8px; box-shadow: 0 0 0 3px ${PEN}, 0 0 0 9px rgba(200, 65, 27, .16), 0 18px 40px -12px rgba(60, 40, 10, .35); }
    #ripple { background: rgba(200, 65, 27, .35); box-shadow: 0 0 0 2px rgba(200, 65, 27, .5); }
  `,
});
const C = { x: 960, y: 540 };

// The hook: what's hard about papers, and what's wrong with the usual shortcut.
word(4, big("Research papers are written for experts.", "s"), "light");
word(4, big(`Dense. Full of jargon.<br>No one to ask.`, "m"), "light");
word(5, `${big("So you paste it into a chatbot.", "s")}${sub("And get a confident summary. Is it what the paper says? You can't tell.")}`, "dark");
word(4, big(`What if the paper could ${grad("teach you?")}`, "s"), "light");
// The product.
word(6, `${logo}${big("PaperSensei")}${sub("Understand any research paper in an evening.")}`, "light", { mark: "reveal", hit: true });
ui(5, { snap: "library", cam: [0.7, C, 0.78, C] });

// 1. Drop in a paper.
word(4, `${eyebrow("01 · Drop in a paper")}${big("Any paper. One click.", "m")}${sub("A PDF, an arXiv link, or the bundled sample.")}`, "light");
ui(7, {
  snap: "library",
  cam: [1.85, { x: 960, y: 690 }, 1.9, { x: 960, y: 700 }],
  cursor: { path: [[0, { x: 760, y: 860 }], [2.6, ".library .sample"], [4.4, ".library .sample"]], click: [2.9] },
  ring: [{ sel: ".level label.on", from: 0.5, to: 2.4 }],
  caption: ["Start", "Pick your level, open a paper"],
});
ui(9, { snap: stream("build", 0, 0.3), cam: [1.3, { x: 740, y: 415 }, 1.36, { x: 740, y: 440 }], caption: ["Live build", "Lessons appear as they're written"] });

// 2. A course, written for you.
word(4, `${eyebrow("02 · A short course")}${big("Plain words. A diagram for each idea.", "s")}`, "light");
ui(8, { snap: "build-done", cam: [1.55, { x: 1085, y: 600 }, 1.6, { x: 1085, y: 800 }], caption: ["Your course", "A summary, a plan, then lessons"] });
ui(9, { snap: "term", cam: [1.8, { x: 921, y: 410 }, 2.0, { x: 880, y: 400 }], caption: ["Glossary", "Hover a term for its meaning"] });
ui(8, { snap: "diagram", cam: [1.65, { x: 940, y: 450 }, 1.8, { x: 921, y: 430 }], caption: ["Diagrams", "Each idea, drawn"] });

// 3. The hero: grounded in the paper.
word(3, big("Summaries sound sure.", "s"), "dark", { mark: "heroIn" });
word(3, big("Even when they're wrong.", "s"), "dark");
word(5, `${big(grad("This one shows you the page."), "s")}${sub("Every quote a lesson uses is checked against the paper's text.")}`, "light", { mark: "hero", hit: true });
ui(9, { snap: "lesson", cam: [1.5, { x: 1100, y: 420 }, 1.95, { x: 1440, y: 390 }], ring: [{ sel: ".margin .note", from: 1.8 }], caption: ["From the paper", "Each quote, found in the text"] });
const Q = "Why does reciprocal rank fusion ignore raw scores?";
ui(5, {
  snap: "tutor",
  type: { sel: ".tutor input", text: Q, from: 0.3, to: 2.3 },
  cursor: { path: [[0, { x: 1560, y: 860 }], [2.3, ".tutor form button"], [3.2, ".tutor form button"]], click: [2.55] },
  cam: [1.9, { x: 1500, y: 900 }, 1.95, { x: 1500, y: 920 }],
  caption: ["Ask the sensei", "Answers cite the page"],
});
ui(7, { snap: stream("ask", 0, 0.3), cam: [1.9, { x: 1700, y: 300 }, 1.95, { x: 1700, y: 310 }], caption: ["Ask the sensei", "Answers cite the page"] });
ui(8, {
  snap: [[0, "ask-done"], [1.5, "cite"]],
  cursor: { path: [[0, { x: 1450, y: 600 }], [1.1, ".tutor .answer .pg"], [2.4, ".tutor .answer .pg"], [3.4, { x: 1820, y: 520 }]], click: [1.3] },
  cam: [1.95, { x: 1700, y: 300 }, 2.1, { x: 1700, y: 330 }],
  caption: ["Citations", "Tap the page, read the sentence"],
});
ui(9, { snap: stream("off", 0, 0.3), cam: [1.85, { x: 1700, y: 400 }, 1.95, { x: 1700, y: 480 }], caption: ["Honest", "If the paper doesn't say, it tells you"] }, { mark: "heroEnd" });

// 4. Learn at your level.
word(4, `${eyebrow("03 · At your level")}${big("Test yourself. Go deeper.", "s")}`, "light");
ui(9, {
  snap: [[0, "quiz"], [2.4, "quiz-done"]],
  cursor: { path: [[0, { x: 1300, y: 760 }], [1.8, ".quiz .option:nth-child(1)"], [2.6, ".quiz .option:nth-child(1)"], [3.6, { x: 1350, y: 700 }]], click: [2.0] },
  cam: [1.55, { x: 921, y: 720 }, 1.62, { x: 921, y: 740 }],
  caption: ["Quiz", "Check your understanding"],
});
ui(7, {
  snap: [[0, "lesson"], [2.2, "rewrite-busy"], [3.6, "rewrite-done"]],
  cursor: { path: [[0, { x: 1100, y: 500 }], [1.6, ".levels button:nth-of-type(3)"], [2.6, ".levels button:nth-of-type(3)"], [3.6, { x: 1150, y: 420 }]], click: [1.9] },
  cam: [1.8, { x: 921, y: 300 }, 1.75, { x: 921, y: 340 }],
  caption: ["Your level", "Explain it again, for an expert"],
});

// Day and night.
word(2, big("Day reading.", "m"), "light");
ui(3, { snap: "off-done", cam: [0.82, C, 0.86, C] });
word(2, big("Night reading.", "m"), "dark");
ui(3, { snap: "night", cam: [0.82, C, 0.86, C] });

// The angles: how it's built, and who it's for.
word(7, `${eyebrow("Under the hood")}${big("A team of agents, not one long prompt.", "s")}${chips("LangGraph fan-out", "Parallel lesson writers", "Quote verification", "Claude citations", "Prompt caching", "Structured outputs", "SSE streaming")}`, "light");
word(6, `${big("For students, engineers and the curious.", "s")}${sub("Anyone handed a paper and one evening to understand it.")}`, "dark");
word(7, `${logo}${big(grad("PaperSensei"))}${sub("Understand any paper in an evening · by Balaji Sri Raj")}`, "light", { mark: "outro" });

run((m) => ({ teaser: [m.reveal, m.reveal + 33 * BEAT], poster: [m.hero + 6 * BEAT, 0] }));
