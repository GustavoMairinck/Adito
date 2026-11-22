> **Nota:** documento histórico. O projeto se chamava Adito na época; depois o nome passou a Adito e voltou a Adito (ver `Docs/ADR/ADR-0008-volta-ao-nome-adito.md`). O texto abaixo não foi reescrito.

# Requirements — Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)

**Status:** REQUIREMENTS_READY  
**Discovery de origem:** [docs/discovery/migracao-arquitetura-sqlite.md](file:///home/andre/test_adito/docs/discovery/migracao-arquitetura-sqlite.md)  
**Classificação de Processo:** NORMAL PROCESS  

---

## Intent Summary

Substituir completamente a pilha heterogênea de dados (PostgreSQL/Docker + exportação de JSONs intermediários + DuckDB) por um pipeline unificado e autocontido em **100% SQLite (`dados.db`)**. O novo banco analítico conterá as **42 tabelas relacionais em 3FN** do `ModeloClassesUnificado.asta` que servem de base para o domínio acadêmico e as **6 tabelas fato como `VIEW`s relacionais dinâmicas (OLTP)**, incorporando as 5 correções de negócio acordadas. O backend núcleo passará a consumir `dados.db` em modo estritamente somente-leitura com proteção por autorizador de segurança, suporte a buscas textuais sem acento e transpilação de queries via `sqlglot`.

---

## Functional Requirements

- **FR01 (DDL 3FN em SQLite com Domínios Completos):** O sistema deve fornecer scripts DDL em sintaxe SQLite (`Adito/scripts/sql/01_tabelas_core.sql` a `03`) definindo as 42 tabelas relacionais em 3FN do `ModeloClassesUnificado.asta` que alimentam as 6 fatos, incluindo integridade referencial (`FOREIGN KEY`), `patente_registro.id_instituicao_depositante` anulável e tabelas de domínio / restrições `CHECK` completas (incorporando `'pivic'`, `'pibic_em'`, `'jtc'`, `'picti'` em programa; `'EXCLUIDO'` em situação de grupo; `'ENSINO_FUNDAMENTAL'` em nível de treinamento; e `'FINANCIAMENTO'` em tipo de apoio).
- **FR02 (DDL Fatos em SQLite v2.0):** O sistema deve fornecer um script DDL dedicado (`Adito/scripts/sql/04_fatos_views.sql`) contendo a definição em dialeto SQLite das 6 tabelas fato analíticas em conformidade estrita com `Docs/Fatos/PropostaFatosV2.md`.
- **FR03 (Fatos como VIEWs Relacionais Dinâmicas):** O sistema deve definir as 6 fatos analíticas como `VIEW`s relacionais nativas (`CREATE VIEW vfact_*_resolved AS SELECT ...`) diretamente sobre as 42 tabelas base relacionais em 3FN, garantindo sincronização transacional imediata (OLTP) e verdade única sem duplicação física de dados em disco.
- **FR04 (Correção P2: Liderança CNPq):** A fato `vfact_grupo_pesquisa_membro_resolved` deve calcular `flag_lider = 1` quando houver registro em `lideranca_grupo_pesquisa` ou quando `papel_membro` indicar liderança (`LOWER(pap.nome) LIKE '%lider%'`), sem duplicar linhas.
- **FR05 (Correção P5: Patentes e Softwares):** A carga deve persistir patentes e softwares registrados do Lattes (graças ao campo depositante anulável) e a fato `vfact_producao_cientifica_resolved` deve expor `flag_patente_software` (para patentes registradas) e `flag_software_sem_patente` (para produções técnicas de software sem patente).
- **FR06 (Correção P1 e P8: Vínculo Institucional e Grão em Produção):** A fato `vfact_producao_cientifica_resolved` deve preencher `campus` exclusivamente com campi reais do Ifes (`'Externo / Não Vinculado'` caso contrário), expor `instituicao_vinculo`, renomear a métrica de contagem para `qtd_autorias` e disponibilizar `flag_obra_unica` (`ROW_NUMBER() OVER (...) = 1`).
- **FR07 (Correção P7: Identificação de Origem em Projetos):** A fato `vfact_projeto_pesquisa_resolved` deve classificar a integridade do registro através de `origem_registro` (`'CADASTRO_COMPLETO_SIGPESQ'` vs. `'INFERIDO_DE_ORIENTACAO'`) e expor a métrica `flag_projeto_completo` (`1/0`).
- **FR08 (Correção P6 e P9: Parceiros Demandantes e Blindagem Anti-Fan-Out):** A fato `vfact_projeto_pesquisa_resolved` deve expor a dimensão agregada `parceiros_demandantes` (via subquery com `GROUP_CONCAT`), e as fatos de extensão (`vfact_extensao_acao_resolved` e `vfact_extensao_participacao_resolved`) devem pré-agregar `acao_campus` e `fomento_acao` impedindo qualquer duplicação de grão (*fan-out*).
- **FR09 (Correção P4: Cálculo Efetivo de Bolsas com Cancelamento):** A fato `vfact_orientacao_bolsa_resolved` deve calcular `duracao_meses_efetiva` e `investimento_total_estimado` com base no tempo real decorrido até `data_cancelado` para bolsas desligadas antes do fim previsto, expondo adicionalmente `investimento_previsto_original`.
- **FR10 (Correção P10: Guarda de Permanência em Grupos):** A fato `vfact_grupo_pesquisa_membro_resolved` deve calcular `tempo_participacao_dias` via `julianday()`, retornando `NULL` e blindando contra valores negativos quando `data_fim < data_inicio`.
- **FR11 (Carga Direta em Python/SQLite):** O script `popular_banco.py` (e o comando `adito-etl popular-banco`) deve executar em Python nativo usando a biblioteca `sqlite3`, priorizando campus Ifes sobre agências de fomento (`FAPES`/`CNPq`), criando a estrutura, inserindo os dados nas 42 tabelas base e criando as 6 fatos como `VIEW`s relacionais dinâmicas em `Adito/app/data/dados.db`.
- **FR12 (Validação Automatizada Estrutural):** O pipeline de carga deve executar checagem de chaves estrangeiras (`PRAGMA foreign_key_check`), varredura anti-PII (bloqueando dados de CPF ou e-mails em colunas públicas) e conferência de integridade estrutural das 42 tabelas e 6 fatos (substituindo travas de contagens fixas rígidas por validações de sanidade).
- **FR13 (Conexão Somente-Leitura no Núcleo):** O componente `core/datastore.py` do backend núcleo deve abrir `dados.db` estritamente com a URI `file:dados.db?mode=ro`, impedindo qualquer mutação no arquivo de dados.
- **FR14 (Transpilação de Queries via sqlglot):** O backend núcleo deve interceptar queries geradas pelo agente de BI e transpilar automaticamente dialetos analíticos (`sqlglot.transpile(sql, read="duckdb", write="sqlite")`), assegurando compatibilidade com sintaxes como `ILIKE`, `::TYPE` ou `EXTRACT`.
- **FR15 (Busca Textual Acentuada Customizada):** O backend núcleo deve registrar uma função Python customizada `LIKE` na conexão SQLite (`conn.create_function("like", 2, ...)`), garantindo que comparações textuais sejam insensíveis a maiúsculas/minúsculas e a acentuação gráfica da língua portuguesa via normalização Unicode NFD.
- **FR16 (Autorizador de Segurança em SQLite):** O backend núcleo deve configurar `conn.set_authorizer(...)` para autorizar exclusivamente operações `SQLITE_SELECT` e `SQLITE_READ` restritas às 6 tabelas fato materializadas, bloqueando comandos de modificação, `ATTACH` e leitura de tabelas base não expostas.
- **FR17 (Introspecção de Metadados e RPC):** Os módulos `contexts.py` (introspecção de schema com `PRAGMA table_info`), `rpc/dashboard.py` e `rpc/explorer.py` devem ser adaptados para executar sobre SQLite sem depender de sintaxes proprietárias do DuckDB.
- **FR18 (Atualização de Metadados de Contexto v2.0):** O contexto acadêmico (`views.json`, `rules.md` e `examples.json`) deve ser atualizado para refletir o dialeto SQLite e a documentação formal da v2.0 (novos campos como `qtd_autorias`, `flag_obra_unica`, `flag_software_sem_patente`, `instituicao_vinculo`, `parceiros_demandantes`, `flag_projeto_completo`, `duracao_meses_efetiva`).
- **FR19 (Descomissionamento de Legados):** Os arquivos obsoletos `docker-compose.yml`, `recriar_banco.sh`, `exportar_json.py`, `gerar_duckdb.py`, `test_exportar_json.py` e arquivos gerados em `saida/json/` e `dados.duckdb` devem ser removidos, e a dependência `duckdb` deve ser expurgada do `Adito/app/backend/requirements.txt`.

---

## Business / Domain Rules

- **BR01 (Integridade de Herança e Domínios Ampliados):** As 42 tabelas base devem respeitar a integridade referencial do modelo unificado; chaves primárias em subclasses de entidades (ex: `pesquisador`, `docente`) devem referenciar a superclasse (`pessoa`) com `ON DELETE CASCADE`. As listas de domínios devem incluir expressamente `'pivic'`, `'pibic_em'`, `'jtc'`, `'picti'`, `'EXCLUIDO'`, `'ENSINO_FUNDAMENTAL'` e `'FINANCIAMENTO'`. `patente_registro.id_instituicao_depositante` deve ser anulável.
- **BR02 (Semântica da Liderança de Grupo CNPq):** Um membro de grupo de pesquisa possui `flag_lider = 1` se constar na tabela `lideranca_grupo_pesquisa` para o respectivo grupo ou se o nome do papel contiver termo de liderança (`%lider%`); caso contrário, `flag_lider = 0`.
- **BR03 (Identificação de Softwares e Patentes):** Patentes registradas e softwares patenteados possuem `flag_patente_software = 1`. Softwares sem patente classificados em produções técnicas possuem `flag_software_sem_patente = 1`.
- **BR04 (Segregação de Campus e Instituição de Lotação):** A coluna `campus` na fato de produção científica só contém campi oficiais do Ifes (`org.id_organizacao_pai IS NOT NULL`); pesquisadores externos ou de órgãos centrais sem campus recebem `'Externo / Não Vinculado'` e sua instituição em `instituicao_vinculo`. Agências de fomento (`FAPES`, `CNPq`) nunca devem ser atribuídas como organização de lotação.
- **BR05 (Preenchimento e Origem de Projetos):** A fato de projetos de pesquisa diferencia explicitamente o cadastro completo (`origem_registro = 'CADASTRO_COMPLETO_SIGPESQ'`, `flag_projeto_completo = 1`) dos projetos inferidos de orientação (`origem_registro = 'INFERIDO_DE_ORIENTACAO'`, `flag_projeto_completo = 0`). Campos sem correspondência recebem 'Não Informado' / 'Não Informada'.
- **BR06 (Preservação de Grão e Métricas de Obra Única):**
  - Relações N:N (campi e fomento em extensão, parceiros demandantes em projetos) são agregadas via `GROUP_CONCAT(..., '; ')` antes do join, impedindo duplicação de linhas.
  - O grão de produção científica é **1 autoria** (`qtd_autorias = 1`); para contabilização de obras únicas sem dupla contagem por coautoria, utiliza-se `flag_obra_unica` (`SUM(flag_obra_unica) == COUNT(DISTINCT id_producao)`).
- **BR07 (Cálculo Financeiro Efetivo de Bolsas):** Em `vfact_orientacao_bolsa_resolved`, bolsas com `cancelado = 1` e `data_cancelado IS NOT NULL` calculam `duracao_meses_efetiva` e `investimento_total_estimado` limitados à data de cancelamento, permitindo comparação transparente com `investimento_previsto_original`.
- **BR08 (Proteção e Privacidade de Dados - Anti-PII):** Nenhuma tabela fato exposta ao agente de BI ou ao usuário final pode conter dados de identificação pessoal restrita, como CPF não mascarado, endereço residencial ou e-mail pessoal.

---

## Non-Functional Requirements

- **NFR01 (Tempo de Execução do ETL):** A geração completa do banco `dados.db` (criação de schema, carga das 42 tabelas base, criação das 6 fatos como VIEWs dinâmicas e validações) deve executar em tempo inferior a **5 segundos** em ambiente de desenvolvimento comum.
- **NFR02 (Latência de Consulta Analítica):** Consultas analíticas executadas pelo backend núcleo sobre qualquer uma das 6 tabelas fato materializadas no `dados.db` devem ter latência de execução no SQLite inferior a **10 milissegundos**.
- **NFR03 (Segurança e Imutabilidade em Runtime):** O backend núcleo da aplicação desktop deve garantir imutabilidade estrita do banco `dados.db` em tempo de execução através de:
  1. Conexão SQLite URI com flag `mode=ro`;
  2. `conn.set_authorizer` bloqueando qualquer operação de mutação (`INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `ATTACH`).
- **NFR04 (Integridade Referencial Estrita):** O banco de dados deve manter `PRAGMA foreign_keys = ON` habilitado e garantir 0 violações em `PRAGMA foreign_key_check`.
- **NFR05 (Zero Dependências Externas de Infraestrutura):** A execução da carga e do aplicativo deve ser totalmente independente de Docker, serviços PostgreSQL em rede ou utilitários externos de compilação C.
- **NFR06 (Portabilidade Multiplataforma):** O arquivo gerado `dados.db` deve ser estritamente binário-compatível e idêntico em sistemas Linux, Windows e macOS.
- **NFR07 (Pegada de Armazenamento Reduzida):** O tamanho total do arquivo `dados.db` contendo todas as 42 tabelas base indexadas e as 6 fatos como VIEWs dinâmicas deve permanecer entre **4 MB e 8 MB**.

---

## User Scenarios

### Main Flow: Carga de Dados e Inicialização Autocontida
1. O desenvolvedor ou o empacotador da aplicação executa o comando `python scripts/popular_banco.py` (ou `adito-etl popular-banco`).
2. O script conecta-se diretamente ao SQLite, cria as 42 tabelas em 3FN, insere a massa de dados acadêmicos estruturados e executa o script `04_fatos_views.sql`.
3. As 6 tabelas fato são como `VIEW`s relacionais dinâmicas (OLTP).
4. O script executa varreduras de integridade referencial, anti-PII e contagens, exibindo relatório com 100% de sucesso.
5. O aplicativo desktop do Adito inicializa, abre `dados.db` via URI somente-leitura em milissegundos e disponibiliza o agente de BI.

### Main Flow: Consulta Analítica do Usuário com Resiliência Linguística
1. O usuário solicita no chat: *"Quais os projetos de pesquisa da área de Mecatrônica desenvolvidos no campus Vitória?"*.
2. O agente de BI formula uma consulta SQL analítica utilizando a fato `vfact_projeto_pesquisa_resolved`.
3. Mesmo que o agente gere `WHERE campus LIKE '%Vitoria%'` (sem acento) ou utilize `ILIKE` em dialeto DuckDB:
   - A transpilação com `sqlglot` converte a query para sintaxe SQLite válida;
   - A função Python customizada `LIKE` normaliza grafias com e sem acento e maiúsculas/minúsculas de forma transparente;
4. O datastore executa a query em < 5 ms e o agente devolve a resposta precisa ao usuário.

### Alternative / Error Case: Tentativa de Acesso Indevido ou Mutação
1. O agente de BI gera inadvertidamente ou sob injeção de prompt uma instrução de escrita (`UPDATE` / `DROP`) ou uma consulta a tabelas base não publicadas (ex: `SELECT * FROM pessoa`).
2. O autorizador SQLite (`set_authorizer`) intercepta a operação e aborta a execução retornando `sqlite3.DatabaseError: access denied`.
3. O datastore captura a falha de segurança de forma controlada, impedindo vazamento de dados ou corrupção do banco.

---

## Business / Domain Context

O domínio acadêmico do IFES consolida informações de quatro grandes fontes:
- **SIGPESQ:** Projetos de pesquisa, planos de trabalho e orientações de bolsas;
- **DGP / CNPq:** Grupos de pesquisa e pesquisadores cadastrados no diretório;
- **Lattes:** Produções bibliográficas, técnicas e científicas dos docentes e discentes;
- **SRC:** Ações de extensão e participações institucionais.

Esses quatro universos convergem nas **42 tabelas relacionais em 3FN** e são resumidos analiticamente nas **6 tabelas fato (`vfact_*_resolved`)**, que servem de interface oficial de consulta para a inteligência de negócios da aplicação.

---

## Technical Context & Constraints

- **Python Runtime:** Python 3.10+ utilizando `sqlite3` nativo da biblioteca padrão.
- **Biblioteca de Transpilação:** `sqlglot` para conversão de dialetos em tempo de execução sem degradação de performance.
- **Isolamento de Bancos de Dados:**
  - `app.db` (localizado em diretório de dados do usuário): banco SQLite read/write para estado local (conversas, mensagens, configurações, RAG e checkpoints).
  - `dados.db` (localizado em `Adito/app/data/dados.db` ou `ORACULO_DATA_DIR`): banco acadêmico read-only gerado pelo ETL.
- **Configurações de Pragmas do SQLite:**
  - Carga: `PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;`
  - Consulta: `PRAGMA query_only = ON; PRAGMA foreign_keys = ON;`

---

## Quality Attributes

- **Manutenibilidade:** Scripts DDL segmentados de forma lógica (01 a 03 para tabelas base, 04 para fatos como VIEWs dinâmicas), facilitando evolução e auditoria.
- **Auditabilidade e Governança:** Decisões arquiteturais registradas em ADRs individuais seguindo o template do projeto.
- **Segurança da Informação:** Blindagem dupla em nível de arquivo (`mode=ro`) e em nível de driver (`set_authorizer`).
- **Testabilidade:** Verificações estáticas e testes de integração executados sem necessidade de mocks de infraestrutura externa.

---

## Assumptions

- **A01:** O volume consolidado de dados acadêmicos do campus permanece perfeitamente dimensionado para execução in-process no SQLite com tempos de resposta instantâneos.
- **A02:** O arquivo gerado `dados.db` (~4 a 8 MB) é estático entre ciclos de atualização de dados (cargas batch) e não sofre concorrência de escrita local.
- **A03:** As 42 tabelas selecionadas cobrem 100% dos relacionamentos consumidos pelas 6 fatos, tornando seguro o descarte das 43 tabelas periféricas do ASTA.

---

## Out of Scope

- Modificações de schema ou lógica no banco de estado operacional `app.db`.
- Inclusão das 43 tabelas do diagrama ASTA não utilizadas pelas 6 fatos.
- Alterações nos componentes visuais do frontend Vue.js.
- Cargas incrementais em tempo real (manutenção de recarga batch completa).

---

## Open Questions

- *Nenhuma pergunta bloqueante em aberto.* Todos os critérios de negócio, cardinalidades e mitigações técnicas estão definidos e aprovados.

---

## Key Decisions Proposed

- **KD01:** Adoção de **100% SQLite (`dados.db`)** como motor único para dados relacionais e analíticos, eliminando Docker, PostgreSQL, JSON intermediário e DuckDB.
- **KD02:** **Separação física de bancos**: `dados.db` (somente-leitura com dados acadêmicos) e `app.db` (leitura e escrita para estado do aplicativo).
- **KD03:** **Definição das 6 fatos como `VIEW`s relacionais dinâmicas (OLTP)** dentro do próprio `dados.db`, garantindo que qualquer mutação transacional nas 42 tabelas base reflita imediatamente na camada analítica com zero redundância de armazenamento.
- **KD04:** **Camada de segurança e resiliência no Datastore**: proteção por URI somente-leitura, `conn.set_authorizer` estrito, busca textual acentuada via função Python customizada e transpilação automática de dialeto com `sqlglot`.

---

## Review & Adjust

O usuário pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes da consolidação do gate.

- [x] Proposta completa apresentada ao usuário
- [x] Ajustes solicitados incorporados (especificações P1 a P12 de DocumentoSolucionalFatos.md e PropostaFatosV2.md)
- [x] IDs estabilizados depois da revisão (FR01 a FR19, BR01 a BR08, NFR01 a NFR07)
- [x] Nenhuma pergunta bloqueante aberta

### User Adjustments
- Requisitos expandidos com base nos documentos `DocumentoSolucionalFatos.md` e `PropostaFatosV2.md` fornecidos pelo usuário, refinando métricas e dimensões de produções, bolsas, liderança, parceiros e domínios.
- Usuário aprovou expressamente o avanço ("prossiga"), consolidando o Gate G1 (REQUIREMENTS_READY).

---

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED  
**Aprovado pelo usuário:** sim  
