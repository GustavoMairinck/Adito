# Product Backlog — Adito

Backlog do Adito no monorepo. As stories do porte desktop (US-001 a US-015) estão indexadas em [README.md](README.md); aqui fica o que veio depois do Discovery rev. 4.

## Epics

### EPIC-07: ETL do Adito
Extração do bruto de SRC, SigPesq, CNPq/DGP e Lattes e cruzamento das bases por nome normalizado, em `Adito/etl/`, rodado só pela equipe de dados. Origem: `docs/discovery/adito.md` (rev. 4) e `docs/requirements/adito-etl.md`.
- **Stories**: US-ETL-01 a US-ETL-07.

---

## User Stories Priorizadas

### 🗂️ EPIC-07 — ETL do Adito (aprovado em 10/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-ETL-01](stories/US-ETL-01_base-etl-acoes-src.md) | Base do `etl/` e extrator de ações do SRC | EPIC-07 | 3 | 🔴 Alta (slice 1) | — | FR01, FR07–09, BR06, NFR03, NFR05 | 🔍 Review |
| [US-ETL-02](stories/US-ETL-02_participacoes-src-sem-pii.md) | Participações do SRC sem CPF nem e-mail | EPIC-07 | 5 | 🔴 Alta (slice 1) | 01 | FR02, FR03, BR01, NFR02, NFR04, NFR06 | 🔄 In Progress |
| [US-ETL-03](stories/US-ETL-03_extrator-sigpesq.md) | Extrator do SigPesq | EPIC-07 | 5 | 🟠 Alta (slice 2) | 01 | FR04, BR01, A01, A04 | 🔄 In Progress |
| [US-ETL-06](stories/US-ETL-06_cruzamento-pessoas-por-nome.md) | Cruzamento de pessoas por nome normalizado | EPIC-07 | 5 | 🟠 Alta (slice 2) | 02 + 1 fonte | FR10, FR11, FR13, BR02, BR03, BR05, NFR06 | 🔍 Review |
| [US-ETL-04](stories/US-ETL-04_extrator-cnpq-dgp.md) | Extrator do CNPq/DGP | EPIC-07 | 3 | 🟡 Média | 03 | FR05, BR04 | Backlog |
| [US-ETL-05](stories/US-ETL-05_extrator-lattes.md) | Extrator do Lattes | EPIC-07 | 5 | 🟡 Média | 01 | FR06, A02, A05 | Backlog |
| [US-ETL-07](stories/US-ETL-07_ligacoes-grupo-orientacao.md) | Ligações de grupo e de orientação | EPIC-07 | 3 | 🟡 Média | 03, 04, 05, 06 | FR12 | Backlog |

> 10/11/2026: o usuário pediu para implementar os slices 1 e 2 direto, sem sprint planning ("sem esse trem de sprint"). Status por story na própria story.
>
> Total: 29 pts. Primeiro vertical slice: US-ETL-01 + US-ETL-02 (SRC completo até o bruto, 8 pts). Segundo: US-ETL-03 + US-ETL-06 (primeiro cruzamento SRC ↔ SigPesq, 10 pts). Todas Nível ScrumAIDev 1, sem Spec nem Contract governados.
