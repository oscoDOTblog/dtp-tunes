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
#   make prod-ps                   list production containers
#
# Secrets live only in .env (gitignored). No flags to remember.

# LOCAL_PORT=8082 keeps the local gateway off production's 8080.
COMPOSE_LOCAL := LOCAL_PORT=8082 docker compose --project-name dtp-tunes-local -f docker-compose.yml -f docker-compose.local.yml
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml

# One shell per recipe, so heredocs work and a failing line stops the target.
.ONESHELL:

.PHONY: help local-up local-down local-config local-ps local-reset prod-config prod-deploy prod-down prod-ps

help:
	@echo "Targets: local-up [ARGS=-d], local-down, local-config, local-ps,"
	@echo "         local-reset CONFIRM=yes, prod-config, prod-deploy, prod-down, prod-ps"

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
	$(COMPOSE_LOCAL) run --rm -T api python - <<-'EOF'
	import os
	from pymongo import MongoClient
	prefix = os.environ.get('MONGODB_COLLECTION_PREFIX', '')
	if 'dev' not in prefix or prefix == 'tunes_':
	    raise SystemExit('Refusing to reset: not a dev prefix: ' + prefix)
	db = MongoClient(os.environ['MONGODB_URI'])[os.environ.get('MONGODB_DB', 'DTP')]
	dropped = [name for name in db.list_collection_names() if name.startswith(prefix)]
	for name in dropped:
	    db.drop_collection(name)
	print('Dropped ' + str(len(dropped)) + ' collection(s): ' + (', '.join(dropped) or '(none)'))
	EOF

prod-config:
	$(COMPOSE_PROD) config --quiet && echo "Production config resolves."

prod-deploy:
	$(COMPOSE_PROD) run --rm --build config-check
	$(COMPOSE_PROD) up -d --build
	@echo "Waiting for http://127.0.0.1:$${LOCAL_PORT:-8080}/health ..."
	@for i in $$(seq 1 30); do \
		if curl -fsS http://127.0.0.1:$${LOCAL_PORT:-8080}/health >/dev/null 2>&1; then \
			echo "Healthy."; break; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "ERROR: stack did not become healthy."; \
			$(COMPOSE_PROD) ps; exit 1; \
		fi; \
		sleep 5; \
	done

prod-down:
	$(COMPOSE_PROD) down

prod-ps:
	$(COMPOSE_PROD) ps
