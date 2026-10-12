#!/usr/bin/env python3
"""
AI Job Hunter - CLI Principal & Orquestador de Evaluación y Búsqueda de Empleo.
Asistente de búsqueda y evaluación de empleo mediante IA.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import get_settings
from engine.evaluator import EvaluationError, JobEvaluator
from engine.vault import JobVault
from ingestion.discovery import search_public_remote_jobs
from ingestion.extractor import ExtractionError, extract_job_from_url
from ingestion.text_reader import read_from_clipboard_or_input, read_from_file
from integrations.notion_client import NotionJobSync
from integrations.telegram_bot import TelegramAlertBot

console = Console()


def display_evaluation_summary(evaluation, source_url: str = "", dossier_path: Path | None = None):
    """Render a visually rich terminal dashboard of the evaluation."""
    score_color = "green" if evaluation.fit_score >= 75 else ("yellow" if evaluation.fit_score >= 55 else "red")
    decision_badge = f"[{score_color} bold]{evaluation.decision} ({evaluation.fit_score}%)[/{score_color} bold]"

    table = Table(title="📊 RESUMEN DE EVALUACIÓN DE EMPLEO", show_header=True, header_style="bold cyan")
    table.add_column("Propiedad", style="bold white", width=22)
    table.add_column("Detalle", style="white")

    table.add_row("Puesto", evaluation.job_title)
    table.add_row("Empresa", evaluation.company_name)
    table.add_row("100% Remoto", "✅ Sí" if evaluation.is_remote else "⚠️ No / Híbrido")
    table.add_row("Salario", evaluation.salary_assessment)
    table.add_row("Conciliación", evaluation.work_life_balance_rating)
    table.add_row("Reputación", evaluation.company_prestige_notes)
    table.add_row("Idioma Trabajo", evaluation.language_assessment)
    table.add_row("Fit Score", f"[{score_color} bold]{evaluation.fit_score} / 100[/{score_color} bold]")
    table.add_row("Decisión", decision_badge)
    if source_url:
        table.add_row("URL", source_url)
    if dossier_path:
        table.add_row("Dossier Local", str(dossier_path))

    console.print()
    console.print(table)
    console.print()

    # Match Reasons
    reasons_text = "\n".join(f"• [green]✓[/green] {r}" for r in evaluation.match_reasons)
    console.print(Panel(reasons_text, title="🎯 Puntos Fuertes de Encaje", border_style="green"))

    # Missing Keywords
    if evaluation.missing_keywords:
        missing_text = "\n".join(f"• [yellow]![/yellow] {m}" for m in evaluation.missing_keywords)
        console.print(Panel(missing_text, title="⚠️ Keywords / Skills Ausentes en CV", border_style="yellow"))

    # CV Tailoring Tips
    console.print(Panel(evaluation.cv_tailoring_tips, title="💡 Consejos de Adaptación al CV", border_style="blue"))

    # Cover Letter
    console.print(Panel(evaluation.cover_letter, title="✉️ Carta de Presentación (120-150 palabras)", border_style="magenta"))

    # Recruiter Outreach
    console.print(
        Panel(
            f"[bold cyan]{evaluation.recruiter_outreach_note}[/bold cyan]\n\n"
            f"[dim]Longitud: {len(evaluation.recruiter_outreach_note)} / 300 caracteres permitidos en LinkedIn[/dim]",
            title="🤝 Nota de Conexión para Recruiter (LinkedIn)",
            border_style="cyan",
        )
    )
    console.print()


def process_job(
    job_text: str,
    source_url: str = "",
    dry_run: bool = False,
    force_alert: bool = False,
    provider_override: str | None = None,
):
    """Execute end-to-end processing pipeline for a job description."""
    settings = get_settings()
    if provider_override:
        settings.llm_provider = provider_override

    vault = JobVault()

    # Deduplication check
    if source_url and vault.is_already_processed(source_url):
        console.print(f"[yellow]ℹ️ La oferta '{source_url}' ya fue evaluada previamente. Saltando reprocesado.[/yellow]")
        return

    # 1. AI Evaluation
    with console.status("[bold green]Analizando oferta contra perfil con IA...", spinner="dots"):
        evaluator = JobEvaluator(settings)
        evaluation = evaluator.evaluate(job_text, source_url)

    # 2. Local Vault (Offline Markdown + History)
    dossier_path = vault.save_markdown_dossier(evaluation, source_url)
    vault.record_job(evaluation, source_url)

    # 3. Terminal Presentation
    display_evaluation_summary(evaluation, source_url, dossier_path)

    if dry_run:
        console.print("[yellow]Modo Dry-Run activo: omitiendo sincronización con Notion y alertas de Telegram.[/yellow]")
        return

    # 4. Notion Sync
    notion_url = None
    if settings.is_notion_configured():
        with console.status("[bold blue]Guardando registro en base de datos de Notion...", spinner="dots"):
            notion_sync = NotionJobSync(settings)
            notion_url = notion_sync.sync_evaluation(evaluation, source_url)
            if notion_url:
                console.print(f"[green]✔ Registro guardado en Notion:[/green] {notion_url}")
            else:
                console.print("[yellow]⚠ No se pudo sincronizar en Notion (revisa NOTION_DATABASE_ID).[/yellow]")
    else:
        console.print("[dim]ℹ️ Notion no configurado en .env (omitido).[/dim]")

    # 5. Telegram Alert
    if settings.is_telegram_configured():
        if evaluation.decision == "APTA" or force_alert:
            with console.status("[bold magenta]Enviando alerta a Telegram...", spinner="dots"):
                telegram_bot = TelegramAlertBot(settings)
                sent = telegram_bot.send_alert(
                    evaluation=evaluation,
                    source_url=source_url,
                    notion_url=notion_url,
                    force=force_alert,
                )
                if sent:
                    console.print("[green]✔ Alerta enviada con éxito a Telegram.[/green]")
                else:
                    console.print("[red]✖ Error al enviar alerta a Telegram.[/red]")
        else:
            console.print(f"[dim]ℹ️ Score ({evaluation.fit_score}%) inferior al umbral ({settings.fit_score_threshold}%). No se envía Telegram.[/dim]")
    else:
        console.print("[dim]ℹ️ Telegram no configurado en .env (omitido).[/dim]")


def run_proactive_hunt(
    keywords: str,
    limit: int,
    dry_run: bool = False,
    watch: bool = False,
    interval_minutes: int = 120,
):
    """Execute proactive job discovery mode (one-shot or continuous watch mode)."""
    while True:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(
            Panel(
                f"[{now_str}] Buscando ofertas remotas con keywords: [bold cyan]{keywords}[/bold cyan] (Límite: {limit})",
                title="🔍 MODO CAZA PROACTIVA",
            )
        )

        with console.status("[bold green]Descubriendo ofertas remotas recientes...", spinner="dots"):
            jobs = search_public_remote_jobs(keywords=keywords, limit=limit)

        if not jobs:
            console.print("[yellow]No se encontraron nuevas ofertas públicas con los criterios actuales.[/yellow]")
        else:
            console.print(f"[green]Se han descubierto {len(jobs)} ofertas para analizar:[/green]")
            vault = JobVault()

            for idx, job in enumerate(jobs, start=1):
                console.rule(f"[bold cyan]Oferta #{idx}: {job.title} en {job.company} ({job.source})[/bold cyan]")
                if vault.is_already_processed(job.url):
                    console.print(f"[dim]Saltando (ya evaluada previamente): {job.url}[/dim]")
                    continue

                try:
                    _, text = extract_job_from_url(job.url)
                    process_job(job_text=text, source_url=job.url, dry_run=dry_run)
                except Exception as exc:
                    console.print(f"[red]Error procesando '{job.title}': {exc}[/red]")

        if not watch:
            break

        console.print(f"\n[dim]⏳ Próximo rastreo en {interval_minutes} minutos. Esperando en segundo plano (Ctrl+C para salir)...[/dim]\n")
        try:
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            console.print("[yellow]\nModo watch detenido por el usuario.[/yellow]")
            break


def main():
    parser = argparse.ArgumentParser(
        description="AI Job Hunter - Sistema Inteligente de Búsqueda y Evaluación de Empleo."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--url", "-u", type=str, help="URL pública de la oferta (LinkedIn, web)")
    group.add_argument("--paste", "-p", action="store_true", help="Pega interactivamente el texto de la oferta en consola")
    group.add_argument("--file", "-f", type=str, help="Ruta a un archivo local de texto con la oferta")
    group.add_argument("--hunt", action="store_true", help="Modo Caza: Busca automáticamente ofertas remotas recientes")

    parser.add_argument("--keywords", "-k", type=str, default="AI Engineer Cloud Automation Google Workspace", help="Keywords para el modo --hunt")
    parser.add_argument("--limit", "-l", type=int, default=3, help="Número de ofertas a analizar en modo --hunt")
    parser.add_argument("--watch", "-w", action="store_true", help="Modo continuo: escanea periódicamente en segundo plano y avisa a Telegram")
    parser.add_argument("--interval", "-i", type=int, default=120, help="Minutos entre cada escaneo en modo --watch (default: 120)")
    parser.add_argument("--provider", choices=["gemini", "deepseek"], default=None, help="Forzar proveedor de LLM (gemini o deepseek)")
    parser.add_argument("--dry-run", action="store_true", help="Evaluar y mostrar resultados sin enviar a Notion ni Telegram")
    parser.add_argument("--force-alert", action="store_true", help="Forzar envío a Telegram independientemente del Fit Score")

    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold white]🚀 AI JOB HUNTER & CAREER AGENT[/bold white]\n"
            "[cyan]Rol:[/cyan] Evaluación cuantitativa de ofertas\n"
            "[dim]Evaluación Cuantitativa | Detección de Brechas | Carta a Medida | Sincronización Notion & Telegram[/dim]",
            border_style="cyan",
        )
    )

    if args.hunt or args.watch:
        run_proactive_hunt(
            keywords=args.keywords,
            limit=args.limit,
            dry_run=args.dry_run,
            watch=args.watch,
            interval_minutes=args.interval,
        )
        return

    job_text: str = ""
    source_url: str = ""

    if args.url:
        source_url = args.url
        try:
            with console.status(f"[bold cyan]Extrayendo contenido de {source_url}...", spinner="dots"):
                clean_url, job_text = extract_job_from_url(source_url)
                source_url = clean_url
        except ExtractionError as exc:
            console.print(f"[yellow]⚠️ {exc}[/yellow]")
            console.print("[bold yellow]Cambio automático a modo pegado:[/bold yellow]")
            job_text = read_from_clipboard_or_input()

    elif args.file:
        try:
            job_text = read_from_file(args.file)
            source_url = f"file://{Path(args.file).resolve()}"
        except Exception as exc:
            console.print(f"[red]Error al leer archivo: {exc}[/red]")
            sys.exit(1)

    elif args.paste:
        job_text = read_from_clipboard_or_input()

    else:
        # Interactive prompt if no arguments were given
        console.print("[bold]¿Cómo deseas ingresar la oferta?[/bold]")
        console.print("  [1] Introducir URL de LinkedIn o Web")
        console.print("  [2] Pegar texto de la oferta en la terminal")
        console.print("  [3] Ejecutar Modo Caza Proactiva (--hunt)")
        choice = console.input("[cyan]Selecciona una opción [1/2/3]: [/cyan]").strip()

        if choice == "1":
            target_url = console.input("[cyan]Introduce la URL de la oferta: [/cyan]").strip()
            source_url = target_url
            try:
                with console.status(f"[bold cyan]Extrayendo contenido de {source_url}...", spinner="dots"):
                    clean_url, job_text = extract_job_from_url(source_url)
                    source_url = clean_url
            except ExtractionError as exc:
                console.print(f"[yellow]⚠️ {exc}[/yellow]")
                job_text = read_from_clipboard_or_input()
        elif choice == "2":
            job_text = read_from_clipboard_or_input()
        elif choice == "3":
            run_proactive_hunt(keywords=args.keywords, limit=args.limit, dry_run=args.dry_run)
            return
        else:
            console.print("[red]Opción no válida. Saliendo.[/red]")
            sys.exit(1)

    if not job_text:
        console.print("[red]No se proporcionó texto de la oferta.[/red]")
        sys.exit(1)

    try:
        process_job(
            job_text=job_text,
            source_url=source_url,
            dry_run=args.dry_run,
            force_alert=args.force_alert,
            provider_override=args.provider,
        )
    except EvaluationError as exc:
        console.print(f"[red]Error durante la evaluación de IA: {exc}[/red]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red]Error imprevisto en el pipeline: {exc}[/red]")
        raise


if __name__ == "__main__":
    main()
