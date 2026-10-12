"""Candidate profile definition (Single Source of Truth) for AI evaluation.

Plantilla de ejemplo: este es el perfil ficticio que se usa para evaluar
ofertas. Cópialo y edítalo con tus datos reales para adaptar el sistema a tu
caso. Es un objeto *frozen* de datos sin lógica: modifica los valores por
defecto con tu información profesional.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateProfile:
    """Master profile representation used to score job offers."""

    name: str = "Nombre Apellido"
    target_roles: list[str] = field(
        default_factory=lambda: [
            "Cloud Automation Engineer",
            "Platform Engineer",
            "DevOps Engineer",
            "AI Solutions Engineer",
        ]
    )
    education: str = "Grado en Ingeniería Informática (o disciplina equivalente)"
    experience_summary: str = (
        "Descripción breve de tu trayectoria: años de experiencia, dominios "
        "técnicos y tipo de entornos en los que has trabajado."
    )
    work_preference: str = "Remoto / Híbrido (Ubicación: Ciudad, País)"
    languages: list[str] = field(
        default_factory=lambda: [
            "Español (nativo)",
            "Inglés (nivel profesional)",
        ]
    )
    salary_conditions: str = (
        "Rango salarial objetivo (ajústalo a tu situación). Ej.: 'A convenir según rol'."
    )
    working_hours_and_balance: str = (
        "Preferencias de jornada, flexibilidad y conciliación."
    )
    contract_flexibility: str = (
        "Modalidades contractuales aceptadas (empleado, freelance, B2B...)."
    )
    company_prestige_criteria: str = (
        "Criterios de empresa que te interesan (producto, sector, tamaño...)."
    )
    differential_value: str = (
        "Describe tu valor diferencial: qué te hace distinto de otros candidatos."
    )
    skills_ai_agents: list[str] = field(
        default_factory=lambda: [
            "Diseño de prompts y system prompts",
            "Integración de APIs LLM (Gemini, DeepSeek, Claude, OpenAI)",
            "Modelos LLM locales (Ollama)",
            "Arquitecturas basadas en agentes y RAG",
        ]
    )
    skills_cloud_infra: list[str] = field(
        default_factory=lambda: [
            "Google Cloud Platform (GCP)",
            "Automatización de infraestructura",
            "Linux",
            "Docker y contenerización",
        ]
    )
    skills_automation_scripting: list[str] = field(
        default_factory=lambda: [
            "Python (automatización, APIs, scraping)",
            "Bash / Shell scripting",
            "Scripting de plataformas (GAS, etc.)",
            "Automatización No-Code/Low-Code (Make, n8n)",
        ]
    )

    def to_markdown_summary(self) -> str:
        """Render candidate profile as structured markdown for LLM prompt injections."""
        return f"""### PERFIL PROFESIONAL DEL CANDIDATO (FUENTE DE VERDAD)

- **Nombre:** {self.name}
- **Roles Objetivo:** {", ".join(self.target_roles)}
- **Formación Académica:** {self.education}
- **Trayectoria:** {self.experience_summary}
- **Modalidad & Ubicación:** {self.work_preference}
- **Idiomas:** {", ".join(self.languages)}
- **Condiciones Salariales:** {self.salary_conditions}
- **Jornada & Conciliación:** {self.working_hours_and_balance}
- **Modalidad Contractual:** {self.contract_flexibility}
- **Prestigio de la Empresa:** {self.company_prestige_criteria}

#### Enfoque Diferencial ("Superpoder"):
{self.differential_value}

#### Competencias Técnicas Clave:
1. **IA, Agentes & Generative AI:**
   - {chr(10).join(f"- {s}" for s in self.skills_ai_agents)}

2. **Cloud & Infraestructura Enterprise:**
   - {chr(10).join(f"- {s}" for s in self.skills_cloud_infra)}

3. **Scripting, Código & Automatización:**
   - {chr(10).join(f"- {s}" for s in self.skills_automation_scripting)}
"""


CANDIDATE_PROFILE = CandidateProfile()


def get_candidate_context() -> str:
    """Helper function to fetch candidate profile context."""
    return CANDIDATE_PROFILE.to_markdown_summary()
