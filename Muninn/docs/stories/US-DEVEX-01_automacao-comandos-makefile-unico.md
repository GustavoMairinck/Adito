# User Story: [US-DEVEX-01] Automação de Comandos do Desenvolvedor via Makefile Único

**Epic:** EPIC-09 — Produtividade de Desenvolvimento & Automação Local (DevEx)  
**GitHub Epic Issue:** -  
**GitHub US Issue:** -  
**Prioridade:** Alta  
**Story Points:** 3 pts  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** NO (ferramental de produtividade e automação local; não altera lógica de negócio do software em produção)  

---

## História

**Como** desenvolvedor ou engenheiro de software do projeto Muninn,  
**Eu quero** executar rotinas de setup de ambiente, construção do banco analítico com fatos, inicialização da aplicação desktop, testes automatizados e limpeza por meio de comandos curtos e mnemônicos em um `Makefile` na raiz,  
**Para que** eu não precise memorizar caminhos longos de diretórios, comandos complexos de ferramentas heterogêneas (Python, Node/Vite, Rust/Cargo, SQLite) ou a ordem correta de execução do pipeline.

### Contexto Adicional
O monorepo do Muninn combina diferentes stacks e pastas de execução (`Muninn/app`, `Muninn/etl`, `Muninn/scripts`). Atualmente, subir o desktop com a base de dados analítica atualizada exige entrar no ETL, rodar o cruzamento de identidades, depois ir para scripts, rodar o `popular_banco.py`, e por fim rodar `./rodar_desktop.sh`. Além disso, a execução de testes automatizados e a preparação de ambientes virtuais (`.venv`) ocorrem de forma descentralizada. Um `Makefile` padronizado na raiz centraliza todo o ciclo de vida do desenvolvedor em um ponto único.

### Pontos de Esclarecimento
Nenhum ponto pendente (todas as dúvidas de design foram sanadas na etapa de Discovery e alinhamento via `/grill-me`).

---

## Critérios de Aceitação

- [ ] **CA01 (Menu de Ajuda):** Ao rodar `make` ou `make help` na raiz do repositório, o terminal deve exibir uma lista formatada, categorizada e com cores ANSI contendo todos os comandos disponíveis e suas descrições.
- [ ] **CA02 (Atalho Mestre Unificado):** Ao rodar `make dev`, o Makefile deve verificar se o ambiente está configurado, executar `make db` previamente (garantindo que o SQLite esteja reconstruído com as fatos) e disparar o script `./rodar_desktop.sh`, abrindo o ambiente completo.
- [ ] **CA03 (Pipeline de Banco e Fatos Rápido):** Ao rodar `make db`, o comando deve orquestrar o cruzamento (`muninn-etl cruzar`), executar `popular_banco.py` gerando as 42 tabelas 3FN e as 6 Views dinâmicas das fatos v2.0 em `dados.db`, e copiar o arquivo para a pasta de dados do Tauri (`~/.local/share/br.edu.ifes.leds.muninn/` no Linux), completando o processo em menos de 5 segundos.
- [ ] **CA04 (Controle de Desktop e Frontend):** Devem existir alvos dedicados para:
  - `make desktop`: inicia o desktop com a base já existente via `./rodar_desktop.sh`.
  - `make dev-front`: inicia apenas o frontend Vite em modo dev (`npm run dev`).
  - `make build-front`: gera o build de produção do frontend (`npm run build`).
  - `make dev-tauri`: executa a janela Tauri (`cargo run`).
- [ ] **CA05 (Extração de Dados Sob Demanda):** O comando `make etl-extract` deve acionar a extração de dados da web, com alvos específicos disponíveis para cada fonte (`make etl-src-acoes`, `make etl-src-participacoes`, `make etl-sigpesq`, `make etl-cnpq`, `make etl-lattes`, `make etl-pii` e `make etl-ver`).
- [ ] **CA06 (Setup com Guardas Amigáveis):** O comando `make setup` deve criar os venvs Python (`Muninn/app/.venv` e `Muninn/etl/.venv`), instalar as dependências de backend, instalar o pacote `muninn_etl` em modo editável e executar `npm install` no frontend. Se o desenvolvedor tentar rodar `make dev` ou `make db` sem o setup concluído, o Makefile deve exibir mensagem clara instruindo: *"Ambiente não configurado. Execute 'make setup' primeiro."*.
- [ ] **CA07 (Testes Automatizados Consolidados):** O comando `make test` deve executar sequencialmente as 5 suítes de testes automatizados do repositório (ETL com `pytest`, testes do núcleo com `unittest`, testes de contrato e STDIO) e retornar código `0` com resumo visual verde apenas se todos passarem. Alvos granulares (`make test-etl`, `make test-core`, `make test-mcp`, `make test-tauri`) devem estar disponíveis.
- [ ] **CA08 (Limpeza):** Os comandos `make clean` e `make clean-all` devem remover arquivos compilados temporários (`__pycache__`, `*.pyc`), caches do pytest (`.pytest_cache`) e logs temporários de desenvolvimento em `/tmp`.
- [ ] **CA09 (Documentação no README):** O arquivo `README.md` da raiz do repositório deve incluir uma seção clara com a tabela de atalhos do Makefile e instruções de primeiro uso.

---

## Governança e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; a entrega consiste em tooling de desenvolvimento (DevEx), automação local e scripts auxiliares, sem alteração de contratos de API ou modelos de dados de produção.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Alteração interna de processo/tooling sem mudança observável de contratos de negócio.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Não introduz nem modifica APIs de rede ou boundaries externos.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A (mensagens diretas no terminal do Makefile)
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Touch List preliminar:**
  - `Makefile` (novo na raiz)
  - `README.md` (atualização da seção de comandos)
  - `docs/product_backlog.md` (registro do EPIC-09 e US-DEVEX-01)
- **Task Issues previstas:** N/A

---

## Notas Técnicas

### Arquitetura
- **Arquivo principal:** `Makefile` localizado na raiz do monorepo (`/home/andre/test_adito/Makefile`).
- **Padrão de implementação:**
  - `SHELL := /bin/bash`
  - `.DEFAULT_GOAL := help`
  - Todas as metas virtuais listadas explicitamente em `.PHONY`.
  - Uso estrito de tabs para identação de receitas Make.
  - Saída estilizada com sequências de escape ANSI para formatação de texto e cores (Ciano, Verde, Amarelo e Reset).

### Dependências
- GNU Make instalado no sistema do desenvolvedor.
- Bash padrão em ambientes Unix (Linux/macOS).

---

## Plano de Testes

### Testes Manuais & Validação Operacional
- [ ] Executar `make help` e verificar alinhamento e cores da saída.
- [ ] Executar `make setup` e validar se os venvs e dependências foram provisionados corretamente.
- [ ] Executar `make db` e verificar se `dados.db` foi criado com 42 tabelas, 6 views analíticas e tempo < 5s.
- [ ] Executar `make test` e verificar se todas as suítes de teste rodam sequencialmente e retornam código 0.
- [ ] Executar `make clean` e checar remoção de `__pycache__` e `.pytest_cache`.
- [ ] Simular ausência de `.venv` e validar se mensagem amigável instrui a rodar `make setup`.
