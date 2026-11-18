# User Story: [US-ETL-03] Extrator do SigPesq

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Alta (segundo slice)  
**Story Points:** 5  
**Sprint:** —  
**Status:** In Progress (conversão validada nos XLSX reais; falta rodar o download com a credencial)  
**Requisitos:** FR04, FR07–FR09, BR01, NFR02, NFR03; A01, A04 (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** baixar os relatórios de grupos, projetos e orientações do SigPesq e guardá-los como JSON só com nome e campos não pessoais  
**Para que** o SigPesq entre no cruzamento e forneça as URLs de espelho que o extrator do CNPq precisa

### Contexto Adicional
No horizon_etl, o `SigPesqAdapter` (`src/adapters/sources/sigpesq/adapter.py`) chama a biblioteca `sigpesq-agent` para baixar relatórios XLSX em `data/raw/sigpesq/` (subpastas `research_group`, `research_projects`, `advisorships`), com credencial vinda do Infisical, e depois carrega tudo no banco. Esta story fica só com o download e a conversão.

---

## ✅ Critérios de Aceitação

- [ ] **CA1:** Um comando (ex.: `adito-etl sigpesq`) baixa os relatórios de grupos, projetos e orientações pela `sigpesq-agent`.
- [x] **CA2:** Cada relatório vira JSON em `etl/brutos/sigpesq/<relatorio>/`, com todas as linhas e só as colunas da lista de permitidas (aprovada pelo usuário antes do merge). *(Aprovada em 2026-11-10, incluindo `Valor` das orientações.)*
- [ ] **CA3:** O XLSX baixado é apagado ao fim da conversão; nenhum XLSX fica em `etl/`.
- [ ] **CA4:** A credencial vem do Infisical (segredos `sigpesq-user`/`sigpesq-password`, como no horizon_etl) ou do `etl/.env`, conforme `ADITO_CREDENCIAIS`; banco e Prefect não são usados. *(Revisto em 2026-11-11.)*
- [ ] **CA5:** O JSON de grupos mantém a URL do espelho do CNPq de cada grupo.
- [ ] **CA6:** Erro 429 espera e tenta de novo até o limite; falha de um relatório não impede os outros e é listada no `_extracao.json`.
- [ ] **CA7:** O teste de PII da US-ETL-02 passa também sobre `etl/brutos/sigpesq/`.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `etl/` subpacote `fontes/sigpesq/`.
- **Origem do código:** `horizon_etl/src/adapters/sources/sigpesq/adapter.py` e `credentials.py` (sem Infisical); leitura do XLSX inspirada em `SigPesqFileLoader`.
- **Database changes:** nenhuma.

### Dependências
- [ ] US-ETL-01.
- [ ] Aprovação de `sigpesq-agent` (git, v0.3.2) e `openpyxl`.
- [ ] Credencial do SigPesq da equipe.

### Considerações de Performance
- Poucos relatórios; o gargalo é o download pela `sigpesq-agent`.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Conversão de um XLSX pequeno (gerado no teste) para JSON com filtro de colunas.

### Testes de Integração
- [ ] Rodada real gera os três relatórios em JSON e nenhum XLSX sobra.

### Testes Manuais
- [ ] Conferir contagens contra o último relatório baixado pelo horizon_etl.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Copiar o adapter e trocar o Infisical por `.env`
- [ ] **[TASK-002]** Converter XLSX → JSON com lista de permitidas
- [ ] **[TASK-003]** Comando, retentativa e `_extracao.json`

---

## 🤖 IA Insights

### Riscos Identificados
- A `sigpesq-agent` pode depender de navegador/driver (selenium); conferir na versão fixada.
- Os relatórios de orientação podem trazer CPF/e-mail de alunos; por isso o XLSX não é guardado.

---

## 📝 Notas e Comentários

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
