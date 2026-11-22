# Discovery — Automação de Comandos do Desenvolvedor via Makefile Único (DevEx)

**Status:** APPROVED  
**Classificação de Processo:** NORMAL PROCESS  
**Origem:** usuário  
**Data:** 18/11/2026  

## Intent
Eliminar a fragmentação de comandos e a fricção operacional no ciclo de desenvolvimento do Adito, permitindo que qualquer desenvolvedor execute setup, pipeline de dados (ETL e banco SQLite com fatos), aplicação desktop e testes automatizados a partir de um único ponto de entrada mnemônico (`make`) na raiz do repositório.

## Problem
Atualmente, o processo de desenvolvimento e manutenção do projeto exige que o desenvolvedor memorize e execute manualmente sequências de comandos complexas em múltiplos diretórios e ambientes virtuais distintos:
1. **Pipeline de Dados Fracionado:** Para preparar a base analítica, é necessário rodar o cruzamento em `Adito/etl`, depois invocar `Adito/scripts/popular_banco.py` para gerar o `dados.db` relacional e suas 6 views analíticas das fatos, e certificar-se de que o arquivo esteja na pasta de dados do Tauri.
2. **Execução do Desktop:** Para subir a aplicação, é necessário lembrar do script `./rodar_desktop.sh` ou iniciar manualmente o Vite no frontend e o cargo no Tauri.
3. **Execução de Testes Descentralizada:** Para testar a integridade do sistema, o desenvolvedor precisa rodar 4 ou 5 comandos em pastas diferentes (`pytest` no ETL, `unittest` no núcleo, `teste_stdio.py` e `teste_contrato.py`).
4. **Onboarding Áspero:** Desenvolvedores recém-chegados não possuem um comando padronizado para preparar o ambiente local (`setup`), gerando erros por dependências ou ambientes virtuais ausentes.

## Users / Stakeholders relevantes
- **Desenvolvedores do Projeto Adito:** Necessitam de agilidade no dia a dia para subir o app, rebuildar o banco analítico e rodar testes antes de commits/PRs.
- **Engenharia de Dados (ETL):** Necessita de atalhos claros para disparar extratores específicos ou rodar o pipeline completo de dados.
- **Revisores de PR / QA:** Precisam rodar toda a suíte de testes do projeto com um único comando confiável.

## Current Situation
- Não existe nenhum arquivo `Makefile` no projeto.
- Cada módulo possui sua própria convenção de execução:
  - App: `./rodar_desktop.sh` ou `cd Adito/app/src-tauri && cargo run` + `npm run dev`.
  - ETL: `cd Adito/etl && .venv/bin/adito-etl <comando>`.
  - Scripts: `python Adito/scripts/popular_banco.py` e `python Adito/scripts/ver_dados.py`.
  - Testes: espalhados entre `Adito/etl/tests`, `Adito/app/backend/nucleo/core/` e `Adito/app/scripts/`.

## Desired Outcome
Um `Makefile` na raiz do projeto com interface clara, auto-documentada (`make help`), que orquestre o setup, o banco analítico, o desktop e os testes através de comandos intuitivos, com guardas de erro amigáveis para orientar o desenvolvedor caso falte alguma dependência.

## Success Criteria
- [ ] `make help` lista todos os comandos disponíveis de forma colorida e autoexplicativa.
- [ ] `make db` executa o cruzamento e popula o SQLite (`dados.db`) com todas as tabelas 3FN e as 6 Views dinâmicas das fatos em tempo inferior a 5 segundos.
- [ ] `make desktop` inicia o ambiente desktop completo (Vite + Núcleo Python + Janela Tauri) via `./rodar_desktop.sh`.
- [ ] `make dev` funciona como atalho mestre unificado: valida dependências, atualiza o banco/fatos e já sobe o desktop.
- [ ] `make test` executa sequencialmente todas as suítes de testes do repositório (ETL, núcleo, contrato e STDIO) reportando o status consolidado.
- [ ] `make setup` cria os ambientes virtuais Python (`.venv` do app e do ETL), instala requirements, pacote do ETL e dependências do frontend (`npm`).
- [ ] O arquivo `README.md` da raiz é atualizado com uma tabela clara dos comandos úteis.

## Scope

### IN
- `Makefile` na raiz do repositório.
- Alvos para Desktop: `make dev`, `make desktop`, `make dev-front`, `make build-front`.
- Alvos para Banco e ETL: `make db`, `make etl-extract`, `make etl-cruzar`, `make etl-pii`, `make etl-ver`.
- Alvos para Testes: `make test`, `make test-etl`, `make test-core`, `make test-mcp`, `make test-tauri`.
- Alvos para Setup e Manutenção: `make setup`, `make setup-app`, `make setup-etl`, `make clean`.
- Mensagens de validação e guardas caso os ambientes virtuais não estejam configurados.
- Atualização da seção de comandos do desenvolvedor no `README.md`.

### OUT
- Criação de instaladores ou empacotamento de produção (PyInstaller, executáveis finais `.exe`/`.deb`).
- Alteração na lógica dos extratores, nos modelos do banco ou nas regras de negócio.
- Sub-Makefiles independentes em cada pasta (decisão: Makefile único e centralizado na raiz).

### LATER
- Integração dos alvos do Makefile em workflows de CI do GitHub Actions.
- Alvos de containerização (Docker) caso o projeto adote no futuro.

## Constraints / Feasibility
- Compatibilidade total com ambientes Linux e macOS utilizando bash e GNU Make.
- No Windows, depende de terminal bash/WSL ou ambiente Make compatível (ex.: Git Bash ou MinGW).
- Preservação estrita dos scripts existentes (`popular_banco.py`, `rodar_desktop.sh`, CLI `adito-etl`).

## Assumptions
- O desenvolvedor possui `python3`, `npm` e `cargo` instalados no sistema operacional.
- O arquivo `.env` do app ou do ETL pode ser configurado a partir de `.env.example` caso não exista.

## Open Questions
- Nenhuma pergunta bloqueante aberta (todas as decisões foram alinhadas na sessão de `/grill-me`).

## Review & Adjust

- [ ] Usuário revisou a proposta de Discovery.
- [ ] Alterações solicitadas foram incorporadas.
- [ ] Decisões relevantes foram confirmadas.
- [ ] Não existem perguntas bloqueantes abertas.

### User adjustments
- Alinhado previamente via `/grill-me`: abordagem em 2 camadas para ETL (banco rápido vs extração web), comando mestre `dev`, setup explícito e inclusão de atalhos de testes.

## Gate G0 — PROBLEM READY

**Status:** APPROVED  
**Aprovado pelo usuário:** [x] Sim  [ ] Não
