# ORACULO-ESX

Assistente de inteligencia estrategica da versao ESX, com backend Django, frontend Vue, orquestracao LangGraph, BI Agent via MCP, PostgreSQL/pgvector, Redis e bootstrap direto de dados de vendas no PostgreSQL.

## Documentacao Principal

Todo o setup local, inicializacao, migracao de dados, treinamento do agente, embeddings do rewrite e comandos Make ficam documentados em:

[SETUP_GUIDE.md](./SETUP_GUIDE.md)

## Visao Geral

- Backend Django/DRF em `backend/`.
- Frontend Vue/Vite servido por Nginx em `frontend-vue/`.
- Orquestrador multiagente em `backend/api/agents/orchestrator/`.
- BI Agent em `backend/api/agents/bi_agent/`, exposto via MCP em `oraculo_esx_mcp`.
- Knowledge base do agente em `knowledge_knowledgeitem`.
- Embeddings textuais para resolucao semantica em `analytics_text_embedding`.
- PostgreSQL com pgvector como banco principal.
- Redis como checkpointer do LangGraph.
- Dados analiticos ESX carregados a partir de `mudanças/mudanca/`.

## Estrutura

```text
backend/       Backend Django, agentes, chat, dashboard e knowledge base
frontend-vue/  Frontend Vue/Vite/Nginx
infra/         Docker Compose da infraestrutura e migracao MSSQL
k8s/           Manifests Kubernetes
cube/          Modelos Cube.js
database/      Scripts SQL de origem MSSQL
docs/          Documentacao complementar
```

## Atalhos

```bash
make up
make data-bootstrap TENANT=fapes
```

- Setup completo: [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- Contrato de API: [api_contract-completo.md](./api_contract-completo.md)
- Documentacao dos agentes: [docs/agents](./docs/agents)
- Modelo de dados: [docs/data_dictionary_conectaolap.md](./docs/data_dictionary_conectaolap.md)

## Preparacao de Dados ESX

O fluxo padrao nao usa Airflow. Para preparar o ambiente de vendas ESX:

```bash
make infra-up
make up
make data-bootstrap TENANT=fapes
```

Esse comando aplica `schema-ddl.sql`, carrega os inserts de `02-schema-dados.sql`, recria `vfactvendasresolved`, treina exemplos/DDL/docs e sincroniza embeddings textuais.

Os arquivos de Airflow continuam no repositorio como legado, mas ficam fora do fluxo recomendado.
