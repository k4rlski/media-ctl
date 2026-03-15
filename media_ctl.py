#!/usr/bin/env python3
"""media-ctl — PERM Media Outlet Curation CLI

Entry point for the media-ctl tool. Lib modules (lib.db, lib.outlets)
are being built in parallel; DB helpers are inline until those land.
"""

import sys
import click
import pymysql
import pymysql.cursors
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

try:
    from lib.db import get_db
    from lib.outlets import lookup_outlet
except ImportError:
    pass

VERSION = "0.1.0"
console = Console()

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "perm_ctl",
    "password": "Db206ohUYP4tNHiosv6U",
    "database": "perm_intel",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db():
    """Connect to perm_intel on DBX via local tunnel (port 3307)."""
    return pymysql.connect(**DB_CONFIG)


def pct_color(count, total):
    """Rich-formatted count + percentage — green >90 %, yellow 50-90 %, red <50 %."""
    if total == 0:
        return "[dim]—[/dim]"
    pct = count / total * 100
    if pct > 90:
        c = "green"
    elif pct >= 50:
        c = "yellow"
    else:
        c = "red"
    return f"[{c}]{count:,} ({pct:.0f}%)[/{c}]"


def _pct(n, total):
    return (n / total * 100) if total else 0


def status_label(news_pct, local_pct, radio_pct):
    """Completion status based on average coverage."""
    avg = (news_pct + local_pct + radio_pct) / 3
    if avg >= 95:
        return "[bold green]COMPLETE[/bold green]"
    if avg >= 80:
        return "[yellow]IN PROGRESS[/yellow]"
    if avg > 0:
        return "[red]STARTED[/red]"
    return "[dim]PENDING[/dim]"


def banner():
    console.print()
    console.print(Panel(
        "[bold cyan]media-ctl[/bold cyan]  |  PERM Media Outlet Curation"
        f"   [dim]v{VERSION}[/dim]",
        style="blue", expand=False,
    ))
    console.print()


# ─── CLI Group ────────────────────────────────────────────────────

@click.group()
def cli():
    """media-ctl — PERM Media Outlet Curation CLI"""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  stats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@cli.command()
@click.option("--state", default=None, help="Detailed county breakdown for one state")
def stats(state):
    """Show assignment progress by state."""
    banner()
    conn = get_db()
    try:
        if state:
            _stats_detail(conn, state.upper())
        else:
            _stats_summary(conn)
    finally:
        conn.close()


def _stats_summary(conn):
    """Per-state summary — all 50+ states in one table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT state,
                   COUNT(*)                                               AS total,
                   SUM(CASE WHEN news_id  IS NOT NULL THEN 1 ELSE 0 END) AS news_n,
                   SUM(CASE WHEN local_id IS NOT NULL THEN 1 ELSE 0 END) AS local_n,
                   SUM(CASE WHEN radio_id IS NOT NULL THEN 1 ELSE 0 END) AS radio_n
            FROM zip_to_media
            GROUP BY state
            ORDER BY state
        """)
        rows = cur.fetchall()

    if not rows:
        console.print("[red]No data in zip_to_media.[/red]")
        return

    tbl = Table(title="Assignment Progress — All States", show_lines=True)
    tbl.add_column("State",  style="bold", justify="center", width=6)
    tbl.add_column("ZIPs",   justify="right", width=8)
    tbl.add_column("News",   justify="right", width=16)
    tbl.add_column("Local",  justify="right", width=16)
    tbl.add_column("Radio",  justify="right", width=16)
    tbl.add_column("Status", justify="center", width=14)

    gt = gn = gl = gr = 0

    for r in rows:
        t  = r["total"]
        nn = r["news_n"]
        ln = r["local_n"]
        rn = r["radio_n"]
        gt += t; gn += nn; gl += ln; gr += rn

        tbl.add_row(
            r["state"] or "??",
            f"{t:,}",
            pct_color(nn, t),
            pct_color(ln, t),
            pct_color(rn, t),
            status_label(_pct(nn, t), _pct(ln, t), _pct(rn, t)),
        )

    tbl.add_section()
    tbl.add_row(
        "[bold]ALL[/bold]",
        f"[bold]{gt:,}[/bold]",
        pct_color(gn, gt),
        pct_color(gl, gt),
        pct_color(gr, gt),
        "",
    )

    console.print(tbl)
    console.print()


