# User Story: [US-DEVEX-03] Guarda de Rust (`cargo`) e Validações Modulares de Pré-Requisitos (`Makefile` + `rodar_desktop.sh`)

**Epic:** EPIC-09 — Produtividade de Desenvolvimento & Automação Local (DevEx)  
**GitHub Epic Issue:** [#84](https://github.com/SmartIdea-ifes-serra/Adito/issues/84)  
**GitHub US Issue:** [#84](https://github.com/SmartIdea-ifes-serra/Adito/issues/84)  
**Prioridade:** Alta (Slice 1)  
**Story Points:** 2  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** YES (diagnóstico amigável quando faltam `cargo` ou `node`/`npm` sem bloquear alvos Python-only)

---

## Historia

**Como** desenvolvedor rodando o Muninn em uma máquina sem Rust ou Node configurados,  
**Eu quero** receber mensagens claras sobre dependências de sistema ausentes (`cargo`, `node`/`npm`) no `rodar_desktop.sh` e no `Makefile`,  
**Para que** eu saiba exatamente como instalar o que falta sem receber erros crípticos de `source ~/.cargo/env` e sem quebrar comandos exclusivamente Python.

### Contexto Adicional
Hoje `rodar_desktop.sh` (L16) executa `command -v cargo >/dev/null || source "$HOME/.cargo/env"` sob `set -euo pipefail`, quebrando abruptamente quando `~/.cargo/env` não existe. No `Makefile`, `check-setup` valida apenas venvs Python e `check-front` valida apenas `node_modules` (sem validar `node`/`npm`), enquanto nenhum alvo valida `cargo` antes de chamar `rodar_desktop.sh`, `cargo run` ou `cargo test`.

### Pontos de Esclarecimento
Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **CA01 (Guarda segura de `cargo` em `rodar_desktop.sh`):** Se `cargo` não estiver no `PATH`, verificar `[ -f "$HOME/.cargo/env" ]` antes de executar `source "$HOME/.cargo/env"` e revalidar `command -v cargo`. Se continuar indisponível, encerrar com exit code != 0 e mensagem clara exibindo `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`.
- [x] **CA02 (`check-front` completo no `Makefile`):** Expandir `check-front` para validar `node` e `npm` disponíveis no `PATH` além de `Muninn/app/frontend-vue/node_modules`, com instruções claras em caso de ausência.
- [x] **CA03 (`check-desktop` modular no `Makefile`):** Criar alvo `check-desktop` validando `cargo` (no `PATH` ou em `~/.cargo/env`) e aplicá-lo apenas aos alvos que dependem de Tauri/Rust (`all`, `dev`, `desktop`, `dev-tauri`, `test-tauri`), além de `check-front` em `dev` e `desktop`.
- [x] **CA04 (Preservação de alvos Python-only):** `check-setup` continua validando apenas `APP_VENV` e `ETL_VENV`, garantindo que `make test-etl`, `make test-core`, `make test-mcp`, `make etl-*` e `make db` não falhem pela ausência de `cargo` ou `node`/`npm` (`BR04`).
- [x] **CA05 (Testes automatizados offline):** Testes cobrindo `bash -n rodar_desktop.sh`, simulação de `PATH` sem `cargo` e sem `~/.cargo/env` (falha amigável com instrução `rustup`), simulação com `~/.cargo/env` presente, e validação de `check-desktop`/`check-front` no `Makefile`.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; validações operacionais em shell/Makefile sem alteração de contrato de aplicação.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Sem mudança em API, dados ou regra de negócio do produto.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Sem endpoint ou schema compartilhado.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR03`, `FR04`, `FR09`, `BR04`, `NFR01`, `NFR02`, `NFR04`, `NFR05`
- **Touch List preliminar:**
  - `rodar_desktop.sh`
  - `Makefile`
  - `Muninn/etl/tests/test_onboarding_makefile.py`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** `rodar_desktop.sh` (L16) e `Makefile` (`check-front`, novo `check-desktop`, `.PHONY`, alvos `dev`, `desktop`, `dev-tauri`, `test-tauri`, `all`).
- **APIs necessarias:** Nenhuma.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A.
- **Erros observaveis esperados:** Exit code `1` com instrução de instalação do `rustup` (quando falta `cargo`) ou Node.js/npm (quando falta `node`/`npm`).

### Dependencias
- [x] Zero novas dependências externas.

### Consideracoes de Performance
- Pré-validações executam em < 50 ms.

---

## Plano de Testes

### Testes Unitarios / Integracao Local
- [x] `bash -n rodar_desktop.sh` sem erros de sintaxe.
- [x] Simulação de `rodar_desktop.sh` com `HOME` temporário sem `.cargo/env` e `PATH` sem `cargo` retorna exit code 1 com mensagem contendo `rustup`.
- [x] `make check-desktop` falha com instrução clara sem `cargo` e passa quando `cargo` existe.
- [x] `make check-front` falha com instrução clara quando falta `node`/`npm` ou `node_modules`.
