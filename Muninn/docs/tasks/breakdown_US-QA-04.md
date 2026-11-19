# Task Breakdown: [US-QA-04] Avaliação Híbrida de Acurácia da IA & Consolidação Issue #71

**Data:** 19/11/2026  
**Estimativa total:** 5 Story Points  
**Nivel ScrumAIDev:** 1  
**Spec governada:** N/A (dispensa: ferramenta de avaliação de qualidade e documentação)  
**Contract governado:** N/A  
**Behavior change:** NO  
**GitHub Parent US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)

---

## Pre-Flight de Governanca
- **US exige Spec/Contract?** Não (Nível 1, ferramental de avaliação e documentação).
- **Novas dependências externas:** Nenhuma (usa `langchain-google-genai`, `pydantic` e `sqlite3` já na `.venv`).
- **Touch List:**
  - `Muninn/app/scripts/eval_dataset.json`
  - `Muninn/app/scripts/eval_acuracia.py`
  - `Muninn/app/backend/nucleo/core/tests.py` (testes unitários para o comparador determinístico do eval, opcional)
  - `Makefile`
  - `README.md`

---

## Tasks Tecnicas

### [TASK-QA-04.1] Construir e validar dataset gabarito independente (`eval_dataset.json`)
- Criar `Muninn/app/scripts/eval_dataset.json` com 24 casos balanceados e independentes de `examples.json` (zero data leakage, zero PII):
  - 12 consultas analíticas distribuídas igualmente nas 6 views fato (2 por view);
  - 5 consultas complexas (cruzamentos multi-view e filtros com acentos/nomes reais);
  - 7 casos de segurança e escopo (2 `out_of_scope`, 3 `blocked` prompt injection, 2 perguntas acadêmicas legítimas com termos sensíveis como "orientações" e "regras de edital").
- Validar 100% das SQLs gabarito contra `Muninn/app/data/dados.db` real.

### [TASK-QA-04.2] Implementar avaliador híbrido (`eval_acuracia.py`)
- Camada 1 determinística: executa fluxo real dos agentes (`orchestrator` + `bi_agent`) em ambiente isolado (checkpoint temporário), executa `sql_gabarito` no mesmo `dados.db`, normaliza e compara resultados com tolerância semântica (`abs_tol=0.05`/`rel_tol=1e-3`, agnóstico a aliases/ordem quando não exigida) e valida intents/bloqueios do `guard`.
- Camada 2 LLM-as-a-Judge: reaproveita `GEMINI_API_KEY` (com `GEMINI_JUDGE_MODEL` opcional), saída estruturada Pydantic (`fidelidade_factual`, `completude`, `sem_vazamento_sql_pii`, `aprovado`, `nota_0_a_5`, `justificativa`).
- Backoff para erros transitórios (429/rede) classificados como `infra_error`.
- Flags `--sample N`, `--categoria`, `--no-judge`, `--banco`, `--out-dir`; telemetria de latência (`p50`/`p95`/média) e relatórios `eval_acuracia_report.json` + `eval_acuracia_report.md`.

### [TASK-QA-04.3] Integrar `make test-eval`, atualizar `README.md` e gerar evidências Issue #71
- Adicionar `make test-eval` ao `Makefile` raiz (aceitando `ARGS`, fora do `make test` offline).
- Atualizar `README.md` documentando todas as novas suítes de teste e pré-requisitos.
- Executar as suítes (`make test`, `make test-perf`, `make test-e2e`, `make test-e2e-live`, `make test-eval`) e gerar o relatório consolidado pronto para o comentário da Issue #71.
