# Isolated Local Docker Database

## Summary

Add an explicit local-debug Compose mode that always uses a fresh bundled MongoDB and cannot write to the production MongoDB configured in `.env`.

Local song IDs may differ from production, which is acceptable for this mode.

## Implementation Changes

- Add `docker-compose.local.yml` that overrides `MONGODB_URI` for every database-using service:
  - `api`
  - scanner `worker`
  - `ingest-worker`
  - `playlist-transfer-worker`
- Force local settings to:
  - `MONGODB_URI=mongodb://mongodb:27017`
  - `MONGODB_DB=DTP_local`
  - `MONGODB_COLLECTION_PREFIX=tunes_`
- Enable the bundled MongoDB service and use a local-only named volume.
- Use a distinct Compose project name, `dtp-tunes-local`, so containers, networks, and volumes cannot collide with another dtp-tunes deployment.
- Add a small local-debug launcher with `up`, `down`, and `reset` commands:
  - `up` starts the base and local override files.
  - `down` stops local services while preserving the local database.
  - `reset` removes only the explicitly named local Compose volume after confirmation.
- Keep `.env` available for normal application secrets and API credentials, but make the local Compose override authoritative for all Mongo settings.
- Document that ordinary production deployment commands remain unchanged, while local debugging uses the launcher or the equivalent explicit Compose command.
- Print the resolved Mongo target before startup so it is obvious that the deployment is using `mongodb://mongodb:27017/DTP_local`.

## Test Plan

- Run `docker compose config` with the local override and verify every database-using service resolves to the bundled Mongo URI and `DTP_local`.
- Confirm local startup creates only the `dtp-tunes-local` containers and volume.
- Create or modify local library/playlists, then verify production Mongo collections are unchanged.
- Restart local Compose and confirm local data persists.
- Run the reset command and confirm only the local database volume is removed.
- Run existing backend tests and validate the normal production Compose configuration remains unchanged.

## Assumptions

- Local debugging does not need production song IDs.
- Local scans will generate independent song IDs and metadata.
- Production continues using the existing external Mongo configuration.
- No production data is automatically copied into the local database.
