# Requirements — Correção de Onboarding, Setup e Execução Local (`Makefile` e `rodar_desktop.sh` — Issues #83, #84, #87 e #88)

**Status:** REQUIREMENTS_READY
**Discovery de origem:** `Muninn/docs/discovery/correcao-onboarding-makefile-desktop.md`
**Classificacao de Processo:** NORMAL PROCESS

## Intent Summary
Garantir que qualquer desenvolvedor ou revisor consiga configurar, extrair dados e iniciar o Muninn Desktop em ambientes limpos (Linux Wayland/VS Code Snap, WSL e macOS) com pré-validações claras, fluxo condicional inteligente em `make all`, geração automática e segura de `entradas/lattes.csv` e testes automatizados offline cobrindo os 4 bugs (#83, #84, #87 e #88).

## Functional Requirements
- **FR01 (#83 — Geração de `entradas/lattes.csv`):** Fornecer o script `Muninn/scripts/gerar_lista_lattes.py` capaz de extrair o dicionário `ROSTER_IDS` de `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py` (sem importar código legado) e gravar `Muninn/etl/entradas/lattes.csv` no formato CSV `nome,lattes_id` (UTF-8 com cabeçalho).
- **FR02 (#83 — Integração no `Makefile`):** Tornar `Muninn/etl/entradas/lattes.csv` pré-requisito do alvo `etl-lattes` no `Makefile`, executando `gerar_lista_lattes.py` automaticamente quando o arquivo ainda não existir.
- **FR03 (#84 — Guarda de Rust/cargo em `rodar_desktop.sh`):** Verificar `command -v cargo`; se ausente, checar `[ -f "$HOME/.cargo/env" ]` antes de executar `source` e revalidar `command -v cargo`. Se continuar indisponível, interromper com exit code != 0 e mensagem amigável exibindo o comando de instalação via `rustup` (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`).
- **FR04 (#84 — Checagens modulares de pré-requisitos no `Makefile`):**
  - Manter `check-setup` focado nos ambientes virtuais Python (`APP_VENV` e `ETL_VENV`);
  - Expandir `check-front` para validar `node` e `npm` no `PATH`, além da pasta `Muninn/app/frontend-vue/node_modules`;
  - Criar alvo `check-desktop` (ou `check-cargo`) validando `cargo` (no `PATH` ou em `~/.cargo/env`) e associá-lo apenas aos alvos que exigem Tauri/Rust (`all`, `dev`, `desktop`, `dev-tauri`, `test-tauri`), além de `check-front` em `dev` e `desktop`.
- **FR05 (#87 — Sanitização de ambiente Snap e compatibilidade Wayland em `rodar_desktop.sh`):**
  - Antes do `cargo run`, remover (`unset`) variáveis de ambiente injetadas por Snap (`GTK_PATH`, `GIO_MODULE_DIR`, `GSETTINGS_SCHEMA_DIR`, `LD_LIBRARY_PATH`, `GTK_EXE_PREFIX`, `GTK_IM_MODULE_FILE`) quando seus valores contiverem `/snap/`;
  - No bloco condicional de Wayland (`[ "${XDG_SESSION_TYPE:-}" = "wayland" ]`), exportar `GDK_BACKEND="${GDK_BACKEND:-x11}"` junto a `WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"`.
- **FR06 (#88 — Fluxo condicional em `make all` e guarda em `make db` / `make dev`):**
  - `make all` verifica se `Muninn/etl/brutos/` existe e contém arquivos de dados; se vazio/inexistente, executa `etl` → `db` → `desktop`; se já populado, pula o scraping e executa `db` → `desktop`;
  - `make db` e `make dev` falham rápido com mensagem amigável orientando rodar `make etl` ou `make all` quando `Muninn/etl/brutos/` não existir ou estiver vazio.
- **FR07 (#88 — Aviso de credenciais no `make setup-etl`):** Quando `setup-etl` criar `Muninn/etl/.env` pela primeira vez a partir de `.env.example`, exibir aviso destacado no terminal informando que as credenciais precisam ser preenchidas antes de executar o ETL (sem sobrescrever `.env` já existente).
- **FR08 (#88 — Pré-validação granular `check-etl-env`):** Validar `Muninn/etl/.env` antes dos alvos autenticados do ETL (`etl`, `etl-extract`, `etl-src-participacoes`, `etl-sigpesq`), checando o modo `MUNINN_CREDENCIAIS`:
  - `infisical`: exige `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET` e `INFISICAL_PROJECT_ID` preenchidos;
  - `env`: `etl-src-participacoes` exige `SRC_USER` e `SRC_PASSWORD`; `etl-sigpesq` exige `SIGPESQ_USER` e `SIGPESQ_PASSWORD`; `etl` e `etl-extract` exigem ambos (SRC + SigPesq);
  - ausente ou valor inválido: falha rápido listando os dois modos aceitos (`infisical` ou `env`).
- **FR09 (Testes automatizados offline):** Fornecer testes automatizados 100% offline cobrindo `gerar_lista_lattes.py`, guardas de `rodar_desktop.sh` e alvos/guardas do `Makefile` em ambientes temporários isolados, integrados à validação do projeto.

## Business / Domain Rules
- **BR01 (Respeito a arquivos do usuário):** Nunca sobrescrever um `Muninn/etl/entradas/lattes.csv` nem um `Muninn/etl/.env` já existentes.
- **BR02 (Anti-PII e proteção de segredos):** `Muninn/etl/entradas/lattes.csv` e `Muninn/etl/.env` devem continuar fora do controle de versão (`.gitignore`); nenhum script ou alvo do `Makefile` pode imprimir valores de senhas, client secrets ou tokens no terminal.
- **BR03 (Separação entre alvos públicos e autenticados):** Alvos públicos do ETL (`etl-src-acoes`, `etl-cnpq`, `etl-lattes`) nunca devem exigir credenciais de login em `Muninn/etl/.env`.
- **BR04 (Isolamento de pré-requisitos Python-only):** Alvos exclusivamente Python (`test-etl`, `test-core`, `test-mcp`, `etl-*`, `db`) não devem falhar pela ausência de `cargo` (Rust) ou `node`/`npm`.
- **BR05 (Override explícito do usuário no desktop):** Se o usuário exportar manualmente `GDK_BACKEND` ou `WEBKIT_DISABLE_DMABUF_RENDERER` antes de chamar `rodar_desktop.sh`, o script deve respeitar o valor informado.
- **BR06 (Não disparar scraping escondido em `make db` / `make dev`):** Apenas `make all` (em ambiente sem `brutos/`) e `make etl*` disparam extração web; `make db` e `make dev` devem apenas orientar o usuário quando `brutos/` estiver ausente.

## Non-Functional Requirements
- **NFR01 (Zero novas dependências externas):** Utilizar exclusivamente `bash`, GNU `make` e biblioteca padrão Python (`stdlib`, como `ast`, `csv`, `pathlib`, `unittest`).
- **NFR02 (Portabilidade):** Compatível com Linux (Ubuntu/Debian, incluindo GNOME Wayland e VS Code Snap), WSL (incluindo arquivos `.env` com terminação CRLF) e macOS (`bash`).
- **NFR03 (Segurança no parsing do `.env`):** O validador de `.env` não pode executar `source`/shell sobre o arquivo (evitando execução arbitrária de comandos); deve interpretar pares `CHAVE=VALOR` ignorando comentários, linhas vazias, aspas e `\r`.
- **NFR04 (Mensagens acionáveis e falha rápida):** Toda pré-validação deve falhar em < 1 segundo com exit code != 0 e instrução clara do comando ou arquivo a ajustar.
- **NFR05 (Não regressão):** Todas as suítes existentes (`make test`, `make build-front`, `make test-e2e`, `make test-e2e-live`, `make test-perf`) devem permanecer 100% verdes após as alterações.

## User Scenarios

### Main flow
1. Desenvolvedor clona o repositório limpo e executa `make setup`. O `setup-etl` cria `Muninn/etl/.env` a partir de `.env.example` e exibe aviso claro para preencher as credenciais.
2. Desenvolvedor executa `make etl-lattes` sem ter criado `entradas/lattes.csv`: o `Makefile` gera automaticamente `Muninn/etl/entradas/lattes.csv` via `gerar_lista_lattes.py` (sem exigir `.env`) e inicia o extrator.
3. Desenvolvedor preenche `Muninn/etl/.env` e executa `make all`: como `Muninn/etl/brutos/` ainda não existe, o `Makefile` valida o `.env` (`check-etl-env`), executa `etl`, constrói `dados.db` (`db`) e abre o app desktop (`rodar_desktop.sh`).
4. Na segunda execução de `make all`, como `Muninn/etl/brutos/` já contém dados, o `Makefile` pula o scraping e vai direto para `db` → `desktop`.
5. No terminal integrado do VS Code Snap em Ubuntu GNOME Wayland, `rodar_desktop.sh` higieniza variáveis `/snap/`, define `GDK_BACKEND=x11` e `WEBKIT_DISABLE_DMABUF_RENDERER=1`, encontra `cargo` e abre a janela Tauri sem erro 134.

### Alternative / Error / Edge cases
- **CSV customizado existente (#83):** `Muninn/etl/entradas/lattes.csv` já existe com 5 docentes; `make etl-lattes` não chama sobrescrita e preserva o arquivo intacto.
- **Fonte legada ausente (#83):** `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py` não existe e `entradas/lattes.csv` está ausente; `gerar_lista_lattes.py` falha com erro claro indicando caminho e formato `nome,lattes_id`.
- **Sem Rust instalado (#84):** `cargo` ausente no `PATH` e `~/.cargo/env` inexistente; `rodar_desktop.sh` e `make dev` exibem comando oficial do `rustup` e encerram com exit code 1, sem erro de `source` em arquivo inexistente.
- **Rust instalado apenas em `~/.cargo/env` (#84):** `cargo` fora do `PATH` inicial, mas `~/.cargo/env` presente; `rodar_desktop.sh` carrega `~/.cargo/env` e prossegue normalmente.
- **`LD_LIBRARY_PATH` customizado sem `/snap/` (#87):** usuário possui `LD_LIBRARY_PATH=/opt/custom/lib`; `rodar_desktop.sh` preserva a variável intacta.
- **Override manual de `GDK_BACKEND=wayland` (#87):** usuário roda `GDK_BACKEND=wayland ./rodar_desktop.sh`; script respeita o valor `wayland`.
- **`.env` com `MUNINN_CREDENCIAIS=env` preenchido só para SRC (#88):** `make etl-src-participacoes` passa na validação; `make etl-sigpesq` e `make etl` falham informando que faltam `SIGPESQ_USER`/`SIGPESQ_PASSWORD`.
- **`.env` ausente, com CRLF ou modo inválido (#88):** `check-etl-env` falha com mensagem clara indicando o problema sem exibir segredos.
- **`make db` ou `make dev` em clone limpo (#88):** `Muninn/etl/brutos/` ausente ou vazio; interrompe antes de chamar `muninn-etl cruzar` orientando rodar `make etl` ou `make all`.

## Business / Domain Context
- O projeto Muninn consolida 4 bases acadêmicas do IFES (SRC, SigPesq, Lattes e CNPq DGP) em SQLite (`dados.db`) e executa localmente via Tauri (Rust) + Vue 3 + núcleo Python.
- As 4 issues (#83, #84, #87 e #88) foram reportadas por integrantes do time ao configurar o projeto em máquinas Linux/Ubuntu limpas (incluindo GNOME Wayland e VS Code Snap).

## Technical Context & Constraints
- **Arquivos impactados previstos:**
  - `Makefile` (raiz)
  - `rodar_desktop.sh` (raiz)
  - `Muninn/scripts/gerar_lista_lattes.py` (novo script auxiliar, stdlib)
  - `Muninn/scripts/validar_etl_env.py` *(ou função inline/script auxiliar stdlib para validar `Muninn/etl/.env` com segurança contra CRLF/comentários/injeção)*
  - Testes automatizados offline (ex.: `Muninn/etl/tests/` ou `Muninn/app/backend/nucleo/core/tests.py` / novo módulo de teste de scripts/onboarding)
- **Integração com `Makefile` existente:** preservar todos os alvos atuais (`make help`, `make test`, `make test-e2e`, `make test-e2e-live`, `make test-perf`, `make test-eval`, `make db`, etc.).

## Quality Attributes
- **Testability:** Toda lógica de guarda e geração deve ser testável offline via ambientes temporários (`tempfile`), PATH simulado e variáveis de ambiente injetadas.
- **Security:** Parsing seguro do `.env` sem `source`, sem impressão de valores sensíveis e sem versionar PII (`lattes.csv`).
- **Maintainability:** Commits atômicos separados por issue (#83, #84, #87 e #88) e responsabilidades claras entre `Makefile`, `rodar_desktop.sh` e scripts auxiliares Python.

## Assumptions
- **A01:** `gerar_lista_lattes.py` lê `ROSTER_IDS` via `ast.parse` de `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py`, sem executar o módulo legado.
- **A02:** Um diretório `Muninn/etl/brutos/` é considerado populado se existir e possuir ao menos um arquivo regular em sua árvore (ignorando pasta completamente vazia).
- **A03:** Para validar `Muninn/etl/.env` de forma robusta (comentários, espaços, aspas, CRLF, sem risco de shell injection), usar um pequeno script auxiliar Python stdlib (ou bloco `$(ETL_PYTHON) -c ...`) chamado pelo `Makefile`.
- **A04:** A sanitização de Snap em `rodar_desktop.sh` atua sobre `GTK_PATH`, `GIO_MODULE_DIR`, `GSETTINGS_SCHEMA_DIR`, `LD_LIBRARY_PATH`, `GTK_EXE_PREFIX` e `GTK_IM_MODULE_FILE` sempre que o valor contiver `/snap/`.

## Out of Scope
- Refatoração dos extratores internos do `muninn-etl`.
- Instalação automatizada de Rust/Node/browsers pelo `Makefile`.
- Alterações no frontend Vue (`Muninn/app/frontend-vue/src/`) ou nos agentes IA (`Muninn/app/backend/`).

## Open Questions
- Nenhuma pergunta bloqueante aberta.

## Key Decisions Proposed
1. **Parsing seguro do `.env` sem `source`:** validar `Muninn/etl/.env` usando Python stdlib (`check-etl-env`) em vez de `source` em bash, eliminando risco de execução arbitrária e tratando CRLF/aspas/comentários de forma determinística.
2. **Checagens modulares no `Makefile`:** separar `check-setup` (Python venvs), `check-front` (`node`/`npm` + `node_modules`) e `check-desktop` (`cargo` / `~/.cargo/env`) para não quebrar fluxos Python-only em máquinas sem Rust.
3. **Extração segura de `ROSTER_IDS` via `ast`:** `gerar_lista_lattes.py` não importa nem executa o script legado de `Etls/Horizon/`, apenas lê o literal `ROSTER_IDS` via AST e fornece fallback claro se ausente.
4. **Sanitização seletiva de variáveis `/snap/` + `GDK_BACKEND=x11` em Wayland:** limpa somente variáveis contaminadas por `/snap/` (preservando variáveis customizadas legítimas) e aplica `GDK_BACKEND="${GDK_BACKEND:-x11}"` respeitando override do usuário.

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- Aprovado sem alteracoes pelo usuario no Checkpoint R1.

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
