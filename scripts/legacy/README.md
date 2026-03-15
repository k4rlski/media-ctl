# Legacy Scripts

These scripts predate media-ctl and were used during early zip_to_media curation.

## ⚠️ WARNING — DB Redirect Required
All scripts currently point to `permtrak2_prod` on permtrak.com (wrong DB).
Before running ANY of these, update the DB connection to:
  host=127.0.0.1, port=3307, user=perm_ctl, db=perm_intel

## Scripts
| File | Purpose |
|------|---------|
| generate_google_maps_urls.py | Generate Google Maps URLs for outlet geocoding |
| test_google_maps.py | Test Maps URL generation |
| process_remaining_states.py | Bulk state processing for zip_to_media |
| comprehensive-media-preference-update.py | Mass outlet preference update |

These are preserved as reference and starting points for media-ctl commands.
