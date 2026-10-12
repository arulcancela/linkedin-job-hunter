"""Local job vault and SQLite idempotency history to prevent duplicate evaluations."""

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from engine.schemas import JobEvaluation


class JobVault:
    """Manages offline markdown dossiers and deduplication database."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.apps_dir = self.base_dir / "applications"
        self.data_dir = self.base_dir / "data"
        self.db_path = self.data_dir / "job_history.db"

        self.apps_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create history table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    company TEXT,
                    title TEXT,
                    score INTEGER,
                    decision TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def is_already_processed(self, url: str) -> bool:
        """Check if a URL was already evaluated."""
        if not url:
            return False
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_jobs WHERE url = ?", (url,))
            return cursor.fetchone() is not None

    def record_job(self, evaluation: JobEvaluation, url: str):
        """Insert or ignore job record in history DB."""
        if not url:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_jobs (url, company, title, score, decision)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url, evaluation.company_name, evaluation.job_title, evaluation.fit_score, evaluation.decision),
            )
            conn.commit()

    def save_markdown_dossier(self, evaluation: JobEvaluation, source_url: str = "") -> Path:
        """Save a clean, formatted Markdown brief for the candidate's local archive."""
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_company = re.sub(r"[^\w\-]", "_", evaluation.company_name.lower())[:25]
        safe_title = re.sub(r"[^\w\-]", "_", evaluation.job_title.lower())[:30]
        filename = f"{date_str}_{safe_company}_{safe_title}.md"
        filepath = self.apps_dir / filename

        reasons_md = "\n".join(f"- {r}" for r in evaluation.match_reasons)
        missing_md = "\n".join(f"- {m}" for m in evaluation.missing_keywords) if evaluation.missing_keywords else "Ninguna detectada"

        content = f"""# Dossier de Postulación: {evaluation.job_title} @ {evaluation.company_name}

- **Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Fit Score:** {evaluation.fit_score}/100 ({evaluation.decision})
- **100% Remoto:** {"Sí" if evaluation.is_remote else "No"}
- **Salario / Banda:** {evaluation.salary_assessment}
- **Jornada & Conciliación:** {evaluation.work_life_balance_rating}
- **Prestigio Empresa:** {evaluation.company_prestige_notes}
- **Idioma Trabajo:** {evaluation.language_assessment}
- **URL Oferta:** {source_url or "Pegado manual"}

---

## 🎯 Motivos de Encaje
{reasons_md}

## ⚠️ Brechas Técnicas / Keywords Ausentes
{missing_md}

## 💡 Consejos de Adaptación de CV
{evaluation.cv_tailoring_tips}

---

## ✉️ Carta de Presentación (Cover Letter)
```text
{evaluation.cover_letter}
```

---

## 🤝 Nota de Conexión para LinkedIn (<300 chars)
```text
{evaluation.recruiter_outreach_note}
```
"""
        filepath.write_text(content, encoding="utf-8")
        return filepath
