# Especificação Técnica: Resoluções e Regras de Negócio das Fatos Analíticas (v2.0)

**Status:** Aprovado / Implementado  
**Data da Revisão:** 18/11/2026  
**Foco:** Conceito, modelagem dimensional (Kimball) e resolução integral das inconsistências estruturais e semânticas identificadas nas **6 tabelas fato (`vfact_*_resolved`)**, adaptadas à arquitetura **100% SQLite (`dados.db`)** e implementadas como **VIEWs dinâmicas relacionais**.  
**Documento Canônico de Fatos:** [Docs/Fatos/PropostaFatos.md](../../../Docs/Fatos/PropostaFatos.md)  
**ADRs Relacionadas:** [ADR-0001 (Migração SQLite)](../../../Docs/ADR/ADR-0001-migracao-dados-100-sqlite.md) e [ADR-0003 (Views Dinâmicas OLTP)](../../../Docs/ADR/ADR-0003-camadas-3fn-e-fatos-materializadas.md)  

---

## 1. Conceito, Funcionamento e Modelo Dimensional (100% SQLite)

O Adito adota uma **Constelação de Fatos Conformes (Kimball)**: em vez de expor ~85 tabelas normalizadas (3FN) ou misturar tudo em uma única tabela esparsa, o sistema materializa **6 visões/tabelas analíticas desnormalizadas**, cada uma representando um **evento de negócio** e um **grão** (o que significa exatamente **1 linha**):

| Tabela Fato (`vfact_*_resolved`) | Fonte Principal | Grão (1 linha =) | Papel Analítico |
| :--- | :--- | :--- | :--- |
| **`vfact_extensao_acao_resolved`** | SRC | 1 ação de extensão (`id_acao`) | Portfólio, tipos, aprovação de relatório e fomento da extensão |
| **`vfact_extensao_participacao_resolved`** | SRC | 1 inscrição em atividade (`id_participacao`) | Público atendido, certificados e carga horária cumprida |
| **`vfact_projeto_pesquisa_resolved`** | SigPesq | 1 projeto de pesquisa (`id_projeto`) | Natureza (básica/aplicada), parecer da diretoria e planos vinculados |
| **`vfact_orientacao_bolsa_resolved`** | SigPesq | 1 concessão de bolsa/orientação (`id_orientacao`) | Programas (PIBIC, PIBITI...), agências, bolsistas/voluntários e investimento |
| **`vfact_producao_cientifica_resolved`** | Lattes | 1 **autoria** de produção (`id_producao` + `id_pessoa_lattes`) | Artigos, congressos, livros/capítulos, produções técnicas e softwares |
| **`vfact_grupo_pesquisa_membro_resolved`** | CNPq DGP | 1 vínculo de membro em grupo (`id_membro_grupo`) | Grupos certificados, membros ativos/egressos, papéis e titulação |

### O que muda com a ADR-0001 (PostgreSQL + JSON + DuckDB → 100% SQLite `dados.db`)
- **Pipeline simplificado:** elimina Docker/PostgreSQL, `recriar_banco.sh`, `psql`, `exportar_json.py` e `gerar_duckdb.py`. Um script Python único com `sqlite3` gera diretamente `Adito/app/data/dados.db` a partir dos dados do `Adito/etl/`.
- **Fim do gargalo de exportação de 41 tabelas:** como todo o modelo unificado e as 6 fatos passam a residir diretamente dentro do mesmo `dados.db`, tabelas como `lideranca_grupo_pesquisa` já ficam acessíveis na geração das fatos sem depender de etapa intermediária de JSON.
- **Mudança obrigatória de dialeto SQL:** todas as queries das 6 fatos, o validador `sql_security.py` e o contexto do Oráculo (`rules.md` / `examples.json`) passam a operar em **SQLite** (sem `unificado.`, sem `::TYPE`, sem `EXTRACT`, sem `ILIKE`, usando `julianday()` para diferença de dias, `strftime()` para datas, `GROUP_CONCAT()` e `MIN()`/`MAX()`).

---

## 2. Os 5 Problemas de Prioridade Máxima (Causa Raiz + Solução Lógica)

