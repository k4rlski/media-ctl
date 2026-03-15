# media-ctl — Cursor Handoff
_Generated: 2026-03-15_

## What This Is
A Python CLI tool for curating the `zip_to_media` table — the master mapping of every
US ZIP code to its PERM-compliant media outlets (newspaper, local, radio).

This is NOT a web app. NOT a Mars feature. It is a standalone terminal tool that an
operator runs to walk through ZIP codes state by state, review outlet options, and
populate the database with curated, compliance-verified choices.

Once populated, `zip_to_media` becomes the authoritative source for case media
assignment in Mars — no AI guessing, just deterministic lookups.

---

## Repo
- Name: `k4rlski/media-ctl` (new, public)
- Deploy: claw.auto-ctl.io at `/opt/media-ctl/`
- Language: Python 3, Click CLI, rich terminal UI (use `rich` library for tables/prompts)

---

## Database (all reads/writes go to perm_intel on DBX — never permtrak.com)
- Host: `127.0.0.1` Port: `3307` User: `perm_ctl` Password: `Db206ohUYP4tNHiosv6U` DB: `perm_intel`
- Access: SSH to `root@172.236.243.118` (claw), then connect locally
- Tunnel: `dbx-tunnel.service` runs on claw, always active

---

## Core Tables (all in perm_intel on DBX)

### zip_to_media — the target table (44,422 rows loaded)
```sql
-- Key fields (full schema below)
zip           varchar(10)   -- ZIP code
state         varchar(2)    -- state abbreviation
county_name   varchar(100)
city          varchar(100)
msa_name      varchar(200)  -- Metro Statistical Area
cbsa_name     varchar(200)  -- Core Based Statistical Area
news_id       varchar(17)   -- FK → news.id
altnews_id    varchar(17)   -- FK → news.id (secondary/exception)
local_id      varchar(17)   -- FK → local.id
altlocal_id   varchar(17)   -- FK → local.id
radio_id      varchar(17)   -- FK → radio.id
altradio_id   varchar(17)   -- FK → radio.id
walker_status varchar(20)   -- 'pending' | 'reviewed' | 'skipped' | 'needs_review'
walker_notes  text
walker_updated datetime
population    int
lat           decimal(10,6)
lng           decimal(10,6)
gmapurl       varchar(500)
```

### news — newspaper outlets (mirrored from permtrak2_crm)
Key curation fields: `id, name, state, city, circulation, rank, msa, costperline,
charsperline, emailmain, phonemain, preferredvendor, dateverified`

### local — local/ethnic papers (mirrored)
Key fields: `id, name, state, city, circulation, costperline`

### radio — radio stations (mirrored)
Key fields: `id, name, state, city, format, coverage`

### newspaper_by_zip — DOL frequency data (166,497 rows)
`worksite_zip, worksite_state, worksite_city, newspaper_name, news_id, case_count`
This is the DOL-derived table showing which newspapers were actually used in
certified PERM cases per ZIP. Primary source for automated suggestions.

### crm_outlet_history — our purchase history (perm_intel)
`outlet_name, media_type, outlet_state, outlet_city, total_cases, last_used`

---

## CLI Commands

```bash
# Walk through a state, one media type at a time
media-ctl walk --state CA --type news
media-ctl walk --state CA --type local
media-ctl walk --state CA --type radio

# Walk by county within a state
media-ctl walk --state CA --county "Los Angeles" --type news

# Walk only unassigned ZIPs
media-ctl walk --state CA --type news --unassigned-only

# Walk ZIPs that need review (walker_status = 'needs_review')
media-ctl walk --state CA --type news --needs-review

# Batch auto-assign from DOL data (top DOL pick per ZIP, no review)
media-ctl auto-assign --state CA --type news --dry-run
media-ctl auto-assign --state CA --type news

# Show stats: how many ZIPs assigned per state
media-ctl stats
media-ctl stats --state CA

# Show what's assigned for a specific ZIP
media-ctl show --zip 90001

# Set exception/alt outlet for a ZIP or county
media-ctl set-alt --zip 92612 --type news --outlet-id <id> --note "EPD client prefers LA Times"
media-ctl set-alt --county "Orange" --state CA --type news --outlet-id <id>

# Export state to CSV for review
media-ctl export --state CA --type news --output ca_news.csv

# Import from CSV after offline review
media-ctl import --file ca_news.csv --dry-run
```

