"""AI Evaluator implementation supporting Google Gemini and DeepSeek."""

import json
import logging
from typing import Optional
import requests

from config.settings import Settings, get_settings
from engine.prompts import SYSTEM_INSTRUCTION, build_evaluation_prompt
from engine.schemas import JobEvaluation

logger = logging.getLogger("ai_job_hunter.evaluator")


class EvaluationError(Exception):
    """Raised when the LLM evaluation fails."""
    pass


class JobEvaluator:
    """Evaluates job postings against the candidate's master profile."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def evaluate(self, job_text: str, source_url: str = "") -> JobEvaluation:
        """
        Evaluate job text against candidate profile using the configured LLM provider.

        Args:
            job_text: Cleaned text content of the job posting.
            source_url: Optional source URL for context.

        Returns:
            JobEvaluation: Validated structured evaluation.
        """
        provider = self.settings.llm_provider.lower()

        if provider == "gemini":
            return self._evaluate_with_gemini(job_text, source_url)
        elif provider == "deepseek":
            return self._evaluate_with_deepseek(job_text, source_url)
        else:
            raise ValueError(f"Proveedor de LLM no soportado: '{provider}'. Usa 'gemini' o 'deepseek'.")

    def _evaluate_with_gemini(self, job_text: str, source_url: str) -> JobEvaluation:
        """Call Google Gemini API using the official google-genai SDK."""
        if not self.settings.gemini_api_key:
            raise EvaluationError(
                "GEMINI_API_KEY no está configurada en las variables de entorno o archivo .env"
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise EvaluationError(
                "El paquete 'google-genai' no está instalado. Ejecuta: pip install -r requirements.txt"
            ) from exc

        prompt = build_evaluation_prompt(job_text, source_url)

        try:
            client = genai.Client(api_key=self.settings.gemini_api_key)
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=JobEvaluation,
                temperature=0.2,
            )

            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=config,
            )

            raw_text = response.text
            if not raw_text:
                raise EvaluationError("Gemini devolvió una respuesta vacía.")

            # Parse and validate with Pydantic
            evaluation = JobEvaluation.model_validate_json(raw_text)
            return evaluation

        except Exception as exc:
            if isinstance(exc, EvaluationError):
                raise
            raise EvaluationError(f"Fallo al invocar la API de Gemini: {exc}") from exc

    def _evaluate_with_deepseek(self, job_text: str, source_url: str) -> JobEvaluation:
        """Call DeepSeek API using OpenAI-compatible JSON mode."""
        if not self.settings.deepseek_api_key:
            raise EvaluationError(
                "DEEPSEEK_API_KEY no está configurada en las variables de entorno o archivo .env"
            )

        prompt = build_evaluation_prompt(job_text, source_url)

        headers = {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.settings.deepseek_model,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        endpoint = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            if response.status_code != 200:
                raise EvaluationError(
                    f"Error de DeepSeek API ({response.status_code}): {response.text}"
                )

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            evaluation = JobEvaluation.model_validate_json(content)
            return evaluation

        except Exception as exc:
            if isinstance(exc, EvaluationError):
                raise
            raise EvaluationError(f"Fallo al invocar la API de DeepSeek: {exc}") from exc
