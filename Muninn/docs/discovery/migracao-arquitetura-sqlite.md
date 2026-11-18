> **Nota:** documento histórico. O projeto se chamava Adito na época; o nome atual é Muninn (ver `Docs/ADR/ADR-0005-nome-muninn.md`). O texto abaixo não foi reescrito.

# Discovery — Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)

**Status:** PROBLEM_READY  
**Classificação de Processo:** NORMAL PROCESS  
**Origem:** híbrido (diretriz de produto e refinamento arquitetural)  

---

## Intent

Unificar e simplificar radicalmente a pipeline de dados e o banco analítico do Adito, migrando para **100% SQLite (`dados.db`)**. A iniciativa elimina as dependências externas pesadas de infraestrutura (**Docker, PostgreSQL e DuckDB**) e a etapa intermediária de exportação de múltiplos arquivos JSON. O ETL passa a gerar diretamente o banco SQLite contendo tanto as **42 tabelas relacionais em 3FN** (derivadas do `ModeloClassesUnificado.asta`) quanto as **6 tabelas fato materializadas** com todas as correções de negócio aplicadas.

---

## Problem

Atualmente, o processo de carga e consulta de dados analíticos do Adito sofre de complexidade arquitetural excessiva e atrito operacional para uma aplicação desktop local:
1. **Sobrecarga de Infraestrutura:** Exige execução de um container Docker com PostgreSQL apenas para rodar scripts SQL relacionais locais, gerando dependência externa desnecessária.
2. **Gargalo no Pipeline ETL:** O fluxo atual é fragmentado em múltiplos estágios desconectados (`PostgreSQL em Docker` → `popular_banco.py via psql` → `exportar_json.py` gerando dezenas de JSONs em disco → `gerar_duckdb.py` lendo JSONs para montar `dados.duckdb`).
3. **Complexidade de Dependência (DuckDB):** Para um volume de dados acadêmicos consolidado de ~27.000 registros relacionais e ~10.000 linhas de fatos (~4 MB total), o uso de DuckDB adiciona peso de dependência binária sem oferecer ganhos perceptíveis de latência em relação ao SQLite nativo (ambos respondem em < 10 ms).
4. **Acoplamento de Drivers:** A convivência de dois motores analíticos/operacionais distintos (PostgreSQL/DuckDB para dados e SQLite para `app.db`) fragmenta a governança de queries, tipos e segurança.

---

## Users / Stakeholders Relevantes

- **Desenvolvedores do Adito:** Configuração simplificada de ambiente (`zero-setup`, sem necessidade de Docker ou serviços externos de banco).
- **Usuários Finais da Aplicação Desktop (Tauri):** Execução do aplicativo local totalmente autocontida, mais leve, com inicialização instantânea e menor consumo de memória/disco.
- **Agente de BI (LLM) e Sistema de Contextos:** Consultas analíticas seguras, rápidas e padronizadas em dialeto SQLite nativo sobre as tabelas fato materializadas (`vfact_*_resolved`), com suporte a buscas textuais acentuadas e case-insensitive transparentes.
- **Engenharia de Dados / Mantenedores do ETL:** Manutenção de um pipeline direto, unificado e determinístico em Python padrão (`sqlite3`).

---

## Current Situation

- Camada relacional legada em PostgreSQL 16 (executado via `Adito/scripts/docker-compose.yml` e scripts shell `recriar_banco.sh`).
- Carga de dados realizada por `Adito/scripts/popular_banco.py` via `psql`.
- Exportação para arquivos JSON desacoplados por `Adito/scripts/exportar_json.py`.
- Criação do banco analítico `dados.duckdb` por `Adito/scripts/gerar_duckdb.py` via DuckDB Python.
- Backend do Adito (`Adito/app/backend/nucleo/`) abre `dados.duckdb` via driver DuckDB em modo somente-leitura.
- As definições SQL das fatos estavam no documento conceitual `Docs/Fatos/PropostaFatos.md`.

---

## Desired Outcome