---

## Walk Session UX (the heart of the tool)

When operator runs `media-ctl walk --state CA --type news`:

```
╔══════════════════════════════════════════════════════════════════╗
║  media-ctl  |  California  |  Newspaper of General Circulation  ║
║  Progress: 1,203 / 2,847 ZIPs assigned  (42%)                   ║
╚══════════════════════════════════════════════════════════════════╝

ZIP: 90001  |  Los Angeles, CA
County: Los Angeles  |  MSA: Los Angeles-Long Beach-Anaheim
Population: 57,110

CURRENT ASSIGNMENT:  Los Angeles Times  ✓

── DOL HISTORY (newspaper_by_zip) ──────────────────────────────
  1. Los Angeles Times        4,231 certified PERM cases
  2. Los Angeles Daily News     892 cases
  3. La Opinion                 341 cases  [ethnic]

── OUR CASES IN THIS ZIP ────────────────────────────────────────
  14 cases — all used Los Angeles Times

── AVAILABLE OUTLETS (news, CA) ─────────────────────────────────
  [1] Los Angeles Times        circ: 697,000  rank: A  cost: $18.50/line
  [2] Los Angeles Daily News   circ: 178,000  rank: B  cost: $11.20/line
  [3] Orange County Register   circ: 144,000  rank: B  cost: $9.80/line
  [4] Long Beach Press-Telegram circ: 52,000  rank: C  cost: $7.40/line

Actions: [K]eep  [1-4] Pick outlet  [A] Set Alt  [N] No assignment
         [?] More outlets  [S] Skip  [Q] Quit  [!] Flag for review
> 
```

On selection:
- `K` — keep current, mark `walker_status='reviewed'`, advance
- `1-4` — assign that outlet, advance
- `A` — assign current as primary AND prompt for alt (sets `altnews_id`)
- `N` — set null assignment (intentionally unassigned), advance
- `?` — show more outlets (paginate)
- `S` — skip (leave status as-is), advance
- `Q` — quit, save progress
- `!` — flag as `needs_review`, advance

Progress auto-saves after each ZIP. Session can be interrupted and resumed.

---

## Alt / Exception Layer

The `altnews_id` (and `altlocal_id`, `altradio_id`) columns support client/attorney-level
exceptions WITHOUT modifying the primary assignment.

**Use case**: WBB clients (Blizzard/Activision) in Irvine, CA (ZIP 92618-92614) prefer
LA Times over OC Register. Primary `news_id` stays as OC Register for most clients.
`altnews_id` = LA Times for WBB exception.

This is stored in `zip_to_media` directly. Mars Ad-CTL can later query:
- `news_id` for default
- `altnews_id` for firm-level override (once attorney override logic is built)

The `walker_notes` field stores reasoning: "WBB preference: LA Times over OC Register per
Bill Bennett firm policy — set as altnews 2025-12-05"

---

## Auto-assign from DOL Data

`media-ctl auto-assign --state CA --type news` does:
1. For each ZIP in CA with no `news_id`:
   - Query `newspaper_by_zip` for top newspaper by `case_count` in that ZIP
   - Look up `news_id` by matching `newspaper_name` against `news` table
   - If match found with confidence > 80%: assign, set `walker_status='auto'`
   - If no match: set `walker_status='needs_review'`
2. Print summary: N auto-assigned, M need review
3. With `--dry-run`: print what would happen, no writes

This is how to bulk-populate the remaining 7,823 ZIPs without news_id efficiently.
After auto-assign, operator does `walk --needs-review` to spot-check.

---

