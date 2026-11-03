"""SQLite persistence for papers and lessons. PDFs live next to the database."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.dir = Path(data_dir)
        (self.dir / "papers").mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "papersensei.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.db:
            self.db.executescript(
                """
                CREATE TABLE IF NOT EXISTS papers (
                  id TEXT PRIMARY KEY, title TEXT, filename TEXT, status TEXT, level TEXT, error TEXT,
                  pages INTEGER, parsed TEXT, plan TEXT, glossary TEXT, grounding REAL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS lessons (
                  paper_id TEXT, idx INTEGER, data TEXT, PRIMARY KEY (paper_id, idx));
                """
            )

    def pdf_path(self, paper_id: str) -> Path:
        return self.dir / "papers" / f"{paper_id}.pdf"

    def create(self, filename: str, pdf: bytes, parsed: dict, level: str) -> str:
        paper_id = uuid.uuid4().hex[:12]
        self.pdf_path(paper_id).write_bytes(pdf)
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO papers(id, title, filename, status, level, pages, parsed) VALUES (?,?,?,?,?,?,?)",
                (paper_id, parsed["title"], filename, "building", level, parsed["pages"], json.dumps(parsed)),
            )
        return paper_id

    def update(self, paper_id: str, **fields) -> None:
        cols = {k: json.dumps(v) if k in ("plan", "glossary", "parsed") else v for k, v in fields.items()}
        sets = ", ".join(f"{k} = ?" for k in cols)
        with self.lock, self.db:
            self.db.execute(f"UPDATE papers SET {sets} WHERE id = ?", (*cols.values(), paper_id))

    def save_lesson(self, paper_id: str, lesson: dict) -> None:
        with self.lock, self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO lessons(paper_id, idx, data) VALUES (?,?,?)",
                (paper_id, lesson["index"], json.dumps(lesson)),
            )

    def clear_lessons(self, paper_id: str) -> None:
        with self.lock, self.db:
            self.db.execute("DELETE FROM lessons WHERE paper_id = ?", (paper_id,))

    def get(self, paper_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if not row:
            return None
        paper = dict(row)
        for key in ("parsed", "plan", "glossary"):
            paper[key] = json.loads(paper[key]) if paper[key] else None
        rows = self.db.execute("SELECT data FROM lessons WHERE paper_id = ? ORDER BY idx", (paper_id,)).fetchall()
        paper["lessons"] = [json.loads(r["data"]) for r in rows]
        return paper

    def list(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, title, filename, status, level, pages, grounding, created_at, "
            "(SELECT count(*) FROM lessons l WHERE l.paper_id = papers.id) AS lessons "
            "FROM papers ORDER BY created_at DESC, rowid DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, paper_id: str) -> bool:
        with self.lock, self.db:
            self.db.execute("DELETE FROM lessons WHERE paper_id = ?", (paper_id,))
            gone = self.db.execute("DELETE FROM papers WHERE id = ?", (paper_id,)).rowcount
        self.pdf_path(paper_id).unlink(missing_ok=True)
        return bool(gone)
