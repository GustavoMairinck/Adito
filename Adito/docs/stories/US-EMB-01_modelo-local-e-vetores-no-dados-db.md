# User Story: [US-EMB-01] Modelo de embedding local e vetores dos valores dentro do dados.db

**Epic:** EPIC-16 — Embeddings locais no `dados.db` e respostas mais estáveis
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** 🔴 Alta (slice 1)
**Story Points:** 5
**Sprint:** - (implementação direta na branch `feat/embeddings-locais`, no fork)
**Status:** Em teste no fork
**Behavior Change Esperado:** YES

---

## Historia

**Como** administrador que publica as cargas do Adito
**Eu quero** gerar os vetores de busca dos valores com um modelo local, sem API de IA, e publicá-los dentro do `dados.db` junto com o modelo
**Para que** que todo usuário receba os mesmos vetores prontos, sem gastar a cota do provedor de IA

### Contexto Adicional

Antes, cada usuário embedava pela API milhares de valores distintos das `embed_columns`, e trocar de provedor invalidava o índice. Ver ADR-0009.

Origem: análise de 27/11/2026 (`/mnt/project-files/embeddings/analise-fluxo-resposta-embeddings.md`) e [ADR-0009](../../../Docs/ADR/ADR-0009-embeddings-locais-no-dados-db.md).

### Pontos de Esclarecimento

- Modelo final e limite de similaridade dependem da comparação no `dados.db` real.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Modelo local único):** `analytics_index/modelo_local.py` define o modelo (fastembed, ONNX int8, CPU) e o `EmbedderLocal`, que devolve vetores normalizados.
- [x] **Criterio 2 (Geração na publicação):** `scripts/gerar_embeddings_dados.py` faz `SELECT DISTINCT` por coluna das `embed_columns`, quebra `multi_valor_columns` em `; ` e grava `adito_valor_embedding` (float16) e `adito_embedding_meta` (modelo, dim, data, totais). O `publicar_dados.sh` roda o script numa cópia antes de cifrar.
- [x] **Criterio 3 (Modelo na release `dados` sem criptografia):** `scripts/empacotar_modelo.py` gera `modelo.json` e `modelo-<chave>-<sha12>.tar.gz`. O app confere tamanho e SHA-256, extrai com filtro seguro e troca a pasta de forma atômica.
- [x] **Criterio 4 (Carga na abertura):** o núcleo baixa (se faltar), aquece o modelo e carrega o índice em segundo plano, sem atrasar a abertura.
- [x] **Criterio 5 (Modelo diferente desliga a busca):** se `adito_embedding_meta.modelo` não for o do app, ou a dimensão não bater, o índice fica indisponível com o motivo, e o chat segue sem busca semântica.
- [x] **Criterio 6 (Tabelas protegidas):** as tabelas de vetores ficam fora das `exposed_views` e o validador de SQL bloqueia leitura delas.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Mudança interna do núcleo (e do painel admin), coberta por testes unitários sem rede nem LLM.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** A decisão de arquitetura está no ADR-0009.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Só RPCs internos entre o front e o núcleo.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Depende de:** —
- **Touch List preliminar:**
  - `Adito/app/backend/nucleo/analytics_index/modelo_local.py`
  - `Adito/app/backend/nucleo/analytics_index/valores.py`
  - `Adito/scripts/gerar_embeddings_dados.py`
  - `Adito/scripts/empacotar_modelo.py`
  - `Adito/scripts/publicar_dados.sh`
  - `Adito/app/backend/nucleo/rpc/server.py`
  - `Adito/app/backend/adito-backend.spec`
  - `Adito/app/backend/nucleo/requirements.txt`

---

## Tasks

- [x] **[TASK-001]** Criar `modelo_local.py` e `valores.py` (índice e catálogo).
- [x] **[TASK-002]** Criar `gerar_embeddings_dados.py` e `empacotar_modelo.py` e ligar no `publicar_dados.sh`.
- [x] **[TASK-003]** Carregar o modelo na abertura (`rpc/server.py`) e incluir fastembed, onnxruntime e tokenizers no `adito-backend.spec`.
- [x] **[TASK-004]** Testes em `core/test_embeddings_locais.py` com motor falso (sem download).

---

## Definition of Done Checklist

- [x] Codigo implementado conforme criterios de aceitacao
- [x] Decisao sobre Spec governada foi registrada
- [x] Decisao sobre Contract governado foi registrada
- [x] Nivel ScrumAIDev foi registrado
- [x] Gates opcionais executados ou dispensados com justificativa
- [ ] Code review aprovado
- [x] Testes unitarios com cobertura adequada
- [x] Documentacao atualizada
- [ ] Teste conjunto no fork (Gustavo)
- [ ] `Behavior change` documentado no PR
- [ ] Aprovacao do Product Owner
