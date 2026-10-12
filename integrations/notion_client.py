"""Notion database integration for recording job evaluations."""

import logging
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from config.settings import Settings, get_settings
from engine.schemas import JobEvaluation

logger = logging.getLogger("ai_job_hunter.notion")


class NotionJobSync:
    """Manages recording and updating job evaluation entries in a Notion database."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = Client(auth=self.settings.notion_token) if self.settings.notion_token else None
        self.database_id = self.settings.notion_database_id

    def sync_evaluation(self, evaluation: JobEvaluation, source_url: str = "") -> str | None:
        """
        Create a new row and rich content blocks in the Notion database.

        Args:
            evaluation: Validated JobEvaluation instance.
            source_url: Source link of the job posting.

        Returns:
            Optional[str]: URL of the created Notion page, or None if skipped/failed.
        """
        if not self.settings.is_notion_configured():
            logger.warning("Notion no está configurado (NOTION_TOKEN o NOTION_DATABASE_ID faltantes). Saltando sync.")
            return None

        # Build resilient Notion properties dictionary
        properties: dict[str, Any] = {
            "Título": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": evaluation.job_title[:2000]},
                    }
                ]
            },
            "Empresa": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": evaluation.company_name[:2000]},
                    }
                ]
            },
            "Score": {
                "number": evaluation.fit_score,
            },
            "Estado": {
                "select": {
                    "name": evaluation.decision,
                }
            },
            "Remoto": {
                "checkbox": evaluation.is_remote,
            },
        }

        # URL property if available
        if source_url and source_url.startswith(("http://", "https://")):
            properties["URL"] = {
                "url": source_url[:2000],
            }

        # Missing Keywords
        if evaluation.missing_keywords:
            keywords_text = ", ".join(evaluation.missing_keywords)
            properties["Missing Keywords"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": keywords_text[:2000]},
                    }
                ]
            }

        # Outreach Note snippet
        properties["Nota de Outreach"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": evaluation.recruiter_outreach_note[:2000]},
                }
            ]
        }

        # Rich page body blocks for in-depth viewing inside Notion
        children_blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🎯 Motivos de Encaje (Match Reasons)"}}]
                },
            },
            *[
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": reason[:2000]}}]
                    },
                }
                for reason in evaluation.match_reasons
            ],
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🛠️ Ajustes Recomendados al CV"}}]
                },
            },
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": evaluation.cv_tailoring_tips[:2000]}}],
                    "icon": {"type": "emoji", "emoji": "💡"},
                },
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "✉️ Carta de Presentación (Cover Letter)"}}]
                },
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": evaluation.cover_letter[:2000]}}]
                },
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🤝 Mensaje de Conexión para Recruiter (<300 caracteres)"}}]
                },
            },
            {
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": evaluation.recruiter_outreach_note[:2000]}}]
                },
            },
        ]

        try:
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children_blocks,
            )
            page_url = response.get("url")
            logger.info("Fila creada exitosamente en Notion: %s", page_url)
            return page_url
        except APIResponseError as exc:
            logger.error("Error de la API de Notion al crear la página: %s", exc)
            # Fallback attempt: if database is missing optional properties, try with minimum core properties
            return self._retry_with_minimal_properties(evaluation, source_url)

    def _retry_with_minimal_properties(self, evaluation: JobEvaluation, source_url: str) -> str | None:
        """Fallback in case the user's Notion database doesn't have all exact property columns configured."""
        try:
            minimal_properties = {
                "Título": {
                    "title": [{"type": "text", "text": {"content": f"{evaluation.job_title} @ {evaluation.company_name}"}}]
                }
            }
            if source_url:
                minimal_properties["URL"] = {"url": source_url}

            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=minimal_properties,
            )
            return response.get("url")
        except Exception as retry_exc:
            logger.error("Fallo definitivo al guardar en Notion: %s", retry_exc)
            return None
