> **Nota:** ADR escrita quando o projeto se chamava Adito. Os caminhos `Adito/`, o pacote `adito_etl` e as variáveis `ORACULO_*`/`ADITO_*` citados aqui hoje são `Muninn/`, `muninn_etl` e `MUNINN_*` (ver [ADR-0005](ADR-0005-nome-muninn.md)).

# ADR 0004: Estratégia de Segurança e Resiliência de Consultas SQL no Núcleo (Authorizer, Custom LIKE e Transpilação com sqlglot)

**Status:** Aceito  
**Data:** 18/11/2026  

## Contexto/Problema  
No Adito, consultas SQL analíticas são sintetizadas dinamicamente por modelos de linguagem (LLMs) através do Agente de BI e executadas pelo backend núcleo (`core/datastore.py`).
Esse cenário impõe três desafios técnicos críticos:
1. **Segurança contra Injeção e Execução Indevida:** Um modelo de linguagem pode alucinar comandos destrutivos (`DROP`, `DELETE`, `ATTACH`) ou tentar inspecionar tabelas internas da base (`pessoa`, `aluno`, dados base 3FN) que não devem ser expostas.
2. **Incompatibilidade de Dialetos SQL:** LLMs frequentemente geram dialetos analíticos como DuckDB ou PostgreSQL (ex: `ILIKE`, `EXTRACT(YEAR FROM data)::INTEGER`), que não são suportados nativamente pelo SQLite.
3. **Busca Textual em Português sem Suporte a Acentos:** O comando `LIKE` padrão do SQLite é case-insensitive apenas para caracteres ASCII (`a-z`), sendo estritamente case-sensitive e sensível a acentos para caracteres latinos acentuados (ex: `'Vitória'` não casa com `'vitoria'` nem `'Vitoria'`).

## Decisão Tomada  
Implementaremos uma camada tripla de proteção e compatibilidade no `core/datastore.py`:
1. **Autorizador de Segurança em Nível de Driver (`conn.set_authorizer`):** Registraremos uma função de autorização no SQLite que permite estritamente operações de leitura (`SQLITE_SELECT` e `SQLITE_READ`) exclusivamente sobre a lista branca das 6 tabelas fato (`vfact_*_resolved`). Qualquer comando de mutação ou acesso a tabelas base 3FN é bloqueado imediatamente pelo próprio motor do banco com `sqlite3.DatabaseError: access denied`.
2. **Transpilação de Queries com `sqlglot`:** Antes de executar qualquer query no banco, o datastore transpila o comando via `sqlglot.transpile(sql, read="duckdb", write="sqlite")`, convertendo operadores analíticos e casts de tipo para sintaxe SQLite compatível.
3. **Função Python Customizada `LIKE` (Accent e Case Insensitive):** Registraremos via `conn.create_function("like", 2, ...)` uma função customizada em Python que normaliza as strings usando `unicodedata.normalize('NFD')` e remove marcas diacríticas (`Mn`), garantindo correspondência transparente para termos em português com ou sem acentos e em qualquer caixa alta/baixa.

## Justificativa  
1. **Defesa em Profundidade:** A proteção não depende apenas de validação de texto por regex ou prompt engineering; o próprio engine C do SQLite bloqueia comandos não autorizados antes do parsing de execução.
2. **Resiliência do Agente de BI:** A transpilação automática evita retrabalho ou falhas em tempo de execução quando o modelo utiliza sintaxe analítica usual.
3. **Experiência do Usuário (UX):** Usuários frequentemente buscam nomes de pesquisadores, áreas e campi sem acento (ex: "pesquisas em computacao no campus serra"), e o sistema deve retornar os dados de forma idêntica e amigável.

## Alternativas Consideradas  
* **Compilar extensões C externas do SQLite (ex: ICU ou fts5 customizado):** Descartado por complexidade de empacotamento binário e compatibilidade multiplataforma no Tauri. A função Python via `create_function` roda in-memory com impacto desprezível de milissegundos para tabelas de 10.000 linhas.
* **Validação apenas por Regex no backend:** Descartado por ser vulnerável a bypasses de sintaxe SQL complexos.
* **Proibir `ILIKE` e forçar via prompt:** Descartado por fragilidade; o LLM pode eventualmente produzir operadores de dialeto alternativo.

## Consequências  
* **Positivas:** Blindagem de segurança absoluta contra injeção e alteração de dados; consultas resilientes a pequenas variações de dialeto; suporte completo a buscas com e sem acento em português.
* **Negativas:** Sobrecarga computacional mínima da transpilação via `sqlglot` (~1 ms por query) e da chamada da função Python para filtros `LIKE`.
* **Riscos:** Queries altamente exóticas com constructs complexos não suportados nem pelo `sqlglot` (mitigado pelas instruções e exemplos fornecidos no `rules.md` e `examples.json`).

## Referências  
* [ADR 0001: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)](file:///home/andre/test_adito/docs/adr/ADR-0001-migracao-dados-100-sqlite.md)
* [ADR 0002: Separação Arquitetural entre Banco Analítico (dados.db) e Banco Operacional (app.db)](file:///home/andre/test_adito/docs/adr/ADR-0002-separacao-dados-db-app-db.md)
* [Requirements — Migração da Arquitetura de Dados Acadêmicos para 100% SQLite](file:///home/andre/test_adito/docs/requirements/migracao-arquitetura-sqlite.md)
