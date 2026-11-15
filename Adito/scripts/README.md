# Ambiente PostgreSQL — Modelo Unificado (Oraculo)

Este diretório contém a infraestrutura em Docker e os scripts SQL para provisionar o banco de dados PostgreSQL com o schema relacional unificado extraído do modelo de classes Astah (`ModeloClassesUnificado.asta`).

---

## 🚀 Como Subir o Banco

Na raiz deste diretório (`Adito/scripts/`):

### 1. Inicialização Automática e Validação
```bash
./recriar_banco.sh
```
O script:
1. Carrega o `.env` (porta padrão: `5435`).
2. Sobe o container `oraculo_postgres_unificado`.
3. Executa os scripts da pasta `sql/` na ordem correta (`00` a `99`).
4. Imprime o relatório de validação das tabelas e chaves criadas.

### 2. Ou via Docker Compose padrão
```bash
docker compose up -d
```

---

## 🔌 Conexão

| Parâmetro | Valor Padrão |
| :--- | :--- |
| **Host** | `localhost` |
| **Porta** | `5435` |
| **Database** | `oraculo_db` |
| **Usuário** | `oraculo` |
| **Senha** | `oraculo_password` |
| **Schema Padrão** | `unificado` |

Comando para conectar via `psql` direto no container:
```bash
docker compose exec -it oraculo-postgres psql -U oraculo -d oraculo_db
```

---

## 📁 Estrutura dos Scripts SQL

* `sql/00_schema.sql`: Cria o schema `unificado` e configura o `search_path`.
* `sql/01_tipos_e_dominios.sql`: Define os 16 tipos `ENUM` nativos e cria/popula as 14 tabelas de domínio.
* `sql/02_tabelas.sql`: Cria todas as tabelas de entidades de negócio, aplicando herança com chaves primárias e estrangeiras alinhadas.
* `sql/03_relacionamentos_e_juncoes.sql`: Cria classes associativas (com `id`), tabelas de junção N:N puras (sem `id`) e índices de alta performance em FKs.
* `sql/99_validacao.sql`: Consultas de auditoria (contagem de tabelas, colunas, enums e domínios).

---

## 📥 Popular com os dados do ETL do Adito

`popular_banco.py` (só Python padrão, sem dependências) lê a pasta `Adito/etl/`, com `brutos/` de cada fonte e `trabalho/pessoas.json` do cruzamento. Ele gera um SQL só de `INSERT`, numa transação, e executa esse SQL com o `psql` do container.

```bash
docker compose up -d                                  # banco vazio
python3 popular_banco.py                               # lê ../etl (Adito/etl)
python3 popular_banco.py --so-gerar                    # só gera o SQL e o relatório
```

- **Estrutura intacta:** não altera o banco (nada de CREATE, ALTER, DROP ou TRUNCATE). Se já houver dados, a carga para sem gravar nada; para recarregar, rode `./recriar_banco.sh` antes.
- **Tabelas de domínio:** as do `01_tipos_e_dominios.sql` não recebem linhas novas. Valor fora delas ou fora de um ENUM vira NULL e aparece no relatório.
- **Pessoas:** uma linha em `pessoa` por pessoa do cruzamento (nome normalizado, regras do horizon_etl). O banco não tem CPF nem e-mail de pessoa (colunas removidas do DDL); telefone e fax não vêm do ETL e ficam vazios; endereço profissional (Lattes, sem telefone) e o endereço do grupo (CNPq) entram. Sexo e data de nascimento não existem mais no banco. Antes de executar, o SQL é conferido contra e-mail e CPF.
- **`pessoa_lattes`:** além dos titulares de currículo, tem linhas sem dados para quem só aparece num currículo (integrante de projeto, orientando, aluno de banca), porque as tabelas do Lattes exigem `pessoa_lattes`.
- **Orientações sem projeto:** a orientação do SigPesq cujo projeto não está no relatório de projetos ganha um `projeto_pesquisa` mínimo (só título).
- **Onde ficam as saídas:** o SQL e o relatório (`carga_banco.sql`, `carga_banco_relatorio.json`) vão para `<etl>/saida/`, fora deste repositório, porque têm nomes de pessoas.
- **Ligações inferidas (documentadas):** a ação do SRC só traz a grande área, então `acao.id_area_conhecimento` aponta para uma área com o nome da grande área; o Ifes e seus campi, em qualquer grafia das fontes, viram uma única organização (campus com `id_organizacao_pai` = Ifes); líder de grupo do SigPesq ganha a unidade do grupo, coordenador de projeto o campus do projeto e orientado sem campus o campus de execução; o nível do bolsista sai do programa (Pibic-Jr/EM = ensino médio, demais = graduação) quando o CNPq não informa.
- **CNPq:** grupo no DGP (situação, datas, repercussões, endereço e site), membros ativos e egressos, líderes, linhas de pesquisa e grande área, para os grupos que também estão no SigPesq.

---

## 📤 Exportar JSON para o DuckDB

`exportar_json.py` (apenas biblioteca padrão do Python 3.10+) lê o schema `unificado` do PostgreSQL em modo estritamente somente leitura (`BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY; ... ROLLBACK;`) e gera em `Adito/etl/saida/json/` um arquivo `<tabela>.json` por tabela usada pelas views analíticas de `Docs/Fatos/PropostaFatos.md`, além de `manifesto.json`.

