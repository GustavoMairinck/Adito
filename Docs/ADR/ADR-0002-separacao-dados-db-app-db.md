# ADR 0002: Separação Arquitetural entre Banco Analítico (dados.db) e Banco Operacional (app.db)

**Status:** Aceito  
**Data:** 18/11/2026  

## Contexto/Problema  
A aplicação desktop Adito possui duas naturezas de dados muito distintas:
1. **Dados Acadêmicos e Analíticos:** Provenientes do ETL dos sistemas institucionais do IFES (projetos, orientações, grupos de pesquisa, produções científicas e extensão). São dados consolidados institucionalmente, atualizados em lote (batch) e que devem ser estritamente protegidos contra alterações acidentais ou injeções maliciosas em tempo de execução.
2. **Dados Operacionais e de Sessão da Aplicação:** Gerados pelo uso do aplicativo no dispositivo do usuário (perfis locais, histórico de conversas, mensagens do chat, checkpoints de fluxo do LangGraph e vetores/RAG local). São dados dinâmicos, mutáveis a cada interação e de escopo pessoal do usuário.

Precisamos definir se essas duas camadas compartilham o mesmo arquivo de banco de dados ou se devem ser segregadas fisicamente.

## Decisão Tomada  
Adotaremos uma segregação física estrita entre dois bancos de dados SQLite independentes:
1. **`app.db` (Banco Operacional e de Sessão):** Aberto em modo Leitura e Escrita (Read/Write) em nível de usuário local. Gerencia tabelas operacionais, checkpoints de grafos, sessões de chat, widgets e embeddings do RAG.
2. **`dados.db` (Banco Acadêmico e Analítico):** Gerado exclusivamente pelo pipeline de carga/ETL em `Adito/app/data/dados.db` (ou caminho definido por `ORACULO_DATA_DIR`). Aberto pelo backend núcleo em tempo de execução sempre com a URI somente-leitura `file:dados.db?mode=ro`.

## Justificativa  
1. **Segurança e Imutabilidade Garantida:** Ao abrir `dados.db` com flag `mode=ro` no nível de SO/driver SQLite, garantimos matematicamente que nenhuma falha, query maliciosa ou alucinação do LLM consiga alterar, corromper ou apagar a base acadêmica institucional.
2. **Ciclos de Vida Independentes:** O banco `dados.db` pode ser substituído integralmente por uma nova versão gerada pelo ETL sem afetar o histórico de mensagens, preferências ou conversas do usuário armazenadas em `app.db`.
3. **Isolamento de Concorrência e Locks:** Operações intensas de escrita em `app.db` (ex: salvamento de checkpoints do LangGraph ou RAG) não concorrem com as consultas analíticas simultâneas de leitura sobre `dados.db`.

## Alternativas Consideradas  
* **Banco SQLite Único (`app.db` contendo tabelas analíticas e operacionais):** Descartado porque a atualização periódica dos dados acadêmicos exigiria migrations complexas em vez de simples substituição do arquivo, além de eliminar a proteção por flag somente-leitura em nível de conexão.
* **Tabelas Acadêmicas In-Memory (`:memory:`):** Descartado por demandar tempo de carga e alocação desnecessária de memória a cada inicialização da aplicação.

## Consequências  
* **Positivas:** Isolamento de falhas completo; proteção de dados sensíveis; atualização simples do banco analítico; performance previsível em concorrência.
* **Negativas:** Necessidade de gerenciar dois pools de conexão independentes no backend núcleo (`core/datastore.py` e gerenciador do `app.db`).
* **Riscos:** Tentativa de joins diretos entre tabelas operacionais e analíticas em uma única query SQL (mitigado porque o domínio do agente de BI é estritamente analítico sobre as tabelas fato).

## Referências  
* [ADR 0001: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)](file:///home/andre/test_adito/docs/adr/ADR-0001-migracao-dados-100-sqlite.md)
* [Discovery — Migração da Arquitetura de Dados Acadêmicos para 100% SQLite](file:///home/andre/test_adito/docs/discovery/migracao-arquitetura-sqlite.md)
