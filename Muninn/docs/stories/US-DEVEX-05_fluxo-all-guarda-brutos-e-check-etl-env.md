# User Story: [US-DEVEX-05] Fluxo Condicional em `make all`, Guarda de `brutos/`, Aviso de `.env` e `check-etl-env` Granular

**Epic:** EPIC-09 — Produtividade de Desenvolvimento & Automação Local (DevEx)  
**GitHub Epic Issue:** [#88](https://github.com/SmartIdea-ifes-serra/Adito/issues/88)  
**GitHub US Issue:** [#88](https://github.com/SmartIdea-ifes-serra/Adito/issues/88)  
**Prioridade:** Alta (Slice 2)  
**Story Points:** 3  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** YES (`make all` condicional a `brutos/`, guarda em `db`/`dev`, aviso no `setup-etl` e validação granular `check-etl-env`)

---

## Historia

**Como** desenvolvedor executando `make setup`, `make etl*`, `make db`, `make dev` ou `make all` em um ambiente limpo,  
**Eu quero** ser avisado sobre o preenchimento do `Muninn/etl/.env`, ter validação antecipada das credenciais nos alvos autenticados e contar com fluxo condicional inteligente em `make all` (e guarda em `make db`/`dev`) para `Muninn/etl/brutos/`,  
**Para que** o projeto não falhe silenciosamente ou no meio da execução Python nem rode scraping web desnecessariamente quando os dados locais já existem.

### Contexto Adicional
Hoje `make all` é apenas alias para `dev` (`check-setup → db → rodar_desktop.sh`), quebrando ou gerando banco incompleto quando `Muninn/etl/brutos/` não existe. Além disso, `setup-etl` cria `Muninn/etl/.env` a partir de `.env.example` com credenciais vazias sem emitir nenhum aviso, e os alvos autenticados (`etl`, `etl-extract`, `etl-src-participacoes`, `etl-sigpesq`) não validam credenciais previamente.

### Pontos de Esclarecimento
Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **CA01 (`make all` condicional a `Muninn/etl/brutos/`):** Verificar se `Muninn/etl/brutos/` existe e contém ao menos um arquivo regular. Se não existir ou estiver vazio, executar `etl → db → desktop`; se já estiver populado, pular o scraping e ir direto para `db → desktop`.
- [x] **CA02 (Guarda explícita em `make db` e `make dev`):** Se `Muninn/etl/brutos/` não existir ou estiver vazio, `make db` (e consequentemente `make dev`) falha rápido antes de chamar `muninn-etl cruzar` ou `popular_banco.py`, orientando rodar `make etl` ou `make all` (`BR06`).
- [x] **CA03 (Aviso em destaque no `make setup-etl`):** Quando `Muninn/etl/.env` não existir, copiar `.env.example` e exibir aviso destacado informando que as credenciais precisam ser preenchidas antes de rodar o ETL. Se `.env` já existir, preservar sem sobrescrever (`BR01`).
- [x] **CA04 (Validador seguro e granular `check-etl-env`):** Criar `Muninn/scripts/validar_etl_env.py` (Python stdlib, sem `source`, tratando comentários, espaços, aspas e CRLF, sem nunca imprimir valores de segredos) seguindo a **mesma precedência do ETL** (`muninn_etl.comum.config`: primeiro `etl/.env`, depois `os.environ`, funcionando sem `.env` em CI/containers) e aceitando os mesmos aliases (`SIGPESQ_USER`/`SIGPESQ_USERNAME`):
  - `MUNINN_CREDENCIAIS=infisical` exige `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET` e `INFISICAL_PROJECT_ID`;
  - `MUNINN_CREDENCIAIS=env` exige granularmente: `SRC_USER`+`SRC_PASSWORD` para `etl-src-participacoes`, `SIGPESQ_USER` (ou `SIGPESQ_USERNAME`)+`SIGPESQ_PASSWORD` para `etl-sigpesq`, e ambos (SRC + SigPesq) para `etl` e `etl-extract`;
  - ausente tanto no `.env` quanto no ambiente ou `MUNINN_CREDENCIAIS` vazio/inválido falha rápido listando os dois modos aceitos (`infisical` ou `env`).
- [x] **CA05 (Alvos públicos livres de login):** `etl-src-acoes`, `etl-cnpq` e `etl-lattes` continuam funcionando sem exigir `Muninn/etl/.env` preenchido (`BR03`).
- [x] **CA06 (Testes automatizados offline e não regressão):** Testes em ambiente temporário isolado cobrindo todos os cenários do validador `.env` (infisical, env granular, CRLF, aspas, ausência de vazamento de segredo), guarda de `brutos/` vazio em `db`/`dev`, lógica condicional de `all`, aviso no `setup-etl` e alvos públicos livres; além de `make test` 100% verde.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; orquestração local no `Makefile` e script stdlib de validação de ambiente sem alteração de contrato de aplicação.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Sem mudança em API, banco de dados ou UI.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Sem contrato externo compartilhado.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR06`, `FR07`, `FR08`, `FR09`, `BR01`, `BR02`, `BR03`, `BR06`, `NFR01`, `NFR02`, `NFR03`, `NFR04`, `NFR05`, `A02`, `A03`
- **Touch List preliminar:**
  - `Muninn/scripts/validar_etl_env.py` (novo)
  - `Makefile`
  - `Muninn/etl/tests/test_onboarding_makefile.py`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** `Muninn/scripts/validar_etl_env.py` e `Makefile` (`all`, `dev`, `db`, `setup-etl`, `etl`, `etl-extract`, `etl-src-participacoes`, `etl-sigpesq`, novos alvos internos `check-brutos`, `check-etl-env`, `check-etl-env-src`, `check-etl-env-sigpesq`).
- **APIs necessarias:** Nenhuma.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A.
- **Erros observaveis esperados:** Exit code `1` com lista exata de variáveis faltantes (apenas nomes, nunca valores) ou instrução para rodar `make etl`/`make all` quando `brutos/` está vazio.

### Dependencias
- [x] `US-DEVEX-02` e `US-DEVEX-03` concluídas (commits anteriores no `Makefile`).
- [x] Zero novas dependências externas.

### Consideracoes de Performance
- Validação de `.env` e verificação de `brutos/` executam em < 50 ms.

---

## Plano de Testes

### Testes Unitarios / Integracao Local
- [x] `validar_etl_env.py` cobre: `.env` ausente, `MUNINN_CREDENCIAIS` ausente/inválido, `infisical` incompleto/completo, `env` granular (`src`, `sigpesq`, `all`), arquivo com CRLF/aspas/comentários e garantia de que nenhum valor de senha aparece no stdout/stderr.
- [x] `Makefile` em diretório temporário isolado valida: `make db` falha sem `brutos/`; `make all` escolhe fluxo com `etl` quando `brutos/` vazio e pula `etl` quando `brutos/` populado; `make etl-src-acoes`/`etl-cnpq`/`etl-lattes` não exigem `.env`.
- [x] Regressão completa: `make test` verde.
