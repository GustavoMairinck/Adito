# ==============================================================================
# Makefile — Muninn (Automação de Desenvolvimento, ETL e Desktop)
# ==============================================================================
#
# Execute `make` ou `make help` para visualizar a lista completa de comandos.
# Todos os comandos partem da raiz do repositório.
#

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------
# Diretórios do Monorepo
# ------------------------------------------------------------------------------
ROOT_DIR     := $(shell pwd)
APP_DIR      := $(ROOT_DIR)/Muninn/app
ETL_DIR      := $(ROOT_DIR)/Muninn/etl
SCRIPTS_DIR  := $(ROOT_DIR)/Muninn/scripts
FRONT_DIR    := $(APP_DIR)/frontend-vue
TAURI_DIR    := $(APP_DIR)/src-tauri
DATA_DIR     := $(if $(XDG_DATA_HOME),$(XDG_DATA_HOME),$(HOME)/.local/share)/br.edu.ifes.leds.muninn

# ------------------------------------------------------------------------------
# Ambientes Virtuais e Executáveis Python
# ------------------------------------------------------------------------------
APP_VENV     := $(APP_DIR)/.venv
APP_PYTHON   := $(if $(wildcard $(APP_VENV)/bin/python),$(APP_VENV)/bin/python,python3)

ETL_VENV     := $(ETL_DIR)/.venv
ETL_PYTHON   := $(if $(wildcard $(ETL_VENV)/bin/python),$(ETL_VENV)/bin/python,python3)
ETL_CLI      := $(if $(wildcard $(ETL_VENV)/bin/muninn-etl),$(ETL_VENV)/bin/muninn-etl,poetry run muninn-etl)

