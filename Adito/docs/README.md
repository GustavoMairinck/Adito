# Oráculo desktop: decisões do porte

Decisões tomadas para levar o Oráculo-ESX (web, em Docker) para um aplicativo desktop em Tauri, no Windows e no Linux. O código está em [../app/](../app/).

- **[stories/](stories/)**: user stories no template do Oráculo, uma por decisão ou entrega.
- **[PORTE_DESKTOP_DECISOES.md](PORTE_DESKTOP_DECISOES.md)**: registro completo, com datas, consequências, achados no código e o que não foi verificado.

## User stories

| US | Título | Status |
|---|---|---|
| [US-001](stories/US-001_app-desktop-tauri.md) | Rodar o Oráculo como aplicativo desktop | Done |
| [US-002](stories/US-002_sqlite-sem-docker.md) | Guardar tudo em SQLite, sem Postgres nem Redis | Done |
| [US-003](stories/US-003_sem-login.md) | Abrir o app direto, sem login | Done |
| [US-004](stories/US-004_chave-mistral.md) | Informar a minha própria chave da Mistral | Done |
| [US-005](stories/US-005_dados-pessoais-llm.md) | Controlar quais dados saem para o LLM | In Progress |
| [US-006](stories/US-006_contextos.md) | Trabalhar com vários contextos de dados | Done |
| [US-007](stories/US-007_entrada-arquivo-sqlite.md) | Trazer meus dados num arquivo SQLite pronto | In Progress |
| [US-008](stories/US-008_agente-mesmo-processo.md) | Agente BI no mesmo processo do backend | Done |
| [US-009](stories/US-009_demo-vendas.md) | Testar o app com a demonstração de vendas | Done |
| [US-010](stories/US-010_telas-herdadas.md) | Tirar do app as telas que só faziam sentido na web | Done |
| [US-011](stories/US-011_instalador.md) | Instalar o app sem ferramentas de desenvolvimento | Backlog |
| [US-012](stories/US-012_limite-linhas-llm.md) | Respeitar o limite de linhas do contexto no envio ao LLM | Backlog |
| [US-013](stories/US-013_backend-orfao.md) | Não deixar o backend rodando quando o app morre | Backlog |
| [US-014](stories/US-014_busca-local-nomes.md) | Resolver nomes de pessoas sem enviá-los à nuvem | Backlog |
| [US-015](stories/US-015_filtros-por-contexto.md) | Filtros do dashboard e Explorar Dados por contexto | Backlog |

## Decisões em uma linha

| Tema | Decisão | US |
|---|---|---|
| Casca | Tauri + front Vue + backend Python como processo filho; Windows e Linux | US-001 |
| Banco | SQLite para tudo; `app.db` (app) e `dados.db` (dados, só leitura); Redis removido | US-002 |
| Acesso | Sem login; usuário local e tenant fixos; token efêmero por execução | US-003 |
| Chave do LLM | O usuário informa a chave da Mistral, guardada no cofre do SO | US-004 |
| LGPD | Mascarar e limitar; 20 linhas no prompt; histórico só com SQL; criptografia do disco do SO | US-005 |
| Contextos | Modelo `Contexto` novo; só views do arquivo; views de views permitidas | US-006 |
| Entrada de dados | Arquivo SQLite pronto, copiado para a pasta de dados do usuário | US-007 |
| Processos | Agente BI no mesmo processo; sem servidor MCP | US-008 |
