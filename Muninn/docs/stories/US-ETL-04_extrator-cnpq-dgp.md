# User Story: [US-ETL-04] Extrator do CNPq/DGP

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Média  
**Story Points:** 3  
**Sprint:** —  
**Status:** In Progress (rodando de verdade desde 2026-11-11; carga no banco em `Adito/scripts/popular_banco.py`)  
**Requisitos:** FR05, FR07–FR09, BR01, BR04, NFR03 (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** baixar o espelho no DGP/CNPq de cada grupo de pesquisa listado no SigPesq  
**Para que** os membros, linhas e áreas dos grupos entrem no cruzamento e o grupo SigPesq seja ligado ao CNPq pelo espelho

### Contexto Adicional
No horizon_etl, `flows/cnpq/groups.py` lê os grupos e as `cnpq_url` do banco, valida o formato `dgp.cnpq.br/dgp/espelhogrupo/<16 dígitos>` e chama o `CnpqCrawlerAdapter` (sobre a `dgp-cnpq-lib`). Aqui a lista de URLs sai do bruto do SigPesq.

---

## ✅ Critérios de Aceitação

- [ ] **CA1:** Um comando (ex.: `adito-etl cnpq`) lê as URLs de espelho em `etl/brutos/sigpesq/` e para com mensagem clara se o bruto do SigPesq não existir.
- [ ] **CA2:** Cada grupo é gravado em `etl/brutos/cnpq/grupo_<id16>.json`, com os dados que a `dgp-cnpq-lib` devolve, filtrados pela lista de permitidas (nome dos membros sim; nada além do nome como dado pessoal).
- [ ] **CA3:** Grupos sem URL ou com URL fora do formato do espelho são listados (grupo, URL) no `_extracao.json` e pulados.
- [ ] **CA4:** A falha de um grupo não interrompe os demais e é listada.
- [ ] **CA5:** Sem banco, Prefect, Telegram ou `research-domain`.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `etl/` subpacote `fontes/cnpq/`.
- **Origem do código:** `horizon_etl/src/adapters/sources/cnpq_crawler.py`, validação de URL de `flows/cnpq/groups.py`.

### Dependências
- [ ] US-ETL-03 (bruto do SigPesq com as URLs).
- [ ] Aprovação de `dgp-cnpq-lib` (git, v0.5.0).

### Considerações de Performance
- Dezenas a centenas de grupos; uma requisição por grupo, sem paralelismo agressivo.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Validação de URL de espelho (válida, sem id, com barras duplas).

### Testes de Integração
- [ ] Rodada com um grupo real grava um `grupo_<id16>.json`.

### Testes Manuais
- [ ] Conferir a lista de URLs inválidas com o relatório do horizon_etl.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Copiar o adapter e a validação de URL
- [ ] **[TASK-002]** Ler URLs do bruto do SigPesq
- [ ] **[TASK-003]** Comando, filtro de colunas e `_extracao.json`

---

## 📝 Notas e Comentários

- **2026-11-10:** `adito-etl cnpq [--unidade Serra] [--max N] [--refazer]` implementado em `fontes/cnpq/grupos.py`; lê `Column1` do bruto do SigPesq (352 de 354 grupos com URL). Retomada: grupo já gravado é pulado.
- **Filtro (decidido pelo usuário em 2026-11-11 — CA2):** ficam identificação, repercussões, linhas, recursos humanos, indicadores, instituições/INCTs parceiras, equipamentos e o endereço do grupo com site; saem telefone, fax e e-mail de contato. Nomes de seção conferidos na primeira rodada real (`repercussoes`, `endereco_contato`...).
- **Dependência:** a instalação da `dgp-cnpq-lib` (git v0.5.0) foi bloqueada até aprovação do usuário (AGENTS.md regra 6).
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