1. **Pipeline de Carga Direta em Python (`popular_banco.py` / `adito-etl`):** O script executa localmente via biblioteca padrão `sqlite3`, cria a estrutura das 42 tabelas base, insere os dados acadêmicos consolidados, executa o DDL dedicado `04_fatos_views.sql` e materializa as 6 tabelas fato como `TABLE` dentro de `Adito/app/data/dados.db` (ou no diretório configurado via `ORACULO_DATA_DIR`).
2. **Governança de Dados no `dados.db`:**
   - 42 tabelas base em 3FN do `ModeloClassesUnificado.asta` com integridade referencial estrita (`PRAGMA foreign_keys = ON`), constraints `CHECK`, domínios ampliados (`pivic`, `pibic_em`, `jtc`, `picti`, `'EXCLUIDO'`, etc.), `patente_registro.id_instituicao_depositante` anulável e estratégia de herança íntegra.
   - 6 tabelas fato materializadas (`vfact_extensao_acao_resolved`, `vfact_extensao_participacao_resolved`, `vfact_projeto_pesquisa_resolved`, `vfact_orientacao_bolsa_resolved`, `vfact_producao_cientifica_resolved`, `vfact_grupo_pesquisa_membro_resolved`) conforme a especificação formal `Docs/Fatos/PropostaFatosV2.md` e o diagnóstico `Docs/Fatos/DocumentoSolucionalFatos.md`, aplicando integralmente as correções P1 a P12.
   - Validação automatizada pós-carga: `foreign_key_check`, varredura anti-PII (bloqueio de CPF/e-mails expostos) e conferência estrutural de volumetria.
3. **Núcleo do Backend Autocontido e Seguro:**
   - `core/datastore.py` utiliza exclusivamente `sqlite3` conectando via URI somente-leitura (`file:dados.db?mode=ro`).
   - Implementação de `conn.set_authorizer(...)` para garantir que apenas comandos `SELECT` nas 6 tabelas fato sejam executados, bloqueando comandos de escrita, `ATTACH`, `PRAGMA` indevidos ou acesso às tabelas base.
   - Registro de função Python customizada `LIKE` insensível a maiúsculas/minúsculas e **insensível a acentos** via `unicodedata.normalize('NFD')`.
   - Transpilação resiliente de queries SQL do agente de BI via `sqlglot` (`read="duckdb"`, `write="sqlite"`), garantindo retrocompatibilidade caso o LLM gere funções como `ILIKE` ou `EXTRACT`.
4. **Remoção de Débitos Técnicos:** Exclusão definitiva de Docker Compose, scripts shell do Postgres, scripts de JSON, script gerador de DuckDB e dependência do `duckdb` no `requirements.txt`.

---

## Success Criteria

- [ ] Execução do script `popular_banco.py` (ou `adito-etl`) gera o arquivo `dados.db` íntegro em menos de 5 segundos, sem dependência de containers ou serviços externos.
- [ ] `dados.db` contém as 42 tabelas relacionais em 3FN e as 6 tabelas fato como `VIEW`s relacionais dinâmicas (OLTP), com tamanho total estimado entre 4 MB e 8 MB.
- [ ] Validações de integridade passam com 100% de conformidade: `PRAGMA foreign_key_check` sem violações, 0 violações de PII (CPFs e e-mails não expostos) e contagens de linhas correspondentes aos dados de origem.
- [ ] As correções de negócio P1 a P12 de `Docs/Fatos/PropostaFatosV2.md` são validadas com sucesso:
  1. **P1 (`campus` vs `instituicao_vinculo`):** `0` ocorrências de `'FAPES'` ou `'UFES'` na coluna `campus` de produções; apenas campi oficiais do Ifes ou `'Externo / Não Vinculado'`, expondo a instituição de lotação em `instituicao_vinculo`.
  2. **P2 (`flag_lider`):** `SUM(flag_lider) > 0`, identificando líderes via `lideranca_grupo_pesquisa` e `papel_membro LIKE '%lider%'`.
  3. **P3 (Domínios completos):** `0` ocorrências válidas de `PIVIC`/`PIBIC-EM`/`JTC`/`PICTI` caindo em `'Não Especificado'` e `0` registros com `situacao_grupo IS NULL` por motivo `'Excluído'`.
  4. **P4 (Investimento efetivo em bolsas):** Bolsas canceladas antes de `data_fim` calculam investimento e duração efetiva até `data_cancelado`, expondo `duracao_meses_efetiva` e `investimento_previsto_original`.
  5. **P5 (Patentes e Softwares Lattes):** `patente_registro.id_instituicao_depositante` anulável, populando patentes do Lattes e distinguindo `flag_patente_software` e `flag_software_sem_patente`.
  6. **P6 (`parceiros_demandantes`):** Exposta em `vfact_projeto_pesquisa_resolved` agregando parceiros via `GROUP_CONCAT`.
  7. **P7 (`origem_registro` e `flag_projeto_completo`):** Distinção clara entre `CADASTRO_COMPLETO_SIGPESQ` e `INFERIDO_DE_ORIENTACAO`.
  8. **P8 (Grão de Produção):** Coluna renomeada para `qtd_autorias` e adição de `flag_obra_unica` (`SUM(flag_obra_unica) == COUNT(DISTINCT id_producao)`).
  9. **P9 (Anti-Fan-Out em Extensão):** `COUNT(*) == COUNT(DISTINCT pk)` em ações e participações com pré-agregação de campi e fomentos.
  10. **P10 (Permanência em Grupos CNPq):** `0` registros com `tempo_participacao_dias < 0` via `julianday()` protegido.
  11. **P11 (Dialeto SQLite e Testes Estruturais):** Todas as 6 fatos em dialeto SQLite nativo e remoção de travas fixas rígidas em testes.
  12. **P12 (Contexto Geográfico):** Regras de negócio explicitam assimetrias geográficas de amostragem.