### Problema 1 — Vínculo de `campus` distorcido nas Produções Científicas do Lattes
- **Escopo exato do problema:**
  - Ocorre especificamente nas **Produções Científicas do Lattes** (`vfact_producao_cientifica_resolved` — artigos, livros, produções técnicas), e **não** nos projetos do Lattes (`projeto_lattes` nem participa das 6 fatos).
  - Como uma publicação no Lattes não traz campus próprio, a view herda `pesquisador.id_organizacao`. Quando o pesquisador **não** recebeu campus prévio do SigPesq, a carga em [popular_banco.py](../../Adito/scripts/popular_banco.py) pega a **1ª atuação marcada como `"Atual"`** no currículo Lattes — que pode ser outra universidade (`UFES`) ou até uma **agência de fomento (`FAPES`)**.
- **Evidência nos dados reais (`1.220` linhas):** `421` produções saem como `campus = 'Universidade Federal do Espírito Santo'` e `247` como `'Fundação de Amparo à Pesquisa e Inovação do Espírito Santo'` (`54,8%` da tabela), misturando campi do IFES (`Serra`, `Vitória`), universidade externa e agência de fomento na mesma coluna.
- **Solução lógica:**
  1. **Hierarquia de vínculo institucional na carga SQLite:** priorizar sempre um **Campus do IFES** (vindo do SigPesq, do CNPq ou de atuação no IFES dentro do Lattes) antes de aceitar instituições externas, e **nunca** promover agência de fomento (`FAPES`, `CNPq`) a organização de lotação.
  2. **Separação semântica na fato (`vfact_producao_cientifica_resolved`):** manter `campus` restrita a campi reais do IFES (`'Externo / Não Vinculado'` quando de fora) e expor `instituicao_vinculo` (ex.: `'Universidade Federal do Espírito Santo'`), eliminando a mistura na coluna `campus`.

---

### Problema 2 — `flag_lider` sempre `0` (`lideranca_grupo_pesquisa` ausente da fato)
- **Conceito do problema:** A [PropostaFatos.md](PropostaFatos.md) promete identificar líderes de grupos de pesquisa via `papel_membro = 'Líder'` e `flag_lider = 1`. Porém, os líderes não são gravados como papel dentro de `membro_grupo` (que guarda apenas `Pesquisador`, `Estudante`, `Técnico`, `Membro`), e sim na tabela própria `lideranca_grupo_pesquisa` (`595` registros no banco).
- **Evidência nos dados reais:** Em `9.497` vínculos de `vfact_grupo_pesquisa_membro_resolved`, **`flag_lider = 1` ocorre `0` vezes**.
- **Solução lógica:**
  - Com a unificação em `dados.db` (ADR-0001), `lideranca_grupo_pesquisa` já reside no mesmo banco SQLite. Basta consultar `EXISTS (SELECT 1 FROM lideranca_grupo_pesquisa ...)` na criação da `vfact_grupo_pesquisa_membro_resolved` para calcular `flag_lider` sem multiplicar linhas.

---

### Problema 3 — Perda de dados como `NULL` por listas fechadas (ENUMs e Domínios incompletos)
- **Conceito do problema:** O modelo usa listas fechadas de categorias (`programa`, `situacao_grupo`, `nivel_treinamento`, `tipo_apoio_financiamento`). Quando a origem traz um valor válido fora dessas listas, a carga descarta o valor e grava `NULL`.
- **Evidência nos dados reais:**
  - Domínio `programa`: faltam `'pivic'`, `'pibic_em'`, `'jtc'` e `'picti'` → **`159` orientações** caíram em `'Não Especificado'` (só o `Pivic` tem `149` registros).
  - Situação de grupo (`tipo_situacao_grupo`): falta `'EXCLUIDO'` → **`19` grupos (`234` vínculos)** vieram como `"Excluído"` no CNPq e viraram `situacao_grupo = NULL`.
  - Domínios menores: `"Ensino Fundamental (1o grau)"` (`3` casos) e `"Financiamento"` (`3` casos).
- **Solução lógica:**
  - No schema SQLite (tabelas de domínio e `CHECK` constraints equivalentes aos antigos ENUMs) e no script de carga Python, ampliar as listas válidas com `'pivic'`, `'pibic_em'`, `'jtc'`, `'picti'`, `'EXCLUIDO'`, `'ENSINO_FUNDAMENTAL'` e `'FINANCIAMENTO'`, além de mapear `'excluido'` no carregador do CNPq.

---

