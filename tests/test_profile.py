"""Tests del perfil de candidato (config/profile.py)."""

from __future__ import annotations

from config.profile import CANDIDATE_PROFILE, get_candidate_context


def test_perfil_carga_por_defecto() -> None:
    """El perfil se instancia con valores por defecto válidos."""
    assert CANDIDATE_PROFILE.name
    assert CANDIDATE_PROFILE.target_roles
    assert CANDIDATE_PROFILE.skills_ai_agents


def test_contexto_markdown_generado() -> None:
    """El contexto de perfil se renderiza como markdown con las secciones clave."""
    ctx = get_candidate_context()
    assert "PERFIL PROFESIONAL DEL CANDIDATO" in ctx
    assert "Roles Objetivo" in ctx
    assert "Competencias Técnicas Clave" in ctx


def test_contexto_no_expone_datos_personales_reales() -> None:
    """El perfil de ejemplo NO debe contener datos personales reales."""
    ctx = get_candidate_context().lower()
    for dato in ("raúl", "cancela", "55.000", "60.000", "madrid", "cárnica"):
        assert dato not in ctx, f"El perfil público contiene dato sensible: {dato}"


def test_perfil_es_inmutable() -> None:
    """El perfil es un dataclass frozen: no se puede modificar en runtime."""
    import dataclasses

    import pytest

    assert dataclasses.is_dataclass(CANDIDATE_PROFILE)
    with pytest.raises(dataclasses.FrozenInstanceError):
        CANDIDATE_PROFILE.name = "otro"  # type: ignore[misc]


def test_competencias_tienen_contenido() -> None:
    """Los grupos de competencias no están vacíos."""
    assert len(CANDIDATE_PROFILE.skills_ai_agents) > 0
    assert len(CANDIDATE_PROFILE.skills_cloud_infra) > 0
    assert len(CANDIDATE_PROFILE.skills_automation_scripting) > 0
