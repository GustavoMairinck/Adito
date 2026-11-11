# User Story: [US-ETL-05] Extrator do Lattes

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Média  
**Story Points:** 5  
**Sprint:** —  
**Status:** In Progress (download real em 2026-11-11: 126 de 126 currículos, 10 só na segunda tentativa)  
**Requisitos:** FR06, FR07–FR09, BR01, NFR03; A02, A05 (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** baixar os currículos Lattes de uma lista de pesquisadores mantida em arquivo  
**Para que** projetos e orientações do Lattes entrem no cruzamento sem depender do banco do horizon_etl

### Contexto Adicional
No horizon_etl, `flows/lattes/download.py` monta uma lista `.list` (id Lattes, nome) a partir de uma lista fixa no código, gera um `lattes.config` e roda o `scriptLattes`, com cache por id. Aqui a lista vira `etl/entradas/lattes.csv`.

---

## ✅ Critérios de Aceitação

- [x] **CA1:** `etl/entradas/lattes.csv` (colunas `nome,lattes_id`) existe, versionado, começando pela lista hoje fixa no horizon_etl.
- [ ] **CA2:** Um comando (ex.: `adito-etl lattes`) baixa os currículos da lista pelo `scriptLattes` e grava o bruto de cada um em `etl/brutos/lattes/<lattes_id>.json` (convertido para JSON se o `scriptLattes` não produzir JSON).
- [x] **CA3:** Linhas com id que não tem 16 dígitos são listadas e puladas.
- [ ] **CA4:** Currículo que não baixa depois do limite de tentativas vai para a lista de falhas, sem travar a fase.
- [ ] **CA5:** Só nome e campos não pessoais saem no bruto (lista de permitidas aprovada pelo usuário); o teste de PII passa sobre `etl/brutos/lattes/`.
- [ ] **CA6:** Sem Prefect, Telegram ou banco.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `etl/` subpacote `fontes/lattes/`, `etl/entradas/lattes.csv`.
- **Origem do código:** `horizon_etl/src/flows/lattes/download.py` (sem `@flow`/`@task`), `core/logic/lattes_generators.py`, `adapters/sources/lattes_parser.py`.

### Dependências
- [ ] US-ETL-01.
- [ ] Aprovação de `scriptLattes` (git, v0.8.0) e do que ele exigir (selenium/navegador).

### Considerações de Performance
- O `scriptLattes` repete tentativas sem fim em timeout; o horizon_etl já limita isso (`HORIZON_LATTES_DOWNLOAD_MAX_ATTEMPTS`). Manter o limite.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Leitura do `lattes.csv` e validação do id.
- [ ] Conversão de um currículo de exemplo para JSON filtrado.

### Testes de Integração
- [ ] Rodada com 2 ids reais grava 2 arquivos.

### Testes Manuais
- [ ] Comparar a quantidade de projetos/orientações de um currículo com o que o horizon_etl extrai.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Criar `entradas/lattes.csv` a partir da lista do horizon_etl
- [ ] **[TASK-002]** Copiar geração de config/lista e o download, sem Prefect
- [ ] **[TASK-003]** Conversão para JSON com filtro de colunas
- [ ] **[TASK-004]** Comando, limite de tentativas e `_extracao.json`

---

## 📝 Notas e Comentários

- **2026-11-10:** `adito-etl lattes` (download + conversão) e `adito-etl lattes-converter --de` implementados em `fontes/lattes/`. A conversão dos 126 JSON que o horizon_etl já tinha gerou 119 currículos; 7 vieram vazios (`[Nome-nao-identificado]`, download falho no horizon) e ficam como falha no `_extracao.json`.
- **Lista de permitidas (decidida pelo usuário em 2026-11-11 — CA5):** todas as seções acadêmicas; em `informacoes_pessoais` entra `endereco_profissional` (sem telefone, fax e ramal). `sexo` foi aprovado, mas sai: o Lattes público não mostra mais o sexo e o scriptLattes preenche "Masculino" para todos. Ver `etl/src/adito_etl/fontes/lattes/colunas.py`.
- **Dependência:** a instalação do `scriptLattes` (git v0.8.0; puxa scipy, networkx, rapidfuzz) foi bloqueada até aprovação do usuário (AGENTS.md regra 6).
- **Spec governada:** US não exige Spec.
- **Contract governado:** US não exige Contract.

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [ ] Documentação atualizada
- [ ] Aprovação do Product Owner