- [ ] Consultas analíticas executadas pelo núcleo em `dados.db` retornam latência inferior a 10 ms.
- [ ] Busca por texto com ou sem acentos (ex: `'Mecatronica'` vs `'Mecatrônica'`, `'Vitoria'` vs `'Vitória'`) funciona de forma transparente e idêntica via `LIKE`.
- [ ] Suite completa de testes automatizados executa e passa com 100% de sucesso sem `duckdb` instalado.

---

## Scope

### IN

- **Modelagem Relacional (DDL 00 a 03):** Adequação dos scripts DDL em `Adito/scripts/sql/` para sintaxe SQLite, mantendo apenas as 42 tabelas do `ModeloClassesUnificado.asta` que alimentam as fatos.
- **DDL das Fatos (04):** Criação de `Adito/scripts/sql/04_fatos_views.sql` contendo o DDL das 6 fatos em SQLite com as 5 correções de negócio.
- **Pipeline ETL (`popular_banco.py` e `Adito/etl/`):**
  - Adaptação para conectar em SQLite, rodar DDLs 01..03, popular 42 tabelas base, executar `04_fatos_views.sql`, materializar fatos como `TABLE` e validar integridade/PII.
  - Atualização da CLI `adito-etl` e script de visualização `ver_dados.py`.
- **Backend Núcleo (`Adito/app/backend/nucleo/`):**
  - Substituição de `duckdb` por `sqlite3` em `core/datastore.py`.
  - Configuração de URI somente-leitura (`file:dados.db?mode=ro`).
  - Implementação de `authorizer` de segurança em nível de conexão SQLite.
  - Registro de função customizada de `LIKE` sem acentos (Unicode NFD).
  - Transpilação de SQL com `sqlglot` (`duckdb` -> `sqlite`).
  - Adaptação de `contexts.py` (introspecção de schema via `PRAGMA table_info`), `rpc/dashboard.py` e `rpc/explorer.py`.
  - Atualização dos metadados do contexto acadêmico (`views.json`, `rules.md`, `examples.json`).
- **Limpeza e Descomissionamento:** Remoção de `docker-compose.yml`, `recriar_banco.sh`, `exportar_json.py`, `gerar_duckdb.py`, `test_exportar_json.py`, `dados.duckdb` e remoção de `duckdb` do `requirements.txt`.
- **Governança Técnica:**
  - Atualização da especificação técnica `Adito/docs/specs/especificacao_ddl_unificado.md`.
  - Elaboração de ADRs na pasta `docs/adr/` seguindo o template do projeto:
    - `ADR-0001: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)`
    - `ADR-0002: Separação Arquitetural entre Banco Analítico (dados.db) e Banco Operacional (app.db)`
    - `ADR-0003: Modelagem em Camadas no SQLite (42 Tabelas Base 3FN e 6 Fatos Materializadas)`
    - `ADR-0004: Estratégia de Segurança e Resiliência de Consultas SQL (Authorizer, Custom LIKE e sqlglot)`

