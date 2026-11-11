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
* `sql/01_tipos_e_dominios.sql`: Define os 17 tipos `ENUM` nativos e cria/popula as 14 tabelas de domínio.
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
- **Pessoas:** uma linha em `pessoa` por pessoa do cruzamento (nome normalizado, regras do horizon_etl). CPF, e-mail, telefone, fax e data de nascimento não vêm do ETL e ficam vazios; sexo e endereço profissional (Lattes, sem telefone) e o endereço do grupo (CNPq) entram. Antes de executar, o SQL é conferido contra e-mail e CPF.
- **`pessoa_lattes`:** além dos titulares de currículo, tem linhas sem dados para quem só aparece num currículo (integrante de projeto, orientando, aluno de banca), porque as tabelas do Lattes exigem `pessoa_lattes`.
- **Orientações sem projeto:** a orientação do SigPesq cujo projeto não está no relatório de projetos ganha um `projeto_pesquisa` mínimo (só título).
- **Onde ficam as saídas:** o SQL e o relatório (`carga_banco.sql`, `carga_banco_relatorio.json`) vão para `<etl>/saida/`, fora deste repositório, porque têm nomes de pessoas.
- **Ligações inferidas (documentadas):** a ação do SRC só traz a grande área, então `acao.id_area_conhecimento` aponta para uma área com o nome da grande área; o Ifes e seus campi, em qualquer grafia das fontes, viram uma única organização (campus com `id_organizacao_pai` = Ifes); líder de grupo do SigPesq ganha a unidade do grupo, coordenador de projeto o campus do projeto e orientado sem campus o campus de execução; o nível do bolsista sai do programa (Pibic-Jr/EM = ensino médio, demais = graduação) quando o CNPq não informa.
- **CNPq:** grupo no DGP (situação, datas, repercussões, endereço e site), membros ativos e egressos, líderes, linhas de pesquisa e grande área, para os grupos que também estão no SigPesq.
