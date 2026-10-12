"""Tests de los esquemas Pydantic (engine/schemas.py).

Verifica que el esquema valida correctamente una salida válida de la IA y
rechaza salidas incompletas o con tipos erróneos.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engine.schemas import JobEvaluation


def _payload_valido() -> dict:
    return {
        "company_name": "Acme Corp",
        "job_title": "Cloud Automation Engineer",
        "is_remote": True,
        "fit_score": 85,
        "decision": "APTA",
        "salary_assessment": "60.000€, cumple",
        "work_life_balance_rating": "Flexible",
        "company_prestige_notes": "Producto tech consolidado",
        "language_assessment": "Español en el día a día",
        "match_reasons": ["Encaja en automatización", "Experiencia cloud"],
        "missing_keywords": ["Kubernetes"],
        "cv_tailoring_tips": "Destacar proyectos de automatización",
        "cover_letter": "Carta de prueba con contenido suficiente para la validación.",
        "recruiter_outreach_note": "Hola, me interesa la posición.",
    }


def test_schema_acepta_payload_valido() -> None:
    """Un payload completo se valida sin errores."""
    ev = JobEvaluation(**_payload_valido())
    assert ev.decision == "APTA"
    assert ev.fit_score == 85


def test_schema_rechaza_faltantes() -> None:
    """Falta un campo obligatorio -> error de validación."""
    data = _payload_valido()
    del data["fit_score"]
    with pytest.raises(ValidationError):
        JobEvaluation(**data)


def test_schema_rechaza_tipo_incorrecto() -> None:
    """fit_score no numérico -> error de validación."""
    data = _payload_valido()
    data["fit_score"] = "no-es-un-numero"
    with pytest.raises(ValidationError):
        JobEvaluation(**data)


def test_match_reasons_es_lista() -> None:
    """Los motivos de encaje se normalizan a lista."""
    ev = JobEvaluation(**_payload_valido())
    assert isinstance(ev.match_reasons, list)
    assert len(ev.match_reasons) == 2