## File Structure
```
/opt/media-ctl/
  media_ctl.py              ← Click CLI entry point
  lib/
    db.py                   ← pymysql connection to perm_intel (127.0.0.1:3307)
    walker.py               ← walk session logic, progress tracking
    auto_assign.py          ← DOL-based auto-assignment
    outlets.py              ← outlet lookup, search, fuzzy match
    exporter.py             ← CSV export/import
    normalizer.py           ← outlet name normalization for DOL matching
  config/
    media-ctl.yaml          ← DB creds, defaults
  rag/
    media-ctl-rag.md        ← RAG reference for OpenClaw
  requirements.txt          ← click, rich, pymysql, pyyaml, rapidfuzz
  README.md
```

---

## Implementation Order

1. `lib/db.py` — pymysql connection + helper functions
2. `media_ctl.py` — Click CLI skeleton with all command stubs
3. `lib/outlets.py` — outlet search/lookup from news/local/radio tables
4. `lib/walker.py` — core walk session: load ZIPs, display prompt, handle input, save
5. `media-ctl walk` — end-to-end with CA news (happy path first)
6. `lib/auto_assign.py` — DOL-based auto-assign + rapidfuzz name matching
7. `media-ctl auto-assign` — with --dry-run
8. `media-ctl stats` + `media-ctl show`
9. `lib/exporter.py` — CSV export/import
10. `media-ctl set-alt` — exception/alt layer
11. banner_ctl registration
12. `rag/media-ctl-rag.md`

---

## Porting Existing Scripts

### generate_google_maps_urls.py
- Currently connects to `permtrak2_prod` on permtrak.com — CHANGE to perm_intel on DBX
- Update connection: `host='127.0.0.1', port=3307, user='perm_ctl', password='Db206ohUYP4tNHiosv6U', database='perm_intel'`
- Integrate as `media-ctl gen-maps --state CA` command

### comprehensive-media-preference-update.py
- Client exception script (EPD/WBB overrides)
- Port to `media-ctl set-alt --file overrides.yaml` — YAML-driven batch alt assignments
- Current overrides to preserve:
  - Orange County, CA (92xxx ZIPs): altnews = LA Times (WBB/Blizzard/Activision)
  - NYC boroughs: specific borough papers
  - See existing script for full list

### process_remaining_states.py / .sh
- Batch runner for state-by-state processing
- Becomes `media-ctl auto-assign --state all` with per-state progress

---

## Key Data References
- `newspaper_by_zip`: DOL frequency by ZIP — primary auto-assign source
- `us_zips`: ZIP→county/MSA/CBSA/lat-lon reference (simplemaps v1.82, full USA)
- Dec 2025 backups in `/home/openclaw/.openclaw/workspace/inbox/media-walker/ZIPS-TO-MEDIA/backups/`
- CA was fully populated in Sep-Dec 2025 Cursor session
- TX, FL, NY partially done (MSA/CBSA assignments)

---

## DB Connection (for all scripts)
```python
import pymysql
conn = pymysql.connect(
    host='127.0.0.1', port=3307,
    user='perm_ctl', password='Db206ohUYP4tNHiosv6U',
    database='perm_intel', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
```
Must run on claw (172.236.243.118) — tunnel is local to claw only.

---

## After media-ctl Populates zip_to_media

Then and only then does Mars Ad-CTL get wired to use it:

```python
# In routes/quote_ctl.py — deterministic lookup replaces AI suggestion
def get_zip_media(zip_code):
    row = _dbx_query(
        f"SELECT z.*, n.name as news_name, lo.name as local_name, r.name as radio_name "
        f"FROM zip_to_media z "
        f"LEFT JOIN news n ON z.news_id=n.id "
        f"LEFT JOIN local lo ON z.local_id=lo.id "
        f"LEFT JOIN radio r ON z.radio_id=r.id "
        f"WHERE z.zip='{zip_code}' LIMIT 1;"
    )
    return row[0] if row else None
```

One call, deterministic result. No AI. No uncertainty.

---

## Test Command After Install
```bash
ssh root@172.236.243.118
cd /opt/media-ctl
python3 media_ctl.py stats
# Expected: table of states with ZIP assignment counts

python3 media_ctl.py show --zip 90001
# Expected: LA Times assigned, all fields shown

python3 media_ctl.py walk --state CA --type news --needs-review
# Expected: walk through any CA ZIPs flagged needs_review
```

