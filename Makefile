# Friendly entry points for the course system.
#
# The system lives under `system/`; this Makefile wraps the few docker
# commands you actually need so the course doesn't lean on memorising
# compose flags.
#
#   make up        - build the base image, then build and start everything
#   make down      - stop and remove containers (volumes kept)
#   make logs      - tail every service's logs
#   make rebuild   - rebuild images and restart (skips the cache)
#   make clean     - down + remove volumes (wipes registry, traces, inbox)
#   make ps        - show what's running
#   make studio    - open the studio in your browser
#   make local-up  - same as `up`, but also starts a local Ollama server
#
# Override the model on the fly:
#   PROVIDER=ollama MODEL=gpt-oss:120b make local-up
#   PROVIDER=openai MODEL=qwen3-32b OPENAI_BASE_URL=https://provider.example/v1 make up

COMPOSE       := docker compose -f system/docker-compose.yml
BASE_IMAGE    := aoa-course/agent-base:latest
BASE_CONTEXT  := system/agents/_base

.PHONY: help up down logs rebuild clean ps studio local-up base-image

help:
	@awk '/^# / {sub(/^# ?/, ""); print}' $(MAKEFILE_LIST) | sed -n '1,30p'

base-image:
	docker build -t $(BASE_IMAGE) $(BASE_CONTEXT)

up: base-image
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

rebuild: base-image
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

clean:
	$(COMPOSE) down -v

ps:
	$(COMPOSE) ps

studio:
	@echo "Studio: http://localhost:8080"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:8080 || \
	 command -v open      >/dev/null 2>&1 && open      http://localhost:8080 || \
	 echo "Open http://localhost:8080 in your browser."

local-up: base-image
	$(COMPOSE) --profile local up --build -d
