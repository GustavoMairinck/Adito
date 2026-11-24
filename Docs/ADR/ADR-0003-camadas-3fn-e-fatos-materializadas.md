> **Nota:** ADR escrita quando o projeto se chamava Adito. O nome passou a Adito e depois voltou a Adito; hoje as variáveis `ORACULO_*` citadas aqui são `ADITO_*` (ver [ADR-0008](ADR-0008-volta-ao-nome-adito.md)).

# ADR 0003: Modelagem Relacional OLTP no SQLite (82 Tabelas Base 3FN e 6 Fatos como VIEWs Dinâmicas)

**Status:** Aceito (revisado em 24/11/2026)  
**Data:** 18/11/2026 (revisão de escopo das tabelas base: 24/11/2026)  

## Contexto/Problema  
O modelo conceitual do projeto Adito (`ModeloClassesUnificado.asta`) define um diagrama relacional de 85 tabelas em 3FN. O agente de BI e as interfaces de visualização consomem dados analíticos consolidados de 6 dimensões de negócio (ações de extensão, participações em extensão, projetos de pesquisa, orientações e bolsas, produções científicas e membros de grupos de pesquisa).
Na revisão inicial desta ADR considerou-se manter apenas as 42 tabelas referenciadas diretamente pelas 6 views atuais, mas o pipeline ETL já extrai e carrega dados úteis de outras tabelas do modelo unificado (como projetos/orientações Lattes, bancas examinadoras, eventos científicos, formação acadêmica, atuação profissional e linhas de pesquisa) que interessam para futuras views analíticas. Por outro lado, 3 tabelas de contato (`email`, `fax`, `telefone`) nunca são populadas por política LGPD do ETL e permaneciam vazias no schema.
Precisamos decidir:
1. Qual subconjunto do modelo relacional deve ser preservado no SQLite (`dados.db`).
2. Como disponibilizar as 6 visões analíticas (`vfact_*_resolved`) no `dados.db`: se como tabelas físicas materializadas (estilo OLAP batch) ou como **`VIEW`s relacionais dinâmicas (estilo OLTP)** diretamente sobre as tabelas base.

## Decisão Tomada  
Adotaremos uma **arquitetura relacional estrita (OLTP)** dentro do arquivo `dados.db`:
1. **Camada Relacional Base (82 Tabelas em 3FN):** Manteremos fisicamente no SQLite as **82 tabelas** do `ModeloClassesUnificado.asta` relevantes ao domínio acadêmico — **removendo as 3 tabelas de contato/PII vazias (`email`, `fax`, `telefone`)** do conjunto original de 85 tabelas. A composição é:
   - **42 tabelas** consumidas diretamente pelas 6 views analíticas atuais (`04_fatos_views.sql`);
   - **2 tabelas** mantidas como dependências de chave estrangeira de `organizacao` (`endereco`, `tipo_organizacao`);
   - **38 tabelas** já populadas pelo ETL e preservadas para futuras views/fatos e auditoria (ex.: `projeto_lattes`, `orientacao_lattes`, `banca_examinadora`, `membro_banca_examinadora`, `evento_cientifico`, `participacao_evento`, `formacao_academica`, `atuacao_profissional`, `linha_pesquisa`, `grupo_pesquisa_linha_pesquisa`, `pesquisador_linha_pesquisa`, `membro_equipe_execucao_src`, `fomento_projeto`, `participacao_estudante_projeto`, `participacao_pesquisador_projeto`, entre outras).
   O DDL é segmentado em `01_tipos_e_dominios.sql` (14 tabelas), `02_tabelas.sql` (48 tabelas) e `03_relacionamentos_e_juncoes.sql` (20 tabelas), preservando tipagem, integridade de herança (chaves primárias com `REFERENCES superclasse(id) ON DELETE CASCADE`) e constraints `CHECK`.