---

## UPDATED: Exact Command Names & UX Flow (supersedes walk command above)

### Commands
```bash
media-ctl curate-news   # curate newspapers of general circulation
media-ctl curate-local  # curate local/ethnic papers
media-ctl curate-radio  # curate radio stations
media-ctl stats         # show assignment progress by state
media-ctl show --zip 90210  # show current assignment for a ZIP
```

### curate-news UX Flow (exact)

```
$ media-ctl curate-news

Enter a ZIP code, city, state, MSA, or CBSA for newspaper research & selection:
> 90210

ZIP: 90210 | Beverly Hills, CA | County: Los Angeles | MSA: Los Angeles-Long Beach-Anaheim

Newspapers of general circulation for 90210:

── PRIMARY CANDIDATE ──────────────────────────────────────────────
Los Angeles Times
  Circulation:  697,000 (weekday) | 1.1M (Sunday)
  Cost/line:    $18.50 | Chars/line: 38
  DOL PERM data: 4,231 certified PERM cases in this MSA (72% share)
  Our cases in 90210: 8 — all used Los Angeles Times
  Verified: 2025-11-14 | Preferred vendor: Yes
  Contact: ads@latimes.com | (213) 237-5000

── SECONDARY CANDIDATE ────────────────────────────────────────────
Los Angeles Daily News
  Circulation:  178,000
  Cost/line:    $11.20 | Chars/line: 35
  DOL PERM data: 892 certified PERM cases in this MSA (15% share)
  Our cases in 90210: 0

Select primary newspaper:
  1. Los Angeles Times     (72% DOL share, 697K circ)
  2. Los Angeles Daily News (15% DOL share, 178K circ)
  3. Show more options
> 1

You selected: Los Angeles Times as primary newspaper.
Populate now? (y/n): y

✓ Set Los Angeles Times as primary newspaper for ZIP 90210.

Designate a secondary newspaper (altnews)? (y/n): y

Select secondary newspaper:
  1. Los Angeles Times     (72% DOL share, 697K circ)
  2. Los Angeles Daily News (15% DOL share, 178K circ)
  3. Show more options
> 2

You selected: Los Angeles Daily News as secondary newspaper.
Populate now? (y/n): y

✓ Set Los Angeles Daily News as secondary newspaper for ZIP 90210.

── SUMMARY ────────────────────────────────────────────────────────
ZIP 90210 | Beverly Hills, CA
  Primary:   Los Angeles Times
  Secondary: Los Angeles Daily News

Continue? Enter next ZIP/city/state/MSA, or [Q] to quit:
>
```

### Input Flexibility
The prompt accepts any of:
- ZIP code: `90210`
- City + state: `Beverly Hills CA` or `Beverly Hills, CA`
- State only: `CA` → walk all unassigned ZIPs in CA in order
- MSA name: `Los Angeles-Long Beach-Anaheim` → walk all ZIPs in MSA
- CBSA/county: `Los Angeles County` → walk that county

Resolve to ZIP(s) via `perm_intel.us_zips` table:
- `zip` → direct lookup
- `city + state` → `WHERE city=X AND state=Y`
- `state only` → iterate all unassigned ZIPs in state, sorted by population DESC
- MSA/CBSA → `WHERE msa_name LIKE '%X%'`

### DOL Statistics Display
Pull from `perm_intel.newspaper_by_zip` for the ZIP.
If ZIP has no cases, pull MSA-level aggregate:
```sql
SELECT newspaper_name, SUM(case_count) as total,
       ROUND(100*SUM(case_count)/SUM(SUM(case_count)) OVER (), 1) as pct
FROM newspaper_by_zip
WHERE worksite_zip = '90210'   -- or WHERE msa_name = X for MSA fallback
GROUP BY newspaper_name
ORDER BY total DESC
LIMIT 10;
```
Show percentage share, not just raw count. "72% DOL share" is far more meaningful.

