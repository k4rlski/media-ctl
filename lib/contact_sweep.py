"""contact_sweep.py - Phase 3: scrape outlet websites for contact info.

Per media-ctl-contact-sweep-design.md:
- Search for missing websites via Brave Search API
- Scrape advertising/contact pages for phone, email, contact name
- Dry-run by default; --write updates CRM via SSH to hiro
- Rate limited: 1 request/sec
"""

import re
import time
import subprocess
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from lib import db
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

BRAVE_API_KEY = "BSAlrtsNMrPxxjTDv_xBo05-58UOc9a"
BRAVE_URL     = "https://api.search.brave.com/res/v1/web/search"
CRM_SSH       = "root@45.33.114.131"
CRM_DB        = "permtrak2_crm"

PHONE_RE = re.compile(r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}')
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

AD_PATHS = [
    '/advertise', '/advertising', '/classifieds',
    '/contact', '/contact-us', '/about',
    '/media-kit', '/rate-card', '/rates',
]

AD_EMAIL_KW       = ['advertis', 'ads@', 'display', 'classif']
FALLBACK_EMAIL_KW = ['contact@', 'info@']

SKIP_DOMAINS = frozenset([
    'facebook.com', 'twitter.com', 'x.com', 'linkedin.com',
    'yelp.com', 'yellowpages.com', 'wikipedia.org', 'mapquest.com',
    'instagram.com', 'tiktok.com',
])

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


# -- helpers ---------------------------------------------------------

def _brave_search(query, count=5):
    try:
        r = requests.get(
            BRAVE_URL,
            headers={"X-Subscription-Token": BRAVE_API_KEY,
                     "Accept": "application/json"},
            params={"q": query, "count": count},
            timeout=10,
        )
        r.raise_for_status()
        return [
            {"title": w.get("title", ""), "url": w.get("url", "")}
            for w in r.json().get("web", {}).get("results", [])
        ]
    except Exception as exc:
        console.print(f"  [dim]Brave search error: {exc}[/dim]")
        return []


