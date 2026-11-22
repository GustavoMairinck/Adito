# ==============================================================================
# Makefile — Adito (Automação de Desenvolvimento, ETL e Desktop)
# ==============================================================================
#
# Execute `make` ou `make help` para visualizar a lista completa de comandos.
# Todos os comandos partem da raiz do repositório.
# Suporta ambientes Linux, WSL e macOS (bash).
#

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------
# Diretórios do Monorepo
# ------------------------------------------------------------------------------
ROOT_DIR     := $(shell pwd)
APP_DIR      := $(ROOT_DIR)/Adito/app
ETL_DIR      := $(ROOT_DIR)/Adito/etl
SCRIPTS_DIR  := $(ROOT_DIR)/Adito/scripts
FRONT_DIR    := $(APP_DIR)/frontend-vue
TAURI_DIR    := $(APP_DIR)/src-tauri
DATA_DIR     := $(if $(XDG_DATA_HOME),$(XDG_DATA_HOME),$(HOME)/.local/share)/br.edu.ifes.leds.adito

# ------------------------------------------------------------------------------
# Ambientes Virtuais e Executáveis
# ------------------------------------------------------------------------------
APP_VENV     := $(APP_DIR)/.venv
APP_PYTHON   := $(APP_VENV)/bin/python

ETL_VENV     := $(ETL_DIR)/.venv
ETL_PYTHON   := $(ETL_VENV)/bin/python
ETL_CLI      := $(ETL_VENV)/bin/adito-etl

