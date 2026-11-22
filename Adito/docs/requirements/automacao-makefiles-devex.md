# Requirements — Automação de Comandos do Desenvolvedor via Makefile Único (DevEx)

**Status:** APPROVED  
**Discovery de origem:** [`docs/discovery/automacao-makefiles-devex.md`](../discovery/automacao-makefiles-devex.md)  
**Classificação de Processo:** NORMAL PROCESS  
**Data:** 18/11/2026  

## Intent Summary
Prover um conjunto de comandos padronizados, rápidos e mnemônicos através de um `Makefile` na raiz do repositório, permitindo que a equipe de engenharia e novos desenvolvedores realizem setup de ambiente, construção do banco analítico com fatos, inicialização da aplicação desktop, execução de testes e tarefas de ETL sem atritos operacionais nem necessidade de memorizar caminhos internos de diretórios.

## Functional Requirements

- **FR01 — Menu de Ajuda Interativo:** O comando `make` (ou `make help`) deve analisar as diretivas do arquivo e exibir uma listagem colorida, categorizada e com breve descrição de todos os alvos disponíveis.
- **FR02 — Atalho Mestre Unificado (`make dev`):** Deve verificar os pré-requisitos essenciais, reconstruir/atualizar o banco SQLite `dados.db` com as 6 Views dinâmicas das fatos analíticas e disparar a execução do desktop completo (frontend Vite + casca Tauri + núcleo Python) de forma orquestrada.
- **FR03 — Execução Isolada do Desktop:**
  - `make desktop`: dispara o script `./rodar_desktop.sh` com a base de dados existente.
  - `make dev-front`: inicia apenas o servidor de desenvolvimento do frontend (`npm run dev` na porta 5173).
  - `make build-front`: gera o pacote compilado do frontend (`npm run build`).
  - `make dev-tauri`: executa a janela Tauri (`cargo run`).
- **FR04 — Pipeline Rápido de Banco e Fatos Analíticas (`make db`):** Deve executar o cruzamento por nome normalizado (`adito-etl cruzar`), rodar a carga relacional em Python (`Adito/scripts/popular_banco.py`) gerando as 42 tabelas 3FN e as 6 Views analíticas dinâmicas em `dados.db`, e disponibilizar o arquivo na pasta padrão do Tauri (`~/.local/share/br.edu.ifes.leds.adito/` no Linux) em tempo total inferior a 5 segundos.
- **FR05 — Pipeline de Extração Web Sob Demanda (`make etl-extract`):** Deve permitir acionar os extratores externos da web (SRC ações/participações, SigPesq, CNPq, Lattes) de forma sequencial ou isolada via alvos específicos (`make etl-src-acoes`, `make etl-sigpesq`, etc.).
- **FR06 — Setup Inicial com Guardas Amigáveis (`make setup`):** Deve automatizar a criação dos ambientes virtuais Python (`Adito/app/.venv` e `Adito/etl/.venv`), instalação das dependências (`pip install -r backend/requirements.txt`, instalação editável do `adito_etl` com dependências de dev) e instalação de pacotes npm (`npm install`).
- **FR07 — Execução Consolidada de Testes Automatizados (`make test`):** Deve executar de forma sequencial todas as suítes de testes do repositório (ETL com `pytest`, testes unitários do núcleo com `unittest`, testes de contrato RPC e testes de STDIO) e retornar código de saída `0` com resumo visual verde apenas se todos passarem. Alvos granulares (`make test-etl`, `make test-core`, `make test-mcp`, `make test-tauri`) também devem estar disponíveis.
- **FR08 — Limpeza de Caches e Resíduos (`make clean` / `make clean-all`):** Deve remover recursivamente arquivos temporários de compilação Python (`__pycache__`, `*.pyc`), caches do pytest (`.pytest_cache`) e logs transitórios do Vite em `/tmp`.
- **FR09 — Documentação de Onboarding:** O arquivo `README.md` da raiz do repositório deve ser atualizado com uma tabela clara contendo os principais comandos do Makefile e instruções rápidas de primeiro uso.

## Business / Domain Rules

