import os
import sys
import json
from pathlib import Path
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .config import Config
from .connector import ssh_connect, run_commands
from .parser import parse_running_config
from .embedder import get_model
from .indexer import index_manuals, search
from .analyzer import analyze_with_rules, analyze_with_knowledge
from .listener import listen_session
from .models import Finding, Severity

console = Console()
cfg = Config.load()


@click.group()
@click.version_option(version=__version__)
def cli():
    """Netzunami — Network config analyzer with AI embeddings"""


@cli.command()
@click.argument("host")
@click.option("-u", "--user", default="admin", help="SSH username")
@click.option("-k", "--key", default=None, help="SSH key path")
@click.option("-p", "--port", default=22, help="SSH port")
@click.option("--enable/--no-enable", default=True, help="Send enable")
@click.option("--save", is_flag=True, help="Save config to file")
def ssh(host, user, key, port, enable, save):
    """Connect to device via SSH and grab running-config"""
    bastion = None
    if cfg.bastion.host:
        bastion = {
            "host": cfg.bastion.host,
            "user": cfg.bastion.user or user,
            "key": cfg.bastion.key or key,
            "port": cfg.bastion.port,
        }

    try:
        client = ssh_connect(host, user, key, port=port, bastion=bastion)
        console.print(f"[green]✓[/green] Connected to {host}")

        commands = ["show running-config"]
        raw = run_commands(client, commands, enable=enable)
        client.close()

        if save:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{host}_{ts}.cfg"
            data_dir = Path(cfg.data_dir) / "configs"
            data_dir.mkdir(parents=True, exist_ok=True)
            fpath = data_dir / fname
            with open(fpath, "w") as f:
                f.write(raw)
            console.print(f"[green]✓[/green] Saved to {fpath}")

        blocks = parse_running_config(raw)
        results = analyze_with_rules(blocks)

        console.print(f"\n[bold cyan]Netzunami Report — {host}[/bold cyan]")
        console.print(f"  Blocks parsed: {len(blocks)}")
        console.print(f"  Findings: {len(results)}\n")

        if results:
            _display_findings(results)

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("-v", "--vendor", default="cisco", help="Device vendor")
def analyze(config_file, vendor):
    """Analyze a running-config file"""
    with open(config_file) as f:
        raw = f.read()

    blocks = parse_running_config(raw, vendor)
    results = analyze_with_rules(blocks, vendor)

    data_dir = Path(cfg.data_dir) / "knowledge"
    index_path = data_dir / "faiss.index"
    meta_path = data_dir / "metadata.json"
    if index_path.exists() and meta_path.exists():
        from .indexer import index_manuals as _im
        idx, meta = _im(str(data_dir.parent / "manuals"), str(data_dir), rebuild=False)
        knowledge_results = analyze_with_knowledge(blocks, idx, meta)
        results.extend(knowledge_results)

    console.print(f"\n[bold cyan]Netzunami Analysis — {config_file}[/bold cyan]")
    console.print(f"  Blocks: {len(blocks)}  Findings: {len(results)}\n")

    if results:
        _display_findings(results)

    out_dir = Path(cfg.data_dir) / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = out_dir / f"report_{ts}.json"
    with open(report_path, "w") as f:
        json.dump(
            {
                "file": config_file,
                "timestamp": ts,
                "findings": [
                    {
                        "severity": f.severity.value,
                        "title": f.title,
                        "detail": f.detail,
                        "suggestion": f.suggestion,
                        "lines": f.config_lines,
                    }
                    for f in results
                ],
            },
            f,
            indent=2,
        )
    console.print(f"[dim]Report salvato: {report_path}[/dim]")


