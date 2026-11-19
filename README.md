# Muninn (assistente de BI de pesquisa e extensão do IFES)
<img width="700" height="76" alt="image" src="https://github.com/user-attachments/assets/bb871070-f07e-4c9a-b2fd-0a4e2146bb01" />



Painel que reúne os dados já públicos dos sistemas do IFES Campus Serra — SRC, Diretoria, Editais, Egressos e Horizon — numa visão única de pesquisa e extensão do campus.

Os dados vêm dos pipelines, painéis e agentes do **[ifesserra-lab](https://github.com/ifesserra-lab)**.

**[Site → ifesserra-lab.github.io](https://ifesserra-lab.github.io/)** &nbsp;·&nbsp; **[Painel de Extensão →](https://ifesserra-lab.github.io/src/)** &nbsp;·&nbsp; **[Pesquisa STEM →](https://ifesserra-lab.github.io/pesquisa-stem.html)**

---

## 🛠️ Comandos de Desenvolvimento (Makefile)

O projeto conta com um **Makefile centralizado na raiz** para agilizar todo o ciclo de desenvolvimento, preparação de dados e testes:

| Comando | O que faz |
|---|---|
| `make` ou `make help` | Exibe o menu com todos os comandos disponíveis e descrições |
| `make all` ou `make dev` | **Atalho mestre:** verifica setup, reconstrói o banco/fatos e sobe o app desktop completo |
| `make desktop` | Inicia a aplicação desktop (`./rodar_desktop.sh`) com a base SQLite existente |
| `make db` | Reconstrói o banco relacional e as 6 Views dinâmicas das fatos no SQLite (~1.2s) |
| `make etl` | Ciclo completo de ETL: extração externa na web, cruzamento e carga no SQLite |
| `make etl-extract` | Executa a extração completa de dados da web (SRC, SigPesq, CNPq, Lattes) |
| `make etl-ver` | Abre o explorador interativo de dados acadêmicos no terminal |
| `make test` | Executa sequencialmente as suítes rápidas/offline (ETL, núcleo Python, STDIO, contrato RPC e frontend unitário Vitest) |
| `make test-front` | Executa os testes unitários do frontend Vue (`vitest` + `@vue/test-utils`) |
| `make test-e2e` | Executa os testes E2E de interface no Chromium via Playwright (modo determinístico com mock de IPC Tauri) |
| `make test-e2e-live` | Executa os testes E2E integrados conectando o Playwright ao núcleo Python real sobre o `dados.db` |
| `make test-perf` | Executa o benchmark local de cold-start, RPCs, 6 views fato e concorrência STDIO sobre `dados.db` (exporta JSON/MD) |
| `make test-eval` | Executa a avaliação híbrida de acurácia da IA (SQL gabarito + LLM Judge, requer `GEMINI_API_KEY`; aceita `ARGS="--sample 6"`) |
| `make setup` | Cria os ambientes virtuais Python (`.venv` do app e do ETL) e instala todas as dependências |
| `make clean` | Remove arquivos temporários de log do Muninn, caches de compilação e pytest |
| `make clean-all` | Limpa também os diretórios de build gerados pelo frontend e Tauri (`dist/`, `target/`) |

> **Primeira vez no projeto?** Execute `make setup` para configurar os ambientes virtuais e dependências e depois `make dev` para iniciar o sistema.  
> **Pré-requisito para Playwright (`make test-e2e`):** caso não haja Chrome/Chromium instalado no sistema, instale o browser uma vez com `cd Muninn/app/frontend-vue && npx playwright install chromium`.  
> **Relatórios de Performance e Acurácia:** `make test-perf` e `make test-eval` salvam relatórios em JSON e Markdown em `Muninn/app/data/reports/`. O `make test-eval` aceita `GEMINI_JUDGE_MODEL` (opcional, fallback para `GEMINI_MODEL`) e flags como `ARGS="--sample 6 --no-judge"`.  
> **Compatibilidade de Sistema Operacional:** O `Makefile` foi projetado para ambientes **Linux**, **WSL** (Windows Subsystem for Linux) e **macOS** (com bash). No Windows nativo, recomenda-se executar os comandos via WSL.


---

## Painéis em produção

| # | Painel | O que é |
|:--|:--|:--|
| 01 | **[Extensão — SRC](https://ifesserra-lab.github.io/src/)** | ações, atividades, extensionistas, temas, investimento e o índice FORPROEX |
| 02 | **[Editais](https://ifesserra-lab.github.io/portal_edital/)** | editais de pesquisa, extensão e fomento — reunidos, filtráveis e atualizados |
| 03 | **[Salários & carreira de egressos](https://ifesserra-lab.github.io/egressos/)** | trajetória e faixa salarial dos formados (visão executiva anonimizada) |
| 04 | **[Diretoria](https://ifesserra-lab.github.io/diretoria/)** | indicadores consolidados de ensino, pesquisa e extensão para a gestão |
| 05 | **[GEDoc](https://gedocs.vercel.app/)** | busca full-text no acervo de documentos institucionais do campus |
| 06 | **[Horizon](https://ifesserra-lab.github.io/horizon_dashboard/)** | inteligência sobre grupos de pesquisa, produção e editais (Prefect + Supabase) |
| 07 | **[Projetos FACTO](https://ifesserra-lab.github.io/factor/)** | projetos de desenvolvimento científico e tecnológico da Fundação FACTO |

## Repositórios ifesserra-lab

**Painéis & visualização**
- [src](https://github.com/ifesserra-lab/src) — painel de extensão do Campus Serra (Astro + ETL Python)
- [horizon_dashboard](https://github.com/ifesserra-lab/horizon_dashboard) — dashboard de pesquisa (Projeto Horizon)
- [egressos](https://github.com/ifesserra-lab/egressos) — carreira e salários de egressos (anonimizado)
- [diretoria](https://github.com/ifesserra-lab/diretoria) — indicadores de apoio à gestão
- [factor](https://github.com/ifesserra-lab/factor) — portal de projetos FACTO (dashboard estático)

**ETL & bibliotecas de dados**
- [horizon_etl](https://github.com/ifesserra-lab/horizon_etl) — pipeline ETL (Prefect + Supabase, arquitetura hexagonal)
- [factor_lib](https://github.com/ifesserra-lab/factor_lib) — extração de projetos do portal Facto (Playwright)
- [scriptLattes](https://github.com/ifesserra-lab/scriptLattes) — extrai dados do Lattes para JSON
- [research_domain_lib](https://github.com/ifesserra-lab/research_domain_lib) · [dgp.cnqp_lib](https://github.com/ifesserra-lab/dgp.cnqp_lib)
- [research_hub](https://github.com/ifesserra-lab/research_hub) — aplicação desktop para corrigir os dados do Horizon

**Agentes & automação**
- [hermes](https://github.com/ifesserra-lab/hermes) — agente de integração Pesquisa/Ensino/Editais
- [sigpesq_agent](https://github.com/ifesserra-lab/sigpesq_agent) — baixa relatórios do portal Sigpesq
- [retrieve_edital](https://github.com/ifesserra-lab/retrieve_edital) — download automatizado de editais (Playwright)
- [homologacao-ponto](https://github.com/ifesserra-lab/homologacao-ponto) — extração do Espelho de Ponto do SIGRH

**Portais, sites & busca**
- [portal_edital](https://github.com/ifesserra-lab/portal_edital) — portal de editais (Astro + Tailwind + BDD)
- [gedoc-ifes-busca](https://github.com/ifesserra-lab/gedoc-ifes-busca) — busca de documentos
- [sbf](https://github.com/ifesserra-lab/sbf) — Simpósio Regional de Física (Campus Serra)
- [ifesserra-lab.github.io](https://github.com/ifesserra-lab/ifesserra-lab.github.io) — site institucional do laboratório

> Lista completa em [todos os repositórios](https://github.com/orgs/ifesserra-lab/repositories).

## Fontes originais dos dados

| Fonte | Usada em |
|:--|:--|
| [SRC — consulta pública de ações](https://src.ifes.edu.br/src/public/consulta-acao.xhtml) | SRC, Diretoria |
| [SigPesq](https://sigpesq.ifes.edu.br/) | Horizon |
| [Plataforma Lattes](http://lattes.cnpq.br/) | Horizon |
| [LinkedIn](https://www.linkedin.com) | Egressos |
| [IBGE — SIDRA](https://apisidra.ibge.gov.br/) | Egressos |
| [Ipeadata](http://www.ipeadata.gov.br/) | Egressos |
| [Stack Overflow Developer Survey](https://survey.stackoverflow.co/) | Egressos |

---

**IFES — Campus Serra** · [serra.ifes.edu.br](https://serra.ifes.edu.br/) · [github.com/ifesserra-lab](https://github.com/ifesserra-lab)
