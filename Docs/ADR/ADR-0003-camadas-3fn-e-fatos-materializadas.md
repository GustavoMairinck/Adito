> **Nota:** ADR escrita quando o projeto se chamava Adito. O nome passou a Adito e depois voltou a Adito; hoje as variáveis `ORACULO_*` citadas aqui são `ADITO_*` (ver [ADR-0008](ADR-0008-volta-ao-nome-adito.md)).

# ADR 0003: Modelagem Relacional OLTP no SQLite (42 Tabelas Base 3FN e 6 Fatos como VIEWs Dinâmicas)

**Status:** Aceito  
**Data:** 18/11/2026  

## Contexto/Problema  
O modelo conceitual do projeto Adito (`ModeloClassesUnificado.asta`) define um diagrama relacional de 85 tabelas em 3FN. O agente de BI e as interfaces de visualização consomem dados analíticos consolidados de 6 dimensões de negócio (ações de extensão, participações em extensão, projetos de pesquisa, orientações e bolsas, produções científicas e membros de grupos de pesquisa).
Precisamos decidir:
1. Qual subconjunto do modelo relacional deve ser preservado no SQLite.
2. Como disponibilizar as 6 visões analíticas (`vfact_*_resolved`) no `dados.db`: se como tabelas físicas materializadas (estilo OLAP batch) ou como **`VIEW`s relacionais dinâmicas (estilo OLTP)** diretamente sobre as tabelas base.

## Decisão Tomada  
Adotaremos uma **arquitetura relacional estrita (OLTP)** dentro do arquivo `dados.db`:
1. **Camada Relacional Base (42 Tabelas em 3FN):** Manteremos fisicamente no SQLite apenas as 42 tabelas do `ModeloClassesUnificado.asta` que participam da geração das 6 fatos, descartando as 43 tabelas não consumidas. O DDL é segmentado em `01_tabelas_core.sql` a `03`, preservando tipagem, integridade de herança (chaves primárias com `REFERENCES superclasse(id) ON DELETE CASCADE`) e constraints `CHECK`.
2. **Camada de Fatos como VIEWs Dinâmicas (6 VIEWs):** As 6 fatos serão definidas no script dedicado `04_fatos_views.sql` como **`CREATE VIEW vfact_*_resolved AS SELECT ...`** diretamente sobre as 42 tabelas base, incorporando as correções de negócio P1 a P12 da especificação [Docs/Fatos/PropostaFatos.md](file:///home/andre/test_adito/Docs/Fatos/PropostaFatos.md). Nenhuma tabela fato física é duplicada em disco.

## Justificativa  
1. **Verdade Única Transacional (Single Source of Truth):** Como as fatos são `VIEW`s dinâmicas, qualquer `INSERT`, `UPDATE` ou `DELETE` realizado transacionalmente (OLTP) nas 42 tabelas base é refletido instantaneamente nas fatos em tempo de execução, sem necessidade de rotinas de recarga ou materialização em lote.
2. **Zero Redundância de Armazenamento:** Não há duplicação dos dados em tabelas físicas separadas, mantendo o arquivo `dados.db` enxuto (~4 MB) e 100% em memória no cache do SO.
3. **Desempenho Instantâneo no Volume do IFES:** Para a volumetria consolidada (~27.000 linhas base), o query planner do SQLite resolve as queries sobre as `VIEW`s em menos de 5 milissegundos com os índices B-Tree criados nas chaves estrangeiras.
4. **Simplificação do Pipeline ETL:** O script de carga Python apenas insere os dados nas 42 tabelas base e cria as `VIEW`s, eliminando o estágio de materialização de tabelas e acelerando a carga.

## Alternativas Consideradas  
* **Materializar as Fatos como TABLE física (estilo OLAP estático):** Descartado para garantir a natureza transacional OLTP do banco e evitar redundância de dados e riscos de dessincronização entre as tabelas base e as fatos.
* **Manter as 85 tabelas completas do ASTA:** Descartado porque 43 tabelas não possuem dados alimentados no pipeline nem alimentam qualquer fato, gerando ruído desnecessário.
* **Armazenar apenas as 6 Fatos (sem as 42 tabelas base):** Descartado para preservar a capacidade de auditoria, rastreabilidade transacional e integridade formal com o modelo acadêmico do IFES.

## Consequências  
* **Positivas:** Modelo 100% transacional OLTP; sincronização em tempo real; zero dados duplicados; tamanho mínimo do banco em disco; pipeline de carga simplificado.
* **Negativas:** Consultas analíticas extremamente complexas que filtram grandes volumes exigem que os índices B-Tree nas chaves estrangeiras das 42 tabelas base estejam bem ajustados.
* **Riscos:** Criação de queries pelo LLM que gerem planos de execução não indexados sobre as VIEWs (mitigado pela criação de índices estratégicos nas chaves de junção e monitoramento de latência).

## Referências  
* [Docs/ModelosClasses/ModeloClassesUnificado.asta](file:///home/andre/test_adito/Docs/ModelosClasses/ModeloClassesUnificado.asta)
* [Docs/Fatos/PropostaFatos.md](file:///home/andre/test_adito/Docs/Fatos/PropostaFatos.md)
* [Adito/docs/specs/especificacao_resolucoes_fatos_v2.md](file:///home/andre/test_adito/Adito/docs/specs/especificacao_resolucoes_fatos_v2.md)
* [ADR 0001: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)](file:///home/andre/test_adito/docs/adr/ADR-0001-migracao-dados-100-sqlite.md)