### OUT

- Modificações estruturais no banco de estado da aplicação (`app.db` gerenciando usuários locais, conversas, RAG e checkpoints LangGraph).
- Inclusão das 43 tabelas do diagrama `ModeloClassesUnificado.asta` que não participam da geração das 6 fatos.
- Alterações em interfaces visuais do frontend Tauri/Vue (a camada RPC mantém retrocompatibilidade de payload).

### LATER

- Mecanismos de atualização diferencial / incremental de dados (a carga atual permanece como recriação batch completa).
- Compressão de páginas SQLite (ex: `PRAGMA page_size`, compressão externa de distribuição) caso o volume futuro ultrapasse dezenas de megabytes.

---

## Constraints / Feasibility

- **Runtime Padronizado:** O `sqlite3` é biblioteca padrão do Python 3.10+, não exigindo drivers C binários externos ou compilação nativa adicional.
- **Estritamente Read-Only em Execução:** O aplicativo desktop nunca deve abrir `dados.db` para escrita. A conexão deve falhar imediatamente caso haja tentativa de mutação no arquivo acadêmico (`file:dados.db?mode=ro`).
- **Performance Analítica:** O volume atual (~4 MB) cabe inteiramente no cache de páginas do SO e do SQLite, garantindo que junções e filtros sobre as tabelas materializadas rodem em frações de milissegundo.

---

## Assumptions

- `[ASSUMPTION]` O volume de dados acadêmicos do IFES continuará na faixa de dezenas a centenas de milhares de registros, escala onde SQLite opera com excelente desempenho analítico.
- `[ASSUMPTION]` O arquivo gerado `dados.db` (~4 a 8 MB) é suficientemente pequeno para ser versionado, gerado localmente em segundos ou distribuído junto ao instalador do Adito.
- `[ASSUMPTION]` As 42 tabelas base selecionadas contêm todos os dados necessários para suprir as 6 fatos e eventuais consultas complementares de auditoria.

---

## Risks

| Risco | Impacto | Mitigação |
|---|---|---|
| O agente de BI gerar SQL com funções específicas do DuckDB (`ILIKE`, `::TYPE`, `EXTRACT`) | Médio | Transpilação transparente em tempo de execução via `sqlglot` (`duckdb` -> `sqlite`) e atualização de regras no prompt do agente (`rules.md`). |
| Incompatibilidade de busca textual com acentos na língua portuguesa no `LIKE` padrão do SQLite | Alto | Registro de função Python customizada `LIKE` utilizando normalização Unicode (`unicodedata.normalize('NFD')`) e `.casefold()`. |
| LLM tentar executar comandos de escrita ou acessar tabelas base não autorizadas | Crítico | Configuração estrita de `sqlite3.Connection.set_authorizer` permitindo apenas `SQLITE_SELECT` e `SQLITE_READ` nas 6 tabelas `vfact_*_resolved`. |
| Concorrência de leitura com múltiplos componentes locais | Baixo | `dados.db` aberto como `mode=ro` permite conexões de leitura simultâneas ilimitadas sem contenção de lock. |

---

## Open Questions

- *Nenhuma pergunta bloqueante em aberto no momento.* As 5 regras de negócio e os parâmetros de migração foram amplamente discutidos e especificados.

---

## Review & Adjust

- [x] Usuário revisou a proposta completa de Discovery
- [x] Alterações solicitadas foram incorporadas
- [x] Decisões arquiteturais e escopo de tabelas (42 base + 6 fatos) confirmados
- [x] Não existem perguntas bloqueantes abertas

### User Adjustments
- Usuário revisou o Checkpoint D1 e autorizou o avanço ("prossiga"), aprovando escopo, critérios de sucesso e diretrizes de migração para o Gate G0.

---

## Gate G0 — PROBLEM READY

**Status:** APPROVED  
**Aprovado pelo usuário:** sim  
