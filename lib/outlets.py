"""Outlet lookup module for media-ctl.

Queries news, local, and radio tables in perm_intel (read-only mirrors
of permtrak2_crm) to search, retrieve, and fuzzy-match media outlets.

Tables:  news, local, radio
Schema:  id (varchar 17 hex), name, city, state, zip, circulation (int),
         rank (char), costperline (decimal), charsperline (int),
         emailmain, phonemain, website, preferredvendor, dateverified,
         deleted (tinyint 0=active 1=deleted), msa (news only)
"""

from lib import db
from rapidfuzz import fuzz, process

VALID_TYPES = ("news", "local", "radio")


def _validate_media_type(media_type):
    if media_type not in VALID_TYPES:
        raise ValueError(
            f"media_type must be one of {VALID_TYPES}, got {media_type!r}"
        )
    return media_type


# ── search / retrieve ───────────────────────────────────────────────


def search_outlets(media_type, state, city=None, county=None, msa=None, limit=20):
    """Search outlets by type and geography.

    Args:
        media_type: news, local, or radio
        state:      Two-letter state code (required)
        city:       Optional city filter (LIKE match)
        county:     Reserved — not yet mapped to a column
        msa:        Optional MSA filter (news table only)
        limit:      Max rows returned (default 20)

    Returns:
        List of outlet dicts, ordered by circulation DESC then rank ASC.
    """
    table = _validate_media_type(media_type)

    clauses = ["deleted = 0", "state = %s"]
    params = [state.upper()]

    if city:
        clauses.append("city LIKE %s")
        params.append(f"%{city}%")

    if msa and media_type == "news":
        clauses.append("msa LIKE %s")
        params.append(f"%{msa}%")

    where = " AND ".join(clauses)
    params.append(int(limit))

    sql = (
        f"SELECT * FROM `{table}` "
        f"WHERE {where} "
        f"ORDER BY CAST(circulation AS UNSIGNED) DESC, rank ASC "
        f"LIMIT %s"
    )
    return db.query(sql, params)


def get_outlet(media_type, outlet_id):
    """Get a single outlet by its hex ID.

    Returns:
        Outlet dict, or None if not found.
    """
    table = _validate_media_type(media_type)
    sql = f"SELECT * FROM `{table}` WHERE id = %s"
    return db.query_one(sql, (outlet_id,))


def get_outlets_for_zip(media_type, zip_code):
    """Resolve a ZIP to a state via zip_to_media, then return all active
    outlets in that state for the given media_type.

    Returns:
        List of outlet dicts ordered by circulation DESC, or [] if the
        ZIP is not found.
    """
    table = _validate_media_type(media_type)

    row = db.query_one(
        "SELECT state FROM zip_to_media WHERE zip = %s LIMIT 1",
        (str(zip_code).zfill(5),),
    )
    if not row:
        return []

    state = row["state"]
    sql = (
        f"SELECT * FROM `{table}` "
        f"WHERE deleted = 0 AND state = %s "
        f"ORDER BY CAST(circulation AS UNSIGNED) DESC"
    )
    return db.query(sql, (state,))


# ── display formatting ──────────────────────────────────────────────


def format_outlet_line(outlet, index=None):
    """Format an outlet dict into a compact display line.

    Example output:
        [1] Los Angeles Times              circ: 697,000  rank: A  cost: $18.50/line
    """
    prefix = f"[{index}] " if index is not None else ""
    name = (outlet.get("name") or "Unknown")[:35].ljust(35)

    circ = outlet.get("circulation") or 0
    try:
        circ_str = f"{int(circ):,}"
    except (ValueError, TypeError):
        circ_str = str(circ)

    rank = outlet.get("rank") or "-"

    cost = outlet.get("costperline")
    cost_str = f"${cost:.2f}/line" if cost else "n/a"

    return f"{prefix}{name}  circ: {circ_str}  rank: {rank}  cost: {cost_str}"


# ── fuzzy matching ──────────────────────────────────────────────────


def fuzzy_match_outlet(name, media_type, state, threshold=85):
    """Fuzzy-match an outlet name (e.g. from DOL data) against the table.

    Uses rapidfuzz token_sort_ratio so word-order differences and minor
    spelling variants still score well.

    Args:
        name:       Name string to match
        media_type: news, local, or radio
        state:      Two-letter state code to narrow candidates
        threshold:  Minimum score 0-100 (default 85)

    Returns:
        Dict with outlet and score keys, or None if no match
        meets the threshold.
    """
    table = _validate_media_type(media_type)

    rows = db.query(
        f"SELECT * FROM `{table}` WHERE deleted = 0 AND state = %s",
        (state.upper(),),
    )
    if not rows:
        return None

    choices = {i: (r.get("name") or "") for i, r in enumerate(rows)}

    result = process.extractOne(
        name,
        choices,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )
    if not result:
        return None

    matched_name, score, idx = result
    return {"outlet": rows[idx], "score": score}