### Problema 4 — Investimento em bolsas superestimado por ignorar desligamentos/cancelamentos
- **Conceito do problema:** Em `vfact_orientacao_bolsa_resolved`, `investimento_total_estimado` multiplica `valor_bolsa` pela duração prevista (`data_fim - data_inicio`), ignorando os campos `cancelado` e `data_cancelado` que já existem em `orientacao`.
- **Evidência nos dados reais:** Das `231` bolsas canceladas (`R$ 473.300,00` somados), **`71` foram canceladas antes da `data_fim`** e continuam somando **`R$ 221.000,00`** como se tivessem durado até o encerramento previsto.
- **Solução lógica (SQLite):**
  - Usar `julianday()` para diferença real de dias no SQLite e `MIN(data_fim, data_cancelado)` quando `cancelado = 1` e `data_cancelado IS NOT NULL` (zerando se `data_cancelado <= data_inicio`).
  - Expor `duracao_meses_efetiva` e `investimento_previsto_original` ao lado de `investimento_total_estimado` (efetivo).

---

### Problema 5 — Patentes e softwares com patente não são registrados (`0` linhas)
- **Conceito do problema:** `patente_registro` exige `id_instituicao_depositante NOT NULL`. Como o JSON do Lattes não traz essa informação estruturada, a carga descarta todas as `patentes_registros` e `softwares_com_patente` (`0` linhas no banco). Mesmo assim, `vfact_producao_cientifica_resolved` e `rules.md` prometem `flag_patente_software = 1` para patentes e softwares — ocultando inclusive os **`28` softwares sem patente** que já existem em `producao_tecnica_artistica_bibliografica` (`SOFTWARE_SEM_PATENTE`).
- **Solução lógica:**
  - **Caminho A (recomendado):** tornar `patente_registro.id_instituicao_depositante` anulável no DDL SQLite, implementar a gravação de `patentes_registros` e `softwares_com_patente` na carga, e adicionar `flag_software_sem_patente` na fato para distinguir softwares registrados dos não registrados.
  - **Caminho B (alternativo):** remover `flag_patente_software` das regras do contexto e direcionar consultas de software para `subtipo_producao = 'SOFTWARE_SEM_PATENTE'`.

---

## 3. Demais Problemas Relacionados às Fatos e à Migração SQLite

### Problema 6 — Dimensão prometida e esquecida no SQL (`parceiro_demandante_projeto`)
- **O que acontece:** `parceiro_demandante_projeto` (`38` registros no banco) é citada na Seção 3.3 e na Matriz da Seção 4 de `PropostaFatos.md`, mas não participa da query de `vfact_projeto_pesquisa_resolved`.
- **Solução lógica:** Agregar os parceiros por `id_projeto_pesquisa` via subquery com `GROUP_CONCAT` (SQLite) e expor `parceiros_demandantes` mantendo o grão `1:1`.

---

### Problema 7 — Projetos completos (`103`) misturados com projetos mínimos inferidos (`133`)
- **O que acontece:** `56,4%` das `236` linhas de `vfact_projeto_pesquisa_resolved` foram geradas apenas como "âncoras mínimas" (só título) a partir do relatório de Orientações, ficando com `parecer_diretoria`, `natureza_projeto` e `data_inicio` nulos sem identificação de origem.
- **Solução lógica:** Expor `origem_registro` (`'CADASTRO_COMPLETO_SIGPESQ'` vs. `'INFERIDO_DE_ORIENTACAO'`) e `flag_projeto_completo` (`0/1`).

---

### Problema 8 — Armadilha de grão em Produções (`qtd_producoes = 1` para autorias)
- **O que acontece:** O grão de `vfact_producao_cientifica_resolved` é **1 autoria** (`1.220` linhas para `1.175` obras distintas — `45` repetições por coautoria), mas a coluna se chama `1 AS qtd_producoes`, induzindo dupla contagem.
- **Solução lógica:** Renomear para `qtd_autorias` e criar `flag_obra_unica` (`ROW_NUMBER() OVER (PARTITION BY ap.id_producao ORDER BY ap.id_pessoa_lattes) = 1`, suportado nativamente no SQLite 3.25+).

---

### Problema 9 — Risco estrutural de *fan-out* (multiplicação de linhas) em Extensão
- **O que acontece:** `vfact_extensao_acao_resolved` e `vfact_extensao_participacao_resolved` fazem `LEFT JOIN` direto com `acao_campus` e `fomento_acao` (relações N:N). Múltiplos campi ou múltiplos fomentos multiplicariam ações e participações.
- **Solução lógica:** Pré-agregar `acao_campus` e `fomento_acao` por `id_acao` em subqueries com `GROUP_CONCAT(..., '; ')` antes do `JOIN`.

---