# ------------------------------------------------------------------------------
# Cores e Formatação ANSI para o Terminal
# ------------------------------------------------------------------------------
COLOR_RESET  := \033[0m
COLOR_BOLD   := \033[1m
COLOR_CYAN   := \033[36m
COLOR_GREEN  := \033[32m
COLOR_YELLOW := \033[33m
COLOR_RED    := \033[31m

.PHONY: help dev desktop dev-front build-front dev-tauri \
        db etl-popular etl-cruzar etl-ver etl-pii etl-extract \
        etl-src-acoes etl-src-participacoes etl-sigpesq etl-cnpq etl-lattes \
        test test-etl test-core test-mcp test-tauri \
        setup setup-app setup-etl clean clean-all check-setup

# ------------------------------------------------------------------------------
# 📖 Ajuda & Documentação Interativa
# ------------------------------------------------------------------------------
help: ## Exibe esta mensagem de ajuda com todos os comandos disponíveis
	@echo ""
	@echo -e "$(COLOR_BOLD)$(COLOR_CYAN)🦅 Muninn — Automação de Desenvolvimento (Makefile)$(COLOR_RESET)"
	@echo -e "Uso: $(COLOR_YELLOW)make [alvo]$(COLOR_RESET)\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(COLOR_GREEN)%-24s$(COLOR_RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# ------------------------------------------------------------------------------
# 🖥️ Aplicação Desktop & Frontend
# ------------------------------------------------------------------------------
dev: check-setup db ## Atalho mestre: verifica setup, reconstrói banco/fatos e sobe o app completo
	@echo -e "$(COLOR_CYAN)→ Iniciando Muninn Desktop via script oficial...$(COLOR_RESET)"
	@./rodar_desktop.sh

desktop: check-setup ## Inicia o ambiente desktop via ./rodar_desktop.sh (banco existente)
	@echo -e "$(COLOR_CYAN)→ Subindo Muninn Desktop (Vite + Núcleo Python + Janela Tauri)...$(COLOR_RESET)"
	@./rodar_desktop.sh

dev-front: ## Inicia apenas o servidor de desenvolvimento do frontend (Vite na porta 5173)
	@echo -e "$(COLOR_CYAN)→ Iniciando Frontend Vue em modo desenvolvimento...$(COLOR_RESET)"
	@cd $(FRONT_DIR) && npm run dev

build-front: ## Gera o build de produção do frontend Vue
	@echo -e "$(COLOR_CYAN)→ Compilando frontend Vue para produção...$(COLOR_RESET)"
	@cd $(FRONT_DIR) && npm run build

dev-tauri: ## Roda a casca desktop Tauri diretamente via cargo run
	@echo -e "$(COLOR_CYAN)→ Executando Tauri via Cargo...$(COLOR_RESET)"
	@cd $(TAURI_DIR) && cargo run

# ------------------------------------------------------------------------------
# 🔄 Banco de Dados & Fatos Analíticas (SQLite)
# ------------------------------------------------------------------------------
db: ## Reconstrói o banco SQLite (dados.db) com as 42 tabelas 3FN e as 6 Views dinâmicas das fatos (< 5s)
	@echo -e "$(COLOR_CYAN)→ Processando cruzamento e populando banco SQLite nativo (dados.db)...$(COLOR_RESET)"
	@if [ -f "$(ETL_DIR)/trabalho/pessoas.json" ]; then \
		echo -e "  [1/2] Usando trabalho/pessoas.json existente para carga rápida..."; \
	else \
		echo -e "  [1/2] Gerando cruzamento inicial de identidades..."; \
		cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) cruzar || true; \
	fi
	@echo -e "  [2/2] Inserindo tabelas 3FN e gerando 6 Views de fatos analíticas v2.0..."
	@$(APP_PYTHON) $(SCRIPTS_DIR)/popular_banco.py --etl $(ETL_DIR) --banco $(APP_DIR)/data/dados.db
	@mkdir -p "$(DATA_DIR)" 2>/dev/null || true
	@cp -f "$(APP_DIR)/data/dados.db" "$(DATA_DIR)/dados.db" 2>/dev/null || true
	@echo -e "$(COLOR_GREEN)✓ Banco dados.db (SQLite) e views analíticas prontos com sucesso!$(COLOR_RESET)"

etl-popular: db ## Alias para 'make db'

etl-ver: ## Abre o explorador de dados acadêmicos no terminal (ou passe ARGS="tabela")
	@$(APP_PYTHON) $(SCRIPTS_DIR)/ver_dados.py $(ARGS)

etl-cruzar: ## Executa o cruzamento de pessoas por nome normalizado (US-ETL-06)
	@echo -e "$(COLOR_CYAN)→ Executando cruzamento de identidades por nome...$(COLOR_RESET)"
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) cruzar

etl-pii: ## Realiza varredura de privacidade (Anti-PII) nos dados brutos e trabalho
	@echo -e "$(COLOR_CYAN)→ Verificando integridade e proteção de dados pessoais (PII)...$(COLOR_RESET)"
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) verificar-pii

etl-extract: etl-src-acoes etl-src-participacoes etl-sigpesq etl-cnpq etl-lattes ## Executa a extração completa de todas as fontes externas na web
	@echo -e "$(COLOR_GREEN)✓ Extração completa das fontes concluída.$(COLOR_RESET)"

etl-src-acoes: ## Extrai ações públicas do SRC (Campus Serra)
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) src-acoes --campus Serra

etl-src-participacoes: ## Extrai participações e equipes do SRC (área autenticada)
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) src-participacoes

etl-sigpesq: ## Extrai projetos e grupos do SigPesq
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) sigpesq

etl-cnpq: ## Extrai dados de espelho de grupos no CNPq/DGP
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) cnpq --unidade Serra

etl-lattes: ## Extrai currículos Lattes da lista de pesquisadores
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_CLI) lattes

# ------------------------------------------------------------------------------
# 🧪 Testes Automatizados
# ------------------------------------------------------------------------------
test: test-etl test-core test-mcp ## Executa sequencialmente todas as suítes de testes automatizados
	@echo -e "\n$(COLOR_BOLD)$(COLOR_GREEN)✓ Todas as suítes de testes foram executadas com sucesso!$(COLOR_RESET)\n"

test-etl: ## Executa os testes automatizados do ETL (pytest)
	@echo -e "$(COLOR_CYAN)→ Executando testes do ETL (Muninn/etl/tests)...$(COLOR_RESET)"
	@cd $(ETL_DIR) && PYTHONPATH=src $(ETL_PYTHON) -m pytest tests

