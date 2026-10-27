# ==============================================================================
# SismoWatch — Master Makefile
# ==============================================================================
# Control integral de pipeline, Spark, Ollama IA, backend FastAPI y frontend React.

SHELL := /bin/bash
PYTHON := .venv/bin/python3
PYTEST := .venv/bin/pytest
UVICORN := .venv/bin/uvicorn
OLLAMA_BIN := $(shell which ollama 2>/dev/null || echo "$$HOME/.local/ollama/bin/ollama")
PORT := 8000

.DEFAULT_GOAL := run

# ------------------------------------------------------------------------------
# 1. COMANDO PRINCIPAL: PONE A CORRER TODO DE UN SOLO COMANDO
# ------------------------------------------------------------------------------
.PHONY: run
run: ollama pipeline frontend start-server ## Pone a correr todo: Ollama IA + Pipeline USGS/Spark + Frontend + Backend

# ------------------------------------------------------------------------------
# 2. SERVICIO DE IA LOCAL: OLLAMA CON LLAMA 3.2 (3B)
# ------------------------------------------------------------------------------
.PHONY: ollama
ollama: ## Verifica e inicia el servicio Ollama con el modelo Llama 3.2 (3B)
	@echo "==> [1/4] Verificando servicio local de Ollama (127.0.0.1:11434)..."
	@if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then \
		echo "    Iniciando daemon Ollama en segundo plano..."; \
		nohup $(OLLAMA_BIN) serve >/dev/null 2>&1 & \
		sleep 2; \
	fi
	@if curl -s http://127.0.0.1:11434/api/tags | grep -q "llama3.2:3b"; then \
		echo "    Modelo llama3.2:3b listo en memoria."; \
	else \
		echo "    Descargando modelo llama3.2:3b (~2.0 GB)..."; \
		$(OLLAMA_BIN) pull llama3.2:3b; \
	fi

# ------------------------------------------------------------------------------
# 3. PIPELINE DE DATOS: EXTRACCIÓN EN VIVO USGS + ARQUITECTURA MEDALLION (SPARK)
# ------------------------------------------------------------------------------
.PHONY: pipeline
pipeline: ## Ejecuta el pipeline Medallion de Spark con ingesta 100% real de USGS
	@echo "==> [2/4] Ejecutando Pipeline Medallion (Ingesta Real USGS -> Raw -> Curated)..."
	@PYTHONPATH=. $(PYTHON) spark/jobs/seismic_medallion_job.py

# ------------------------------------------------------------------------------
# 4. FRONTEND: COMPILACIÓN REACT + VITE + TAILWIND
# ------------------------------------------------------------------------------
.PHONY: frontend
frontend: ## Compila el frontend moderno, minimalista y monocromático con Vite
	@echo "==> [3/4] Compilando frontend React + Vite + Tailwind..."
	@cd webapp/frontend && npm run build --silent
	@echo "    Frontend compilado en webapp/frontend/dist"

# ------------------------------------------------------------------------------
# 5. BACKEND & SERVIDOR WEB CONSOLIDADO
# ------------------------------------------------------------------------------
.PHONY: start-server
start-server: ## Inicia el servidor FastAPI sirviendo la API REST, Chatbot IA y la UI
	@echo "==> [4/4] Iniciando servidor SismoWatch en http://localhost:$(PORT)..."
	@fuser -k $(PORT)/tcp 2>/dev/null || true
	@echo ""
	@echo "=========================================================================="
	@echo "  SISMO/WATCH OPERACIONAL"
	@echo "  • Plataforma Web: http://localhost:$(PORT)"
	@echo "  • API Docs:       http://localhost:$(PORT)/docs"
	@echo "  • Inferencia IA:  Meta Llama 3.2 (3B) en Ollama (Local)"
	@echo "  • Datos:          100% Reales en Vivo desde USGS"
	@echo "=========================================================================="
	@echo ""
	@PYTHONPATH=. $(UVICORN) webapp.backend.main:app --host 0.0.0.0 --port $(PORT) --reload

# ------------------------------------------------------------------------------
# 6. SINCRONIZACIÓN EN VIVO (HOT REFRESH DESDE USGS API)
# ------------------------------------------------------------------------------
.PHONY: sync
sync: ## Sincroniza sismos reales en vivo desde la API de USGS hacia la base de datos
	@echo "==> Sincronizando eventos en vivo desde USGS..."
	@curl -s -X POST http://localhost:$(PORT)/api/events/sync | grep -o '"message":"[^"]*"' || echo "Servidor no responde en puerto $(PORT)"

# ------------------------------------------------------------------------------
# 7. ENTORNO DE DESARROLLO (VITE DEV SERVER + FASTAPI)
# ------------------------------------------------------------------------------
.PHONY: dev-ui
dev-ui: ## Inicia el servidor de desarrollo de Vite con Hot Module Replacement (HMR)
	@echo "==> Iniciando Vite Dev Server en http://localhost:5173..."
	@cd webapp/frontend && npm run dev

# ------------------------------------------------------------------------------
# 8. BATERÍA COMPLETA DE PRUEBAS AUTOMATIZADAS
# ------------------------------------------------------------------------------
.PHONY: test
test: ## Ejecuta los 45 tests automatizados del proyecto
	@echo "==> Ejecutando suite completa de 45 tests con Pytest..."
	@PYTHONPATH=. $(PYTEST) tests/ -v

# ------------------------------------------------------------------------------
# 9. GESTIÓN DE PROCESOS Y LIMPIEZA
# ------------------------------------------------------------------------------
.PHONY: stop
stop: ## Detiene el servidor web liberando el puerto 8000
	@echo "==> Deteniendo servidor en puerto $(PORT)..."
	@fuser -k $(PORT)/tcp 2>/dev/null && echo "Servidor detenido." || echo "Puerto $(PORT) ya estaba libre."

.PHONY: clean
clean: ## Limpia archivos temporales de Python, caché de pytest y builds
	@echo "==> Limpiando archivos temporales y cachés..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache
	@echo "Limpieza completada."

# ------------------------------------------------------------------------------
# 10. AYUDA INTERACTIVA
# ------------------------------------------------------------------------------
.PHONY: help
help: ## Muestra la lista de comandos disponibles
	@echo ""
	@echo "Uso: make [comando]"
	@echo ""
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""
