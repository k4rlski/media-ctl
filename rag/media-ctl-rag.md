# media-ctl RAG — Machine-Readable Context
_Last updated: 2026-03-15_
_Repo: k4rlski/media-ctl | Deploy: /opt/media-ctl/ on claw (172.236.243.118)_

## What This Tool Does
media-ctl is a standalone Python CLI for curating the `zip_to_media` table — mapping every
US ZIP to the best newspaper of general circulation (news_id), local paper (local_id), and
radio station (radio_id) for PERM labor certification advertising under CFR 656.17.

**Zero AI** — all recommendations from DOL PERM frequency data (166K cases), not LLMs.
**Human decides** — tool presents data; operator accepts, skips, or overrides.

## Three-Phase Workflow (per state)

### Phase 1 — Research & Attribution
Assign news_id/local_id/radio_id to every ZIP. Search key: "[County Name] County papers"
to find all local publications per county. Verify print status before assigning.
IL: COMPLETE 2026-03-15 (100% primary, 95% local — Peoria+Champaign genuinely have no
distinct print local from their primary).

### Phase 2 — Geocoding Sweep
Every news/local record needs city+state to appear as map pin in Ad-CTL.
Run after Phase 1. Quick SQL audit + fill pass.
IL: COMPLETE 2026-03-15 — all 14 primary + 27 local IL papers geocodable.

### Phase 3 — Contact Info Sweep
Confirm website, extract phone, extract ad dept email for every paper.
Planned command: contact-sweep. See docs/media-ctl-contact-sweep-design.md.
Priority email: advertis*@ > classif*@ > contact@ > info@
IL: PENDING.

## Commands (planned / in progress)
  media-ctl curate-news   --zip <ZIP>    # interactive per-ZIP primary assignment
  media-ctl curate-local  --zip <ZIP>    # interactive local paper assignment
  media-ctl curate-radio  --zip <ZIP>    # interactive radio assignment
  media-ctl populate      --state <ST>   # mass-fill from DOL data
  media-ctl contact-sweep --state <ST>   # Phase 3 scrape: website/phone/email
  media-ctl contact-sweep --id <crm_id>  # single record
  media-ctl stats         --state <ST>   # completion %

## Database
- Write target: perm_intel on DBX (127.0.0.1:3307) — ZIP/outlet mapping
- CRM writes: permtrak2_crm via SSH hop through hiro (45.33.114.131)
- CRM SSH: ssh root@45.33.114.131 'mysql -h permtrak.com -u permtrak2_crm -p... permtrak2_crm'

## Key Tables
zip_to_media (perm_intel) — ZIP->outlet; news_id/local_id/radio_id/altnews_id/altlocal_id/altradio_id/walker_*
newspaper_by_zip (perm_intel) — DOL frequency data 166K cases (reference only)
dol_newspaper_freq_clean (perm_intel) — 5,680 canonical DOL newspaper names
news (permtrak2_crm) — newspapers of general circulation
local (permtrak2_crm) — local papers
radio (permtrak2_crm) — radio stations

## news/local Table Fields
id (17-char hex), name, city, state, zip, circulation, website, phone, phonemain,
email, emailmain, contactname, owner, description, deleted, dateverified, verifycontacts

## Illinois Status (2026-03-15) — FULLY COMPLETE
1,593 total IL ZIPs | 1,593 have news_id (100%) | 1,514 have local_id (95%)
79 ZIPs in Peoria+Champaign counties have no viable print local (intentional NULL)
All 14 primary + 27 local papers: geocodable

### IL Primary Assignments
Chicago metro (collar+city)         -> Chicago Sun-Times       (5006695af96398cd4)
Champaign-Urbana+Vermilion/Ford/IQ  -> News-Gazette            (fbeb03775c3454bd6)
Southern IL 18 counties             -> The Southern Illinoisan  (29c479bc8d0cba5be)
Metro East / Belleville             -> Belleville News-Democrat (6bfffbffd717eb3dd)
NW Illinois / Sterling              -> Sauk Valley Weekend      (b56e57bbd6e31660c)
Quad Cities                         -> Quad-City Times          (817b57e8aa3b4563f)
Peoria CBSA                         -> Peoria Journal Star      (c012df0aa03a01bca)
Bloomington-Normal                  -> The Pantagraph           (687168cc36e58897b)
Rockford CBSA                       -> Rockford Register Star   (0bd7a4e1b0f66e063)
Springfield CBSA                    -> State Journal-Register   (e17b69f73d916b3a3)
Decatur cluster                     -> Decatur Herald & Review  (a675bbbbd599b594d)
Quincy / western IL                 -> Quincy Herald-Whig       (23cedf335c8dfcbf6)
DeKalb                              -> DeKalb Daily Chronicle   (aec7d9f4cd789d8e9)
Effingham / central-south           -> Effingham Daily News     (4b3789e6b8ba0dc6f)

