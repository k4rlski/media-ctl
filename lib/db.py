"""db.py - perm_intel database helpers for media-ctl."""

import pymysql
from pymysql.cursors import DictCursor

_CFG = dict(
    host="127.0.0.1",
    port=3307,
    user="perm_ctl",
    password="Db206ohUYP4tNHiosv6U",
    database="perm_intel",
    charset="utf8mb4",
    cursorclass=DictCursor,
)

_conn = None


def get_conn():
    """Return cached connection, reconnecting if needed."""
    global _conn
    if _conn is None or not _conn.open:
        _conn = pymysql.connect(**_CFG)
    else:
        _conn.ping(reconnect=True)
    return _conn


def close():
    """Close the cached connection."""
    global _conn
    if _conn and _conn.open:
        _conn.close()
    _conn = None


def query(sql, params=None):
    """Execute SELECT, return list of dicts."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()



def query_one(sql, params=None):
    """Execute SELECT, return first row as dict or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    """Execute INSERT/UPDATE/DELETE, return affected row count."""
    conn = get_conn()
    with conn.cursor() as cur:
        affected = cur.execute(sql, params)
        conn.commit()
        return affected


# ── domain helpers ────────────────────────────────────────────


def get_zip_info(zip_code):
    """Look up a single ZIP in zip_to_media."""
    rows = query("SELECT * FROM zip_to_media WHERE zip = %s", (zip_code,))
    return rows[0] if rows else None


def get_state_zips(state, media_type=None, unassigned_only=False,
                   needs_review=False):
    """Get ZIPs for a state with optional filters."""
    sql = "SELECT * FROM zip_to_media WHERE state = %s"
    params = [state]

    if media_type in ("news", "local", "radio") and unassigned_only:
        sql += f" AND {media_type}_id IS NULL"

    if needs_review:
        sql += " AND walker_status = 'needs_review'"

    sql += " ORDER BY population DESC"
    return query(sql, params)


def get_state_stats():
    """Per-state coverage stats from zip_to_media."""
    return query("""
        SELECT state,
               COUNT(*)                     AS total_zips,
               SUM(news_id  IS NOT NULL)    AS news_count,
               SUM(local_id IS NOT NULL)    AS local_count,
               SUM(radio_id IS NOT NULL)    AS radio_count
          FROM zip_to_media
         GROUP BY state
         ORDER BY state
    """)


def get_dol_data(zip_code=None, state=None, limit=10):
    """DOL frequency data from newspaper_by_zip.

    Columns: worksite_zip, worksite_city, worksite_state, newspaper_name,
    case_count, last_case_year. No county/msa columns exist.
    """
    conds, params = [], []

    if zip_code:
        conds.append("worksite_zip = %s")
        params.append(zip_code)
    if state:
        conds.append("worksite_state = %s")
        params.append(state)

    where = (" WHERE " + " AND ".join(conds)) if conds else ""

    sql = f"""
        SELECT newspaper_name,
               SUM(case_count) AS case_count,
               MAX(last_case_year) AS last_case_year
          FROM newspaper_by_zip{where}
         GROUP BY newspaper_name
         ORDER BY case_count DESC
         LIMIT %s
    """
    rows = query(sql, params + [limit])
    total = sum(int(r["case_count"]) for r in rows) if rows else 1
    for r in rows:
        r["case_count"] = int(r["case_count"])
        r["pct_share"] = round(r["case_count"] * 100.0 / total, 1) if total else 0
    return rows


def get_outlet_history(state=None, media_type=None, city=None):
    """Purchase history from crm_outlet_history."""
    conds, params = [], []

    if state:
        conds.append("state = %s")
        params.append(state)
    if media_type:
        conds.append("media_type = %s")
        params.append(media_type)
    if city:
        conds.append("city = %s")
        params.append(city)

    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    return query(
        f"SELECT * FROM crm_outlet_history{where} ORDER BY created_at DESC",
        params or None,
    )