### Outlet Details Display
Pull from `perm_intel.news` (mirrored):
```sql
SELECT n.*, z.news_id, z.altnews_id
FROM news n
LEFT JOIN zip_to_media z ON z.news_id = n.id AND z.zip = '90210'
WHERE n.state = 'CA'
ORDER BY n.rank ASC, n.circulation DESC
LIMIT 10;
```

### Write on confirm
```sql
UPDATE zip_to_media
SET news_id = '{id}', walker_status = 'reviewed', walker_updated = NOW()
WHERE zip = '90210';

-- For secondary:
UPDATE zip_to_media
SET altnews_id = '{id}', walker_updated = NOW()
WHERE zip = '90210';
```

### same flow for curate-local and curate-radio
- `curate-local`: queries `local` table, references `local_id` / `altlocal_id`
- `curate-radio`: queries `radio` table, references `radio_id` / `altradio_id`
- Same DOL stats, same confirm flow, same input flexibility


---

## Mass-Populate Levels (IMPORTANT for Cursor)

When input resolves to multiple ZIPs, curate-news enters a walk loop — it iterates
through every ZIP at that level, one by one, in population-descending order.

```bash
# Single ZIP
media-ctl curate-news
> 90210
# → shows 1 ZIP, done

# City level — all ZIPs in Beverly Hills CA
> Beverly Hills CA
# → walks each ZIP in Beverly Hills in order

# County level — all ZIPs in Los Angeles County
> Los Angeles County CA
# → walks ~500 ZIPs in LA County, pop desc

# MSA level — all ZIPs in the MSA
> Los Angeles-Long Beach-Anaheim
# → walks entire MSA

# State level — all unassigned ZIPs in California
> CA
# → walks all CA ZIPs with no news_id, pop desc
# → operator can Q to stop and resume later
# → walker_status tracks progress
```

### Batch with --auto flag (no prompts)
For mass-populate without operator review (uses top DOL pick automatically):
```bash
media-ctl curate-news --auto --state CA
media-ctl curate-news --auto --county "Los Angeles" --state CA
media-ctl curate-news --auto --msa "Los Angeles-Long Beach-Anaheim"
```
--auto mode: picks top DOL candidate, no confirmation, sets walker_status='auto'.
Operator then does targeted review: `media-ctl curate-news --needs-review --state CA`

### Level flags (alternative to freeform input)
```bash
media-ctl curate-news --zip 90210
media-ctl curate-news --city "Beverly Hills" --state CA
media-ctl curate-news --county "Los Angeles" --state CA
media-ctl curate-news --msa "Los Angeles-Long Beach-Anaheim"
media-ctl curate-news --cbsa "Los Angeles-Long Beach" 
media-ctl curate-news --state CA
media-ctl curate-news --state CA --unassigned-only
media-ctl curate-news --state CA --needs-review
```

---

## NO AI — Hard Requirement

media-ctl has zero AI involvement. No Claude, no LLM, no API calls to any AI service.

Every recommendation comes exclusively from:
1. `perm_intel.newspaper_by_zip` — DOL-certified PERM case frequency (166K rows, real data)
2. `perm_intel.crm_outlet_history` — our own purchase history
3. `perm_intel.news` / `local` / `radio` — outlet details (circulation, cost, rank)
4. `perm_intel.zip_to_media` — existing curated assignments

The data IS the advice. "72% of certified PERM cases in this MSA used LA Times"
is worth more than any AI opinion. The operator makes every decision.

Do NOT add any AI/LLM features to this tool.

---

## Mass-Populate Command

```bash
# Auto-populate entire state from DOL data (no prompts)
media-ctl populate --state CA --type news
media-ctl populate --state CA --type local
media-ctl populate --state CA --type radio

# All types at once
media-ctl populate --state CA --all-types

# All states, all types (full DB population run)
media-ctl populate --all

# Dry run first — shows what would be written, no DB changes
media-ctl populate --state CA --type news --dry-run

# Only fill unassigned ZIPs (don't overwrite existing curated choices)
media-ctl populate --state CA --type news --unassigned-only

# Force overwrite even existing assignments
media-ctl populate --state CA --type news --overwrite
```

