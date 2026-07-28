"""Orquestração: varre, extrai o texto bruto, grava o ``.txt`` e registra falhas.

Fail-soft por documento (um erro vai para o CSV e a run continua) e incremental
(o que já tem ``.txt`` não é reprocessado). Fatais: árvore de origem ausente
(:class:`DiscoveryError`) e backend-ocr fora do ar (:class:`ServiceUnavailable`) —
ambos fariam todos os documentos falharem igual, então param a run cedo.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from raw_text_maker.discovery import Job, discover_jobs, split_pending
from raw_text_maker.manifest import SEEDED_ENGINE, FormattedManifest, is_pending
from raw_text_maker.ocr_client import check_service, extract_raw_text
from raw_text_maker.outputs import ErrorRecord, ErrorReportWriter, save_text_atomic
from raw_text_maker.textlayer import ensure_available, has_text_layer

if TYPE_CHECKING:
    from raw_text_maker.config import Config

# Nome do documento na barra: cortado para não quebrar a linha em terminal estreito.
_DESC_WIDTH = 44


def run(
    config: Config,
    *,
    session=None,
    sleep: Callable[[float], None] = time.sleep,
    verbose: bool = False,
    console: Console | None = None,
) -> dict[str, int]:
    """Executa a produção dos ``.txt``. Levanta ``DiscoveryError``/``ServiceUnavailable``."""
    out = console or Console()
    jobs, colisoes = discover_jobs(config)  # DiscoveryError (fatal) sobe

    if config.formatted:
        return _run_formatted(config, jobs, colisoes, out, sleep, verbose, session)

    concluidos, pendentes = split_pending(jobs)

    summary = {
        "total": len(jobs),
        "ja_produzidos": len(concluidos),
        "produzidos": 0,
        "erros": 0,
        "colisoes": len(colisoes),
    }
    _print_plan(out, config, summary, len(pendentes))

    if not pendentes and not colisoes:
        out.print("[green]Nada a fazer: todos os .txt já foram produzidos.[/green]")
        return summary

    if session is None:
        import requests

        session = requests.Session()

    if pendentes:
        engines = check_service(config, session=session)  # ServiceUnavailable (fatal) sobe
        out.print(
            f"[dim]backend-ocr ok em {config.ocr_url} — engines: {', '.join(engines)}[/dim]\n"
        )

    with ErrorReportWriter(config.errors_path) as errs:
        for job in colisoes:
            _record_collision(job, errs, summary, out)

        with _make_progress(out) as progress:
            task = progress.add_task(
                _describe(pendentes[0]) if pendentes else "concluído",
                total=len(jobs),
                completed=len(concluidos),  # o já-produzido conta na barra
            )
            for job in pendentes:
                progress.update(task, description=_describe(job))
                _process_job(config, job, session, sleep, errs, summary, progress, verbose)
                progress.advance(task)
            progress.update(task, description="concluído")

    _print_summary(out, config, summary)
    return summary


def _run_formatted(config, jobs, colisoes, out, sleep, verbose, session) -> dict[str, int]:
    """Modo --formatted: regrava com ``raw_text_formatted`` só os arquivos docling.

    Gateia por camada de texto (sonda local, sem custo) para decidir o que enviar,
    e só sobrescreve quando o backend confirma docling com formatado não-vazio —
    então os ``.txt`` produzidos via openrouter ficam intactos, mesmo se a sonda
    errar. Ao contrário do modo padrão, aqui **sobrescreve** os ``.txt`` alvo.

    O manifesto (:mod:`raw_text_maker.manifest`) é o segundo gate: documento já
    formatado numa run anterior não volta ao backend só porque a árvore ganhou
    arquivos novos. ``--reformat-all`` ignora esse gate.
    """
    ensure_available()  # PyMuPDFUnavailable (fatal) sobe antes de qualquer trabalho

    com_texto: list[Job] = []
    mantidos: list[Job] = []  # sem camada de texto → scans (openrouter), não reenvia
    for job in jobs:
        destino = com_texto if has_text_layer(job.source, config.text_layer_min_chars) else mantidos
        destino.append(job)

    with FormattedManifest(config.manifest_path) as manifesto:
        alvos: list[Job] = []
        ja_formatados = 0
        for job in com_texto:
            if config.reformat_all or is_pending(manifesto, job.rel, job.dest):
                alvos.append(job)
            else:
                ja_formatados += 1

        summary = {
            "total": len(jobs),
            "formatados": 0,
            "ja_formatados": ja_formatados,
            "mantidos_scan": len(mantidos),
            "sem_formatado": 0,  # enviado mas voltou não-docling/vazio → preservado
            "erros": 0,
            "colisoes": len(colisoes),
        }
        _print_plan_formatted(out, config, summary, len(alvos))

        if not alvos and not colisoes:
            out.print("[green]Nada a fazer: todos os formatáveis já estão formatados.[/green]")
            return summary

        if session is None:
            import requests

            session = requests.Session()

        if alvos:
            engines = check_service(config, session=session)  # ServiceUnavailable (fatal) sobe
            out.print(
                f"[dim]backend-ocr ok em {config.ocr_url} — engines: {', '.join(engines)}[/dim]\n"
            )

        with ErrorReportWriter(config.errors_path) as errs:
            for job in colisoes:
                _record_collision(job, errs, summary, out)

            with _make_progress(out) as progress:
                task = progress.add_task(
                    _describe(alvos[0]) if alvos else "concluído", total=len(alvos)
                )
                for job in alvos:
                    progress.update(task, description=_describe(job))
                    _process_job_formatted(
                        config, job, session, sleep, errs, summary, progress, verbose, manifesto
                    )
                    progress.advance(task)
                progress.update(task, description="concluído")

    _print_summary_formatted(out, config, summary)
    return summary


def seed_formatted_manifest(config: Config, *, console: Console | None = None) -> dict[str, int]:
    """Marca como formatado o que já está pronto, **sem** chamar o backend.

    Migração de uma vez só para árvores formatadas antes do manifesto existir: o
    critério é o mesmo que o ``--formatted`` usaria (camada de texto local) mais a
    presença de um ``.txt`` não-vazio. Sem isso, a primeira run com o gate
    reprocessaria tudo — exatamente o que o gate existe para evitar.
    """
    out = console or Console()
    ensure_available()
    jobs, _ = discover_jobs(config)

    summary = {"total": len(jobs), "semeados": 0, "ja_no_manifesto": 0, "ignorados": 0}
    with FormattedManifest(config.manifest_path) as manifesto:
        for job in jobs:
            tem_texto = has_text_layer(job.source, config.text_layer_min_chars)
            pronto = job.dest.exists() and job.dest.stat().st_size > 0
            if not (tem_texto and pronto):
                summary["ignorados"] += 1  # scan, ou ainda sem .txt
                continue
            if manifesto.mark(job.rel, SEEDED_ENGINE, job.dest.stat().st_size):
                summary["semeados"] += 1
            else:
                summary["ja_no_manifesto"] += 1

    out.print("\n[bold]Semeadura do manifesto de formatados[/bold]")
    out.print(f"  Documentos:        {summary['total']}")
    out.print(f"  Marcados agora:    {summary['semeados']} → {config.manifest_path}")
    out.print(f"  Já no manifesto:   {summary['ja_no_manifesto']}")
    out.print(
        f"  Ignorados:         {summary['ignorados']} [dim](scan sem camada de texto, "
        f"ou ainda sem .txt)[/dim]"
    )
    return summary


def _process_job_formatted(
    config, job: Job, session, sleep, errs, summary, progress, verbose, manifesto
):
    """Reprocessa um alvo e sobrescreve o ``.txt`` com o formatado, se for docling puro."""
    outcome = extract_raw_text(job.source, config, session=session, sleep=sleep)
    if config.ocr_pause_s:
        sleep(config.ocr_pause_s)

    if not outcome.ok:
        errs.write(
            ErrorRecord(
                arquivo_origem=job.rel,
                categoria=job.categoria,
                motivo=outcome.motivo,
                tentativas=outcome.tentativas,
            )
        )
        summary["erros"] += 1
        progress.console.print(f"  [red]![/red] {job.rel} — {outcome.motivo}")
        return

    formatado = outcome.raw_text_formatted.strip()
    # Só docling produz formatado; se veio vazio ou de engine com fallback, a sonda
    # errou (é scan) — preserva o .txt existente em vez de sobrescrever.
    if not formatado or outcome.engine != "docling":
        summary["sem_formatado"] += 1
        if verbose:
            progress.console.print(
                f"  [yellow]=[/yellow] {job.rel} — mantido "
                f"[dim](engine={outcome.engine}, sem formatado)[/dim]"
            )
        return

    try:
        save_text_atomic(job.dest, outcome.raw_text_formatted)
    except OSError as exc:
        errs.write(
            ErrorRecord(
                arquivo_origem=job.rel,
                categoria=job.categoria,
                motivo=f"falha ao gravar o .txt: {exc}",
                tentativas=outcome.tentativas,
            )
        )
        summary["erros"] += 1
        progress.console.print(f"  [red]![/red] {job.rel} — falha de escrita: {exc}")
        return

    manifesto.mark(job.rel, outcome.engine, len(outcome.raw_text_formatted))
    summary["formatados"] += 1
    if verbose:
        progress.console.print(
            f"  [green]+[/green] {job.dest.name} "
            f"[dim]({len(outcome.raw_text_formatted)} chars formatados)[/dim]"
        )


def _process_job(config, job: Job, session, sleep, errs, summary, progress, verbose) -> None:
    """Processa um documento (fail-soft): grava o ``.txt`` ou registra o erro."""
    outcome = extract_raw_text(job.source, config, session=session, sleep=sleep)
    if config.ocr_pause_s:
        sleep(config.ocr_pause_s)

    if not outcome.ok:
        errs.write(
            ErrorRecord(
                arquivo_origem=job.rel,
                categoria=job.categoria,
                motivo=outcome.motivo,
                tentativas=outcome.tentativas,
            )
        )
        summary["erros"] += 1
        progress.console.print(f"  [red]![/red] {job.rel} — {outcome.motivo}")
        return

    try:
        save_text_atomic(job.dest, outcome.raw_text)
    except OSError as exc:
        # Disco cheio/permissão: fail-soft por documento — o CSV mostra o padrão
        # se for generalizado, e a retomada refaz o que faltou.
        errs.write(
            ErrorRecord(
                arquivo_origem=job.rel,
                categoria=job.categoria,
                motivo=f"falha ao gravar o .txt: {exc}",
                tentativas=outcome.tentativas,
            )
        )
        summary["erros"] += 1
        progress.console.print(f"  [red]![/red] {job.rel} — falha de escrita: {exc}")
        return

    summary["produzidos"] += 1
    if verbose:
        progress.console.print(
            f"  [green]+[/green] {job.dest.name} "
            f"[dim]({len(outcome.raw_text)} chars, {outcome.engine})[/dim]"
        )


def _record_collision(job: Job, errs, summary, out: Console) -> None:
    errs.write(
        ErrorRecord(
            arquivo_origem=job.rel,
            categoria=job.categoria,
            motivo=f"nome de destino já usado por outro documento: {job.dest.name}",
            tentativas=0,
        )
    )
    summary["erros"] += 1
    out.print(f"  [yellow]![/yellow] colisão de nome, ignorado: {job.rel}")


def _make_progress(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}", justify="left"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("restante:"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def _describe(job: Job) -> str:
    name = job.source.name
    if len(name) > _DESC_WIDTH:
        name = name[: _DESC_WIDTH - 1] + "…"
    return name.ljust(_DESC_WIDTH)


def _print_plan(out: Console, config: Config, summary: dict[str, int], pendentes: int) -> None:
    out.print("\n[bold]raw_text_maker[/bold] — documento → texto bruto")
    out.print(f"  Origem:      {config.source_root}")
    out.print(f"  Destino:     {config.output_root}")
    out.print(f"  Documentos:  {summary['total']}")
    out.print(f"  Já prontos:  {summary['ja_produzidos']} [dim](.txt presente, será pulado)[/dim]")
    out.print(f"  Faltam:      {pendentes}")
    if summary["colisoes"]:
        out.print(f"  [yellow]Colisões:    {summary['colisoes']} (ver CSV de erros)[/yellow]")
    out.print("")


def _print_summary(out: Console, config: Config, summary: dict[str, int]) -> None:
    out.print("\n[bold]Resumo:[/bold]")
    out.print(f"  Documentos:      {summary['total']}")
    out.print(f"  Produzidos agora: {summary['produzidos']} → {config.output_root}")
    out.print(f"  Já prontos:      {summary['ja_produzidos']} (pulados)")
    out.print(f"  Com erro:        {summary['erros']}")
    if summary["erros"]:
        out.print(f"\n  [yellow]⚠ Erros em: {config.errors_path}[/yellow]")
        out.print("    Re-rode o comando: ele retoma só o que faltou.")


def _print_plan_formatted(
    out: Console, config: Config, summary: dict[str, int], alvos: int
) -> None:
    out.print("\n[bold]raw_text_maker[/bold] — modo formatado (texto com layout espacial)")
    out.print(f"  Origem:      {config.source_root}")
    out.print(f"  Destino:     {config.output_root}")
    out.print(f"  Documentos:  {summary['total']}")
    out.print(f"  A formatar:  {alvos} [dim](têm camada de texto → docling)[/dim]")
    if summary.get("ja_formatados"):
        out.print(
            f"  Já formatados: {summary['ja_formatados']} "
            f"[dim](no manifesto — não reenviados)[/dim]"
        )
    out.print(
        f"  Mantidos:    {summary['mantidos_scan']} "
        f"[dim](scans/openrouter — .txt preservado, não reenviado)[/dim]"
    )
    if config.reformat_all:
        out.print("  [yellow]--reformat-all: ignorando o manifesto[/yellow]")
    if summary["colisoes"]:
        out.print(f"  [yellow]Colisões:    {summary['colisoes']} (ver CSV de erros)[/yellow]")
    out.print("")


def _print_summary_formatted(out: Console, config: Config, summary: dict[str, int]) -> None:
    out.print("\n[bold]Resumo (formatado):[/bold]")
    out.print(f"  Documentos:        {summary['total']}")
    out.print(f"  Formatados agora:  {summary['formatados']} → {config.output_root}")
    if summary.get("ja_formatados"):
        out.print(f"  Já formatados:     {summary['ja_formatados']} (pulados, ver manifesto)")
    out.print(f"  Mantidos (scan):   {summary['mantidos_scan']} (openrouter, intactos)")
    if summary["sem_formatado"]:
        out.print(f"  Enviados sem formatado: {summary['sem_formatado']} (preservados)")
    out.print(f"  Com erro:          {summary['erros']}")
    if summary["erros"]:
        out.print(f"\n  [yellow]⚠ Erros em: {config.errors_path}[/yellow]")