def _stats_detail(conn, state):
    """County-level breakdown for a single state."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)                                               AS total,
                   SUM(CASE WHEN news_id  IS NOT NULL THEN 1 ELSE 0 END) AS news_n,
                   SUM(CASE WHEN local_id IS NOT NULL THEN 1 ELSE 0 END) AS local_n,
                   SUM(CASE WHEN radio_id IS NOT NULL THEN 1 ELSE 0 END) AS radio_n
            FROM zip_to_media WHERE state = %s
        """, (state,))
        hdr = cur.fetchone()

        if not hdr or hdr["total"] == 0:
            console.print(f"[red]No ZIPs found for state {state}.[/red]")
            return

        cur.execute("""
            SELECT COALESCE(county, '(unknown)') AS county,
                   COUNT(*)                                               AS total,
                   SUM(CASE WHEN news_id  IS NOT NULL THEN 1 ELSE 0 END) AS news_n,
                   SUM(CASE WHEN local_id IS NOT NULL THEN 1 ELSE 0 END) AS local_n,
                   SUM(CASE WHEN radio_id IS NOT NULL THEN 1 ELSE 0 END) AS radio_n
            FROM zip_to_media WHERE state = %s
            GROUP BY county ORDER BY county
        """, (state,))
        counties = cur.fetchall()

    t = hdr["total"]
    console.print(Panel(
        f"[bold]{state}[/bold]  —  {t:,} ZIPs  |  "
        f"News: {hdr['news_n']:,}/{t:,}  |  "
        f"Local: {hdr['local_n']:,}/{t:,}  |  "
        f"Radio: {hdr['radio_n']:,}/{t:,}",
        title=f"[bold cyan]{state} Detail[/bold cyan]",
        style="blue", expand=False,
    ))
    console.print()

    tbl = Table(title=f"{state} — County Breakdown", show_lines=True)
    tbl.add_column("County", style="bold", width=28)
    tbl.add_column("ZIPs",   justify="right", width=8)
    tbl.add_column("News",   justify="right", width=16)
    tbl.add_column("Local",  justify="right", width=16)
    tbl.add_column("Radio",  justify="right", width=16)

    for c in counties:
        ct = c["total"]
        tbl.add_row(
            c["county"],
            f"{ct:,}",
            pct_color(c["news_n"], ct),
            pct_color(c["local_n"], ct),
            pct_color(c["radio_n"], ct),
        )

    console.print(tbl)
    console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  show
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@cli.command()
@click.option("--zip", "zipcode", required=True, help="ZIP code to inspect")
def show(zipcode):
    """Show everything known about a ZIP code."""
    banner()
    conn = get_db()
    try:
        _show_zip(conn, zipcode)
    finally:
        conn.close()


def _outlet_name(cur, table, oid):
    """Look up outlet name from news/local/radio table in perm_intel."""
    if not oid:
        return None
    try:
        cur.execute(f"SELECT name FROM `{table}` WHERE id = %s", (oid,))
        row = cur.fetchone()
        return row["name"] if row else None
    except Exception:
        return None


