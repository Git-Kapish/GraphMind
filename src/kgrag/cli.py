"""GraphMind CLI: Terminal Interface for Enterprise Knowledge Graph RAG.

Provides interactive and one-shot terminal access to GraphMind:
- One-shot queries with citation invariants, graph paths, and latency breakdown.
- Interactive REPL shell with slash commands and dynamic mode switching.
- Side-by-side A/B comparison between GraphMind (Hybrid) and Plain Vector Baseline.
- Entity topology and chunk provenance inspection.
- Live database & model runtime health verification.
"""

from __future__ import annotations

import json
import sys
import warnings
from typing import Any

import click
import httpx
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

warnings.filterwarnings("ignore")

console = Console()


# ---------------------------------------------------------------------------
# Client Transport Abstraction
# ---------------------------------------------------------------------------
class QueryClient:
    """Hybrid transport client supporting local in-process and remote HTTP APIs."""

    def __init__(self, api_url: str | None = None) -> None:
        self.api_url = api_url.rstrip("/") if api_url else None
        self._is_remote = False
        self._client: httpx.Client | None = None
        self._test_client: Any = None

        if self.api_url:
            self._client = httpx.Client(base_url=self.api_url, timeout=180.0)
            self._is_remote = True
        else:
            # Check if a live server is already running on default http://localhost:8000
            try:
                probe = httpx.get("http://localhost:8000/health", timeout=0.8)
                if probe.status_code == 200:
                    pdata = probe.json()
                    if (
                        isinstance(pdata, dict)
                        and "components" in pdata
                        and "postgres" in pdata.get("components", {})
                    ):
                        self.api_url = "http://localhost:8000"
                        self._client = httpx.Client(base_url="http://localhost:8000", timeout=180.0)
                        self._is_remote = True
            except Exception:
                pass

        if not self._is_remote:
            # Fall back to zero-config in-process TestClient
            from fastapi.testclient import TestClient

            from kgrag.api.app import app

            self._test_client = TestClient(app)

    @property
    def mode_description(self) -> str:
        if self._is_remote:
            return f"Remote Server ({self.api_url})"
        return "Local In-Process (Direct DB + Model)"

    @property
    def client(self) -> httpx.Client | Any:
        return self._client if self._is_remote else self._test_client

    def query(
        self, question: str, mode: str = "auto", top_k: int = 8, debug: bool = True
    ) -> dict[str, Any]:
        resp = self.client.post(
            "/query",
            json={"question": question, "mode": mode, "top_k": top_k, "debug": debug},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Query error (HTTP {resp.status_code}): {resp.text}")
        return resp.json()

    def query_baseline(self, question: str, top_k: int = 8, debug: bool = True) -> dict[str, Any]:
        resp = self.client.post(
            "/query/baseline",
            json={"question": question, "top_k": top_k, "debug": debug},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Baseline query error (HTTP {resp.status_code}): {resp.text}")
        return resp.json()

    def get_entity(self, entity_id_or_name: str) -> dict[str, Any]:
        resp = self.client.get(f"/entities/{entity_id_or_name}")
        if resp.status_code == 200:
            return resp.json()

        # If not found directly, try resolving name / mention to entity_id
        try:
            from kgrag.graph.templates import StrictResolutionStatus, resolve_entity_strict

            strict_res = resolve_entity_strict(entity_id_or_name)
            if strict_res.status == StrictResolutionStatus.RESOLVED and strict_res.entity_id:
                resp2 = self.client.get(f"/entities/{strict_res.entity_id}")
                if resp2.status_code == 200:
                    return resp2.json()
        except Exception:
            pass

        # Try database ILIKE match on canonical_name
        try:
            from kgrag.db import postgres as pg_db

            with pg_db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT entity_id FROM entities WHERE canonical_name ILIKE %s LIMIT 1;",
                        (f"%{entity_id_or_name}%",),
                    )
                    row = cur.fetchone()
                    if row:
                        resp3 = self.client.get(f"/entities/{row['entity_id']}")
                        if resp3.status_code == 200:
                            return resp3.json()
        except Exception:
            pass

        if resp.status_code == 404:
            raise KeyError(f"Entity '{entity_id_or_name}' not found.")
        raise RuntimeError(f"Entity lookup error (HTTP {resp.status_code}): {resp.text}")

    def get_chunk(self, chunk_id: str) -> dict[str, Any]:
        resp = self.client.get(f"/chunks/{chunk_id}")
        if resp.status_code == 404:
            raise KeyError(f"Chunk '{chunk_id}' not found.")
        if resp.status_code != 200:
            raise RuntimeError(f"Chunk lookup error (HTTP {resp.status_code}): {resp.text}")
        return resp.json()

    def get_health(self) -> dict[str, Any]:
        resp = self.client.get("/health")
        if resp.status_code != 200:
            raise RuntimeError(f"Health check error (HTTP {resp.status_code}): {resp.text}")
        return resp.json()


# ---------------------------------------------------------------------------
# Formatting & Presentation Utilities
# ---------------------------------------------------------------------------
def print_banner(mode_desc: str) -> None:
    banner_text = Text()
    banner_text.append("GraphMind", style="bold cyan")
    banner_text.append(" | Enterprise Knowledge Graph RAG CLI\n", style="bold white")
    banner_text.append(
        "Local-first hybrid graph + vector QA over SEC 10-K Filings\n", style="italic dim"
    )
    banner_text.append("Engine Status: ", style="dim")
    banner_text.append(mode_desc, style="bold green")

    console.print(
        Panel(
            banner_text,
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )


def render_route_pill(route_info: dict[str, Any]) -> Text:
    chosen = route_info.get("chosen", "unknown").upper()
    conf = route_info.get("confidence", 0.0)
    fallback = route_info.get("fallback_used", False)

    pill = Text()
    if chosen == "HYBRID":
        pill.append(" HYBRID ", style="bold black on bright_cyan")
    elif chosen == "GRAPH":
        pill.append(" GRAPH ", style="bold white on dark_green")
    elif chosen == "VECTOR":
        pill.append(" VECTOR ", style="bold white on navy_blue")
    else:
        pill.append(f" {chosen} ", style="bold white on red")

    pill.append(f" conf={conf:.2f}", style="bold yellow")
    if fallback:
        pill.append(" [fallback used]", style="italic magenta")
    return pill


def render_query_response(
    data: dict[str, Any],
    show_citations: bool = True,
    show_graph: bool = True,
    show_passages: bool = False,
) -> None:
    """Format and print full query response with answer, route, citations, and evidence."""
    # 1. Header Information (Route & Latency)
    route_info = data.get("route", {})
    latencies = data.get("latency_ms", {})
    validation = data.get("validation", {})
    status = data.get("status", "ok")

    # Status & Route Header Table
    head_table = Table.grid(expand=True)
    head_table.add_column("left", justify="left")
    head_table.add_column("right", justify="right")

    left_text = Text("Route: ")
    left_text.append_text(render_route_pill(route_info))
    left_text.append(f"  |  Status: {status.upper()}", style="bold white")

    right_text = Text(
        f"Total: {latencies.get('total', 0)}ms (Route: {latencies.get('route', 0)}ms | "
        f"Retrieve: {latencies.get('retrieve', 0)}ms | Gen: {latencies.get('generate', 0)}ms)",
        style="dim",
    )
    head_table.add_row(left_text, right_text)

    console.print()
    console.print(head_table)

    # 2. Main Grounded Answer Panel
    answer_text = data.get("answer", "")
    border_color = "cyan" if status == "ok" else ("yellow" if status == "refused" else "red")
    console.print(
        Panel(
            Markdown(answer_text),
            title="[bold white]Grounded Answer[/]",
            border_style=border_color,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    # 3. Validation & Citation Invariant Status
    val_status = validation.get("citation_resolution_passed", False)
    val_attempts = validation.get("attempts", 1)
    val_text = Text("Citation Invariant: ", style="bold")
    if val_status:
        val_text.append("PASSED (100% citations resolved to corpus)", style="bold green")
    else:
        val_text.append("FAILED (Unresolved citation tags detected)", style="bold red")
    val_text.append(f"  (attempts={val_attempts})", style="dim")
    console.print(val_text)

    # 4. Citations Table
    citations = data.get("citations", [])
    if show_citations and citations:
        console.print()
        cit_table = Table(
            title="Supporting Citations (Provenance Registry)",
            box=box.ROUNDED,
            border_style="dim",
            header_style="bold cyan",
        )
        cit_table.add_column("Tag", style="bold yellow", width=6)
        cit_table.add_column("Document / Filer", style="green", width=16)
        cit_table.add_column("Section", style="magenta", width=22)
        cit_table.add_column("Chunk ID", style="dim", width=14)
        cit_table.add_column("Evidence Snippet", style="white")

        for cit in citations:
            snippet = cit.get("snippet", "")
            if len(snippet) > 140:
                snippet = snippet[:137] + "..."
            chunk_display = cit.get("chunk_id", "")[:12] + "..."
            cit_table.add_row(
                cit.get("label", ""),
                cit.get("doc", ""),
                cit.get("section", ""),
                chunk_display,
                snippet,
            )
        console.print(cit_table)

    # 5. Graph Paths (if debug returned paths and requested)
    graph_paths = data.get("graph_paths", [])
    if show_graph and graph_paths:
        console.print()
        gp_table = Table(
            title="Retrieved Knowledge Graph Evidence Paths",
            box=box.ROUNDED,
            border_style="dark_green",
            header_style="bold green",
        )
        gp_table.add_column("Head Entity", style="bold yellow")
        gp_table.add_column("Relation", style="bold magenta")
        gp_table.add_column("Tail Entity", style="bold cyan")
        gp_table.add_column("Observation ID", style="dim", width=14)
        gp_table.add_column("Source Chunk", style="dim", width=14)

        for gp in graph_paths:
            obs_id = str(gp.get("observation_id", ""))[:12] + "..."
            chk_id = str(gp.get("chunk_id", ""))[:12] + "..."
            gp_table.add_row(
                str(gp.get("head_entity", "")),
                str(gp.get("relation_type", "")),
                str(gp.get("tail_entity", "")),
                obs_id,
                chk_id,
            )
        console.print(gp_table)

    # 6. Vector Passages (if debug returned passages and requested)
    passages = data.get("passages", [])
    if show_passages and passages:
        console.print()
        vp_table = Table(
            title="Retrieved Vector Passages",
            box=box.ROUNDED,
            border_style="navy_blue",
            header_style="bold blue",
        )
        vp_table.add_column("Ticker", style="bold green", width=8)
        vp_table.add_column("Section", style="magenta", width=20)
        vp_table.add_column("Score", style="yellow", width=8)
        vp_table.add_column("Chunk ID", style="dim", width=14)
        vp_table.add_column("Text Excerpt", style="white")

        for vp in passages:
            score_str = f"{vp.get('score', 0.0):.3f}"
            text_snip = vp.get("text", "")[:120] + "..."
            chk_id = str(vp.get("chunk_id", ""))[:12] + "..."
            vp_table.add_row(
                vp.get("ticker", ""),
                vp.get("section_path", ""),
                score_str,
                chk_id,
                text_snip,
            )
        console.print(vp_table)


def render_comparison(hybrid_resp: dict[str, Any], baseline_resp: dict[str, Any]) -> None:
    """Format side-by-side or stacked A/B comparison between Hybrid and Baseline."""
    console.print()
    console.print(
        Panel(
            Text(
                "A/B SYSTEM COMPARISON: GRAPH-AUGMENTED RAG VS PLAIN VECTOR BASELINE",
                style="bold yellow",
                justify="center",
            ),
            box=box.HEAVY,
            border_style="yellow",
        )
    )

    # Summary metric comparison table
    summary = Table(box=box.ROUNDED, expand=True)
    summary.add_column("Metric", style="bold white")
    summary.add_column("System C (GraphMind Hybrid)", style="bold cyan")
    summary.add_column("System A (Vector Baseline)", style="bold blue")

    c_lat = hybrid_resp.get("latency_ms", {}).get("total", 0)
    a_lat = baseline_resp.get("latency_ms", {}).get("total", 0)

    c_cit_count = len(hybrid_resp.get("citations", []))
    a_cit_count = len(baseline_resp.get("citations", []))

    c_gp_count = len(hybrid_resp.get("graph_paths", []))

    summary.add_row(
        "Route Chosen", render_route_pill(hybrid_resp.get("route", {})), "VECTOR (Fixed)"
    )
    summary.add_row(
        "Retrieval Sources",
        f"Graph ({c_gp_count} paths) + Vector",
        f"Vector Top-{len(baseline_resp.get('passages', []))} only",
    )
    summary.add_row("Citations Grounded", f"{c_cit_count} citations", f"{a_cit_count} citations")
    summary.add_row(
        "Citation Invariant",
        "Passed"
        if hybrid_resp.get("validation", {}).get("citation_resolution_passed")
        else "Failed",
        "Passed"
        if baseline_resp.get("validation", {}).get("citation_resolution_passed")
        else "Failed",
    )
    summary.add_row("Total Latency", f"{c_lat} ms", f"{a_lat} ms")
    console.print(summary)

    # Answers Display
    console.print()
    console.print(
        Panel(
            Markdown(hybrid_resp.get("answer", "")),
            title="[bold cyan]System C: GraphMind Hybrid Answer[/]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    console.print()
    console.print(
        Panel(
            Markdown(baseline_resp.get("answer", "")),
            title="[bold blue]System A: Vector Baseline Answer[/]",
            border_style="blue",
            box=box.ROUNDED,
        )
    )


def render_entity_detail(data: dict[str, Any]) -> None:
    """Render canonical entity provenance and graph neighborhood."""
    canonical_name = data.get("canonical_name", "")
    entity_id = data.get("entity_id", "")
    entity_type = data.get("type", "")
    degree = data.get("degree", 0)
    aliases = data.get("aliases", [])
    relationships = data.get("relationships", [])

    info_table = Table.grid(padding=(0, 2))
    info_table.add_column("Key", style="bold cyan")
    info_table.add_column("Val", style="white")

    info_table.add_row("Canonical Name:", canonical_name)
    info_table.add_row("Entity ID:", entity_id)
    info_table.add_row("Entity Type:", entity_type)
    info_table.add_row("Graph Degree:", str(degree))
    info_table.add_row("Known Aliases:", ", ".join(aliases) if aliases else "<none>")

    console.print()
    console.print(
        Panel(
            info_table,
            title="[bold yellow]Canonical Entity Details[/]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    if relationships:
        rel_table = Table(
            title=f"Graph Relationships ({len(relationships)} connections)",
            box=box.ROUNDED,
            border_style="green",
        )
        rel_table.add_column("Direction", style="bold magenta", width=10)
        rel_table.add_column("Relation Type", style="bold cyan", width=24)
        rel_table.add_column("Connected Entity", style="bold white")
        rel_table.add_column("Target ID", style="dim")

        for rel in relationships:
            dir_str = "--> OUT" if rel.get("direction") == "outgoing" else "<-- IN"
            rel_table.add_row(
                dir_str,
                rel.get("rel_type", ""),
                rel.get("target_name", ""),
                rel.get("target_id", ""),
            )
        console.print(rel_table)


def render_chunk_detail(data: dict[str, Any]) -> None:
    """Render authoritative chunk text, SEC metadata, and extraction observations."""
    chunk_id = data.get("chunk_id", "")
    company = data.get("company", "")
    ticker = data.get("ticker", "")
    form = data.get("form_type", "")
    fiscal_year = data.get("fiscal_year", "")
    section = data.get("section_path", "")
    text = data.get("text", "")
    observations = data.get("observations", [])

    info_table = Table.grid(padding=(0, 2))
    info_table.add_column("Key", style="bold cyan")
    info_table.add_column("Val", style="white")

    info_table.add_row("Chunk ID:", chunk_id)
    info_table.add_row("Company / Ticker:", f"{company} ({ticker})")
    info_table.add_row("Filing / Year:", f"{form} FY{fiscal_year}")
    info_table.add_row("Section Path:", section)

    console.print()
    console.print(
        Panel(
            info_table,
            title="[bold magenta]Chunk SEC Document Provenance[/]",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    console.print()
    console.print(
        Panel(
            text,
            title="[bold white]Authoritative Verbatim Text[/]",
            border_style="dim",
            box=box.ROUNDED,
        )
    )

    if observations:
        obs_table = Table(
            title=f"Extracted Knowledge Graph Observations ({len(observations)})",
            box=box.ROUNDED,
            border_style="cyan",
        )
        obs_table.add_column("Head Entity", style="bold yellow")
        obs_table.add_column("Relation", style="bold magenta")
        obs_table.add_column("Tail Entity", style="bold cyan")
        obs_table.add_column("Verified?", style="green", width=10)
        obs_table.add_column("Evidence Quote", style="dim")

        for obs in observations:
            v_str = "YES" if obs.get("evidence_verified") else "NO"
            obs_table.add_row(
                obs.get("head_surface", ""),
                obs.get("relation_type", ""),
                obs.get("tail_surface", ""),
                v_str,
                obs.get("evidence_quote", "")[:80] + "...",
            )
        console.print(obs_table)


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------
@click.group(invoke_without_command=True)
@click.option("--api-url", default=None, help="Target remote GraphMind FastAPI server URL")
@click.pass_context
def cli(ctx: click.Context, api_url: str | None) -> None:
    """GraphMind: Local-first Knowledge Graph RAG over Enterprise SEC 10-Ks.

    Run queries directly, compare against baseline vector RAG, or launch
    the interactive REPL shell.
    """
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url

    # If no subcommand specified, default to interactive REPL
    if ctx.invoked_subcommand is None:
        ctx.invoke(interactive)


@cli.command("query")
@click.argument("question")
@click.option(
    "--mode",
    type=click.Choice(["auto", "vector", "graph", "hybrid"]),
    default="auto",
    help="Retrieval routing mode",
)
@click.option("--top-k", type=int, default=8, help="Top-k retrieval limit")
@click.option(
    "--show-citations/--no-citations", default=True, help="Display citation breakdown table"
)
@click.option("--show-graph/--no-graph", default=True, help="Display retrieved graph paths")
@click.option(
    "--show-passages/--no-passages", default=False, help="Display retrieved vector passages"
)
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON response for piping / CI")
@click.pass_context
def query_cmd(
    ctx: click.Context,
    question: str,
    mode: str,
    top_k: int,
    show_citations: bool,
    show_graph: bool,
    show_passages: bool,
    as_json: bool,
) -> None:
    """Execute a grounded query against the enterprise knowledge base."""
    client = QueryClient(api_url=ctx.obj.get("api_url"))

    if as_json:
        try:
            res = client.query(question=question, mode=mode, top_k=top_k, debug=True)
            click.echo(json.dumps(res, indent=2))
        except Exception as e:
            click.echo(json.dumps({"error": str(e)}), err=True)
            sys.exit(1)
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Executing GraphMind query...[/]"),
        transient=True,
    ) as progress:
        progress.add_task("query", total=None)
        try:
            res = client.query(question=question, mode=mode, top_k=top_k, debug=True)
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")
            sys.exit(1)

    render_query_response(
        res,
        show_citations=show_citations,
        show_graph=show_graph,
        show_passages=show_passages,
    )


@cli.command("compare")
@click.argument("question")
@click.option("--top-k", type=int, default=8, help="Top-k retrieval limit")
@click.pass_context
def compare_cmd(ctx: click.Context, question: str, top_k: int) -> None:
    """Compare GraphMind (Hybrid Graph RAG) vs Plain Vector Baseline on a query."""
    client = QueryClient(api_url=ctx.obj.get("api_url"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Running A/B Comparison (Hybrid vs Baseline)...[/]"),
        transient=True,
    ) as progress:
        progress.add_task("compare", total=None)
        try:
            hybrid_res = client.query(question=question, mode="hybrid", top_k=top_k, debug=True)
            base_res = client.query_baseline(question=question, top_k=top_k, debug=True)
        except Exception as e:
            console.print(f"[bold red]Error running comparison:[/] {e}")
            sys.exit(1)

    render_comparison(hybrid_res, base_res)


@cli.command("entity")
@click.argument("entity_id_or_name")
@click.pass_context
def entity_cmd(ctx: click.Context, entity_id_or_name: str) -> None:
    """Inspect canonical entity topology, aliases, and graph relationships."""
    client = QueryClient(api_url=ctx.obj.get("api_url"))
    try:
        data = client.get_entity(entity_id_or_name)
        render_entity_detail(data)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@cli.command("chunk")
@click.argument("chunk_id")
@click.pass_context
def chunk_cmd(ctx: click.Context, chunk_id: str) -> None:
    """Inspect chunk SEC metadata, authoritative text, and extraction triples."""
    client = QueryClient(api_url=ctx.obj.get("api_url"))
    try:
        data = client.get_chunk(chunk_id)
        render_chunk_detail(data)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@cli.command("health")
@click.pass_context
def health_cmd(ctx: click.Context) -> None:
    """Check live status of PostgreSQL, Neo4j, and LLM runtime."""
    client = QueryClient(api_url=ctx.obj.get("api_url"))
    try:
        data = client.get_health()
    except Exception as e:
        console.print(f"[bold red]Service Unreachable:[/] {e}")
        sys.exit(1)

    overall = data.get("status", "unknown").upper()
    style = "green" if overall == "OK" else ("yellow" if overall == "DEGRADED" else "red")

    console.print()
    console.print(
        f"Overall Service Status: [bold {style}]{overall}[/] (Version: {data.get('version')})"
    )

    htable = Table(box=box.ROUNDED, border_style="dim")
    htable.add_column("Component", style="bold cyan")
    htable.add_column("Status", style="bold")
    htable.add_column("Details", style="white")

    for comp, cinfo in data.get("components", {}).items():
        st = cinfo.get("status", "unknown")
        cstyle = "green" if st == "healthy" else "red"
        details_str = json.dumps(cinfo.get("details", {}))
        htable.add_row(comp, f"[{cstyle}]{st.upper()}[/{cstyle}]", details_str)

    console.print(htable)


# ---------------------------------------------------------------------------
# Interactive REPL Shell
# ---------------------------------------------------------------------------
@cli.command("interactive")
@click.pass_context
def interactive(ctx: click.Context) -> None:
    """Launch interactive GraphMind terminal shell."""
    client = QueryClient(api_url=ctx.obj.get("api_url"))
    print_banner(client.mode_description)

    console.print(
        "[dim]Type your question directly, or type [bold cyan]/help[/bold cyan] for commands.[/dim]"
    )
    console.print(
        "[dim]Type [bold cyan]/exit[/bold cyan] or [bold cyan]quit[/bold cyan] to exit.[/dim]\n"
    )

    current_mode = "auto"
    top_k = 8
    show_citations = True
    show_graph = True
    show_passages = False

    while True:
        try:
            prompt_str = f"[bold cyan]graphmind[/] ([bold yellow]{current_mode}[/]) > "
            user_input = Prompt.ask(prompt_str).strip()

            if not user_input:
                continue

            # Command handling
            if user_input.lower() in ("exit", "quit", "q", ":q", "/exit", "/quit"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input == "/help":
                _print_repl_help()
                continue

            if user_input.startswith("/mode"):
                parts = user_input.split()
                if len(parts) > 1 and parts[1].lower() in ("auto", "vector", "graph", "hybrid"):
                    current_mode = parts[1].lower()
                    console.print(f"[green]Active mode set to:[/] [bold]{current_mode}[/]")
                else:
                    console.print("[yellow]Usage: /mode <auto|vector|graph|hybrid>[/]")
                continue

            if user_input.startswith("/topk"):
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    top_k = int(parts[1])
                    console.print(f"[green]Top-K set to:[/] [bold]{top_k}[/]")
                else:
                    console.print("[yellow]Usage: /topk <number>[/]")
                continue

            if user_input.startswith("/compare"):
                q = user_input[len("/compare") :].strip()
                if not q:
                    console.print("[yellow]Usage: /compare <question>[/]")
                    continue
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]Running comparison...[/]"),
                    transient=True,
                ) as progress:
                    progress.add_task("compare", total=None)
                    try:
                        h_res = client.query(question=q, mode="hybrid", top_k=top_k, debug=True)
                        b_res = client.query_baseline(question=q, top_k=top_k, debug=True)
                        render_comparison(h_res, b_res)
                    except Exception as e:
                        console.print(f"[bold red]Comparison Error:[/] {e}")
                continue

            if user_input.startswith("/entity"):
                name = user_input[len("/entity") :].strip()
                if not name:
                    console.print("[yellow]Usage: /entity <name_or_id>[/]")
                    continue
                try:
                    edata = client.get_entity(name)
                    render_entity_detail(edata)
                except Exception as e:
                    console.print(f"[bold red]Entity Lookup Error:[/] {e}")
                continue

            if user_input.startswith("/chunk"):
                cid = user_input[len("/chunk") :].strip()
                if not cid:
                    console.print("[yellow]Usage: /chunk <chunk_id>[/]")
                    continue
                try:
                    cdata = client.get_chunk(cid)
                    render_chunk_detail(cdata)
                except Exception as e:
                    console.print(f"[bold red]Chunk Lookup Error:[/] {e}")
                continue

            if user_input == "/health":
                try:
                    hdata = client.get_health()
                    console.print(f"Status: [bold green]{hdata.get('status')}[/]")
                    for comp, cinfo in hdata.get("components", {}).items():
                        console.print(f"  - {comp}: {cinfo.get('status')}")
                except Exception as e:
                    console.print(f"[bold red]Health check failed:[/] {e}")
                continue

            if user_input.startswith("/citations"):
                show_citations = not show_citations
                console.print(f"[green]Show citations:[/] {show_citations}")
                continue

            if user_input.startswith("/graph"):
                show_graph = not show_graph
                console.print(f"[green]Show graph paths:[/] {show_graph}")
                continue

            if user_input.startswith("/passages"):
                show_passages = not show_passages
                console.print(f"[green]Show vector passages:[/] {show_passages}")
                continue

            if user_input == "/clear":
                console.clear()
                continue

            # Standard question query execution
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]Retrieving evidence and generating answer...[/]"),
                transient=True,
            ) as progress:
                progress.add_task("query", total=None)
                try:
                    res = client.query(
                        question=user_input,
                        mode=current_mode,
                        top_k=top_k,
                        debug=True,
                    )
                except Exception as e:
                    console.print(f"[bold red]Error:[/] {e}")
                    continue

            render_query_response(
                res,
                show_citations=show_citations,
                show_graph=show_graph,
                show_passages=show_passages,
            )

        except KeyboardInterrupt:
            console.print("\n[dim]Use 'exit' or Ctrl+D to exit.[/dim]")
            continue
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break


def _print_repl_help() -> None:
    help_table = Table(
        title="GraphMind Interactive CLI Commands",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    help_table.add_column("Command / Shortcut", style="bold yellow", width=25)
    help_table.add_column("Description", style="white")

    help_table.add_row("<Any question text>", "Run grounded query with current mode")
    help_table.add_row("/mode <auto|vector|graph|hybrid>", "Switch active retrieval routing mode")
    help_table.add_row("/compare <question>", "Compare Hybrid GraphMind vs Plain Vector Baseline")
    help_table.add_row("/entity <name_or_id>", "Look up canonical entity details & connections")
    help_table.add_row("/chunk <chunk_id>", "Look up SEC chunk text and extraction observations")
    help_table.add_row("/health", "Check live database and LLM component health")
    help_table.add_row("/topk <number>", "Set retrieval top_k limit (default: 8)")
    help_table.add_row("/citations", "Toggle display of citation provenance table")
    help_table.add_row("/graph", "Toggle display of graph path triples table")
    help_table.add_row("/passages", "Toggle display of raw vector passages table")
    help_table.add_row("/clear", "Clear terminal screen")
    help_table.add_row("/help", "Show this command reference")
    help_table.add_row("/exit, quit, :q", "Exit interactive session")

    console.print(help_table)


def main() -> None:
    """CLI entry point for console scripts and module execution."""
    cli(obj={})


if __name__ == "__main__":
    main()
