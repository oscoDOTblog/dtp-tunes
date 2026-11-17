# dtp-tunes — one entry point for local debugging and production deployment.
#
# Local dev talks to the SAME MongoDB as .env (typically Atlas) but under the
# dev collection prefix tunes_dev_* (prod uses tunes_*), on loopback port 8082.
# Production serves tunes_* behind Runtipi Traefik, with diagnostics on 8080.
#
#   make local-up [ARGS=-d]        start the local stack (ARGS passes through)
#   make local-down                stop it, preserving dev collections
#   make local-config              print the resolved local configuration
#   make local-ps                  list local containers
#   make local-reset CONFIRM=yes   delete only the tunes_dev_* collections
#   make prod-config               print the resolved production configuration
#   make prod-deploy               preflight, rebuild, start, wait for /health
#   make prod-down                 stop production (volumes preserved)
#   make prod-health                check the production /health endpoint
#   make prod-ps                   list production containers
#
# Secrets live only in .env (gitignored). No flags to remember.

# LOCAL_PORT=8082 keeps the local gateway off production's 8080.
COMPOSE_LOCAL := LOCAL_PORT=8082 docker compose --project-name dtp-tunes-local -f docker-compose.yml -f docker-compose.local.yml
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml

# Health-gate tuning: `make prod-deploy HEALTH_TRIES=60` waits longer.
HEALTH_TRIES ?= 30
HEALTH_WAIT ?= 5

# Portable style: one logical line per recipe step (works on old BSD make too).
.PHONY: help local-up local-down local-config local-ps local-reset prod-config prod-deploy prod-down prod-health prod-ps

help:
	@echo "Targets: local-up [ARGS=-d], local-down, local-config, local-ps,"
	@echo "         local-reset CONFIRM=yes, prod-config, prod-deploy, prod-down, prod-health, prod-ps"

local-up:
	@echo "Local debug collections: <MONGODB_DB from .env>/tunes_dev_*"
	$(COMPOSE_LOCAL) run --rm --build config-check
	$(COMPOSE_LOCAL) up --build $(ARGS)

local-down:
	$(COMPOSE_LOCAL) down

local-config:
	$(COMPOSE_LOCAL) config

local-ps:
	$(COMPOSE_LOCAL) ps

local-reset:
	@if [ "$(CONFIRM)" != "yes" ]; then \
		echo "This deletes tunes_dev_* collections from the shared MongoDB."; \
		echo "Re-run with CONFIRM=yes to proceed."; \
		exit 1; \
	fi
	$(COMPOSE_LOCAL) down
	$(COMPOSE_LOCAL) run --rm -T api python - < scripts/reset-dev-collections.py

prod-config:
	$(COMPOSE_PROD) config --quiet && echo "Production config resolves."

prod-deploy:
	$(COMPOSE_PROD) run --rm --build config-check
	$(COMPOSE_PROD) up -d --build
	$(MAKE) prod-health

# Same check prod-deploy runs, usable on its own against a running stack.
# Written as continuation lines breaking only outside quotes, so it behaves
# identically on old (3.81) and new make.
prod-health:
	@command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is not installed."; exit 1; }
	@URL=http://127.0.0.1:$${LOCAL_PORT:-8080}/health; TMP=$$(mktemp); trap 'rm -f "$$TMP"' EXIT; echo "Checking $$URL ..."; \
	for i in $$(seq 1 $(HEALTH_TRIES)); do if OUT=$$(curl -sS --noproxy '*' --max-time 5 -o "$$TMP" -w '%{http_code}' "$$URL" 2>&1); then \
	if [ "$$OUT" = 200 ]; then echo "Healthy:"; head -c 500 "$$TMP"; echo; exit 0; fi; \
	echo "attempt $$i/$(HEALTH_TRIES): HTTP $$OUT: $$(head -c 200 "$$TMP")"; \
	else echo "attempt $$i/$(HEALTH_TRIES): curl failed: $$OUT"; fi; sleep $(HEALTH_WAIT); done; \
	echo "ERROR: stack did not become healthy at $$URL"; $(COMPOSE_PROD) ps; $(COMPOSE_PROD) logs --tail=30 gateway; exit 1

prod-down:
	$(COMPOSE_PROD) down

prod-ps:
	$(COMPOSE_PROD) ps
