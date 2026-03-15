"""auto_assign.py - DOL-based research tool for the populate command.

DRY-RUN by default. Shows what DOL newspaper_by_zip data suggests for
each unassigned ZIP. Only writes to DB when --write is explicitly passed.
"""

from datetime import datetime
from lib import db, outlets
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def run_populate(state, media_type='news', dry_run=True, unassigned_only=True):
    state = state.upper()
    id_col = f"{media_type}_id"

    zips = db.get_state_zips(state, media_type=media_type,
                             unassigned_only=unassigned_only)
    if not zips:
        tag = 'unassigned ' if unassigned_only else ''
        console.print(f"[yellow]No {tag}ZIPs found for {state} / {media_type}[/yellow]")
        return

    mode_color = 'green' if dry_run else 'red'
    mode_label = 'DRY RUN' if dry_run else 'LIVE WRITE'
    console.print(Panel(
        f"[bold]{state}[/bold] -- {media_type} -- {len(zips):,} ZIPs to process\n"
        f"Mode: [{mode_color}]{mode_label}[/{mode_color}]",
        title="[bold cyan]populate[/bold cyan]",
        style="blue", expand=False,
    ))
    console.print()

    tbl = Table(title=f"DOL Research -- {state} / {media_type}", show_lines=True)
    tbl.add_column("#",              justify="right", width=5)
    tbl.add_column("ZIP",            width=7)
    tbl.add_column("City",           width=18)
    tbl.add_column("County",         width=16)
    tbl.add_column("DOL Newspaper",  width=30)
    tbl.add_column("Cases",          justify="right", width=8)
    tbl.add_column("CRM Match",      width=30)
    tbl.add_column("Score",          justify="right", width=7)
    tbl.add_column("Result",         width=14)

    matched = low_conf = no_data = written = 0

    for i, z in enumerate(zips, 1):
        zip_code = z["name"]
        city     = z.get("city") or "?"
        county   = z.get("county") or "?"

        dol_rows = db.get_dol_data(zip_code=zip_code, limit=1)

        if not dol_rows:
            no_data += 1
            tbl.add_row(str(i), zip_code, city, county,
                        "[dim]-- no DOL data --[/dim]", "--",
                        "[dim]--[/dim]", "--", "[dim]NO DATA[/dim]")
            continue

        dol_name   = dol_rows[0]["newspaper_name"]
        case_count = dol_rows[0]["case_count"]

        match = outlets.fuzzy_match_outlet(dol_name, media_type, state,
                                           threshold=70)

        if match and match["score"] >= 85:
            matched += 1
            outlet   = match["outlet"]
            score    = match["score"]
            crm_name = outlet.get("name", "?")
            result   = "[green]MATCH[/green]"

            if not dry_run and outlet.get("id"):
                db.execute(
                    f"UPDATE zip_to_media SET {id_col} = %s, "
                    f"walker_status = 'auto', walker_updated = %s "
                    f"WHERE name = %s",
                    (outlet["id"],
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     zip_code),
                )
                written += 1
                result = "[bold green]WRITTEN[/bold green]"

        elif match:
            low_conf += 1
            score    = match["score"]
            crm_name = match["outlet"].get("name", "?")
            result   = f"[yellow]LOW ({score:.0f}%)[/yellow]"
        else:
            low_conf += 1
            score    = 0
            crm_name = "[dim]-- no match --[/dim]"
            result   = "[red]NO MATCH[/red]"

        if score >= 85:
            sc = f"[green]{score:.0f}%[/green]"
        elif score >= 70:
            sc = f"[yellow]{score:.0f}%[/yellow]"
        elif score:
            sc = f"[red]{score:.0f}%[/red]"
        else:
            sc = "--"

        tbl.add_row(str(i), zip_code, city, county,
                    dol_name[:30], f"{case_count:,}",
                    str(crm_name)[:30], sc, result)

    console.print(tbl)
    console.print()

    total = len(zips)
    summary = (
        f"[bold]Summary:[/bold]  {total:,} ZIPs processed\n"
        f"  [green]Matched (>=85%)[/green]: {matched:,}\n"
        f"  [yellow]Low confidence / no CRM match[/yellow]: {low_conf:,}\n"
        f"  [dim]No DOL data[/dim]: {no_data:,}"
    )
    if not dry_run:
        summary += f"\n  [bold green]Written to DB[/bold green]: {written:,}"
    else:
        summary += "\n  [dim]DRY RUN -- pass --write to apply matches[/dim]"

    console.print(Panel(summary, style="blue", expand=False))
    console.print()