### Por que exporta tabelas e não as views
O PostgreSQL continua sendo a base relacional oficial em 3ª Forma Normal (3FN). O aplicativo desktop ("Oráculo") consultará seis views analíticas desnormalizadas (`vfact_*_resolved`) em um **DuckDB embutido**, sem depender de servidor PostgreSQL. Por isso, `exportar_json.py` exporta uma fotografia consistente das **tabelas base** (com mesmas colunas, mesmos IDs e chaves estrangeiras coerentes entre si) e um manifesto de schema; as views serão recriadas diretamente no DuckDB de destino.

### Pré-requisitos e modos de execução
O banco `unificado` já deve estar criado (`./recriar_banco.sh`) e populado (`python3 popular_banco.py`). Se o banco estiver vazio ou faltar alguma tabela da lista, o script para e avisa sem criar nem alterar nada.

1. **Modo `docker` (padrão):** executa `docker compose exec -T <servico> psql ...` lendo serviço, banco e usuário de `Adito/scripts/docker-compose.yml` (e `.env` / `.env.example`):
   ```bash
   python3 Adito/scripts/exportar_json.py
   python3 Adito/scripts/exportar_json.py --forcar
   python3 Adito/scripts/exportar_json.py --tabelas pessoa,organizacao,acao --saida /caminho/saida/json
   ```
2. **Modo `conexao`:** usa um cliente `psql` local apontando para qualquer PostgreSQL com o schema `unificado`, configurado pelas variáveis padrão da `libpq` (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` e `.pgpass` / variável de ambiente de sessão):
   ```bash
   PGHOST=localhost PGPORT=5435 PGDATABASE=oraculo_db PGUSER=oraculo \
     python3 Adito/scripts/exportar_json.py --modo conexao --forcar
   ```
3. **Somente validação (`--so-validar`):** revalida uma pasta já exportada (JSON válido, contagens, ordem das colunas e integridade referencial das FKs) sem conectar ao PostgreSQL:
   ```bash
   python3 Adito/scripts/exportar_json.py --so-validar Adito/etl/saida/json
   ```

### Lista de tabelas (41 tabelas) e como atualizar
A lista de tabelas vem de `Docs/Fatos/PropostaFatos.md` (commit `c91761a`), agrupada na constante `TABELAS_POR_VIEW` em `exportar_json.py` (40 tabelas referenciadas nos blocos `CREATE OR REPLACE VIEW` mais `parceiro_demandante_projeto`, citada no texto da seção 3.3.3):

| View | Tabelas usadas |
| :--- | :--- |
| `vfact_extensao_acao_resolved` | `acao`, `acao_campus`, `area_conhecimento`, `atividade`, `fomento_acao`, `grande_area`, `iniciativa`, `natureza`, `organizacao`, `pessoa`, `tipo_acao` |
| `vfact_extensao_participacao_resolved` | `acao`, `acao_campus`, `atividade`, `iniciativa`, `organizacao`, `pessoa`, `registro_participante`, `situacao_participante`, `tipo_acao`, `tipo_atividade` |
| `vfact_projeto_pesquisa_resolved` | `area_conhecimento`, `grande_area`, `iniciativa`, `organizacao`, `parceiro_demandante_projeto`, `pesquisador`, `pessoa`, `plano_trabalho`, `projeto_pesquisa`, `titulacao` |
| `vfact_orientacao_bolsa_resolved` | `area_conhecimento`, `curso`, `edital`, `estudante`, `grande_area`, `iniciativa`, `nivel_treinamento`, `organizacao`, `orientacao`, `pesquisador`, `pessoa`, `plano_trabalho`, `programa`, `projeto_pesquisa`, `titulacao` |
| `vfact_producao_cientifica_resolved` | `artigo_trabalho_evento`, `autoria_producao`, `categoria_producao_tecnica`, `livro_capitulo`, `organizacao`, `patente_registro`, `pesquisador`, `pessoa`, `pessoa_lattes`, `producao`, `producao_tecnica_artistica_bibliografica`, `tipo_artigo_evento`, `tipo_livro_capitulo`, `tipo_patente_registro` |
| `vfact_grupo_pesquisa_membro_resolved` | `area_conhecimento`, `grande_area`, `grupo_pesquisa`, `grupo_pesquisa_cnpq`, `membro_grupo`, `membro_grupo_cnpq`, `organizacao`, `papel`, `pesquisador`, `pessoa`, `titulacao` |

---

## 🦆 Gerar o Banco Analítico DuckDB OLAP (`gerar_duckdb.py`)

`gerar_duckdb.py` lê `Adito/etl/saida/json/manifesto.json` e os 41 arquivos `<tabela>.json`, recria o schema `unificado` com tipagem explícita no DuckDB e **materializa as 6 tabelas fato (`CREATE TABLE main.vfact_*_resolved AS SELECT ...`)** definidas em `Docs/Fatos/PropostaFatos.md` em formato colunar nativo `v1.2.0` para máxima velocidade OLAP no Adito.

```bash
# Gera Adito/app/data/dados.duckdb e valida as contagens das 41 tabelas base e das 6 tabelas fato
../app/.venv/bin/python gerar_duckdb.py

# Ou especificando um caminho customizado de saída
../app/.venv/bin/python gerar_duckdb.py --saida /caminho/para/dados.duckdb
```

Tabelas fato materializadas no schema `main` (e expostas como views equivalentes em `unificado`):
- `vfact_extensao_acao_resolved` (`207` linhas)
- `vfact_extensao_participacao_resolved` (`6.741` linhas)
- `vfact_projeto_pesquisa_resolved` (`236` linhas)
- `vfact_orientacao_bolsa_resolved` (`1.203` linhas)
- `vfact_producao_cientifica_resolved` (`1.232` linhas)
- `vfact_grupo_pesquisa_membro_resolved` (`553` linhas)