### How populate works (algorithm)

For each ZIP in scope, per media type:

**news:**
1. Query `newspaper_by_zip` for top newspaper by `case_count` WHERE `worksite_zip = zip`
2. If found: fuzzy-match `newspaper_name` against `news.name` WHERE `state = zip_state`
   using `rapidfuzz` (threshold: 85% similarity)
3. If match confidence ≥ 85%: assign `news_id`, set `walker_status='auto'`
4. If no ZIP-level data: fall back to county-level aggregate from `newspaper_by_zip`
5. If no county data: fall back to MSA-level aggregate
6. If still no match: set `walker_status='needs_review'`, skip

**local:**
1. Query `crm_outlet_history` WHERE `media_type='local' AND outlet_state=zip_state`
   ORDER BY `total_cases DESC` — our most-used local paper in that state
2. Geo-filter: prefer outlet WHERE city is in same county as ZIP (via `us_zips`)
3. If match: assign `local_id`, set `walker_status='auto'`
4. Else: `walker_status='needs_review'`

**radio:**
1. Query `crm_outlet_history` WHERE `media_type='radio' AND outlet_state=zip_state`
2. Same geo-filter logic as local
3. Assign or flag needs_review

### Output during populate run
```
Populating: California | Newspaper | 2,847 ZIPs

  ✓ 90001  Los Angeles Times           (DOL: 4,231 cases, 94% match)
  ✓ 90002  Los Angeles Times           (DOL: 3,891 cases, 94% match)
  ✓ 90210  Los Angeles Times           (DOL: 812 cases, 94% match)
  ? 93001  Ventura County Star         (DOL: 45 cases, 78% match — needs review)
  ✗ 96001  No DOL data for ZIP         (flagged needs_review)

Summary:
  Auto-assigned:   2,614  (91.8%)
  Needs review:      189  ( 6.6%)
  No data found:      44  ( 1.5%)

Run: media-ctl curate-news --state CA --needs-review
  to review the 189 flagged ZIPs manually.
```

### Post-populate review
After `populate`, operator runs:
```bash
media-ctl curate-news --state CA --needs-review
```
This walks only the 189 flagged ZIPs interactively. Combined workflow:
1. `populate --state CA --type news --dry-run` → verify counts
2. `populate --state CA --type news` → bulk fill 90%+
3. `curate-news --state CA --needs-review` → hand-review the edge cases
4. `stats --state CA` → confirm completion

---

## IMPORTANT: DOL Data is Reference Only — No Auto-Assign

The `dol_newspaper_freq_clean` table has severe name normalization issues.
Example — LA Times has 20+ variants:
  "The Los Angeles Times" (14,567 cases)
  "The La Times" (366 cases)
  "Los Angeles Times-Daily Pilot" (49 cases)
  "La Times, Orange County Edition" (3 cases)
  ... etc.

**DO NOT auto-assign from DOL data.** It will create garbage assignments.

### What DOL data IS used for in media-ctl
Display only — show operator the DOL statistics as research context:

```
DOL PERM data for 90210 (Beverly Hills, CA):
  Top papers used in this ZIP (raw DOL records):
  1. The Los Angeles Times    — 812 cases  (multiple name variants, combined)
  2. Los Angeles Daily News   — 134 cases
  3. Beverly Hills Courier    — 12 cases
```

The operator reads this, then makes their own selection from the clean `news` table.

### --populate command: REMOVED
The `--populate` mass-assign command is removed from scope.
All assignments go through operator review in `curate-news` / `curate-local` / `curate-radio`.
The tool is a curation tool, not a batch importer.

### MARS Report: dol-perm-media-selections
Build a separate read-only report page on MARS at `/ops/dol-media-report`
- Input: ZIP or state filter
- Shows: ZIP, city, state, top 5 DOL newspapers (raw names, case counts)
- Purpose: research reference while using media-ctl
- Source: `perm_intel.newspaper_by_zip` (raw DOL data, no normalization)
- No write capability — report only
