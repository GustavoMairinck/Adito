# Discovery — Correção de Onboarding, Setup e Execução Local (`Makefile` e `rodar_desktop.sh` — Issues #83, #84, #87 e #88)

**Status:** PROBLEM_READY
**Classificacao de Processo:** NORMAL PROCESS
**Origem:** hibrido (issues #83, #84, #87 e #88 + código atual + alinhamento com usuário)

## Intent
Tornar a primeira configuração e execução local do Muninn (`make setup`, `make etl-*`, `make db`, `make dev`, `make all` e `./rodar_desktop.sh`) previsível, autocontida e resiliente em ambientes limpos (Linux, WSL e macOS), eliminando falhas silenciosas ou mensagens crípticas que hoje bloqueiam novos desenvolvedores e revisores.

## Problem
Quatro falhas de onboarding e validação operacional hoje quebram o fluxo de quem clona o repositório e tenta executar o ETL ou abrir o app desktop:

1. **Ausência de `entradas/lattes.csv` (#83):** `make etl-lattes` falha imediatamente com `FileNotFoundError` em clones limpos porque `Muninn/etl/entradas/` está no `.gitignore` (anti-PII) e o `Makefile` não garante nem orienta a geração prévia do CSV.
2. **Assunção rígida de `~/.cargo/env` e ausência de checagem de pré-requisitos (#84):** `rodar_desktop.sh` falha abruptamente na linha 16 (`source "$HOME/.cargo/env": Arquivo ou diretório inexistente`) quando Rust/cargo não está instalado, e o `Makefile` não valida `cargo` nem `node`/`npm` antes de subir o desktop/frontend.
3. **Conflito de ambiente GTK3/Wayland e VS Code Snap (#87):** `rodar_desktop.sh` aborta com `GLib-GIO-ERROR` (chave `antialiasing` ausente no GNOME Wayland, Error 134) ou conflitos de `glibc`/`libpthread` e schemas GTK/GIO quando disparado a partir do terminal integrado do VS Code instalado via Snap.
4. **Fluxo quebrado em `make all` sem `brutos/` e `.env` silenciosamente vazio (#88):** `make all` é apenas alias de `dev` e assume `Muninn/etl/brutos/` já populado; `make setup-etl` cria `Muninn/etl/.env` com credenciais em branco sem avisar; e alvos autenticados (`etl`, `etl-extract`, `etl-src-participacoes`, `etl-sigpesq`) não validam credenciais previamente, estourando só no meio do Python.

## Users / Stakeholders relevantes
- **Desenvolvedores do time Muninn/Adito:** precisam subir o ambiente local rapidamente em Linux (Ubuntu/Debian com GNOME Wayland, inclusive no terminal do VS Code Snap), WSL e macOS.
- **Revisores de PR / QA:** executam `make test`, `make setup`, `make dev` e `make all` em clones limpos ou worktrees isolados.
- **Responsáveis por privacidade/segurança (anti-PII e segredos):** exigem que `entradas/lattes.csv` continue fora do Git e que segredos do `.env` nunca sejam exibidos no terminal ou sobrescritos.

## Current Situation
- `Makefile`:
  - `etl-lattes` chama `muninn-etl lattes` diretamente sem checar `Muninn/etl/entradas/lattes.csv`.
  - `check-setup` valida apenas `APP_VENV` e `ETL_VENV`; `check-front` valida apenas `node_modules` (sem checar `node`/`npm`); nenhum alvo valida `cargo`.
  - `all` é apenas alias `all: dev`; `db` e `dev` não verificam se `Muninn/etl/brutos/` existe ou contém dados.
  - `setup-etl` copia `.env.example` para `.env` silenciosamente; não existe pré-validação `check-etl-env`.
- `rodar_desktop.sh`:
  - Linha 16 executa `command -v cargo >/dev/null || source "$HOME/.cargo/env"` sob `set -euo pipefail`.
  - Linhas 75–77 só exportam `WEBKIT_DISABLE_DMABUF_RENDERER=1` em Wayland, sem definir `GDK_BACKEND=x11` e sem limpar variáveis de ambiente injetadas pelo Snap (`/snap/`).

## Desired Outcome
Qualquer desenvolvedor em ambiente limpo consegue:
- rodar `make setup` recebendo aviso explícito caso `Muninn/etl/.env` tenha sido recém-criado;
- rodar `make etl-lattes` sem erro de arquivo ausente (gerando `entradas/lattes.csv` automaticamente a partir de `ROSTER_IDS` quando não existir, preservando listas customizadas e orientando claramente se a fonte legada estiver ausente);
- receber diagnósticos imediatos e acionáveis quando faltar `cargo`, `node`/`npm`, `Muninn/etl/brutos/` ou credenciais obrigatórias no `Muninn/etl/.env` (sem bloquear alvos Python-only nem alvos públicos do ETL);
- abrir a janela desktop via `make dev`, `make all` ou `./rodar_desktop.sh` sem crashes no GNOME Wayland nem no terminal integrado do VS Code Snap.

## Success Criteria
- **SC01 (#83):** `make etl-lattes` gera `Muninn/etl/entradas/lattes.csv` automaticamente se ausente (via `Muninn/scripts/gerar_lista_lattes.py`), nunca sobrescreve CSV existente e orienta claramente o formato `nome,lattes_id` se a fonte legada não existir.
- **SC02 (#84):** `rodar_desktop.sh` e os alvos desktop/Tauri do `Makefile` detectam ausência de `cargo` (e `node`/`npm` em `check-front`) com instruções claras de instalação, sem bloquear alvos Python-only (`test-etl`, `test-core`, `test-mcp`, `etl-*`).
- **SC03 (#87):** `rodar_desktop.sh` limpa variáveis poluídas por `/snap/` antes do `cargo run` e define `GDK_BACKEND="${GDK_BACKEND:-x11}"` sob Wayland (respeitando override explícito do usuário).
- **SC04 (#88):** `make all` executa `etl` automaticamente somente quando `Muninn/etl/brutos/` não existir ou estiver vazio; `make db` e `make dev` falham rápido sem `brutos/`; `make setup-etl` destaca aviso ao criar `.env` novo; `check-etl-env` valida credenciais de forma granular por modo (`infisical` vs `env` por alvo) sem bloquear alvos públicos (`etl-src-acoes`, `etl-cnpq`, `etl-lattes`) nem expor segredos.
- **SC05 (Verificação):** Testes automatizados 100% offline cobrem todos os 4 cenários (script Python, guardas de `rodar_desktop.sh` e guardas do `Makefile`) e todas as suítes existentes (`make test`) permanecem verdes.

## Scope

### IN
- Novo script auxiliar `Muninn/scripts/gerar_lista_lattes.py` + integração no alvo `etl-lattes` do `Makefile` (#83).
- Guarda amigável de `cargo` em `rodar_desktop.sh` + validações modulares no `Makefile` (`check-front` com `node`/`npm` + novo `check-desktop`/`check-cargo`) (#84).
- Sanitização de variáveis de ambiente do Snap (`/snap/`) e `GDK_BACKEND="${GDK_BACKEND:-x11}"` sob Wayland em `rodar_desktop.sh` (#87).
- Fluxo condicional em `make all`, guarda de `brutos/` em `make db`/`make dev`, aviso de `.env` em `make setup-etl` e pré-validação granular `check-etl-env` nos alvos autenticados do ETL (#88).
- Testes automatizados offline validando o script Python, `rodar_desktop.sh` e os alvos/guardas do `Makefile`.
- Entrega na branch `fix/makefile-e-rodar-desktop` em 1 PR com 4 commits atômicos (1 por issue).

### OUT
- Alterar a lógica interna de scraping/parsing do `muninn-etl` (SRC, SigPesq, CNPq, Lattes).
- Versionar `Muninn/etl/entradas/lattes.csv` ou credenciais reais no repositório.
- Instalar automaticamente Rust (`rustup`) ou Node.js via `Makefile`/`rodar_desktop.sh`.
- Adicionar novas dependências externas (Python, Node ou binários de sistema).
- Alterar código do frontend Vue ou do núcleo Python (`Muninn/app/backend/`).

### LATER
- Migrar a fonte canônica de IDs Lattes de `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py` para uma fonte desacoplada dentro de `Muninn/` caso o diretório legado `Etls/` venha a ser arquivado.
- Unificar o cliente STDIO compartilhado (`scripts/_nucleo_client.py`) sugerido em review anterior (escopo separado).

## Constraints / Feasibility
- **Zero novas dependências externas:** usar apenas `bash`, GNU `make` e biblioteca padrão Python (`stdlib`).
- **Portabilidade:** manter compatibilidade com Linux (Ubuntu/Debian, incluindo Wayland e VS Code Snap), WSL e macOS (`bash`).
- **Segurança / Privacidade:** `Muninn/etl/entradas/lattes.csv` e `Muninn/etl/.env` permanecem fora do controle de versão; logs e mensagens de erro nunca podem imprimir valores de credenciais/tokens.
- **Não regressão:** preservar integralmente o funcionamento de `make test` (ETL, núcleo, MCP, Vitest), `make test-e2e`, `make test-e2e-live` e `make test-perf`, bem como ambientes onde `cargo` não está instalado para tarefas exclusivamente Python.

## Assumptions
- [ASSUMPTION] `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py` permanece disponível no monorepo atual para extração de `ROSTER_IDS`, mas o script `gerar_lista_lattes.py` não depende de importar pacotes do projeto legado (lê/extrai o mapeamento de forma segura via `ast`, falhando com instrução clara caso o arquivo não exista).
- [ASSUMPTION] Considera-se `Muninn/etl/brutos/` "populado" quando o diretório existe e contém pelo menos um arquivo de dados extraído (não vazio).
- [ASSUMPTION] As variáveis de ambiente injetadas pelo VS Code Snap relevantes para conflitos de glibc/GTK/GIO são `GTK_PATH`, `GIO_MODULE_DIR`, `GSETTINGS_SCHEMA_DIR`, `LD_LIBRARY_PATH`, `GTK_EXE_PREFIX` e `GTK_IM_MODULE_FILE`, e devem ser removidas apenas quando apontarem para `/snap/` (ou quando `$SNAP` estiver ativo e a variável apontar para o sandbox Snap), preservando configurações legítimas do sistema.
- [ASSUMPTION] Em `make all`, quando `Muninn/etl/brutos/` não existir, o alvo invoca a sequência `etl` → `db` → `desktop` (reaproveitando automaticamente `check-etl-env` e `check-desktop`).

## Risks
- **Risco 1 (Acoplamento ao código legado `Etls/Horizon/`):** se o diretório `Etls/` for removido no futuro, a geração automática de `lattes.csv` deixará de funcionar. *Mitigação:* parser isolado sem imports do projeto legado + mensagem de fallback clara com caminho e formato `nome,lattes_id`.
- **Risco 2 (Limpeza excessiva de `LD_LIBRARY_PATH` em sistemas customizados):** remover `LD_LIBRARY_PATH` incondicionalmente poderia afetar bibliotecas locais não-Snap. *Mitigação:* remover/filtrar apenas variáveis cujo valor contenha `/snap/`.
- **Risco 3 (Falsos negativos na validação do `.env`):** arquivos `.env` com comentários, espaços, aspas ou CRLF (WSL/Windows) podem quebrar parsers simples em `grep`/`sed`. *Mitigação:* validar `.env` com rotina robusta (ex.: mini-validador em Python stdlib ou parser shell seguro que trate comentários, espaços, aspas e `\r` sem executar código arbitrário do `.env`).
- **Risco 4 (Bloqueio acidental de ambientes sem Rust):** exigir `cargo` em `check-setup` quebraria fluxos Python-only/CI. *Mitigação:* separar `check-desktop` para os alvos Tauri/desktop e manter `check-setup` focado nos venvs Python.

## Open Questions
- Nenhuma pergunta bloqueante aberta (todas as decisões críticas foram alinhadas previamente na entrevista `/grill-me`).

## Review & Adjust

- [x] Usuario revisou a proposta completa
- [x] Alteracoes solicitadas foram incorporadas
- [x] Decisoes relevantes foram confirmadas
- [x] Nao existem perguntas bloqueantes abertas

### User adjustments
- Aprovado sem alteracoes pelo usuario no Checkpoint D1.

## Gate G0 — PROBLEM READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