### IL Key Local Assignments
Cook suburban+DuPage   -> Cook County Daily Herald   (638d0d6e4d3d6ac0e)
Cook downtown/Loop     -> Crains Chicago Business    (8285f7bf398bf97ac)
Cook South/West Side   -> South Side Weekly          (696794e77a92712fa)
Cook North Side        -> Hyde Park Herald           (807e2ad72ee3f00ec)
Lake                   -> Lake County News Sun       (2b9e6d19d7f690dcd)
Will                   -> Joliet Herald-News         (5966a56b117a66cd6)
Kane                   -> Kane County Chronicle      (ba58894de69f0930d)
McHenry                -> Northwest Herald           (3be3fff86cbf74797)
Kendall                -> Kendall County Record      (3f590ff057e17f68c)
Kankakee/IQ/Ford/Grdy  -> Kankakee Daily Journal    (6752ddae585d2bb1e)
La Salle               -> NewsTribune               (d0a6d5c9aa8667175)
Sangamon+Springfield   -> Illinois Times             (e9963819ff71d08d1)
Vermilion              -> Commercial-News            (241bccb5de5b5d141)
Knox                   -> Galesburg Register-Mail    (2f82ce812cb2e0c2a)
McLean/DeWitt          -> Normalite Newspaper Group  (cb13e8e6d3ac0b1e7)
Livingston             -> Pontiac Daily Leader       (fd03ff5b24c2653e8)
Rock Island/Henry/Merc -> River Cities Reader        (b6dad30029d25d8a1)
Winnebago/Boone        -> Rock River Times           (Phase 7 — see MEMORY.md)
Saint Clair/Madison+   -> Alton Telegraph            (78bc7d15bd313c026)
Clinton                -> Breese Journal             (7502c6bbe6775abb5)
19 southern counties   -> Carbondale Times           (785fbae012aec7411)
Tazewell               -> Pekin Daily Times          (f1e0e3dc7e31f63f9)
Fulton                 -> Fulton County News         (e7cd5907f553faa5f)
Clark                  -> Strohm Newspapers          (bb529c20d8c5a063a)
Jersey                 -> Jersey County Journal      (aecea1c1cba820d53)
Schuyler               -> Rushville Times            (e36b842685ea56b42)
McDonough              -> McDonough-Democrat         (765acdf0302bcc6d9)
Mason                  -> Free Press-Progress        (ca6568cd359bdd029)
Henderson              -> Henderson County Quill     (eba911f620a8a1873)
Putnam                 -> Putnam County Record       (a546c3401022f41d2)
Woodford               -> Woodford County Journal    (962bd29f542e0cacd)
Marshall               -> Henry News-Republican      (a8b047a7b76707c43)
Warren                 -> Monmouth Daily Review Atlas (6a473abc14063ea1c)
Stark                  -> Stark County News          (f768c00c28b4c69ed)
Piatt                  -> Journal-Republican         (6508da7ac22576f1d)
Decatur cluster (local)-> Decatur Herald & Review    (55d8e7386a3eece03)
Quincy/western (local) -> Quincy Herald-Whig         (a1fc425e50531df48)
DeKalb (local)         -> DeKalb Daily Chronicle     (56c496763b65a6bbf)
Effingham/central-sth  -> Effingham Daily News       (38158297f950cca50)
Peoria                 -> NULL (no viable print local)
Champaign              -> NULL (Rantoul Press defunct 2021)

## Legacy Scripts (scripts/legacy/) — DO NOT RUN without DB redirect
generate_google_maps_urls.py        — Maps URLs for geocoding; points to permtrak2_prod WRONG DB
test_google_maps.py                 — Maps test; WRONG DB
process_remaining_states.py         — Bulk state processing; WRONG DB
comprehensive-media-preference-update.py — Mass outlet pref update; WRONG DB
All must be redirected to: host=127.0.0.1 port=3307 user=perm_ctl db=perm_intel

## Soft-Deleted Papers (never reassign)
Rantoul Press           dde69dad48e3212cb  closed March 2021
Murphysboro American    c6497d13b3a1c0990  closed summer 2015
Chicago Sun Times (dup) 68b7e5e5ae19eb07f  duplicate; 614 ZIPs migrated to active record
Chicago Reader          7fd042b673779e955  online-only since 2018; compliance gray area

## Rules
- NO AI in media-ctl — zero LLM calls
- Human confirms all writes — dry-run first
- CRM targeted field writes allowed: city/state/website/phone/email/contactname/dateverified
- Never ALTER TABLE — schema changes require Karl's manual approval
- perm_intel = intelligence layer; new tables go here, not permtrak2_crm
- Server (claw) = source of truth; git pull before changes, push after
- "County Name County papers" = standard research search key for local paper discovery

---

## Ohio Market Research (2026-03-15)

### Cincinnati Metro — Defunct Papers (DO NOT USE FOR PERM)
| Paper | Closed | Notes |
|-------|--------|-------|
| Western Star (Lebanon OH) | 2013 | Cox shut it; Ohio's oldest weekly (est. 1806) |
| Pulse-Journal (Mason OH) | 2013 | Merged into "Pulse of Warren County" → also defunct |
| Community Press (Cincinnati) | May 2022 | Gannett shut all 26 suburban editions |
| Springboro Star Press | 2013 | Cox suburban chain folded |

### Cincinnati Metro — Active Papers
| Paper | Type | Coverage | Notes |
|-------|------|----------|-------|
| Cincinnati Enquirer | Primary | Hamilton, Warren, Butler, Clermont, NKY | Only major daily; Sunday edition; 18,908 circ |
| Journal-News | Local | Butler County primary, Warren County secondary | Hamilton OH; Cox; covers Mason area |

### Warren County (Mason OH) Standard
- Primary: Cincinnati Enquirer
- Local: Journal-News (Hamilton OH) — no surviving Warren County print local
- zip_to_media: 45040 area uses Enquirer as primary (existing assignment)

### Defunct Outlet Policy
- CRM `description` field prefixed with `"Defunct [year]."` — no schema changes
- Bake script detects this → `defunct: true` in GeoJSON
- Dark brown `#5c3317` pins on map — preserved for attorney/client dispute context
