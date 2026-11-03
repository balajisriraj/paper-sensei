import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Library } from "./Library";
import { PaperView } from "./PaperView";
import { navigate, usePath } from "./router";
import "./styles.css";

function App() {
  const path = usePath();
  const [theme, setTheme] = useState(document.documentElement.dataset.theme ?? "day");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("papersensei.theme", theme);
  }, [theme]);
  const paper = path.match(/^\/paper\/([a-f0-9]+)$/);

  return (
    <>
      <header className="bar">
        <button className="brand" onClick={() => navigate("/")}>
          <span className="seal" aria-hidden="true">
            PS
          </span>
          <span>
            Paper<i>Sensei</i>
          </span>
        </button>
        <button className="theme" onClick={() => setTheme(theme === "day" ? "night" : "day")} aria-label="Toggle night reading">
          {theme === "day" ? "Night reading" : "Day reading"}
        </button>
      </header>
      {paper ? <PaperView key={paper[1]} id={paper[1]} /> : <Library />}
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
