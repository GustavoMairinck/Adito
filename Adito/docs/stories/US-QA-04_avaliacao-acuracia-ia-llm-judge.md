# User Story: [US-QA-04] Avaliação Híbrida de Acurácia da IA (Dataset + Execution Accuracy + LLM Judge) & Consolidação Issue #71

**Epic:** EPIC-10 — Garantia de Qualidade: Testes Automatizados, Performance e Avaliação da IA  
**GitHub Epic Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**GitHub US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**Prioridade:** Alta (Slice 2)  
**Story Points:** 5  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** NO (ferramental de avaliação da IA, dataset independente e documentação)

---

## Historia

**Como** mantenedor e engenheiro de IA do Adito,  
**Eu quero** avaliar automaticamente a acurácia das respostas do assistente contra um dataset gabarito independente usando verificação determinística de dados (SQL gabarito executada no `dados.db`) combinada com um LLM-as-a-Judge, e consolidar a documentação e resultados da Issue #71,  
**Para que** tenhamos métricas confiáveis de Execution Accuracy, fidelidade factual (zero alucinação), segurança do `guard` e latência de LLM sempre que evoluirmos prompts, contexto ou modelos.

### Contexto Adicional
Armazenar apenas respostas estáticas em texto como gabarito torna-se obsoleto assim que o ETL atualiza o `dados.db`. A abordagem híbrida resolve isso mantendo um dataset independente de `examples.json` (evitando *data leakage*) com pares `(pergunta, sql_gabarito)` para casos analíticos e `(pergunta, expected_intent)` para casos de escopo/segurança. Em tempo de teste, o avaliador executa a SQL gabarito no `dados.db` real para obter os dados verdadeiros, compara com os dados retornados pelo Adito (Camada 1) e submete a resposta textual a um juiz LLM Gemini (Camada 2) para auditar fidelidade, completude e ausência de SQL/PII.

### Pontos de Esclarecimento
Nenhum ponto pendente (estratégia híbrida, porte balanceado ~20–25 casos e reaproveitamento de `GEMINI_API_KEY` aprovados no Gate G1).

---

## Criterios de Aceitacao

- [x] **CA01 (Dataset Gabarito Independente — Zero Data Leakage & Zero PII):** Criar `Adito/app/scripts/eval_dataset.json` com 20–25 casos balanceados, distintos das perguntas verbatim de `Adito/app/contexts/pesquisa-extensao-ifes/examples.json`, cobrindo:
  - Consultas simples e agregadas nas 6 views fato (`src_acao`, `src_participacao`, `sigpesq_projeto`, `sigpesq_bolsa`, `lattes_producao`, `cnpq_grupo`);
  - Cruzamentos multi-view e filtros com acentos/nomes reais;
  - Casos fora de escopo (`out_of_scope`) e *prompt injection* (`blocked`);
  - Perguntas acadêmicas legítimas com termos sensíveis (ex.: "orientações", "regras de edital") que NÃO devem ser bloqueadas.
  - Todas as SQLs gabarito validadas contra `dados.db` real (retornando dados válidos sem erro).
- [x] **CA02 (Camada 1 — Determinística: Execution Accuracy & Guard):** `Adito/app/scripts/eval_acuracia.py` executa cada caso pelo fluxo real dos agentes sobre `dados.db`, executa a `sql_gabarito` no mesmo `dados.db`, compara resultados com tolerância semântica (ignorando aliases de coluna, tolerando pequenas diferenças de float e ordem irrelevante) e valida determinísticamente os bloqueios/passagens do `guard`.
- [x] **CA03 (Camada 2 — LLM-as-a-Judge):** Usa `GEMINI_API_KEY` (com suporte opcional a `GEMINI_JUDGE_MODEL`, fallback para `GEMINI_MODEL`) com saída estruturada (Pydantic/JSON) avaliando fidelidade factual, completude, ausência de vazamento de SQL/PII e justificativa curta. Suporta retry com backoff leve e contabiliza falhas transitórias de API (429/rede) separadamente como `infra_error`.
- [x] **CA04 (Telemetria, Flags e Relatórios):** Suporta `--sample N`, `--categoria <cat>` e `--no-judge`; mede latência ponta a ponta do pipeline de IA (`p50`/`p95`/média); falha com mensagem clara se `dados.db` ou `GEMINI_API_KEY` estiverem ausentes; exporta relatório consolidado em JSON e Markdown com taxa de aprovação por categoria e tabela de falhas.
- [x] **CA05 (Makefile, README e Evidências Issue #71):** Adiciona `make test-eval` (com suporte a `ARGS`) sem acoplar ao `make test` offline; documenta todos os comandos de teste (`test`, `test-front`, `test-e2e`, `test-e2e-live`, `test-perf`, `test-eval`) e pré-requisitos no `README.md`; gera resumo final consolidado dos resultados pronto para comentar na Issue #71.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; suite de avaliação de qualidade e documentação sem mudança de contratos de produção.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Ferramental de avaliação offline/sob demanda.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Sem novo contrato de API.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR07`, `FR08`, `FR09`, `FR10`, `FR11`, `FR12`, `BR01`, `BR02`, `BR03`, `BR04`, `BR05`, `NFR03`, `NFR04`, `NFR05`, `A01`, `A02`
- **Touch List preliminar:**
  - `Adito/app/scripts/eval_dataset.json`
  - `Adito/app/scripts/eval_acuracia.py`
  - `Makefile`
  - `README.md`
  - `Adito/docs/resultados/` (relatório consolidado opcional para rastreabilidade da Issue #71)
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** Novos arquivos `Adito/app/scripts/eval_dataset.json` e `Adito/app/scripts/eval_acuracia.py`.
- **APIs necessarias:** `agents.orchestrator.graph`, `agents.bi_agent.tool`, `agents.config.get_chat_llm`, `core.datastore`.
- **Database changes:** Nenhuma (somente leitura em `dados.db`; `ADITO_CHECKPOINT_DB` isolado em `tempfile`).
- **Referencias do modelo de dados:** 6 views fato (`vfact_*_resolved`).
- **Erros observaveis esperados:** Ausência de `GEMINI_API_KEY`, ausência de `dados.db`, rate limit (429) classificado como `infra_error`.

### Dependencias
- [x] Zero novas dependências Python (usa `langchain-google-genai`, `pydantic` e `sqlite3` já presentes na `.venv`).
- [x] `US-QA-02` e `US-QA-03` concluídas para consolidação completa da documentação no `README.md` e do relatório final da Issue #71.

### Consideracoes de Performance
- Suporte a `--sample N` e `--categoria` permite execuções rápidas (~20–30s) durante iterações de prompt sem consumir cota completa.

---

## Plano de Testes

### Testes Unitarios / Validacao
- [x] Validar 100% das SQLs gabarito do `eval_dataset.json` diretamente no `dados.db` real (0 erros de sintaxe/schema, resultados não vazios onde esperado) e verificar ausência de duplicidade verbatim com `examples.json`.
- [x] Testar comparador determinístico (Camada 1) com casos de aliases diferentes, tolerância numérica e ordenação.
- [x] Executar `make test-eval` (24 casos base + 2 casos multi-turno) e validar geração dos relatórios JSON + Markdown com Execution Accuracy, score do LLM Judge e latência `p50`/`p95`.
- [x] Conferir se todas as instruções no `README.md` funcionam exatamente como documentado.