### Problema 10 — Grupos exclusivos do SigPesq ocultados e cálculo negativo de permanência
- **O que acontece em `vfact_grupo_pesquisa_membro_resolved`:**
  1. `FROM membro_grupo_cnpq INNER JOIN grupo_pesquisa_cnpq` deixa **`6` dos `353` grupos do SigPesq** fora da fato.
  2. O cálculo de dias sem guarda gera **`7` valores negativos** (`tempo_participacao_dias < 0`) quando `data_fim < data_inicio` no DGP.
- **Solução lógica (SQLite):** Calcular dias usando `CAST(julianday(COALESCE(mg.data_fim, date('now'))) - julianday(mg.data_inicio) AS INTEGER)` apenas quando `COALESCE(mg.data_fim, date('now')) >= mg.data_inicio` (retornando `NULL` caso contrário), e avaliar inclusão dos grupos sem espelho CNPq em ciclos pós-MVP.

---

### Problema 11 — Travas fixas de contagem e dialeto SQL incompatível com SQLite
- **O que acontece:**
  1. Scripts/testes antigos (`tests.py`) travavam contagens fixas (`6741`, `1232`, `553`) que quebram a cada nova extração.
  2. As views originais de `PropostaFatos.md` usam sintaxes incompatíveis com SQLite (`unificado.`, `::TEXT`, `::INTEGER`, `EXTRACT(YEAR FROM ...)`, `ILIKE`, `STRING_AGG`, `LEAST`/`GREATEST`, e `data_fim - data_inicio` — que em SQLite subtrai apenas o ano como inteiro em vez de retornar dias!).
- **Solução lógica:** Reescrever todas as 6 definições em SQLite padrão (ver [PropostaFatosV2.md](PropostaFatosV2.md)), alinhar `sql_security.py` + `rules.md` + `examples.json` para o dialeto `sqlite` (com suporte da transpilação via `sqlglot` prevista na ADR-0001) e validar o `dados.db` estruturalmente em `core/tests.py`.

---

### Problema 12 — Assimetria geográfica e lacunas de dimensões úteis no `dados.db`
- **O que acontece:** SRC está 100% em Serra (`207`); SigPesq é 98% Serra; CNPq traz todo o IFES (`347` grupos); Lattes traz `11` CVs específicos. Além disso, tabelas já existentes no modelo unificado como `membro_equipe_execucao_src` (`2.461`), `linha_pesquisa` (`1.266`/`1.310`), `participacao_pesquisador_projeto` (`294`), `participacao_estudante_projeto` (`279`), `fomento_projeto` (`152`) e `projeto_lattes` (`173`) ficam reservadas para evolução pós-MVP.
- **Solução lógica:** Explicitar o escopo geográfico nas regras do contexto (ou ampliar a extração do SRC para todos os campi) e incorporar as dimensões extras seletivamente após estabilizar o MVP das 6 fatos.

---

## 4. Decisão sobre as ~85 Tabelas na Arquitetura 100% SQLite (`dados.db`)

- **No banco `dados.db`:** o script Python único cria e popula o schema relacional necessário diretamente com `sqlite3` (sem Docker/Postgres/JSON intermediário) e materializa/expõe as **6 fatos (`vfact_*_resolved`)**.
- **Para o Oráculo (`ReadPolicy` + `views.json`):** o agente e o Explorador continuam acessando **exclusivamente as 6 fatos** (nunca as ~85 tabelas 3FN cruas), mantendo baixo risco de alucinação de SQL, proteção LGPD (`email`/`telefone`/`fax` ausentes) e latência < 10 ms em SQLite.

---

## 5. Ordem Recomendada de Aplicação (Alinhada à ADR-0001)

1. **DDL & Domínios SQLite:** definir schema SQLite equivalente sem `ENUM`s fechados incompletos (`pivic`, `pibic_em`, `jtc`, `picti`, `'EXCLUIDO'`, etc.) e `patente_registro.id_instituicao_depositante` anulável.
2. **Gerador Python Único (`sqlite3` → `Adito/app/data/dados.db`):** preservar campus IFES no pesquisador (P1), gravar patentes (P5), mapear `'EXCLUIDO'` (P3) e materializar/criar as 6 fatos da [PropostaFatosV2.md](PropostaFatosV2.md).
3. **Backend, Contexto e Testes (`datastore.py`, `sql_security.py`, `pesquisa-extensao-ifes/`, `core/tests.py`):** apontar leitura `read-only` para `dados.db`, dialeto `sqlite`, atualizar `views.json`/`rules.md`/`examples.json` e validar `manage.py test core` sem travas fixas.
