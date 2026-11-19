# User Story: [US-QA-03] Benchmark de Performance e Latência do Núcleo Local (`dados.db`)

**Epic:** EPIC-10 — Garantia de Qualidade: Testes Automatizados, Performance e Avaliação da IA  
**GitHub Epic Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**GitHub US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**Prioridade:** Alta (Slice 1)  
**Story Points:** 3  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** NO (script de benchmark e telemetria local sobre o núcleo existente)

---

## Historia

**Como** engenheiro de software do Muninn,  
**Eu quero** executar um benchmark determinístico e local de performance sobre o núcleo Python e o `dados.db` real,  
**Para que** possamos medir cold-start, percentis de latência (`p50`/`p95`/`p99`), tempo das 6 views fato e concorrência STDIO/RPC contra SLOs claros e anexar evidências objetivas na Issue #71.

### Contexto Adicional
O script `Muninn/app/scripts/teste_stdio.py` hoje valida o protocolo usando um banco sintético minúsculo e apenas imprime uma mediana simples de `explorer.rows` e `me`. Falta uma suíte estruturada de performance executada sobre o `Muninn/app/data/dados.db` real (com milhares de registros e as 6 views analíticas completas), com percentis, carga concorrente, validação de SLOs e geração de relatório pronto em JSON e Markdown.

### Pontos de Esclarecimento
Nenhum ponto pendente (escopo 100% local e sem novas dependências Python aprovado no Gate G1).

---

## Criterios de Aceitacao

- [x] **CA01 (Cold-Start & RPCs Críticas):** `Muninn/app/scripts/bench_backend.py` inicia o processo `desktop_server.py` apontando para o `dados.db` real, mede o tempo de cold-start até o evento `ready` e executa múltiplas iterações (com warm-up) das RPCs `health`, `me`, `contextos.list`, `dashboard.kpis`, `dashboard.charts`, `dashboard.top_projects`, `explorer.tables` e `explorer.rows` (padrão, busca sem acento e ordenação), calculando `min`, `p50`, `p95`, `p99` e `max`.
- [x] **CA02 (Benchmark das 6 Views Fato):** Executa consultas analíticas representativas (agregações `COUNT`/`SUM`/`GROUP BY` e filtros) sobre cada uma das 6 views fato do `dados.db` real via datastore read-only, registrando `p50` e `p95` por view.
- [x] **CA03 (Carga Concorrente STDIO/RPC):** Dispara rajada concorrente de requisições simultâneas no protocolo STDIO/RPC, medindo tempo total, throughput (`req/s`) e validando 0% de erro e correspondência exata dos `id`s de resposta.
- [x] **CA04 (Validação de SLOs & Tratamento de Pré-requisito):** Compara cada métrica contra SLOs configuráveis (retornando exit code != 0 se algum SLO estourar, com flag `--no-fail` para modo informativo). Se `dados.db` não existir, falha imediatamente com mensagem clara instruindo a rodar `make db`.
- [x] **CA05 (Relatórios & Makefile):** Exporta relatório estruturado em JSON e Markdown (pronto para colar na Issue #71) e integra-se ao `Makefile` via `make test-perf` (aceitando `ARGS`), rodando 100% offline e sem novas dependências Python.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; ferramenta de benchmark local sem alteração de comportamento do produto.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Não altera regras de negócio nem contratos.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Consome o protocolo STDIO/RPC já existente.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR04`, `FR05`, `FR06`, `FR11`, `BR04`, `NFR02`, `NFR03`, `NFR04`, `A01`
- **Touch List preliminar:**
  - `Muninn/app/scripts/bench_backend.py`
  - `Makefile`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** Novo script `Muninn/app/scripts/bench_backend.py` (stdlib + `core.datastore`).
- **APIs necessarias:** Protocolo STDIO de `Muninn/app/backend/nucleo/desktop_server.py`.
- **Database changes:** Nenhuma (somente leitura no `dados.db` real; cria `app.db` temporário isolado em `tempfile` para não sujar o ambiente do usuário).
- **Referencias do modelo de dados:** 6 views fato (`vfact_*_resolved`).
- **Erros observaveis esperados:** Erro claro caso `dados.db` não exista; relatório de violação de SLO com exit code `1`.

### Dependencias
- [x] Zero novas dependências Python (usa `stdlib` + ambiente `.venv` existente).

### Consideracoes de Performance
- O script faz warm-up antes de coletar amostras e usa um `MUNINN_DATA_DIR` temporário (copiando ou apontando para o `dados.db` real em modo read-only) para resultados consistentes e sem efeitos colaterais.

---

## Plano de Testes

### Testes Unitarios / Validacao
- [x] Validar cálculo de percentis (`p50`/`p95`/`p99`) e falha esperada quando `dados.db` está ausente.
- [x] Executar `make test-perf` sobre o `dados.db` real e conferir geração do relatório JSON + Markdown e atendimento aos SLOs.
- [x] Validar flag `--no-fail` e passagem de `ARGS` via `make test-perf ARGS="--iterations 5"`.
