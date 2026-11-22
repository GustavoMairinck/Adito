# Task Breakdown: [US-QA-03] Benchmark de Performance e Latência do Núcleo Local (`dados.db`)

**Data:** 19/11/2026  
**Estimativa total:** 3 Story Points  
**Nivel ScrumAIDev:** 1  
**Spec governada:** N/A (dispensa: script local de benchmark sobre o núcleo existente)  
**Contract governado:** N/A  
**Behavior change:** NO  
**GitHub Parent US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)

---

## Pre-Flight de Governanca
- **US exige Spec/Contract?** Não (Nível 1, ferramenta local de medição de desempenho).
- **Novas dependências externas:** Nenhuma (usa stdlib + ambiente Python `.venv` já existente).
- **Touch List:**
  - `Adito/app/scripts/bench_backend.py`
  - `Makefile`

---

## Tasks Tecnicas

### [TASK-QA-03.1] Estrutura do benchmark STDIO e medição de cold-start + RPCs críticas
- Criar `Adito/app/scripts/bench_backend.py` com CLI (`--banco`, `--iterations`, `--concurrency`, `--no-fail`, `--out-dir`).
- Validar existência do `dados.db` com erro amigável instruindo `make db`.
- Preparar `ADITO_DATA_DIR` temporário isolado (symlink/cópia read-only do `dados.db` + contexto `pesquisa-extensao-ifes`) para não afetar o `app.db` do usuário.
- Medir cold-start do `desktop_server.py` até evento `ready`.
- Executar warm-up + N iterações das RPCs críticas (`health`, `me`, `contextos.list`, `dashboard.kpis`, `dashboard.charts`, `dashboard.top_projects`, `explorer.tables`, `explorer.rows` padrão, busca sem acento e ordenação) calculando `min`, `p50`, `p95`, `p99`, `max`.

### [TASK-QA-03.2] Benchmark analítico das 6 views fato e carga concorrente STDIO
- Executar consultas analíticas representativas (`COUNT`/`SUM`/`GROUP BY`) sobre todas as 6 views fato no SQLite via `connect_dados()`.
- Executar rajada concorrente no servidor STDIO/RPC (ex.: 20 requisições simultâneas mistas), medindo tempo total, throughput (`req/s`), taxa de erro e correspondência dos `id`s.

### [TASK-QA-03.3] Validação de SLOs, exportação de relatórios e integração no Makefile
- Validar todas as métricas contra SLOs configuráveis (falhando com código `1` se houver regressão, salvo `--no-fail`).
- Exportar `bench_backend_report.json` e `bench_backend_report.md` (formatado para colar na Issue #71).
- Adicionar `make test-perf` ao `Makefile` raiz (com suporte a `ARGS` e aspas nos caminhos) e validar execução real sobre `Adito/app/data/dados.db`.
