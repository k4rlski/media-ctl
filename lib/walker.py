"""walker.py - Interactive ZIP-by-ZIP curation walk for media-ctl.

Drives the walk session: resolves ZIP filters, presents a rich prompt
for each ZIP, handles user actions, and writes assignments back to
zip_to_media.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from lib import db, outlets

MEDIA_MAP = {
    "news":  {"table": "news",  "col": "news_id",  "alt_col": "altnews_id"},
    "local": {"table": "local", "col": "local_id",  "alt_col": "altlocal_id"},
    "radio": {"table": "radio", "col": "radio_id",  "alt_col": "altradio_id"},
}


# ── ZIP resolution ──────────────────────────────────────────────────


def resolve_zips(state=None, county=None, city=None, msa=None,
                 zipcode=None, media_type="news",
                 unassigned_only=False, needs_review=False):
    """Resolve user filters into a sorted list of ZIP dicts from zip_to_media."""
    clauses, params = [], []

    if zipcode:
        clauses.append("name = %s")
        params.append(str(zipcode).zfill(5))
    elif city and state:
        clauses.append("city = %s")
        clauses.append("state = %s")
        params.extend([city.upper(), state.upper()])
    elif county and state:
        clauses.append("county = %s")
        clauses.append("state = %s")
        params.extend([county.upper(), state.upper()])
    elif msa:
        clauses.append("msaname LIKE %s")
        params.append(f"%{msa}%")
    elif state:
        clauses.append("state = %s")
        params.append(state.upper())

    if unassigned_only and media_type in MEDIA_MAP:
        clauses.append(f"{MEDIA_MAP[media_type]['col']} IS NULL")

    if needs_review:
        clauses.append("walker_status = 'needs_review'")

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = (
        f"SELECT * FROM zip_to_media{where} "
        f"ORDER BY CAST(population AS UNSIGNED) DESC"
    )
    return db.query(sql, params or None)


# ── display ─────────────────────────────────────────────────────────


def display_zip_prompt(zip_row, media_type, console):
    """Show rich prompt for one ZIP. Returns the list of available outlets."""
    meta = MEDIA_MAP[media_type]
    zip_code = zip_row["name"]
    state = zip_row.get("state", "")

    # ---- header ----
    header = (
        f"[bold cyan]{zip_code}[/]  "
        f"{zip_row.get('city', '')}  {state}  |  "
        f"County: {zip_row.get('county', '')}  |  "
        f"MSA: {zip_row.get('msaname') or '-'}  |  "
        f"Pop: {zip_row.get('population', '?')}"
    )
    console.print(Panel(header, title="ZIP", border_style="blue"))

    # ---- current assignment ----
    current_id = zip_row.get(meta["col"])
    if current_id:
        cur_outlet = outlets.get_outlet(media_type, current_id)
        if cur_outlet:
            console.print(
                f"  [green]Current:[/] {outlets.format_outlet_line(cur_outlet)}"
            )
        else:
            console.print(f"  [yellow]Current ID:[/] {current_id}  (not found)")
    else:
        console.print("  [dim]Current: unassigned[/]")

    alt_id = zip_row.get(meta["alt_col"])
    if alt_id:
        alt_outlet = outlets.get_outlet(media_type, alt_id)
        if alt_outlet:
            console.print(
                f"  [green]Alt:[/]     {outlets.format_outlet_line(alt_outlet)}"
            )
        else:
            console.print(f"  [yellow]Alt ID:[/]  {alt_id}  (not found)")

    # ---- DOL / history ----
    console.print()
    if media_type == "news":
        dol_rows = db.get_dol_data(zip_code=zip_code, limit=5)
        if dol_rows:
            tbl = Table(
                title="DOL History (newspaper_by_zip)",
                show_lines=False,
                pad_edge=False,
            )
            tbl.add_column("Newspaper", style="cyan", min_width=30)
            tbl.add_column("Cases", justify="right")
            tbl.add_column("Share %", justify="right")
            for r in dol_rows:
                tbl.add_row(
                    str(r.get("newspaper_name", "")),
                    str(r.get("case_count", 0)),
                    str(r.get("pct_share", "")),
                )
            console.print(tbl)
        else:
            console.print("  [dim]No DOL history for this ZIP[/]")
    else:
        hist = db.get_outlet_history(state=state, media_type=media_type)
        if hist:
            console.print(
                f"  [dim]CRM outlet history: {len(hist)} records "
                f"for {media_type} in {state}[/]"
            )
        else:
            console.print(
                f"  [dim]No CRM outlet history for {media_type} in {state}[/]"
            )

    # ---- available outlets ----
    console.print()
    available = outlets.search_outlets(media_type, state, limit=10)
    if available:
        console.print("[bold]Available outlets:[/]")
        for i, o in enumerate(available, 1):
            console.print(f"  {outlets.format_outlet_line(o, index=i)}")
    else:
        console.print("  [dim]No active outlets found in state[/]")

    # ---- action hint ----
    console.print()
    console.print(
        r"[bold]\[K][/]eep  "
        r"[bold]\[1-N][/] Pick  "
        r"[bold]\[A][/]lt  "
        r"[bold]\[N][/]o assignment  "
        r"[bold]\[S][/]kip  "
        r"[bold]\[Q][/]uit  "
        r"[bold]\[!][/] Flag"
    )
    return available


# ── action handler ──────────────────────────────────────────────────


def handle_action(action, zip_row, media_type, available_outlets, console):
    """Process a single walk action.

    Returns:
        (should_continue, should_quit)  — both booleans.
    """
    meta = MEDIA_MAP[media_type]
    zip_code = zip_row["name"]
    action = action.strip()

    # Keep
    if action.lower() == "k":
        db.execute(
            "UPDATE zip_to_media "
            "SET walker_status='reviewed', walker_updated=NOW() "
            "WHERE name=%s",
            (zip_code,),
        )
        console.print("[green]Kept current assignment.[/]")
        return (True, False)

    # Quit
    if action.lower() == "q":
        return (False, True)

    # Skip
    if action.lower() == "s":
        console.print("[dim]Skipped.[/]")
        return (True, False)

    # Flag for review
    if action == "!":
        db.execute(
            "UPDATE zip_to_media "
            "SET walker_status='needs_review', walker_updated=NOW() "
            "WHERE name=%s",
            (zip_code,),
        )
        console.print("[yellow]Flagged for review.[/]")
        return (True, False)

    # No assignment (intentional null)
    if action.lower() == "n":
        db.execute(
            f"UPDATE zip_to_media "
            f"SET {meta['col']}=NULL, "
            f"walker_status='reviewed', walker_updated=NOW() "
            f"WHERE name=%s",
            (zip_code,),
        )
        console.print("[yellow]Cleared — intentionally unassigned.[/]")
        return (True, False)

    # Alt-outlet selection
    if action.lower() == "a":
        if not available_outlets:
            console.print("[red]No outlets available for alt selection.[/]")
            return (True, False)
        choice = Prompt.ask("  Alt outlet number")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available_outlets):
                picked = available_outlets[idx]
                db.execute(
                    f"UPDATE zip_to_media "
                    f"SET {meta['alt_col']}=%s, walker_updated=NOW() "
                    f"WHERE name=%s",
                    (picked["id"], zip_code),
                )
                console.print(
                    f"[green]Alt set:[/] {outlets.format_outlet_line(picked)}"
                )
            else:
                console.print("[red]Number out of range.[/]")
        except ValueError:
            console.print("[red]Enter a number.[/]")
        return (True, False)

    # Numeric pick (1-N)
    try:
        idx = int(action) - 1
        if 0 <= idx < len(available_outlets):
            picked = available_outlets[idx]
            db.execute(
                f"UPDATE zip_to_media "
                f"SET {meta['col']}=%s, "
                f"walker_status='reviewed', walker_updated=NOW() "
                f"WHERE name=%s",
                (picked["id"], zip_code),
            )
            console.print(
                f"[green]Assigned:[/] {outlets.format_outlet_line(picked)}"
            )
        else:
            console.print("[red]Number out of range.[/]")
        return (True, False)
    except ValueError:
        console.print(f"[red]Unknown action: {action!r}[/]")
        return (True, False)


# ── main walk loop ──────────────────────────────────────────────────


def run_walk(media_type, state=None, county=None, city=None, msa=None,
             zipcode=None, unassigned_only=False, needs_review=False,
             auto=False):
    """Run the interactive (or auto) walk session."""
    console = Console()

    if media_type not in MEDIA_MAP:
        console.print(f"[red]Invalid media_type: {media_type!r}[/]")
        return

    meta = MEDIA_MAP[media_type]

    zips = resolve_zips(
        state=state, county=county, city=city, msa=msa,
        zipcode=zipcode, media_type=media_type,
        unassigned_only=unassigned_only, needs_review=needs_review,
    )

    if not zips:
        console.print("[yellow]No ZIPs matched the given filters.[/]")
        return

    label_parts = [v for v in [state, county, city, msa, zipcode] if v]
    label = " | ".join(str(p) for p in label_parts) or "all"

    console.print(Panel(
        f"Walking [bold]{len(zips)}[/] ZIPs  |  {label}  |  {media_type}",
        border_style="green",
    ))

    stats = {"reviewed": 0, "skipped": 0, "flagged": 0}

    for i, z in enumerate(zips, 1):
        console.rule(f"[bold] {i} / {len(zips)} [/]")

        # ---- auto mode ----
        if auto:
            dol = db.get_dol_data(zip_code=z["name"], limit=1)
            if dol:
                top_name = dol[0].get("newspaper_name", "")
                match = outlets.fuzzy_match_outlet(
                    top_name, media_type, z.get("state", ""),
                )
                if match and match.get("outlet"):
                    picked = match["outlet"]
                    db.execute(
                        f"UPDATE zip_to_media "
                        f"SET {meta['col']}=%s, "
                        f"walker_status='auto', walker_updated=NOW() "
                        f"WHERE name=%s",
                        (picked["id"], z["name"]),
                    )
                    console.print(
                        f"  [green]AUTO {z['name']}:[/] "
                        f"{outlets.format_outlet_line(picked)} "
                        f"(score {match['score']})"
                    )
                    stats["reviewed"] += 1
                    continue

            db.execute(
                "UPDATE zip_to_media "
                "SET walker_status='needs_review', walker_updated=NOW() "
                "WHERE name=%s",
                (z["name"],),
            )
            console.print(f"  [yellow]AUTO {z['name']}:[/] no match — flagged")
            stats["flagged"] += 1
            continue

        # ---- interactive mode ----
        available = display_zip_prompt(z, media_type, console)
        action = Prompt.ask("Action")
        cont, quit_ = handle_action(
            action, z, media_type, available, console,
        )

        if action.strip().lower() == "s":
            stats["skipped"] += 1
        elif action.strip() == "!":
            stats["flagged"] += 1
        elif not quit_:
            stats["reviewed"] += 1

        if quit_:
            break

    # ---- summary ----
    console.print()
    console.print(Panel(
        f"[bold]Done.[/]  "
        f"Reviewed: [green]{stats['reviewed']}[/]  "
        f"Skipped: [dim]{stats['skipped']}[/]  "
        f"Flagged: [yellow]{stats['flagged']}[/]",
        border_style="green",
    ))
