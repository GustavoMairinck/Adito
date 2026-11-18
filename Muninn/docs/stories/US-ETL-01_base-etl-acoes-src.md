# User Story: [US-ETL-01] Base do `etl/` e extrator de ações do SRC

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Alta (primeiro vertical slice)  
**Story Points:** 3  
**Sprint:** —  
**Status:** Review (implementado na branch feat/etl-slices-1-2)  
**Requisitos:** FR01, FR07, FR08, FR09, BR06, NFR03, NFR05 (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** rodar, dentro do repositório do Adito, um comando que baixa todas as ações do SRC do campus Serra  
**Para que** o bruto do SRC exista sem depender do repositório SRCEtl e sirva de base para as participações e o cruzamento

### Contexto Adicional
O SRCEtl (`~/Área de trabalho/SRCEtl/src`) já faz isso: lista as ações pela consulta pública (Playwright), baixa o detalhe (httpx) e os vínculos ação-mãe → filhas (`vinculadas.py`) e grava `acao_<id>.json` + `_index.json`. Esta story copia essa parte quase igual e cria a estrutura do `etl/` (pacote Python, ambiente próprio, convenção de saída) que as outras stories reaproveitam.

---

## ✅ Critérios de Aceitação

- [ ] **CA1:** `etl/` tem `pyproject.toml` próprio, separado do backend do app, com só as dependências aprovadas para esta story (Playwright, httpx, beautifulsoup4, pydantic).
- [ ] **CA2:** Um comando (ex.: `adito-etl src-acoes --campus Serra`) grava `etl/brutos/src/acoes/acao_<id>.json` e `_index.json` no mesmo formato do SRCEtl, incluindo `acoes_vinculadas`.
- [ ] **CA3:** Sem `--campus`, o padrão é Serra; outro campus pode ser passado por parâmetro.
- [ ] **CA4:** Uma ação que falha (detalhe ou vínculos) não interrompe as demais; ao final o comando lista as falhas e sai com código diferente de zero se houve alguma.
- [ ] **CA5:** O comando grava `etl/brutos/src/_extracao.json` com data e hora, commit do código, total de ações, total gravado e falhas.
- [ ] **CA6:** O `etl/README.md` registra o repositório e o commit de origem do código copiado do SRCEtl; o SRCEtl não é alterado.
- [ ] **CA7:** Rodar duas vezes seguidas, sem mudança no SRC, gera os mesmos `acao_*.json`.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** novo `etl/` (pacote `adito_etl`, subpacote `fontes/src/`), `etl/README.md`.
- **Origem do código:** `src_etl/etl/scraper.py`, `detail.py`, `vinculadas.py`, `models.py`, partes de `pipeline.py` e `cli.py`.
- **APIs necessárias:** consulta pública do SRC (`consulta-acao.xhtml`, detalhe, `consulta-acao-vinculada.xhtml`).
- **Database changes:** nenhuma.

### Dependências
- [ ] Aprovação das dependências Python (regra 6 do AGENTS.md).
- [ ] Navegador do Playwright instalado na máquina da equipe.

### Considerações de Performance
- 194 ações hoje; o SRCEtl já aceita `workers` para a listagem. Manter o user-agent identificado.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Parse do detalhe a partir de um HTML de exemplo (o SRCEtl já tem `tests/test_detail.py`; trazer junto).
- [ ] Gravação de `_extracao.json` com falhas.

### Testes de Integração
- [ ] Rodada com `--max-acoes 3` contra o SRC real gera 3 arquivos + índice.

### Testes Manuais
- [ ] Comparar os `acao_*.json` gerados com `SRCEtl/src/data/serra/` (mesmas chaves, mesmas contagens).

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Criar `pyproject.toml`, pacote e CLI do `etl/`
- [ ] **[TASK-002]** Copiar scraper, detalhe, vínculos e modelos do SRCEtl
- [ ] **[TASK-003]** Comando `src-acoes` com falha isolada e `_extracao.json`
- [ ] **[TASK-004]** Testes e registro de origem no README

---

## 🤖 IA Insights

### Sugestões de Implementação
Criar já um pequeno módulo comum (`saida.py`) com a escrita de `_extracao.json` e a lista de falhas; as stories 02–05 reaproveitam.

### Riscos Identificados
- A consulta pública é JSF; mudança na página quebra o scraper.

### Alternativas Consideradas
- Instalar o SRCEtl como dependência em vez de copiar: rejeitado no Discovery rev. 4 (código copiado para `etl/`).

---

## 📝 Notas e Comentários

- **Spec governada:** US não exige Spec (sem boundary de API; comportamento coberto pelos critérios acima).
- **Contract governado:** US não exige Contract.

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [ ] Documentação atualizada
- [ ] Aprovação do Product Owner
