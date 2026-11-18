# ADR 0001: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)

**Status:** Aceito  
**Data:** 18/11/2026  

## Contexto/Problema  
O sistema Adito (Oráculo Local do IFES) foi originalmente estruturado com uma cadeia de dados heterogênea e complexa: um banco PostgreSQL 16 executado via Docker Compose, scripts de carga via `psql`, uma etapa intermediária de exportação de dezenas de arquivos JSON e um banco analítico DuckDB (`dados.duckdb`). Para um aplicativo desktop local baseado em Tauri, essa dependência de Docker e containers cria severo atrito de configuração para desenvolvedores e inviabiliza uma distribuição leve e autocontida para usuários finais. Além disso, o volume total de dados acadêmicos do campus é moderado (~27.000 linhas em 3FN e ~10.000 linhas de fatos, ~4 MB), escala na qual o DuckDB não traz vantagens mensuráveis de latência sobre o SQLite nativo.

## Decisão Tomada  
Migraremos 100% da arquitetura de dados acadêmicos e analíticos para SQLite (`dados.db`). A etapa de carga/ETL em Python utilizará o driver padrão `sqlite3` para criar e popular diretamente o arquivo `Adito/app/data/dados.db`. Eliminaremos completamente o container Docker com PostgreSQL, os scripts shell do Postgres, o script de exportação para JSON e a dependência do DuckDB.

## Justificativa  
1. **Zero-Setup e Autocontenção:** SQLite é embutido na biblioteca padrão do Python, dispensando instalação de servidores, containers ou portas de rede locais.
2. **Performance Suficiente:** Em benchmarks locais com o volume do IFES, SQLite responde a consultas analíticas agregadas em menos de 10 ms, com latência idêntica ou inferior ao DuckDB para esta volumetria.
3. **Simplificação Radical do Pipeline:** O processo de carga passa a ser um script Python único e determinístico que gera o banco final em segundos.
4. **Portabilidade e Distribuição:** O arquivo `dados.db` gerado é estritamente multiplataforma (Linux, Windows, macOS) e pode ser empacotado diretamente com o aplicativo.

## Alternativas Consideradas  
* **Manter PostgreSQL em Docker:** Descartado por exigir instalação e execução contínua do Docker Desktop pelos usuários ou desenvolvedores do app desktop.
* **Manter DuckDB para consultas analíticas:** Descartado porque o ganho colunar do DuckDB é irrelevante para tabelas de 10.000 linhas e adiciona uma biblioteca pesada de compilação binária no aplicativo.
* **Bancos NoSQL / Arquivos JSON em disco:** Descartado por falta de suporte robusto a consultas SQL relacionais complexas demandadas pelo Agente de BI.

## Consequências  
* **Positivas:** Redução de complexidade de código e infraestrutura; eliminação de Docker; carga em < 5 segundos; menor pegada de memória e disco no app desktop.
* **Negativas:** Perda de sintaxes proprietárias do PostgreSQL/DuckDB (como operador `::TYPE` ou certas funções de data), exigindo padronização no dialeto SQLite.
* **Riscos:** Consultas analíticas geradas pelo LLM em sintaxe incompatível com SQLite (mitigado pela camada de transpilação via `sqlglot` e atualização das instruções do agente em `rules.md`).

## Referências  
* [Discovery — Migração da Arquitetura de Dados Acadêmicos para 100% SQLite](file:///home/andre/test_adito/docs/discovery/migracao-arquitetura-sqlite.md)
* [Requirements — Migração da Arquitetura de Dados Acadêmicos para 100% SQLite](file:///home/andre/test_adito/docs/requirements/migracao-arquitetura-sqlite.md)
* [ModeloClassesUnificado.asta](file:///home/andre/test_adito/Docs/ModelosClasses/ModeloClassesUnificado.asta)
