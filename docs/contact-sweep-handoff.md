# media-ctl Contact-Sweep Handoff
_Generated: 2026-03-16 by Cursor_
_Repo: k4rlski/media-ctl | Deploy: /opt/media-ctl/ on claw (172.236.243.118)_

## What This Is

Phase 3 of the media-ctl three-phase workflow. Scrapes newspaper/local outlet websites
to extract advertising contact info (phone, email, contact name, website URL) and
optionally writes findings to the CRM.

**Phase 1 (Research & Attribution)**: COMPLETE — news_id/local_id assigned per ZIP
**Phase 2 (Geocoding Sweep)**: COMPLETE — all outlets have city/state for map pins
**Phase 3 (Contact Sweep)**: READY — this document

## How to Run

```bash
# Dry-run (default) — show findings, no writes
python3 media_ctl.py contact-sweep --state IL --type news

# Single outlet by ID
python3 media_ctl.py contact-sweep --id 5006695af96398cd4

# Write results to CRM (updates permtrak2_crm via SSH to hiro)
python3 media_ctl.py contact-sweep --state IL --type news --write

# Local papers instead of news
python3 media_ctl.py contact-sweep --state IL --type local
```

All commands run from `/opt/media-ctl/` on claw.

## What It Does Per Outlet

1. If `website` is NULL: searches Brave API for `"{name} {city} {state} newspaper advertising"`
2. Fetches the homepage, follows redirects
3. Checks up to 8 sub-pages: `/advertise`, `/advertising`, `/classifieds`, `/contact`, `/contact-us`, `/about`, `/media-kit`, `/rates`
4. Extracts:
   - **Phone**: regex `\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}`
   - **Email**: prioritized by keyword proximity:
     1. `advertis*@` / `ads@` / `display@` (best)
     2. `classifieds@` / `classif*@`
     3. `contact@` / `info@`
     4. Any email on the advertising page (fallback)
   - **Contact name**: looks for "advertising manager", "ad director", "classifieds"
5. Displays findings in a rich table

## CRM Write (--write flag)

Updates `permtrak2_crm` on permtrak.com via SSH hop through hiro:
```
ssh root@45.33.114.131 "mysql -h permtrak.com -u permtrak2_crm -pEzp*r3m -e 'UPDATE...' permtrak2_crm"
```

Fields updated: `website`, `phonemain`, `emailmain`, `contactname`, `dateverified`

Rate limited: 1 request/sec to be polite to outlet websites.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `lib/contact_sweep.py` | 349 | Brave search, web scraping, email extraction, CRM writes |
| `lib/auto_assign.py` | 129 | DOL-based populate (dry-run research tool) |
| `lib/db.py` | 152 | PyMySQL connection to perm_intel |
| `lib/outlets.py` | 172 | Outlet search, lookup, rapidfuzz matching |
| `lib/walker.py` | 365 | Interactive walk session for curate commands |
| `media_ctl.py` | 481 | Click CLI entry point, 9 commands |

## All Available Commands

| Command | Purpose |
|---------|---------|
| `stats` | Per-state assignment progress (colored table) |
| `stats --state IL` | County breakdown for one state |
| `show --zip 90001` | Full ZIP detail: assignments, DOL history, outlets |
| `curate-news --state AL --unassigned-only` | Interactive ZIP walk for newspapers |
| `curate-local --state IL` | Interactive walk for local papers |
| `curate-radio --state CA` | Interactive walk for radio stations |
| `populate --state AL --type news` | DOL research display (dry-run default) |
| `contact-sweep --state IL --type news` | Phase 3: scrape for contact info |
| `export --state CA --type news` | (stub) CSV export |
| `set-alt --zip 92612 --type news --outlet-id X` | (stub) Exception/alt layer |

## Execution Plan for Contact Sweep

1. `contact-sweep --state IL --type news` — dry-run on 14 IL primary papers, review output
2. Approve findings, then `--write` to update CRM
3. `contact-sweep --state IL --type local` — sweep 27 assigned local papers
4. Review and `--write`
5. Repeat for TX, FL, NY, CA in same order
6. After each state: `stats --state XX` to confirm progress

## Rules

- NO AI in media-ctl — zero LLM calls
- Dry-run is always the default — `--write` required to touch CRM
- Rate limit: 1 req/sec to outlet websites
- CRM writes are targeted field updates only (website/phone/email/contact/dateverified)
- Never ALTER TABLE — schema changes require Karl's manual approval