def _show_zip(conn, zipcode):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM zip_to_media WHERE name = %s", (zipcode,))
        z = cur.fetchone()
        if not z:
            console.print(f"[red]ZIP {zipcode} not found in zip_to_media.[/red]")
            return

        news_name     = _outlet_name(cur, "news",  z.get("news_id"))
        altnews_name  = _outlet_name(cur, "news",  z.get("altnews_id"))
        local_name    = _outlet_name(cur, "local", z.get("local_id"))
        altlocal_name = _outlet_name(cur, "local", z.get("altlocal_id"))
        radio_name    = _outlet_name(cur, "radio", z.get("radio_id"))
        altradio_name = _outlet_name(cur, "radio", z.get("altradio_id"))

        cur.execute("""
            SELECT newspaper_name, case_count, last_case_year
            FROM newspaper_by_zip
            WHERE worksite_zip = %s
            ORDER BY case_count DESC LIMIT 10
        """, (zipcode,))
        dol = cur.fetchall()

        cur.execute("""
            SELECT outlet_name, media_type, total_cases, last_used
            FROM crm_outlet_history
            WHERE outlet_state = %s
            ORDER BY total_cases DESC LIMIT 10
        """, (z.get("state", ""),))
        history = cur.fetchall()

    city    = z.get("city") or "?"
    state   = z.get("state") or "?"
    county  = z.get("county") or "?"
    msa     = z.get("msaname") or "—"
    pop_raw = z.get("population")
    try:
        pop_str = f"{int(pop_raw):,}" if pop_raw else "—"
    except (ValueError, TypeError):
        pop_str = str(pop_raw) if pop_raw else "—"
    walker  = z.get("walker_status") or "—"
    wdt     = z.get("walker_updated") or ""

    info = (
        f"[bold]{zipcode}[/bold]  |  {city}, {state}\n"
        f"County: {county}  |  MSA: {msa}\n"
        f"Population: {pop_str}  |  Walker: [cyan]{walker}[/cyan]  {wdt}"
    )
    console.print(Panel(info,
        title=f"[bold cyan]ZIP {zipcode}[/bold cyan]",
        style="blue", expand=False,
    ))

    def _fmt(name, oid):
        if not oid:
            return "[dim]— unassigned —[/dim]"
        return f"[green]{name or oid}[/green]  [dim]{oid}[/dim]"

    at = Table(title="Current Assignments", show_lines=True, expand=False)
    at.add_column("Type",    style="bold", width=10)
    at.add_column("Primary", width=44)
    at.add_column("Alt",     width=44)
    at.add_row("News",  _fmt(news_name,     z.get("news_id")),
                         _fmt(altnews_name,  z.get("altnews_id")))
    at.add_row("Local", _fmt(local_name,     z.get("local_id")),
                         _fmt(altlocal_name, z.get("altlocal_id")))
    at.add_row("Radio", _fmt(radio_name,     z.get("radio_id")),
                         _fmt(altradio_name, z.get("altradio_id")))
    console.print(at)
    console.print()

    if dol:
        dt = Table(title=f"DOL PERM History — ZIP {zipcode}",
                   show_lines=True, expand=False)
        dt.add_column("#",               justify="right", width=4)
        dt.add_column("Newspaper (DOL)", width=40)
        dt.add_column("Cases",           justify="right", width=10)
        dt.add_column("Last Year",       justify="right", width=10)
        for i, d in enumerate(dol, 1):
            dt.add_row(
                str(i),
                d.get("newspaper_name", "?"),
                f"{d.get('case_count', 0):,}",
                str(d.get("last_case_year") or "—"),
            )
        console.print(dt)
    else:
        console.print(f"[dim]No DOL PERM data for ZIP {zipcode}.[/dim]")
    console.print()

    if history:
        ht = Table(title=f"Our Case History — {state}",
                   show_lines=True, expand=False)
        ht.add_column("Outlet",    width=36)
        ht.add_column("Type",      width=8)
        ht.add_column("Cases",     justify="right", width=8)
        ht.add_column("Last Used", width=12)
        for h in history:
            ht.add_row(
                h.get("outlet_name", "?"),
                h.get("media_type", "?"),
                f"{h.get('total_cases', 0):,}",
                str(h.get("last_used", "—")),
            )
        console.print(ht)
        console.print()

    notes = z.get("walker_notes")
    if notes:
        console.print(Panel(notes, title="Walker Notes", style="dim"))
        console.print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Stubs — curate-news / curate-local / curate-radio
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@cli.command("curate-news")
@click.option("--zip", "zipcode", default=None, help="Single ZIP to curate")
@click.option("--city", default=None)
@click.option("--state", default=None)
@click.option("--county", default=None)
@click.option("--msa", default=None)
@click.option("--unassigned-only", is_flag=True, help="Only ZIPs with no news_id")
@click.option("--needs-review", is_flag=True, help="Only walker_status=needs_review")
@click.option("--auto", is_flag=True, help="Auto-pick top DOL candidate, no prompts")
def curate_news(zipcode, city, state, county, msa, unassigned_only, needs_review, auto):
    """Interactive newspaper curation session."""
    from lib.walker import run_walk
    banner()
    run_walk('news', state=state, county=county, city=city, msa=msa,
             zipcode=zipcode, unassigned_only=unassigned_only,
             needs_review=needs_review, auto=auto)