- **BR01 (Ponto de Entrada Único):** Todos os alvos do Makefile devem ser operados exclusivamente a partir do diretório raiz do repositório, gerenciando internamente as mudanças de diretório (`cd`) necessárias para cada subprojeto.
- **BR02 (Guarda Amigável de Ambiente):** Comandos que dependem de ferramentas ou ambientes virtuais (como `make dev`, `make db` ou `make test`) devem verificar a existência dos binários em `.venv`. Caso não existam, o comando deve falhar com mensagem explícita e instrutiva: *"Ambiente não configurado. Execute 'make setup' primeiro."*, em vez de falhas crípticas de `command not found`.
- **BR03 (Garantia de Fatos Atualizadas):** O alvo mestre `make dev` deve invocar `make db` como dependência prévia, garantindo que o desktop nunca suba com um banco ausente, defasado ou corrompido.
- **BR04 (Declaração Estrita de Alvos):** Todos os alvos que não representam arquivos no sistema de arquivos devem ser explicitamente registrados na diretiva `.PHONY` do Makefile.

## Non-Functional Requirements

- **NFR01 (Desempenho de Carga):** A execução do comando `make db` (cruzamento + carga SQLite + DDLs + views analíticas) não deve exceder 5 segundos em hardware padrão de desenvolvimento.
- **NFR02 (Portabilidade e Zero Dependências Extras):** O Makefile deve requerer apenas `bash` e `make` (GNU Make), sendo compatível nativamente com ambientes Linux e macOS.
- **NFR03 (Usabilidade e Feedback Visual):** As saídas do Makefile devem usar cores ANSI padronizadas (Ciano para passos em andamento, Verde para sucessos e Amarelo/Vermelho para avisos/erros).

## User Scenarios

### Cenário 1: Primeiro Acesso de um Desenvolvedor (Onboarding)
1. O desenvolvedor clona o repositório e abre o terminal na raiz.
2. Executa `make help` e visualiza a lista de comandos disponíveis.
3. Executa `make setup`; o Makefile cria os venvs do app e do ETL, instala os pacotes Python e roda `npm install`.
4. Executa `make dev`; o Makefile detecta o setup pronto, processa os dados brutos gerando o `dados.db` com as fatos e abre a janela do Adito pronta para uso.

### Cenário 2: Atualização Rápida de Dados Analíticos (Dia a Dia)
1. O desenvolvedor adicionou ou modificou dados nos arquivos brutos.
2. Executa `make db`.
3. Em menos de 5 segundos, o banco SQLite é recriado com as 42 tabelas 3FN e as 6 Views dinâmicas das fatos v2.0, pronto para ser consultado no app ou via `make etl-ver`.

### Cenário 3: Validação de Qualidade antes de Abrir PR
1. O desenvolvedor alterou código no backend e no ETL.
2. Executa `make test`.
3. O Makefile roda o `pytest` do ETL (69 testes), o `unittest` do núcleo (43 testes), os testes de contrato (51 verificações) e o STDIO (14 verificações), exibindo relatório verde unificado ao final.

### Cenário 4: Tentativa de Execução sem Setup Prévio (Edge Case)
1. O desenvolvedor roda `make dev` logo após clonar, sem ter executado `make setup`.
2. O Makefile intercepta a ausência de `Adito/app/.venv` e emite mensagem amigável: *"Ambiente não configurado. Execute 'make setup' primeiro."*, encerrando com código de erro limpo.

## Technical Context & Constraints
- Arquitetura: Makefile único na raiz delegando internamente para `Adito/app/`, `Adito/etl/` e `Adito/scripts/`.
- Executáveis esperados: `python3`, `npm`, `cargo` (Rust).
- Ferramenta de build: GNU Make standard.

## Assumptions
- **A01:** Os dados brutos mínimos para construção do banco já estão versionados ou disponíveis na máquina local em `Adito/etl/brutos/` e `Adito/etl/trabalho/`.
- **A02:** O desenvolvedor possui permissão de escrita em seu diretório de dados de usuário (`~/.local/share/br.edu.ifes.leds.adito/` no Linux).

## Out of Scope
- Criação de pipelines de CI/CD para GitHub Actions (fica para fase posterior).
- Modificação na lógica dos scripts Python ou componentes Vue existentes.

## Open Questions
- Nenhuma pergunta bloqueante aberta.

## Review & Adjust

O usuário pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito antes da aprovação do gate.

- [ ] Proposta completa de Requirements apresentada ao usuário.
- [ ] Ajustes solicitados incorporados.
- [ ] IDs estabilizados (FR01–FR09, BR01–BR04, NFR01–NFR03).
- [ ] Nenhuma pergunta bloqueante aberta.

### User adjustments
- Proposta construída com base no alinhamento prévio via `/grill-me`.

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED  
**Aprovado pelo usuário:** [x] Sim  [ ] Não
