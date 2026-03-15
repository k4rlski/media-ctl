# media-ctl

Interactive Python CLI for curating PERM advertising media outlet assignments per ZIP code.

Populates `zip_to_media` table in perm_intel (DBX) — the authoritative source for
PERM-compliant media outlet selection, used by Mars Ad-CTL for deterministic case assignment.

## Quick Start
```bash
media-ctl stats                           # show assignment progress by state
media-ctl walk --state CA --type news     # start curation session
media-ctl auto-assign --state CA --dry-run # preview DOL-based auto-assignment
media-ctl show --zip 90001                # show current assignment for ZIP
```

## Design Doc
See `docs/media-ctl-cursor-handoff.md`
