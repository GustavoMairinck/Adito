# Banco de Dados Acadêmicos — Modelo Unificado 100% SQLite (dados.db)

Este diretório contém os scripts SQL e os utilitários de carga e visualização da base de dados acadêmicos do Adito em **100% SQLite (`Adito/app/data/dados.db`)**.

A arquitetura adota o modelo **100% OLTP como Single Source of Truth**:
- **82 Tabelas Base** em 3ª Forma Normal (3FN), derivadas do `ModeloClassesUnificado.asta` sem as 3 tabelas de contato/PII vazias (`email`, `fax`, `telefone`), com integridade referencial estrita (`PRAGMA foreign_keys = ON`). Dessas, 42 alimentam diretamente as 6 views atuais, 2 são dependências de FK (`endereco`, `tipo_organizacao`) e 38 preservam dados acadêmicos já extraídos (Lattes, bancas, eventos, formação, linhas de pesquisa) para futuras views.
- **6 Tabelas Fato Analíticas** modeladas como **VIEWs relacionais dinâmicas (`vfact_*_resolved`)**, calculadas em tempo real sobre as tabelas base sem duplicação física em disco.
- **Segurança em Profundidade**: O backend desktop acessa o banco estritamente em modo somente-leitura (`mode=ro`, `PRAGMA query_only = ON`, `set_authorizer` e normalização Unicode NFD sem acento).
- **Zero Infraestrutura Externa**: Eliminação completa de Docker, PostgreSQL, DuckDB e arquivos JSON intermediários.

---

## 🚀 Como Criar e Popular o Banco (`dados.db`)

Na pasta `Adito/scripts/`, execute o script nativo em Python (sem dependências externas):

```bash
python popular_banco.py
```

O comando realiza o pipeline completo em **~1 segundo**:
1. Cria `Adito/app/data/dados.db` a partir dos scripts DDL (`00_schema.sql` até `04_fatos_views.sql`).
2. Lê os arquivos brutos do ETL (`SRC`, `SigPesq`, `Lattes`, `CNPq/DGP`) e o cruzamento (`trabalho/pessoas.json`).
3. Executa a carga atômica das 82 tabelas relacionais em transação única (`BEGIN TRANSACTION`).
4. Valida integridade referencial (`PRAGMA foreign_key_check`), varredura anti-PII (zero vazamento de CPFs e e-mails) e sanidade estrutural das 6 views analíticas.

### Ou via CLI `adito-etl`:
```bash
adito-etl popular-banco
```

---

## 🔍 Visualizar Dados e Views Analíticas (`ver_dados.py`)

Para inspecionar tabelas e consultar as views analíticas no terminal:

```bash
# Ver resumo geral de contagens e integridade
python ver_dados.py

# Ver dados de uma view analítica específica
python ver_dados.py vfact_projeto_pesquisa_resolved

# Ver dados de uma tabela base
python ver_dados.py pessoa
```

---

## 📁 Estrutura dos Scripts SQL (`sql/`)

Os scripts são executados na ordem topológica de dependência:

* `sql/00_schema.sql`: Pragmas de inicialização SQLite (`foreign_keys = ON`, `encoding = 'UTF-8'`).
* `sql/01_tipos_e_dominios.sql`: 14 tabelas de domínio com `AUTOINCREMENT` e domínios ampliados.
* `sql/02_tabelas.sql`: 48 tabelas de entidades de negócio e heranças em 3FN, com tipagem e chaves estrangeiras (excluindo `email`, `fax` e `telefone` por LGPD).
* `sql/03_relacionamentos_e_juncoes.sql`: 20 tabelas associativas (com `id`) e junções N:N puras, além de índices de performance.
* `sql/04_fatos_views.sql`: Definição SQLite das 6 views analíticas dinâmicas (`vfact_*_resolved`) com todas as correções de consistência e novos campos da especificação v2.0.
* `sql/99_validacao.sql`: Consultas de auditoria estrutural do schema SQLite.

---

## 📊 As 6 Tabelas Fato Analíticas (Views Dinâmicas)

As views são expostas para o agente de BI e para a interface do Adito:

| View Analítica | Descrição | Granularidade |
| :--- | :--- | :--- |
| `vfact_extensao_acao_resolved` | Ações de extensão cadastradas no SRC | 1 linha por Ação |
| `vfact_extensao_participacao_resolved` | Participações individuais em eventos/cursos de extensão | 1 linha por Participação |
| `vfact_projeto_pesquisa_resolved` | Projetos de pesquisa cadastrados no SigPesq | 1 linha por Projeto |
| `vfact_orientacao_bolsa_resolved` | Cotas e orientações de bolsas de pesquisa | 1 linha por Orientação |
| `vfact_producao_cientifica_resolved` | Produções científicas e acadêmicas (Lattes) | 1 linha por Produção/Autor |
| `vfact_grupo_pesquisa_membro_resolved` | Grupos e linhas de pesquisa certificados pelo CNPq | 1 linha por Membro/Grupo |