def _fetch(url, timeout=10):
    try:
        r = requests.get(url, headers={"User-Agent": UA},
                         timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return r.url, BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None, None


def _pick_website(results):
    for r in results:
        domain = urlparse(r["url"]).netloc.lower().replace("www.", "")
        if not any(sd in domain for sd in SKIP_DOMAINS):
            return r["url"]
    return None


def _find_ad_links(soup, base_url):
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = (a.get_text() or "").lower()
        for kw in ("advertis", "classif", "contact", "media-kit",
                   "rate", "about"):
            if kw in href or kw in text:
                full = urljoin(base_url, a["href"])
                if full not in found:
                    found.append(full)
                break
    return found[:10]


def _email_score(email):
    e = email.lower()
    for i, kw in enumerate(AD_EMAIL_KW):
        if kw in e:
            return i
    for i, kw in enumerate(FALLBACK_EMAIL_KW):
        if kw in e:
            return 10 + i
    if 'editor' in e or 'news' in e:
        return 50
    return 30


def _extract_contacts(soup):
    text = soup.get_text(separator=" ", strip=True)
    phones = PHONE_RE.findall(text)
    emails = list(set(EMAIL_RE.findall(text)))
    emails = [e for e in emails
              if not e.endswith(('.png', '.jpg', '.gif', '.css', '.js'))]
    emails.sort(key=_email_score)

    contact_name = None
    for pat in [
        r'[Aa]dvertising\s+[Mm]anager[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
        r'[Aa]d\s+[Dd]irector[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
        r'[Cc]lassifieds?[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
    ]:
        m = re.search(pat, text)
        if m:
            contact_name = m.group(1)
            break

    return {"phones": phones[:5], "emails": emails[:5],
            "contact_name": contact_name}


# -- single-outlet sweep --------------------------------------------

def _sweep_one(outlet, media_type):
    name    = outlet.get("name") or "Unknown"
    city    = outlet.get("city") or ""
    state   = outlet.get("state") or ""
    website = outlet.get("website") or ""

    findings = dict(id=outlet.get("id"), name=name, city=city, state=state,
                    website=website, phone=None, email=None,
                    contact_name=None, searched=False, pages_checked=0)

    if not website:
        q = f"{name} {city} {state} newspaper advertising"
        results = _brave_search(q)
        time.sleep(1)
        url = _pick_website(results)
        if url:
            findings["website"] = url
            findings["searched"] = True
            website = url
        else:
            return findings

    base_url, soup = _fetch(website)
    if not soup:
        return findings
    findings["pages_checked"] += 1

    home = _extract_contacts(soup)
    findings["phone"]        = (home["phones"] or [None])[0]
    findings["email"]        = (home["emails"] or [None])[0]
    findings["contact_name"] = home["contact_name"]

    ad_links = _find_ad_links(soup, base_url or website)
    parsed = urlparse(base_url or website)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    for p in AD_PATHS:
        c = base + p
        if c not in ad_links:
            ad_links.append(c)

    for link in ad_links[:8]:
        time.sleep(1)
        _, sub = _fetch(link)
        if not sub:
            continue
        findings["pages_checked"] += 1
        ct = _extract_contacts(sub)

        if ct["emails"]:
            best = ct["emails"][0]
            if not findings["email"] or _email_score(best) < _email_score(findings["email"]):
                findings["email"] = best
        if ct["phones"] and not findings["phone"]:
            findings["phone"] = ct["phones"][0]
        if ct["contact_name"] and not findings["contact_name"]:
            findings["contact_name"] = ct["contact_name"]

        if findings["email"] and any(
            kw in findings["email"].lower() for kw in AD_EMAIL_KW
        ):
            break

    return findings


# -- CRM write via SSH -----------------------------------------------

def _esc(s):
    return str(s).replace("'", "\\'").replace('"', '\\"')


def _write_crm(outlet_id, table, findings):
    sets = []
    today = date.today().strftime("%Y-%m-%d")
    if findings.get("website"):
        sets.append(f"website='{_esc(findings['website'])}'")
    if findings.get("phone"):
        sets.append(f"phonemain='{_esc(findings['phone'])}'")
    if findings.get("email"):
        sets.append(f"emailmain='{_esc(findings['email'])}'")
    if findings.get("contact_name"):
        sets.append(f"contactname='{_esc(findings['contact_name'])}'")
    sets.append(f"dateverified='{today}'")
    sets.append(f"verifycontacts='SWEEP-{today}'")
    if not sets:
        return False

    set_clause = ", ".join(sets)
    sql = f"UPDATE {table} SET {set_clause} WHERE id=\\'{_esc(outlet_id)}\\'"
    cmd = [
        "ssh", CRM_SSH,
        f'mysql -h permtrak.com -u permtrak2_crm -p"Ezp*r3m" -e "{sql}" {CRM_DB}'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except Exception as exc:
        console.print(f"  [red]CRM write error: {exc}[/red]")
        return False


# -- main entry point ------------------------------------------------

def run_sweep(state=None, media_type='news', outlet_id=None, write=False):
    if media_type not in ('news', 'local', 'radio'):
        console.print(f"[red]Invalid type: {media_type}[/red]")
        return

    state_upper = state.upper() if state else None

    if outlet_id:
        rows = db.query(
            f"SELECT * FROM `{media_type}` WHERE id = %s",
            (outlet_id,))
    elif state_upper:
        rows = db.query(
            f"SELECT * FROM `{media_type}` WHERE deleted = 0 "
            f"AND state = %s ORDER BY name",
            (state_upper,),
        )
    else:
        console.print("[red]--state or --id is required[/red]")
        return

    if not rows:
        console.print(f"[yellow]No {media_type} outlets found.[/yellow]")
        return

    mode_color = 'green' if not write else 'red'
    mode_label = 'DRY RUN' if not write else 'LIVE WRITE'
    console.print(Panel(
        f"[bold]{state_upper or 'Single'}[/bold] -- {media_type} -- "
        f"{len(rows):,} outlets\n"
        f"Mode: [{mode_color}]{mode_label}[/{mode_color}]",
        title="[bold cyan]contact-sweep[/bold cyan]",
        style="blue", expand=False,
    ))
    console.print()

    tbl = Table(title=f"Contact Sweep -- {state_upper or ''} / {media_type}",
                show_lines=True)
    tbl.add_column("#",       justify="right", width=4)
    tbl.add_column("Outlet",  width=28)
    tbl.add_column("City",    width=14)
    tbl.add_column("Website", width=30)
    tbl.add_column("Phone",   width=16)
    tbl.add_column("Email",   width=28)
    tbl.add_column("Contact", width=18)
    tbl.add_column("Pg",      justify="right", width=4)

    found_web = found_phone = found_email = crm_written = 0

    for i, outlet in enumerate(rows, 1):
        console.print(
            f"  [{i}/{len(rows)}] Sweeping "
            f"[bold]{outlet.get('name','?')}[/bold] ...",
            end="\r")

        f = _sweep_one(outlet, media_type)

        ws = f.get("website") or ""
        ws_disp = ws[:30] if ws else "[dim]--[/dim]"
        if f.get("searched"):
            ws_disp = f"[cyan]{ws_disp}[/cyan]"

        phone   = f.get("phone") or ""
        email   = f.get("email") or ""
        contact = f.get("contact_name") or ""

        if ws:    found_web   += 1
        if phone: found_phone += 1
        if email: found_email += 1

        if write and (ws or phone or email or contact):
            if _write_crm(outlet["id"], media_type, f):
                crm_written += 1

        tbl.add_row(
            str(i),
            (f.get("name") or "?")[:28],
            (f.get("city") or "?")[:14],
            ws_disp,
            phone or "[dim]--[/dim]",
            email[:28] if email else "[dim]--[/dim]",
            contact[:18] if contact else "[dim]--[/dim]",
            str(f.get("pages_checked", 0)),
        )

    console.print(" " * 80, end="\r")
    console.print(tbl)
    console.print()

    total = len(rows)
    summary = (
        f"[bold]Summary:[/bold]  {total:,} outlets swept\n"
        f"  Website found/confirmed: {found_web:,}/{total:,}\n"
        f"  Phone found: {found_phone:,}/{total:,}\n"
        f"  Email found: {found_email:,}/{total:,}"
    )
    if write:
        summary += f"\n  [bold green]Written to CRM: {crm_written:,}[/bold green]"
    else:
        summary += "\n  [dim]DRY RUN -- pass --write to update CRM[/dim]"

    console.print(Panel(summary, style="blue", expand=False))
    console.print()
