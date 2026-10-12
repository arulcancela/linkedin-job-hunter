"""Pydantic schemas for structured LLM evaluation output."""

from typing import List, Literal
from pydantic import BaseModel, Field, field_validator


class JobEvaluation(BaseModel):
    """Structured evaluation output matching required JSON schema."""

    company_name: str = Field(
        ...,
        description="Nombre de la empresa contratante o anunciante",
    )
    job_title: str = Field(
        ...,
        description="Título o rol del puesto de trabajo",
    )
    is_remote: bool = Field(
        ...,
        description="Indica si la oferta ofrece o permite trabajo 100% remoto",
    )
    fit_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Puntuación cuantitativa de encaje de 0 a 100",
    )
    decision: Literal["APTA", "NO_APTA"] = Field(
        ...,
        description="'APTA' si el score >= 75 (o umbral configurado), 'NO_APTA' si score < 75",
    )
    salary_assessment: str = Field(
        ...,
        description=(
            "Diagnóstico salarial: salario publicado o estimación realista de mercado. "
            "Debe indicar si cumple con el mínimo y el objetivo salarial definidos en el perfil del candidato."
        ),
    )
    work_life_balance_rating: str = Field(
        ...,
        description=(
            "Evaluación de la jornada y conciliación (flexibilidad horaria, jornada parcial o completa, "
            "ausencia de guardias 24/7 abusivas)."
        ),
    )
    company_prestige_notes: str = Field(
        ...,
        description=(
            "Evaluación de reputación de la empresa (empresa de producto, líder del sector vs consultora/bodyshop masivo)."
        ),
    )
    language_assessment: str = Field(
        ...,
        description=(
            "Diagnóstico de idioma de trabajo: especifica si el día a día hablado/equipo es en español (muy valorado como PLUS), "
            "o si el entorno oral y diario es 100% en inglés."
        ),
    )
    match_reasons: List[str] = Field(
        ...,
        min_length=1,
        description="Lista de motivos concretos de encaje entre la oferta y el perfil del candidato",
    )
    missing_keywords: List[str] = Field(
        default_factory=list,
        description="Palabras clave o habilidades técnicas ausentes o débiles en el perfil frente a la oferta",
    )
    cv_tailoring_tips: str = Field(
        ...,
        description="Ajustes y consejos rápidos recomendados para adaptar el CV a esta vacante específica",
    )
    cover_letter: str = Field(
        ...,
        description=(
            "Carta de presentación corta (120-150 palabras) resaltando el encaje del perfil del candidato "
            "e AI-Augmented Engineer con las necesidades concretas del puesto."
        ),
    )
    recruiter_outreach_note: str = Field(
        ...,
        max_length=320,
        description=(
            "Nota de conexión para LinkedIn (<300 caracteres recomendados) dirigida al recruiter "
            "o Hiring Manager, citando un detalle específico de la oferta."
        ),
    )

    @field_validator("decision", mode="after")
    @classmethod
    def validate_decision_consistency(cls, v: str, info) -> str:
        """Enforce strict consistency between fit_score and decision."""
        # Note: In Pydantic V2, info.data contains previously validated fields
        fit_score = info.data.get("fit_score")
        if fit_score is not None:
            expected = "APTA" if fit_score >= 75 else "NO_APTA"
            return expected
        return v