test-core: ## Executa os testes unitários do núcleo Python (datastore, authorizer e regressão)
	@echo -e "$(COLOR_CYAN)→ Executando testes unitários do núcleo Python...$(COLOR_RESET)"
	@cd $(APP_DIR)/backend/nucleo && $(APP_PYTHON) -m unittest core.tests core.test_datastore_sqlite

test-mcp: ## Executa os testes de contrato e integração STDIO/MCP
	@echo -e "$(COLOR_CYAN)→ Executando testes de STDIO e Contrato RPC...$(COLOR_RESET)"
	@cd $(APP_DIR) && $(APP_PYTHON) scripts/teste_stdio.py
	@cd $(APP_DIR) && $(APP_PYTHON) scripts/teste_contrato.py

test-tauri: ## Executa os testes unitários em Rust da casca Tauri
	@echo -e "$(COLOR_CYAN)→ Executando testes do Tauri (Rust)...$(COLOR_RESET)"
	@cd $(TAURI_DIR) && cargo test

# ------------------------------------------------------------------------------
# ⚙️ Instalação, Setup & Verificações
# ------------------------------------------------------------------------------
check-setup:
	@if [ ! -d "$(APP_VENV)" ]; then \
		echo -e "$(COLOR_YELLOW)⚠️  Ambiente do app (.venv) não encontrado em $(APP_DIR)/.venv$(COLOR_RESET)"; \
		echo -e "Execute '$(COLOR_BOLD)make setup$(COLOR_RESET)' para configurar os ambientes virtuais e dependências.\n"; \
	fi

setup: setup-app setup-etl ## Configura todos os ambientes (Python venvs, dependências e npm)
	@echo -e "\n$(COLOR_BOLD)$(COLOR_GREEN)✓ Setup completo do Muninn concluído!$(COLOR_RESET)\n"

setup-app: ## Cria virtualenv do app, instala requirements e dependências do frontend
	@echo -e "$(COLOR_CYAN)→ Configurando ambiente do App (Python + Node.js)...$(COLOR_RESET)"
	@test -d $(APP_VENV) || python3 -m venv $(APP_VENV)
	@$(APP_VENV)/bin/pip install --upgrade pip
	@$(APP_VENV)/bin/pip install -r $(APP_DIR)/backend/requirements.txt
	@cd $(FRONT_DIR) && npm install

setup-etl: ## Cria virtualenv do ETL e instala o pacote muninn_etl com extras de desenvolvimento
	@echo -e "$(COLOR_CYAN)→ Configurando ambiente do ETL...$(COLOR_RESET)"
	@test -d $(ETL_VENV) || python3 -m venv $(ETL_VENV)
	@$(ETL_VENV)/bin/pip install --upgrade pip
	@$(ETL_VENV)/bin/pip install -e '$(ETL_DIR)[sigpesq,cnpq,lattes,infisical,dev]' 'playwright==1.64.0'
	@test -f $(ETL_DIR)/.env || cp $(ETL_DIR)/.env.example $(ETL_DIR)/.env

# ------------------------------------------------------------------------------
# 🧹 Limpeza
# ------------------------------------------------------------------------------
clean: ## Remove arquivos temporários de logs, caches do Python e pytest
	@echo -e "$(COLOR_CYAN)→ Limpando caches e arquivos temporários...$(COLOR_RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -f /tmp/*vite.log /tmp/*muninn*.log /tmp/oraculo-vite.log 2>/dev/null || true
	@echo -e "$(COLOR_GREEN)✓ Limpeza concluída.$(COLOR_RESET)"

clean-all: clean ## Limpa também builds gerados pelo frontend e Tauri
	@echo -e "$(COLOR_CYAN)→ Limpando diretórios de build (dist, target)...$(COLOR_RESET)"
	@rm -rf $(FRONT_DIR)/dist $(TAURI_DIR)/target 2>/dev/null || true
	@echo -e "$(COLOR_GREEN)✓ Build limpo.$(COLOR_RESET)"
