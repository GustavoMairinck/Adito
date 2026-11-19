# Task Breakdown: [US-DEVEX-01] Automação de Comandos do Desenvolvedor via Makefile Único

**Data:** 18/11/2026  
**Participantes:** Engenharia / Desenvolvedor  
**Estimativa total:** 3 Story Points  
**Nivel ScrumAIDev:** 1  
**Spec governada:** N/A  
**Contract governado:** N/A  
**Padrao de erro:** N/A  
**BDD associado:** N/A  
**Behavior change:** NO  
**GitHub Epic Issue:** -  
**GitHub Parent US Issue:** -  
**GitHub Sprint Container:** -  

---

## Pre-Flight de Governanca

- **US exige Spec governada?** Não
- **US exige Contract governado?** Não
- **Justificativa do Nivel ScrumAIDev:** Nível 1 é o menor suficiente; a entrega consiste em tooling local de desenvolvimento e automação (`Makefile`), sem impacto em contratos de API ou modelos de dados de produção.
- **Justificativa:** Ferramental de Developer Experience (DevEx).
- **Touch List aplicavel:**
  - `Makefile` (novo na raiz)
  - `README.md` (atualização da seção de execução rápida)
  - `docs/stories/US-DEVEX-01_automacao-comandos-makefile-unico.md`
  - `docs/product_backlog.md`
- **Runner BDD a executar:** N/A
- **Validacao de contrato a executar:** N/A
- **Teste de contrato a executar:** N/A
- **Teste de mock a executar:** N/A

---

## Checagem de Principios
Não aplicável (Nível ScrumAIDev 1, Behavior change = NO, estimativa <= 8 pontos).

---

## Tasks Tecnicas

### [TASK-DEVEX-01] Estrutura Base do Makefile & Help Colorido
- **Descricao:** Criar o arquivo `Makefile` na raiz do monorepo definindo `SHELL := /bin/bash`, `.DEFAULT_GOAL := help`, detecção automática de variáveis de ambiente (`APP_VENV`, `ETL_VENV`, `APP_PYTHON`, `ETL_PYTHON`), sequências de escape ANSI para formatação de cores e alvo `help` auto-documentado via `awk`.
- **Estimativa:** 0.5 pt
- **Status:** Done
- **Criterios de Aceite:**
  - `make` ou `make help` exibe listagem categorizada, alinhada e colorida de todos os alvos.
  - Alvos virtuais declarados em `.PHONY`.

### [TASK-DEVEX-02] Alvos de Dados, Fatos Analíticas & ETL
- **Descricao:** Implementar os alvos de manipulação de dados e SQLite:
  - `make db`: executa o cruzamento de identidades (`muninn-etl cruzar`), executa `Muninn/scripts/popular_banco.py` (criando as 42 tabelas 3FN e as 6 Views dinâmicas das fatos v2.0) e copia o `dados.db` para a pasta de dados do Tauri do usuário em < 5 segundos.
  - `make etl-ver`: abre o explorador interativo no terminal via `Muninn/scripts/ver_dados.py`.
  - `make etl-pii`: executa a auditoria de proteção a dados pessoais (`muninn-etl verificar-pii`).
  - `make etl-extract` e alvos granulares para acionar extratores da web sob demanda (`src-acoes`, `src-participacoes`, `sigpesq`, `cnpq`, `lattes`).
- **Estimativa:** 0.75 pt
- **Status:** Done
- **Criterios de Aceite:**
  - `make db` reconstrói o banco e as views analíticas em < 5s (executado em 1.19s).
  - Alvos do ETL executam a partir da raiz sem exigir `cd` manual do desenvolvedor.

### [TASK-DEVEX-03] Alvos do Desktop, Frontend & Guarda Amigável
- **Descricao:** Implementar os alvos de inicialização e build da aplicação desktop:
  - `make dev`: atalho unificado mestre que verifica o setup, executa `make db` previamente e dispara `./rodar_desktop.sh`.
  - `make desktop`: executa `./rodar_desktop.sh` utilizando o banco já existente.
  - `make dev-front`: sobe o servidor Vite (`npm run dev` na porta 5173).
  - `make build-front`: executa `npm run build` no frontend.
  - `make dev-tauri`: executa a janela desktop via `cargo run`.
  - Guarda amigável: se os venvs não existirem, comandos que dependem deles devem exibir: *"Ambiente não configurado. Execute 'make setup' primeiro."*.
- **Estimativa:** 0.75 pt
- **Status:** Done
- **Criterios de Aceite:**
  - `make dev` atualiza o banco e sobe o app de forma integrada.
  - Tentativa de execução sem setup emite mensagem amigável sem stack trace críptico.

### [TASK-DEVEX-04] Alvos de Testes Consolidados & Limpeza
- **Descricao:** Implementar comandos para automação da qualidade e higiene do repositório:
  - `make test`: executa sequencialmente as 5 suítes de testes automatizados (`pytest` do ETL, `unittest` do núcleo, contrato e STDIO) com relatório visual verde consolidado.
  - `make test-etl`, `make test-core`, `make test-mcp`, `make test-tauri`: alvos granulares de teste.
  - `make clean` e `make clean-all`: remoção recursiva de `__pycache__`, caches de pytest e logs transitórios do Vite em `/tmp`.
- **Estimativa:** 0.5 pt
- **Status:** Done
- **Criterios de Aceite:**
  - `make test` reporta sucesso consolidado com código de saída 0.
  - `make clean` purga arquivos transitórios sem tocar em dados permanentes.

### [TASK-DEVEX-05] Setup Automatizado, Documentação no README & Validação
- **Descricao:** Implementar o alvo `make setup` (criação de venvs Python, `pip install` e `npm install`), atualizar o arquivo `README.md` raiz com a tabela de referência de comandos rápidos e validar operacionalmente todos os alvos do Makefile em ambiente local.
- **Estimativa:** 0.5 pt
- **Status:** Done
- **Criterios de Aceite:**
  - `make setup` provisiona os ambientes com sucesso.
  - `README.md` documenta a tabela mnemônica de comandos.
  - 100% dos testes e comandos do Makefile validados na prática.
