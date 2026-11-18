# Muninn (Muninn local do IFES)
<img width="700" height="76" alt="image" src="https://github.com/user-attachments/assets/bb871070-f07e-4c9a-b2fd-0a4e2146bb01" />



Painel que reúne os dados já públicos dos sistemas do IFES Campus Serra — SRC, Diretoria, Editais, Egressos e Horizon — numa visão única de pesquisa e extensão do campus.

Os dados vêm dos pipelines, painéis e agentes do **[ifesserra-lab](https://github.com/ifesserra-lab)**.

**[Site → ifesserra-lab.github.io](https://ifesserra-lab.github.io/)** &nbsp;·&nbsp; **[Painel de Extensão →](https://ifesserra-lab.github.io/src/)** &nbsp;·&nbsp; **[Pesquisa STEM →](https://ifesserra-lab.github.io/pesquisa-stem.html)**

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
