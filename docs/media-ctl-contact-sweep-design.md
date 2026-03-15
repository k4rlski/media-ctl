# media-ctl Contact Sweep — Design Doc
_Created: 2026-03-15_

## Purpose
Crawl every newspaper record in permtrak2_crm (`news` + `local` tables) to:
1. Confirm/fill website URL
2. Extract phone number (advertising/main)
3. Extract advertising contact email (preferred: classifieds/ad dept)
4. Update CRM record with findings

## Three-Phase IL Template (generalizes to all states)

### Phase 1 — Research & Attribution
- Assign `news_id` and `local_id` to every ZIP in `zip_to_media` for the state
- Verify all assigned papers are still in print (not defunct)
- Add supplemental outlet records (map pins) using `[County Name] County papers` search
- **IL: COMPLETE as of 2026-03-15**

### Phase 2 — Geocoding Sweep
- Ensure every `news` and `local` record has `city` + `state` populated
- Records without city cannot show as map pins in Ad-CTL
- Run after Phase 1; quick SQL audit + fill pass
- **IL: COMPLETE as of 2026-03-15** (all 14 active primary + 27 active local records geocodable)

### Phase 3 — Contact Info Sweep
- For each paper: website → scrape → extract phone + ad email
- For papers without website: web search → find site → scrape
- Target fields: `website`, `phone`/`phonemain`, `email`/`emailmain`, `contactname`
- **IL: PENDING — this doc**

---

## Contact Sweep Script Design

### Input
- CRM table: `news` or `local`
- Filter: `state='IL' AND deleted=0`
- Fields to populate: `website`, `phonemain`, `emailmain`, `contactname`, `dateverified`

### Algorithm per record

```
1. If website is NULL/empty:
   a. Search: "{name} {city} {state} newspaper advertising"
   b. Extract first result URL that looks like the paper's own domain
   c. Write to website field

2. Fetch website homepage:
   a. Follow redirects, timeout 10s
   b. Look for links containing: advertise, advertising, classifieds, contact, rates, media-kit

3. Fetch advertising/contact page:
   a. Parse for:
      - Phone: regex \(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}
      - Email: regex [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
        Priority keywords near email: advertis, classif, ad@, ads@, display
      - Contact name: look for "advertising manager", "ad director", "classifieds"

4. Write to CRM:
   - phonemain = best phone found
   - emailmain = best ad email found (prefer advertis*/classif* over info@/editor@)
   - contactname = ad contact name if found
   - dateverified = today
   - website = confirmed URL
```

### Priority email patterns (best → worst)
1. `advertis*@domain` / `ads@domain` / `display@domain`
2. `classifieds@domain` / `classif*@domain`
3. `contact@domain` / `info@domain`
4. Any email on the advertising page

### Pages to check on each site
- `/advertise` `/advertising` `/classifieds`
- `/contact` `/contact-us` `/about`
- `/media-kit` `/rate-card` `/rates`
- Homepage (fallback)

---

## Implementation Options

### Option A: media-ctl CLI command (recommended)
Add `contact-sweep` command to `k4rlski/media-ctl`:
```
media-ctl contact-sweep --state IL --type news   # sweep all IL news records
media-ctl contact-sweep --state IL --type local  # sweep all IL local records
media-ctl contact-sweep --state IL               # both
media-ctl contact-sweep --id <crm_id>            # single record
```
- Runs on claw (has DBX tunnel + CRM SSH access)
- Uses `requests` + `beautifulsoup4` for scraping
- Uses Brave Search API for missing websites
- Dry-run mode: print findings without writing
- Output: rich table with found/not-found status per field

### Option B: Standalone script
- `scripts/contact_sweep.py` in mars-status or media-ctl repo
- Same logic, simpler entry point

**Decision: Option A — add to media-ctl as Phase 3 command**

---

## CRM Write Fields (news table)
| Field | Source |
|-------|--------|
| `website` | scraped/searched URL |
| `phonemain` | best phone on ad page |
| `emailmain` | best ad email on ad page |
| `contactname` | ad manager name if found |
| `dateverified` | today's date |
| `verifycontacts` | set to "SWEEP-{date}" |

Same fields in `local` table (same schema).

---

## IL Scope
- **Active primary papers** (news): 14 records
- **Active local papers** (local): 27 records  
- **Total supplemental local records** (IL, deleted=0): ~230 records
- **Priority**: records with NULL website first, then confirm existing websites

## Execution Plan
1. Build `contact-sweep` command in media-ctl (Cursor session)
2. Run dry-run on IL news (14 records) — review output
3. Approve → run live → update CRM
4. Run on IL locals (27 assigned) — review
5. Run on all IL supplemental records (~200)
6. Template applies to TX, FL, NY in same order

---

## Notes
- Brave Search API key available: `BSAlrtsNMrPxxjTDv_xBo05-58UOc9a`
- CRM SSH write via: `ssh root@45.33.114.131 mysql ... permtrak2_crm`
- Rate limit: 1 request/sec to be polite; total IL run ~30min
- Some Shaw Local papers all route through shawlocal.com — may need domain-specific scraping
- Gannett/USA Today network papers (pjstar.com, galesburg.com, etc.) share ad infrastructure