@cli.command("curate-local")
@click.option("--zip", "zipcode", default=None, help="Single ZIP to curate")
@click.option("--city", default=None)
@click.option("--state", default=None)
@click.option("--county", default=None)
@click.option("--msa", default=None)
@click.option("--unassigned-only", is_flag=True, help="Only ZIPs with no local_id")
@click.option("--needs-review", is_flag=True, help="Only walker_status=needs_review")
@click.option("--auto", is_flag=True, help="Auto-pick top candidate, no prompts")
def curate_local(zipcode, city, state, county, msa, unassigned_only, needs_review, auto):
    """Interactive local paper curation session."""
    from lib.walker import run_walk
    banner()
    run_walk('local', state=state, county=county, city=city, msa=msa,
             zipcode=zipcode, unassigned_only=unassigned_only,
             needs_review=needs_review, auto=auto)


@cli.command("curate-radio")
@click.option("--zip", "zipcode", default=None, help="Single ZIP to curate")
@click.option("--city", default=None)
@click.option("--state", default=None)
@click.option("--county", default=None)
@click.option("--msa", default=None)
@click.option("--unassigned-only", is_flag=True, help="Only ZIPs with no radio_id")
@click.option("--needs-review", is_flag=True, help="Only walker_status=needs_review")
@click.option("--auto", is_flag=True, help="Auto-pick top candidate, no prompts")
def curate_radio(zipcode, city, state, county, msa, unassigned_only, needs_review, auto):
    """Interactive radio station curation session."""
    from lib.walker import run_walk
    banner()
    run_walk('radio', state=state, county=county, city=city, msa=msa,
             zipcode=zipcode, unassigned_only=unassigned_only,
             needs_review=needs_review, auto=auto)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Stubs — populate / contact-sweep / export / set-alt
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@cli.command()
@click.option("--state", default=None, help="State to populate")
@click.option("--type", "media_type", default=None, help="news | local | radio")
@click.option("--write", is_flag=True, default=False, help="Write matches to DB (default is dry-run)")
@click.option("--unassigned-only", is_flag=True, default=True, help="Skip ZIPs that already have assignment")
def populate(state, media_type, write, unassigned_only):
    """DOL-based research tool — shows what DOL data suggests per ZIP."""
    from lib.auto_assign import run_populate
    banner()
    if not state:
        console.print("[red]--state is required[/red]")
        return
    if not media_type:
        media_type = 'news'
    run_populate(state, media_type, dry_run=(not write), unassigned_only=unassigned_only)


@cli.command("contact-sweep")
@click.option("--state", default=None, help="State to sweep")
@click.option("--type", "media_type", default=None, help="news | local | radio")
@click.option("--id", "outlet_id", default=None, help="Single outlet ID to sweep")
@click.option("--write", is_flag=True, default=False, help="Write findings to CRM (default is dry-run)")
def contact_sweep(state, media_type, outlet_id, write):
    """Phase 3: scrape outlet websites for contact info."""
    from lib.contact_sweep import run_sweep
    banner()
    run_sweep(state=state, media_type=media_type or 'news', outlet_id=outlet_id, write=write)


@cli.command()
@click.option("--state", default=None, help="State to export")
@click.option("--type", "media_type", default=None, help="news | local | radio")
@click.option("--output", default=None, help="Output CSV path")
def export(**kwargs):
    """Export assignments to CSV."""
    click.echo("Not yet implemented")


@cli.command("set-alt")
@click.option("--zip", "zipcode", default=None, help="Single ZIP")
@click.option("--county", default=None, help="Apply to all ZIPs in county")
@click.option("--state", default=None)
@click.option("--type", "media_type", default=None, help="news | local | radio")
@click.option("--outlet-id", default=None, help="Outlet ID to set as alt")
@click.option("--note", default=None, help="Reason for the exception")
def set_alt(**kwargs):
    """Set alt/exception outlet for a ZIP or county."""
    click.echo("Not yet implemented")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    cli()
