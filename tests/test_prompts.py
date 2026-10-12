"""Tests de la construcción de prompts (engine/prompts.py)."""

from __future__ import annotations

from config.profile import get_candidate_context
from engine.prompts import SYSTEM_INSTRUCTION, build_evaluation_prompt


def test_instruccion_incluye_contexto_de_perfil() -> None:
    """El system prompt embebe el contexto del perfil del candidato."""
    assert "PERFIL PROFESIONAL DEL CANDIDATO" in SYSTEM_INSTRUCTION


def test_instruccion_define_criterios_de_decision() -> None:
    """El prompt define explícitamente el umbral APTA / NO_APTA."""
    assert "APTA" in SYSTEM_INSTRUCTION
    assert "NO_APTA" in SYSTEM_INSTRUCTION


def test_instruccion_pide_json_estructurado() -> None:
    """El prompt exige salida JSON con campos clave."""
    for campo in ("fit_score", "decision", "cover_letter", "recruiter_outreach_note"):
        assert campo in SYSTEM_INSTRUCTION


def test_instruccion_sin_datos_personales() -> None:
    """El prompt no expone datos personales reales."""
    low = SYSTEM_INSTRUCTION.lower()
    for dato in ("raúl", "cancela", "55.000", "madrid", "físico"):
        assert dato not in low, f"El prompt contiene dato sensible: {dato}"


def test_build_prompt_incluye_texto_y_url() -> None:
    """El prompt de usuario incluye la oferta y su origen."""
    prompt = build_evaluation_prompt("Buscamos un ingeniero Python", "https://x.com/oferta/1")
    assert "Buscamos un ingeniero Python" in prompt
    assert "https://x.com/oferta/1" in prompt


def test_build_prompt_sin_url_es_valido() -> None:
    """El prompt funciona aunque no haya URL de origen."""
    prompt = build_evaluation_prompt("Oferta suelta")
    assert "Oferta suelta" in prompt
    assert "Origen de la oferta" not in prompt


def test_contexto_embebido_coincide() -> None:
    """El contexto usado en el system prompt es el del perfil."""
    ctx = get_candidate_context()
    assert ctx in SYSTEM_INSTRUCTION