# ------------------------------------------------------------------------------
# Cores e Formatação ANSI para o Terminal
# ------------------------------------------------------------------------------
COLOR_RESET  := \033[0m
COLOR_BOLD   := \033[1m
COLOR_CYAN   := \033[36m
COLOR_GREEN  := \033[32m
COLOR_YELLOW := \033[33m
COLOR_RED    := \033[31m

.PHONY: help all dev desktop dev-front build-front dev-tauri \
        db etl etl-popular etl-cruzar etl-ver etl-pii etl-extract \
        etl-src-acoes etl-src-participacoes etl-sigpesq etl-cnpq etl-lattes \
        test test-etl test-core test-mcp test-front test-e2e test-e2e-live test-perf test-eval test-tauri \
        chave-dados publicar-dados nucleo instalador \
        setup setup-app setup-etl clean clean-all \
        check-setup check-front check-desktop check-brutos check-etl-env check-etl-env-src check-etl-env-sigpesq

# ------------------------------------------------------------------------------
# 📖 Ajuda & Documentação Interativa
# ------------------------------------------------------------------------------
help: ## Exibe esta mensagem de ajuda com todos os comandos disponíveis
	@echo ""
	@echo -e "$(COLOR_BOLD)$(COLOR_CYAN)Adito — Automação de Desenvolvimento (Makefile)$(COLOR_RESET)"
	@echo -e "Uso: $(COLOR_YELLOW)make [alvo]$(COLOR_RESET)\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(COLOR_GREEN)%-24s$(COLOR_RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# ------------------------------------------------------------------------------
# 🖥️ Aplicação Desktop & Frontend
# ------------------------------------------------------------------------------
all: check-setup check-front check-desktop ## Roda ETL (se brutos/ não existir), prepara banco/fatos e inicia o app desktop (#73, #88)
	@if [ ! -d "$(ETL_DIR)/brutos" ] || [ -z "$$(find "$(ETL_DIR)/brutos" -type f ! -name '.*' 2>/dev/null | head -n 1)" ]; then \
		echo -e "$(COLOR_YELLOW)→ Pasta Adito/etl/brutos/ vazia ou ausente; executando ETL inicial antes de subir o app...$(COLOR_RESET)"; \
		$(MAKE) etl; \
	else \
		echo -e "$(COLOR_CYAN)→ Dados brutos encontrados em Adito/etl/brutos/; pulando extração web e atualizando banco...$(COLOR_RESET)"; \
		$(MAKE) db; \
	fi
	@$(MAKE) desktop

dev: check-setup check-front check-desktop db ## Atalho mestre: verifica setup, reconstrói banco/fatos e sobe o app completo
	@echo -e "$(COLOR_CYAN)→ Iniciando Adito Desktop via script oficial...$(COLOR_RESET)"
	@"$(ROOT_DIR)/rodar_desktop.sh"

desktop: check-setup check-front check-desktop ## Inicia o ambiente desktop via ./rodar_desktop.sh (banco existente)
	@echo -e "$(COLOR_CYAN)→ Subindo Adito Desktop (Vite + Núcleo Python + Janela Tauri)...$(COLOR_RESET)"
	@"$(ROOT_DIR)/rodar_desktop.sh"

dev-front: check-front ## Inicia apenas o servidor de desenvolvimento do frontend (Vite na porta 5173)
	@echo -e "$(COLOR_CYAN)→ Iniciando Frontend Vue em modo desenvolvimento...$(COLOR_RESET)"
	@cd "$(FRONT_DIR)" && npm run dev

build-front: check-front ## Gera o build de produção do frontend Vue
	@echo -e "$(COLOR_CYAN)→ Compilando frontend Vue para produção...$(COLOR_RESET)"
	@cd "$(FRONT_DIR)" && npm run build

dev-tauri: check-desktop ## Roda a casca desktop Tauri diretamente via cargo run
	@echo -e "$(COLOR_CYAN)→ Executando Tauri via Cargo...$(COLOR_RESET)"
	@cd "$(TAURI_DIR)" && { command -v cargo >/dev/null 2>&1 || source "$$HOME/.cargo/env"; } && cargo run

# ------------------------------------------------------------------------------
# 🔄 Banco de Dados & Fatos Analíticas (SQLite)
# ------------------------------------------------------------------------------
db: check-setup check-brutos ## Reconstrói o banco SQLite (dados.db) com tabelas relacionais e 6 Views dinâmicas das fatos
	@echo -e "$(COLOR_CYAN)→ Processando carga e populando banco SQLite nativo (dados.db)...$(COLOR_RESET)"
	@if [ -f "$(ETL_DIR)/trabalho/pessoas.json" ]; then \
		echo -e "  [1/2] Usando trabalho/pessoas.json existente para carga rápida..."; \
	else \
		echo -e "  [1/2] Gerando cruzamento inicial de identidades..."; \
		cd "$(ETL_DIR)" && "$(ETL_CLI)" cruzar; \
	fi
	@echo -e "  [2/2] Inserindo tabelas relacionais e gerando 6 Views de fatos analíticas v2.0..."
	@"$(APP_PYTHON)" "$(SCRIPTS_DIR)/popular_banco.py" --etl "$(ETL_DIR)" --banco "$(APP_DIR)/data/dados.db"
	@mkdir -p "$(DATA_DIR)"
	@cp -f "$(APP_DIR)/data/dados.db" "$(DATA_DIR)/dados.db"
	@echo -e "$(COLOR_GREEN)✓ Banco dados.db (SQLite) e views analíticas prontos com sucesso!$(COLOR_RESET)"

etl: check-etl-env etl-extract etl-cruzar db ## Ciclo completo de ETL: extração externa, cruzamento e carga no SQLite

etl-popular: db ## Alias para 'make db'

etl-ver: check-setup ## Abre o explorador de dados acadêmicos no terminal (ou passe ARGS="tabela")
	@"$(APP_PYTHON)" "$(SCRIPTS_DIR)/ver_dados.py" $(ARGS)

etl-cruzar: check-setup ## Executa o cruzamento de pessoas por nome normalizado (US-ETL-06)
	@echo -e "$(COLOR_CYAN)→ Executando cruzamento de identidades por nome...$(COLOR_RESET)"
	@cd "$(ETL_DIR)" && "$(ETL_CLI)" cruzar

etl-pii: check-setup ## Realiza varredura de privacidade (Anti-PII) nos dados brutos e trabalho
	@echo -e "$(COLOR_CYAN)→ Verificando integridade e proteção de dados pessoais (PII)...$(COLOR_RESET)"
	@cd "$(ETL_DIR)" && "$(ETL_CLI)" verificar-pii

etl-extract: check-setup check-etl-env etl-src-acoes etl-src-participacoes etl-sigpesq etl-cnpq etl-lattes ## Executa a extração completa de todas as fontes externas na web
	@echo -e "$(COLOR_GREEN)✓ Extração completa das fontes concluída.$(COLOR_RESET)"

etl-src-acoes: check-setup ## Extrai ações públicas do SRC (Campus Serra)
	@cd "$(ETL_DIR)" && "$(ETL_CLI)" src-acoes --campus Serra

etl-src-participacoes: check-setup check-etl-env-src ## Extrai participações e equipes do SRC (área autenticada)
	@cd "$(ETL_DIR)" && "$(ETL_CLI)" src-participacoes

etl-sigpesq: check-setup check-etl-env-sigpesq ## Extrai projetos e grupos do SigPesq
	@cd "$(ETL_DIR)" && "$(ETL_CLI)" sigpesq

etl-cnpq: check-setup ## Extrai dados de espelho de grupos no CNPq/DGP
	@cd "$(ETL_DIR)" && "$(ETL_CLI)" cnpq --unidade Serra

etl-lattes: check-setup ## Extrai currículos Lattes da lista de pesquisadores (gera entradas/lattes.csv se ausente)
	@if [ ! -f "$(ETL_DIR)/entradas/lattes.csv" ]; then \
		"$(ETL_PYTHON)" "$(SCRIPTS_DIR)/gerar_lista_lattes.py" --saida "$(ETL_DIR)/entradas/lattes.csv"; \
	fi
	@cd "$(ETL_DIR)" && "$(ETL_CLI)" lattes

# ------------------------------------------------------------------------------
# 🧪 Testes Automatizados
# ------------------------------------------------------------------------------
test: test-etl test-core test-mcp test-front ## Executa sequencialmente as suítes rápidas/offline (ETL, núcleo, MCP e frontend unit)
	@echo -e "\n$(COLOR_BOLD)$(COLOR_GREEN)✓ Todas as suítes de testes foram executadas com sucesso!$(COLOR_RESET)\n"

test-etl: check-setup ## Executa os testes automatizados do ETL (pytest)
	@echo -e "$(COLOR_CYAN)→ Executando testes do ETL (Adito/etl/tests)...$(COLOR_RESET)"
	@cd "$(ETL_DIR)" && "$(ETL_PYTHON)" -m pytest tests

test-core: check-setup ## Executa os testes unitários do núcleo Python (datastore, authorizer e regressão)
	@echo -e "$(COLOR_CYAN)→ Executando testes unitários do núcleo Python...$(COLOR_RESET)"
	@cd "$(APP_DIR)/backend/nucleo" && "$(APP_PYTHON)" -m unittest core.tests core.test_datastore_sqlite

test-mcp: check-setup ## Executa os testes de contrato e integração STDIO/MCP
	@echo -e "$(COLOR_CYAN)→ Executando testes de STDIO e Contrato RPC...$(COLOR_RESET)"
	@cd "$(APP_DIR)" && "$(APP_PYTHON)" scripts/teste_stdio.py
	@cd "$(APP_DIR)" && "$(APP_PYTHON)" scripts/teste_contrato.py

test-front: check-front ## Executa os testes unitários do frontend Vue (Vitest)
	@echo -e "$(COLOR_CYAN)→ Executando testes unitários do frontend Vue (Vitest)...$(COLOR_RESET)"
	@cd "$(FRONT_DIR)" && npm run test:unit

test-e2e: check-front ## Executa testes E2E do frontend em Chromium via Playwright (modo determinístico/mock IPC)
	@echo -e "$(COLOR_CYAN)→ Executando testes E2E do frontend (Playwright mock)...$(COLOR_RESET)"
	@cd "$(FRONT_DIR)" && npm run test:e2e

test-e2e-live: check-setup check-front ## Executa testes E2E integrados (Playwright + bridge local + núcleo Python real sobre dados.db)
	@echo -e "$(COLOR_CYAN)→ Executando testes E2E integrados com núcleo Python real (dados.db)...$(COLOR_RESET)"
	@set -e; \
	"$(APP_PYTHON)" "$(APP_DIR)/scripts/e2e_bridge.py" --port 18765 & \
	BRIDGE_PID=$$!; \
	trap 'kill $$BRIDGE_PID 2>/dev/null || true; wait $$BRIDGE_PID 2>/dev/null || true' EXIT; \
	for i in $$(seq 1 40); do \
		if curl -sf http://127.0.0.1:18765/health >/dev/null 2>&1; then break; fi; \
		sleep 0.2; \
	done; \
	cd "$(FRONT_DIR)" && E2E_BRIDGE_URL=http://127.0.0.1:18765 npm run test:e2e:live

test-perf: check-setup ## Executa o benchmark de performance/latência do núcleo local sobre dados.db
	@echo -e "$(COLOR_CYAN)→ Executando benchmark de performance do núcleo local...$(COLOR_RESET)"
	@cd "$(APP_DIR)" && "$(APP_PYTHON)" scripts/bench_backend.py $(ARGS)

test-eval: check-setup ## Executa avaliação híbrida de acurácia da IA (SQL gabarito + LLM Judge — requer GEMINI_API_KEY)
	@echo -e "$(COLOR_CYAN)→ Executando avaliação híbrida de acurácia da IA...$(COLOR_RESET)"
	@cd "$(APP_DIR)" && "$(APP_PYTHON)" scripts/eval_acuracia.py $(ARGS)

test-tauri: check-desktop ## Executa os testes unitários em Rust da casca Tauri
	@echo -e "$(COLOR_CYAN)→ Executando testes do Tauri (Rust)...$(COLOR_RESET)"
	@cd "$(TAURI_DIR)" && { command -v cargo >/dev/null 2>&1 || source "$$HOME/.cargo/env"; } && cargo test

# ------------------------------------------------------------------------------
# 📦 Distribuição (ADR-0006/0007)
# ------------------------------------------------------------------------------
nucleo: check-desktop ## Empacota o núcleo Python (adito-backend) com PyInstaller para ir no instalador
	@[ -x "$(APP_PYTHON)" ] || { echo -e "$(COLOR_RED)❌ Falta o .venv do app: rode 'make setup-app'.$(COLOR_RESET)"; exit 1; }
	@echo -e "$(COLOR_CYAN)→ Empacotando o núcleo Python (PyInstaller)...$(COLOR_RESET)"
	@"$(APP_PYTHON)" -m pip install -q "pyinstaller>=6.16,<7"
	@cd "$(APP_DIR)" && { command -v rustc >/dev/null 2>&1 || source "$$HOME/.cargo/env"; } && "$(APP_PYTHON)" scripts/empacotar_nucleo.py

instalador: nucleo check-front ## Gera os instaladores Linux (.deb e .AppImage) com o núcleo embutido
	@echo -e "$(COLOR_CYAN)→ Gerando os instaladores (Tauri)...$(COLOR_RESET)"
	@cd "$(FRONT_DIR)" && npm run build
	@cd "$(TAURI_DIR)" && { command -v cargo >/dev/null 2>&1 || source "$$HOME/.cargo/env"; } && \
		"$(FRONT_DIR)/node_modules/.bin/tauri" build --bundles deb,appimage --config '{"bundle":{"externalBin":["binaries/adito-backend"]}}'
	@echo -e "$(COLOR_GREEN)✓ Instaladores em $(TAURI_DIR)/target/release/bundle/$(COLOR_RESET)"

chave-dados: check-desktop ## Gera uma chave institucional nova para trancar o dados.db (guarde num cofre)
	@cd "$(TAURI_DIR)" && { command -v cargo >/dev/null 2>&1 || source "$$HOME/.cargo/env"; } && cargo run --quiet --example empacotar_dados -- gerar-chave

publicar-dados: check-desktop ## Tranca e publica o dados.db no GitHub Releases (requer ADITO_DADOS_CHAVE e gh)
	@{ command -v cargo >/dev/null 2>&1 || source "$$HOME/.cargo/env"; } && "$(SCRIPTS_DIR)/publicar_dados.sh" $(ARGS)

# ------------------------------------------------------------------------------
# ⚙️ Instalação, Setup & Verificações
# ------------------------------------------------------------------------------
check-setup:
	@if [ ! -d "$(APP_VENV)" ] || [ ! -x "$(APP_PYTHON)" ]; then \
		echo -e "$(COLOR_RED)❌ Erro: Ambiente virtual do app não encontrado em:$(COLOR_RESET)"; \
		echo -e "   $(APP_VENV)"; \
		echo -e "Execute '$(COLOR_BOLD)make setup$(COLOR_RESET)' primeiro para configurar os ambientes.\n"; \
		exit 1; \
	fi
	@if [ ! -d "$(ETL_VENV)" ] || [ ! -x "$(ETL_PYTHON)" ]; then \
		echo -e "$(COLOR_RED)❌ Erro: Ambiente virtual do ETL não encontrado em:$(COLOR_RESET)"; \
		echo -e "   $(ETL_VENV)"; \
		echo -e "Execute '$(COLOR_BOLD)make setup$(COLOR_RESET)' primeiro para configurar os ambientes.\n"; \
		exit 1; \
	fi

check-front:
	@if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then \
		echo -e "$(COLOR_RED)❌ Erro: Node.js/npm não encontrado no PATH.$(COLOR_RESET)"; \
		echo -e "Instale Node.js (LTS) e tente novamente.\n"; \
		exit 1; \
	fi
	@if [ ! -d "$(FRONT_DIR)/node_modules" ]; then \
		echo -e "$(COLOR_RED)❌ Erro: Dependências do frontend não encontradas em:$(COLOR_RESET)"; \
		echo -e "   $(FRONT_DIR)/node_modules"; \
		echo -e "Execute '$(COLOR_BOLD)make setup-app$(COLOR_RESET)' (ou 'cd Adito/app/frontend-vue && npm install') primeiro.\n"; \
		exit 1; \
	fi

check-desktop:
	@if ! command -v cargo >/dev/null 2>&1 && ! { [ -f "$$HOME/.cargo/env" ] && ( . "$$HOME/.cargo/env" && command -v cargo >/dev/null 2>&1 ); }; then \
		echo -e "$(COLOR_RED)❌ Erro: O compilador Rust (cargo) não foi encontrado no sistema.$(COLOR_RESET)"; \
		echo -e "Instale o Rust executando:"; \
		echo -e "  $(COLOR_BOLD)curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh$(COLOR_RESET)\n"; \
		exit 1; \
	fi

# popular_banco.py lê obrigatoriamente brutos/{src,sigpesq,lattes,cnpq} além de trabalho/pessoas.json;
# ignoramos arquivos ocultos (ex.: .gitkeep) para não tratar pasta vazia como populada.
check-brutos:
	@if [ ! -d "$(ETL_DIR)/brutos" ] || [ -z "$$(find "$(ETL_DIR)/brutos" -type f ! -name '.*' 2>/dev/null | head -n 1)" ]; then \
		echo -e "$(COLOR_RED)❌ Erro: Dados brutos do ETL não encontrados em:$(COLOR_RESET)"; \
		echo -e "   $(ETL_DIR)/brutos"; \
		echo -e "Execute '$(COLOR_BOLD)make etl$(COLOR_RESET)' ou '$(COLOR_BOLD)make all$(COLOR_RESET)' primeiro para extrair os dados.\n"; \
		exit 1; \
	fi

check-etl-env: check-setup
	@"$(ETL_PYTHON)" "$(SCRIPTS_DIR)/validar_etl_env.py" --env-file "$(ETL_DIR)/.env" --escopo all

check-etl-env-src: check-setup
	@"$(ETL_PYTHON)" "$(SCRIPTS_DIR)/validar_etl_env.py" --env-file "$(ETL_DIR)/.env" --escopo src

check-etl-env-sigpesq: check-setup
	@"$(ETL_PYTHON)" "$(SCRIPTS_DIR)/validar_etl_env.py" --env-file "$(ETL_DIR)/.env" --escopo sigpesq

setup: setup-app setup-etl ## Configura todos os ambientes (Python venvs, dependências e npm)
	@echo -e "\n$(COLOR_BOLD)$(COLOR_GREEN)✓ Setup completo do Adito concluído!$(COLOR_RESET)\n"

setup-app: ## Cria virtualenv do app, instala requirements e dependências do frontend
	@echo -e "$(COLOR_CYAN)→ Configurando ambiente do App (Python + Node.js)...$(COLOR_RESET)"
	@test -d "$(APP_VENV)" || python3 -m venv "$(APP_VENV)"
	@"$(APP_VENV)/bin/pip" install --upgrade pip
	@"$(APP_VENV)/bin/pip" install -r "$(APP_DIR)/backend/requirements.txt"
	@cd "$(FRONT_DIR)" && npm install

setup-etl: ## Cria virtualenv do ETL e instala o pacote adito_etl com extras de desenvolvimento
	@echo -e "$(COLOR_CYAN)→ Configurando ambiente do ETL...$(COLOR_RESET)"
	@test -d "$(ETL_VENV)" || python3 -m venv "$(ETL_VENV)"
	@"$(ETL_VENV)/bin/pip" install --upgrade pip
	@"$(ETL_VENV)/bin/pip" install -e "$(ETL_DIR)[sigpesq,cnpq,lattes,infisical,dev]" "playwright==1.64.0"
	@if [ ! -f "$(ETL_DIR)/.env" ]; then \
		cp "$(ETL_DIR)/.env.example" "$(ETL_DIR)/.env"; \
		echo -e "\n$(COLOR_YELLOW)⚠️  Arquivo $(ETL_DIR)/.env criado a partir do modelo.$(COLOR_RESET)"; \
		echo -e "$(COLOR_YELLOW)   Preencha as credenciais (ADITO_CREDENCIAIS=infisical ou env) antes de executar 'make etl' ou 'make all'.$(COLOR_RESET)\n"; \
	fi

# ------------------------------------------------------------------------------
# 🧹 Limpeza
# ------------------------------------------------------------------------------
clean: ## Remove arquivos temporários de logs do Adito, caches do Python e pytest
	@echo -e "$(COLOR_CYAN)→ Limpando caches e arquivos temporários...$(COLOR_RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -f /tmp/adito*.log /tmp/oraculo-vite.log
	@echo -e "$(COLOR_GREEN)✓ Limpeza concluída.$(COLOR_RESET)"

clean-all: clean ## Limpa também builds gerados pelo frontend e Tauri
	@echo -e "$(COLOR_CYAN)→ Limpando diretórios de build (dist, target)...$(COLOR_RESET)"
	@rm -rf "$(FRONT_DIR)/dist" "$(TAURI_DIR)/target"
	@echo -e "$(COLOR_GREEN)✓ Build limpo.$(COLOR_RESET)"