@cli.command()
@click.argument("manuals_dir", type=click.Path(exists=True))
@click.option("--rebuild", is_flag=True, help="Rebuild index from scratch")
def index(manuals_dir, rebuild):
    """Index manuals (PDF/TXT) from a directory"""
    data_dir = Path(cfg.data_dir) / "knowledge"
    data_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold cyan]Indicizzazione manuali[/bold cyan]")
    console.print(f"  Source: {manuals_dir}")
    console.print(f"  Output: {data_dir}")

    idx, meta = index_manuals(
        manuals_dir=str(manuals_dir),
        output_dir=str(data_dir),
        model_name=cfg.model_name,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        rebuild=rebuild,
    )

    console.print(f"[green]✓[/green] {len(meta)} chunk, {idx.ntotal} vettori")


@cli.command()
@click.argument("query")
@click.option("-t", "--top-k", default=5, help="Number of results")
def search_kb(query, top_k):
    """Search the knowledge base"""
    data_dir = Path(cfg.data_dir) / "knowledge"
    from .indexer import index_manuals as _im
    idx, meta = _im(str(data_dir.parent / "manuals" if False else data_dir), str(data_dir), rebuild=False)

    if idx.ntotal == 0:
        console.print("[yellow]Knowledge base vuoto. Usa 'netzunami index' prima.[/yellow]")
        return

    results = search(idx, meta, query, model_name=cfg.model_name, top_k=top_k)

    console.print(f"[bold cyan]Ricerca:[/bold cyan] {query}\n")
    for meta_item, score in results:
        console.print(f"  [green]{score:.3f}[/green] {meta_item['source']} chk#{meta_item['chunk']}")
        console.print(f"       {meta_item['text'][:150]}")
        console.print()


@cli.command()
@click.argument("log_file", type=click.Path(exists=True))
@click.option("-v", "--vendor", default="cisco")
def listen(log_file, vendor):
    """Listen to a live session log for real-time suggestions"""
    try:
        listen_session(log_file, vendor=vendor)
    except KeyboardInterrupt:
        console.print("\n[yellow]Listener fermato.[/yellow]")


@cli.command()
def info():
    """Show netzunami status"""
    data_dir = Path(cfg.data_dir)
    knowledge_dir = data_dir / "knowledge"

    console.print(f"[bold cyan]Netzunami {__version__}[/bold cyan]")
    console.print(f"  Data dir:      {data_dir}")
    console.print(f"  Model:         {cfg.model_name}")
    console.print(f"  Bastion:       {cfg.bastion.host or 'none'}")

    if knowledge_dir.exists():
        idx_path = knowledge_dir / "faiss.index"
        meta_path = knowledge_dir / "metadata.json"
        if idx_path.exists():
            import faiss
            idx = faiss.read_index(str(idx_path))
            console.print(f"  Knowledge base: {idx.ntotal} vettori")
        else:
            console.print(f"  Knowledge base: vuoto (usa 'netzunami index')")
    else:
        console.print(f"  Knowledge base: vuoto (usa 'netzunami index')")

    configs_dir = data_dir / "configs"
    if configs_dir.exists():
        count = len(list(configs_dir.glob("*.cfg")))
        console.print(f"  Config salvate: {count}")


def _display_findings(findings: list[Finding]):
    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "INFO": []}
    for f in findings:
        by_sev[f.severity.value].append(f)

    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        items = by_sev[sev]
        if not items:
            continue
        color = {"CRITICAL": "red", "HIGH": "orange1", "MEDIUM": "yellow", "LOW": "cyan", "INFO": "white"}[sev]
        for f in items:
            lines_str = f"linee: {f.config_lines}" if f.config_lines else ""
            panel = Panel(
                f"[bold]{f.detail}[/bold]\n"
                + (f"[dim]Suggerimento: {f.suggestion}[/dim]\n" if f.suggestion else "")
                + (f"[dim]{lines_str}[/dim]" if lines_str else ""),
                title=f"[{color}]{f.severity.value}[/{color}] {f.title}",
                border_style=color,
                padding=(0, 1),
            )
            console.print(panel)
            console.print()


if __name__ == "__main__":
    cli()