2. **Camada de Fatos como VIEWs Dinâmicas (6 VIEWs):** As 6 fatos são definidas no script dedicado `04_fatos_views.sql` como **`CREATE VIEW vfact_*_resolved AS SELECT ...`** diretamente sobre as tabelas base, incorporando as correções de negócio P1 a P12 da especificação [Docs/Fatos/PropostaFatos.md](../Fatos/PropostaFatos.md). Nenhuma tabela fato física é duplicada em disco. Em runtime, o `set_authorizer` e a `ReadPolicy` continuam restringindo o acesso do agente de BI e do Explorador **exclusivamente às 6 views**.

## Justificativa  
1. **Verdade Única Transacional (Single Source of Truth):** Como as fatos são `VIEW`s dinâmicas, qualquer `INSERT`, `UPDATE` ou `DELETE` realizado transacionalmente (OLTP) nas tabelas base é refletido instantaneamente nas fatos em tempo de execução, sem necessidade de rotinas de recarga ou materialização em lote.
2. **Prontidão para Futuras Views sem Retrabalho de ETL:** Preservar as 38 tabelas acadêmicas já alimentadas pelo ETL (Lattes, bancas, eventos, formação, linhas de pesquisa, participações) permite criar novas views analíticas diretamente em SQL sobre `dados.db` sem reescrever DDL ou carga, mantendo o arquivo enxuto (~6–9 MB dependendo do recorte, inteiramente no cache do SO).
3. **Higiene LGPD no Schema:** Remover fisicamente `email`, `fax` e `telefone` elimina tabelas de dados de contato/PII que o ETL já descarta por política de privacidade e que nunca devem existir no banco distribuído.
4. **Desempenho Instantâneo e Zero Redundância:** Mesmo com 82 tabelas base (~40 mil registros no total), não há duplicação física de fatos e o query planner do SQLite resolve as queries sobre as 6 `VIEW`s em menos de 5 milissegundos com os índices B-Tree nas chaves estrangeiras.

## Alternativas Consideradas  
* **Materializar as Fatos como TABLE física (estilo OLAP estático):** Descartado para garantir a natureza transacional OLTP do banco e evitar redundância de dados e riscos de dessincronização entre as tabelas base e as fatos.
* **Reduzir estritamente às 42 tabelas consumidas pelas 6 views atuais:** Considerado na versão original de 18/11/2026 e descartado na revisão de 24/11/2026 porque descartaria dados acadêmicos já extraídos e validados pelo ETL (como Lattes, bancas e linhas de pesquisa) úteis para próximas views, com economia marginal de disco (~1 MB).
* **Manter as 85 tabelas completas do ASTA (incluindo `email`, `fax`, `telefone`):** Descartado porque essas 3 tabelas representam dados de contato/PII vazios e bloqueados pela política LGPD do projeto.
* **Armazenar apenas as 6 Fatos (sem tabelas base 3FN):** Descartado para preservar a capacidade de auditoria, rastreabilidade transacional e integridade formal com o modelo acadêmico do IFES.

## Consequências  
* **Positivas:** Modelo 100% transacional OLTP; sincronização em tempo real; zero dados duplicados; base pronta para novas views analíticas sem mexer na extração; remoção definitiva de tabelas de contato/PII vazias (`email`, `fax`, `telefone`); contrato de 82 tabelas verificado automaticamente em `test_ddl_sqlite.py` e `test_popular_banco_sqlite.py`.
* **Negativas:** O schema mantém 38 tabelas ainda não expostas em views (exigindo cuidado para que continuem bloqueadas ao LLM via `set_authorizer` e `ReadPolicy`, já coberto pelos testes de segurança).
* **Riscos:** Criação de queries pelo LLM que gerem planos de execução não indexados sobre as VIEWs (mitigado pelos índices nas chaves de junção) ou reintrodução acidental de tabelas PII (mitigado por assert explícito nos testes do ETL).

## Referências  
* [Docs/ModelosClasses/ModeloClassesUnificado.asta](../ModelosClasses/ModeloClassesUnificado.asta)
* [Docs/Fatos/PropostaFatos.md](../Fatos/PropostaFatos.md)
* [Adito/docs/specs/especificacao_resolucoes_fatos_v2.md](../../Adito/docs/specs/especificacao_resolucoes_fatos_v2.md)
* [ADR 0001: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)](ADR-0001-migracao-dados-100-sqlite.md)
