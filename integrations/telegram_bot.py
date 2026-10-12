"""Telegram bot integration for sending job alert notifications."""

import html
import logging
from typing import Optional
import requests

from config.settings import Settings, get_settings
from engine.schemas import JobEvaluation

logger = logging.getLogger("ai_job_hunter.telegram")


class TelegramAlertBot:
    """Sends rich Telegram notifications for jobs matching or exceeding criteria."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.bot_token = self.settings.telegram_bot_token
        self.chat_id = self.settings.telegram_chat_id

    def send_alert(
        self,
        evaluation: JobEvaluation,
        source_url: str = "",
        notion_url: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """
        Send a Telegram notification if evaluation is APTA or if force=True.

        Args:
            evaluation: Validated JobEvaluation instance.
            source_url: URL to the job posting.
            notion_url: URL to the recorded Notion page.
            force: Send regardless of fit_score threshold.

        Returns:
            bool: True if alert was sent successfully, False otherwise.
        """
        if not self.settings.is_telegram_configured():
            logger.warning("Telegram no está configurado (TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID faltantes). Saltando alerta.")
            return False

        if not force and evaluation.decision != "APTA":
            logger.info("Oferta no clasificada como APTA (score %d < %d). No se envía alerta de Telegram.",
                        evaluation.fit_score, self.settings.fit_score_threshold)
            return False

        message_html = self._format_message_html(evaluation, source_url, notion_url)
        return self._post_to_telegram(message_html)

    def _format_message_html(
        self,
        evaluation: JobEvaluation,
        source_url: str = "",
        notion_url: Optional[str] = None,
    ) -> str:
        """Render alert message in clean Telegram HTML format."""
        # Progress bar representation
        filled_bars = int(round(evaluation.fit_score / 10))
        bar = "🟩" * filled_bars + "⬜" * (10 - filled_bars)

        safe_title = html.escape(evaluation.job_title)
        safe_company = html.escape(evaluation.company_name)
        remote_icon = "🌐 100% Remoto" if evaluation.is_remote else "🏢 Híbrido / Presencial"

        lines = [
            f"🔥 <b>NUEVA OPORTUNIDAD APTA ({evaluation.fit_score}%)</b>",
            f"━━━━━━━━━━━━━━━━━━━",
            f"💼 <b>Puesto:</b> {safe_title}",
            f"🏢 <b>Empresa:</b> {safe_company}",
            f"📍 <b>Modalidad:</b> {remote_icon}",
            f"💶 <b>Salario:</b> {html.escape(evaluation.salary_assessment)}",
            f"⏰ <b>Conciliación:</b> {html.escape(evaluation.work_life_balance_rating)}",
            f"🏛️ <b>Reputación:</b> {html.escape(evaluation.company_prestige_notes)}",
            f"🗣️ <b>Idioma Trabajo:</b> {html.escape(evaluation.language_assessment)}",
            f"📊 <b>Fit Score:</b> {bar} <b>{evaluation.fit_score}/100</b>",
            "",
            "🎯 <b>Puntos Clave de Encaje:</b>",
        ]

        for reason in evaluation.match_reasons[:3]:
            lines.append(f"  • {html.escape(reason)}")

        if evaluation.missing_keywords:
            safe_keywords = html.escape(", ".join(evaluation.missing_keywords[:5]))
            lines.extend([
                "",
                f"⚠️ <b>Keywords Ausentes:</b> <i>{safe_keywords}</i>",
            ])

        # Recruiter message pre-formatted for 1-tap copy
        safe_outreach = html.escape(evaluation.recruiter_outreach_note)
        lines.extend([
            "",
            "💬 <b>Nota de Conexión LinkedIn (Toca para copiar):</b>",
            f"<code>{safe_outreach}</code>",
        ])

        # Action links
        links = []
        if source_url:
            links.append(f'<a href="{html.escape(source_url)}">🔗 Ver Oferta</a>')
        if notion_url:
            links.append(f'<a href="{html.escape(notion_url)}">📓 Ver en Notion</a>')

        if links:
            lines.extend(["", " | ".join(links)])

        return "\n".join(lines)

    def _post_to_telegram(self, html_text: str) -> bool:
        """Execute HTTP request to Telegram Bot API."""
        endpoint = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": html_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=15)
            if response.status_code == 200:
                logger.info("Alerta de Telegram enviada con éxito.")
                return True
            else:
                logger.error("Error al enviar a Telegram (%d): %s", response.status_code, response.text)
                return False
        except requests.RequestException as exc:
            logger.error("Excepción de red al contactar con Telegram: %s", exc)
            return False
