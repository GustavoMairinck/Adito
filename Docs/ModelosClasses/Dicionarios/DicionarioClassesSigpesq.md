# Dicionário de Dados do Modelo de Classes SigPesq

**Arquivo de Referência:** `Adito/Docs/ModelosClasses/ModeloClassesSigpesq.asta` (Diagrama de Classes UML do SIGPESq)  
**Bases de Origem (Extração Bruta do ETL Horizon):** Planilhas oficiais extraídas do SIGPESq presentes em `horizon_etl/data/raw/sigpesq/`:
* `horizon_etl/data/raw/sigpesq/research_group/Relatorio_16_10_2026.xlsx`
* `horizon_etl/data/raw/sigpesq/research_projects/Relatorio_16_10_2026.xlsx`
* `horizon_etl/data/raw/sigpesq/advisorships/*/Relatorio_16_10_2026.xlsx` (ciclos anuais de 2016 a 2026)

---

## Sumário das Classes, Associações e Enums do Modelo

1. **Núcleo de Pessoas e Atores:**
   * [`Pessoa`](#1-classe-pessoa) (Superclasse)
   * [`Pesquisador`](#2-classe-pesquisador) (Especialização de `Pessoa`)
   * [`Estudante`](#3-classe-estudante) (Especialização de `Pessoa`)
2. **Atividades e Estruturas de Pesquisa:**
   * [`ProjetoPesquisa`](#4-classe-projetopesquisa)
   * [`GrupoPesquisa`](#5-classe-grupopesquisa)
   * [`Orientacao`](#6-classe-orientacao)
   * [`PlanoTrabalho`](#7-classe-planotrabalho)
3. **Organização Institucional e Acadêmica:**
   * [`Campus`](#8-classe-campus)
   * [`Curso`](#9-classe-curso)
   * [`AreaConhecimento`](#10-classe-areaconhecimento)
   * [`GrandeArea`](#11-classe-grandearea)
4. **Agentes Externos, Parcerias e Fomento:**
   * [`ParceiroDemandante`](#12-classe-parceirodemandante)
   * [`GrupoPesquisaExterno`](#13-classe-grupopesquisaexterno)
   * [`AgenciaFinanciamento`](#14-classe-agenciafinanciamento)
   * [`Edital`](#15-classe-edital)
5. **Tipos Enumerados (`<<enumeration>>`):**
   * [`SituacaoGrupo`](#16-enum-situacaogrupo)
   * [`NaturezaProjeto`](#17-enum-naturezaprojeto)
   * [`ParecerDiretoria`](#18-enum-parecerdiretoria)
   * [`Modalidade`](#19-enum-modalidade)
   * [`Gerenciamento`](#20-enum-gerenciamento)
   * [`Programa`](#21-enum-programa)

---

## 1. Núcleo de Pessoas e Atores

### 1. Classe: `Pessoa`
Superclasse conceitual generalizada que unifica qualquer indivíduo físico registrado no ecossistema de pesquisa institucional do Ifes.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `research_group` (`Lideres`)<br>• `research_projects` (`Coordenador`, `Pesquisadores`, `Estudantes`)<br>• `advisorships` (`Orientador`, `Orientado`) | Nome civil completo da pessoa física. Chave fundamental para resolução de identidade de pesquisadores e discentes. | `"Carlos Eduardo de Oliveira"`, `"Mariana Souza Ribeiro"`, `"Lucas Mendes Pereira"` *(exemplo fictício)* |
| **`email`** | `String` | `0..*` | • `research_group` (`Lideres` - extraído entre parênteses)<br>• `research_projects` (`EmailCoordenador`)<br>• `advisorships` (`OrientadorEmail`, `OrientadoEmail`) | Endereço de correio eletrônico de contato (pessoal ou institucional `@ifes.edu.br`). Uma pessoa pode acumular múltiplos endereços nos diferentes relatórios. | `"pesquisador.exemplo@ifes.edu.br"`, `"coordenador.projeto@ifes.edu.br"`, `"estudante.pesquisa@email.com"` *(exemplo fictício)* |
| **`cpf`** | `String` | `0..1` | • `advisorships` (`OrientadoCpf`) | Cadastro de Pessoa Física da Receita Federal. No SIGPESq bruto, vem informado apenas para os alunos orientados na planilha de orientações/bolsas; nos projetos de pesquisa e grupos não há coluna de CPF. | `"12345678901"`, `"98765432100"` *(exemplo fictício)* |
| **`celular`** | `String` | `0..1` | • `advisorships` (`CelularOrientador`, `CelularOrientado`) | Número de telefone móvel para contato direto, com código de área (DDD). Preenchido nos registros de orientações. | `"(27) 99999-1234"`, `"(27) 98888-5678"` *(exemplo fictício)* |

---

### 2. Classe: `Pesquisador`
Especialização de `Pessoa`. Representa o servidor docente, técnico-administrativo ou pesquisador colaborador com formação acadêmica que formula, coordena ou colabora em projetos e orienta bolsistas.

* **Herança:** Herda todos os atributos de `Pessoa` (`nome`, `email`, `cpf`, `celular`).
* **Papéis e Associações no Modelo:**
  * `coordena`: `Pesquisador [1]` $\leftarrow$ `ProjetoPesquisa [0..*]` (Coordenador técnico-científico do projeto).
  * `participa`: `Pesquisador [1..*]` $\leftarrow$ `ProjetoPesquisa [0..*]` (Pesquisador membro de equipe de projeto).
  * `lidera`: `Pesquisador [1..*]` $\leftarrow$ `GrupoPesquisa [1..*]` (Líder ou vice-líder cadastrado no DGP/CNPq).
  * `orienta`: `Pesquisador [1]` $\leftarrow$ `Orientacao [0..*]` (Orientador de plano de trabalho acadêmico).
  * `pertence a`: `Pesquisador [0..*]` $\rightarrow$ `Campus [0..1]` (Lotação funcional do pesquisador, oriunda de `CampusOrientador` em `advisorships`).

---

### 3. Classe: `Estudante`
Especialização de `Pessoa`. Representa o discente em nível técnico, graduação ou pós-graduação vinculado a atividades de Iniciação Científica e Tecnológica.

* **Herança:** Herda todos os atributos de `Pessoa` (`nome`, `email`, `cpf`, `celular`).
* **Papéis e Associações no Modelo:**
  * `participa`: `Estudante [0..*]` $\leftarrow$ `ProjetoPesquisa [0..*]` (Discente participante na equipe de pesquisa).
  * `participa (orientado)`: `Estudante [1]` $\leftarrow$ `Orientacao [0..*]` (Discente executor do plano de trabalho).
  * `cursa`: `Estudante [0..*]` $\rightarrow$ `Curso [0..1]` (Curso de matrícula regular no Ifes, vindo de `advisorships.Curso`).
  * `pertence a`: `Estudante [0..*]` $\rightarrow$ `Campus [0..1]` (Campus de oferta do curso).

---

## 2. Atividades e Estruturas de Pesquisa

### 4. Classe: `ProjetoPesquisa`
Entidade central que modela um Projeto de Pesquisa Institucional submetido, aprovado e homologado no Ifes.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`id`** | `int` | `1` | • `research_projects` (`Id`)<br>• `advisorships` (`CodPJ` - após extração do prefixo `"PJ "`) | Identificador inteiro único do projeto gerado pelo SIGPESq. Chave primária de relacionamento entre projetos e orientações. | `6903`, `7809`, `8448` |
| **`nome`** | `String` | `1` | • `research_projects` (`Titulo`)<br>• `advisorships` (`TituloPJ`) | Título formal e oficial da proposta de pesquisa aprovada. | `"A necessidade de metodologias e ferramentas adequadas para avaliação, desenvolvimento e validação de ideias no contexto dos habitats e ambientes de inovação."`, `"Laboratório Espaço Energia: avanços na mobilidade elétrica com a implantação de eletroposto para recarga de veículos elétricos"` |
| **`data_inicio`** | `Date` | `1` | • `research_projects` (`Inicio`) | Data formal de início da vigência do projeto. Padrão no arquivo bruto `dd-mm-yy` (convertido para ISO `YYYY-MM-DD`). | `2022-08-01` (na planilha: `"01-08-22"`) |
| **`data_fim`** | `Date` | `1` | • `research_projects` (`Fim`) | Data final prevista ou prorrogada para a conclusão das atividades da pesquisa. | `2026-12-31` (na planilha: `"31-12-26"`) |
| **`linha_pesquisa`** | `String` | `0..1` | • `research_projects` (`LinhaPesquisa`) | Linha temática de investigação na qual o projeto se insere dentro de seu grupo de pesquisa. Nulo quando não declarada. | `"Engenharia de Software e Ciência de Dados"`, `"Inteligência Artificial e Processamento de Linguagem Natural"`, `"Prototipagem e Simulação para agricultura 4.0"` |
| **`palavras_chave`** | `String` | `0..1` | • `research_projects` (`PalavraChave`) | Termos descritores do conteúdo temático do projeto, separados por ponto-e-vírgula ou quebras de linha no formulário. | `"Processo;\nMetodologias Ágeis;\nPrototipação;\nDesign Sprint;\nDesign Thinking;\nValidação;"` |
| **`sigilo`** | `boolean` | `1` | • `research_projects` (`Sigilo`) | Indicador booleano que define se o projeto possui cláusula de confidencialidade/sigilo industrial ou tecnológico. | `false`, `true` |

* **Associações da Classe `ProjetoPesquisa`:**
  * `coordena`: `Pesquisador [1]` (Coordenador do projeto, vindo de `research_projects.Coordenador`).
  * `participa`: `Pesquisador [1..*]` (Pesquisadores da equipe, vindos de `research_projects.Pesquisadores`).
  * `participa`: `Estudante [0..*]` (Estudantes da equipe, vindos de `research_projects.Estudantes`).
  * `ocorre em`: `Campus [1]` (Campus de execução física do projeto, vindo de `research_projects.CampusExecucao`).
  * `tem`: `AreaConhecimento [1]` (Área temática CNPq, vinda de `research_projects.AreaConhecimento`).
  * `atua em`: `GrupoPesquisa [0..*]` (Grupo institucional vinculado, vindo de `research_projects.GrupoPesquisa`).
  * `demanda`: `ParceiroDemandante [0..*]` (Entidade externa beneficiária, vinda de `research_projects.ParceiroDemandante`).
  * `coopera`: `GrupoPesquisaExterno [0..*]` (Laboratório ou grupo de outra IES parceira, vindo de `research_projects.GrupoPesquisaExterno`).
  * `possui`: `PlanoTrabalho [0..*]` (Planos de trabalho específicos submetidos vinculados ao projeto).
  * Associação de Enumeração: `NaturezaProjeto [1]` (vinda de `research_projects.Natureza`).
  * Associação de Enumeração: `ParecerDiretoria [1]` (vinda de `research_projects.ParecerDiretoria`).

---

### 5. Classe: `GrupoPesquisa`
Representa um Grupo de Pesquisa formalmente instituído no Ifes e chancelado pela instituição no Diretório dos Grupos de Pesquisa do CNPq (DGP).

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `research_group` (`Nome`)<br>• `research_projects` (`GrupoPesquisa`) | Nome por extenso oficial do grupo certificado no CNPq. Chave nominal de vínculo com os projetos. | `"Divulgação e Popularizaçao da Ciência"`, `"Núcleo de Estudos em Agroecologia e Produção Orgânica"`, `"Grupo de Automação Industrial - GAIn"` |
| **`sigla`** | `String` | `0..1` | • `research_group` (`Sigla`) | Sigla, código mnemônico ou acrônimo acadêmico do grupo. | `"DIVIPOP "`, `"NETRA"`, `"BioEn"`, `"GAIn"` |
| **`url_cnpq`** | `String` | `1` | • `research_group` (`Column1`) | Endereço URL público do espelho oficial do grupo no portal DGP/CNPq (`http://dgp.cnpq.br/dgp/espelhogrupo/<id_16_digitos>`). | `"http://dgp.cnpq.br/dgp/espelhogrupo/4439471564090237"`, `"http://dgp.cnpq.br/dgp/espelhogrupo/4099181037333209"` |

* **Associações da Classe `GrupoPesquisa`:**
  * `lidera`: `Pesquisador [1..*]` (Líderes docentes e pesquisadores registrados em `research_group.Lideres`).
  * `pertence a`: `Campus [1]` (Campus sede do grupo, registrado em `research_group.Unidade`).
  * `tem`: `AreaConhecimento [1]` (Área predominante do CNPq, vinda de `research_group.AreaConhecimento`).
  * `atua em`: `ProjetoPesquisa [0..*]` (Projetos executados sob o escopo do grupo).
  * Associação de Enumeração: `SituacaoGrupo [1]` (Situação perante a PRPPG/CNPq, vinda de `research_group.ParecerDiretoria`).

---

### 6. Classe: `Orientacao`
Representa o vínculo individualizado de orientação entre um orientador docente e um discente para a execução de um plano de trabalho durante um ciclo anual de fomento/pesquisa.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`id`** | `int` | `1` | • `advisorships` (`Id`) | Identificador numérico único da orientação no SIGPESq. | `10512`, `5439`, `6254`, `7715` |
| **`ano`** | `int` | `1` | • `advisorships` (`Ano`) | Exercício anual de referência do ciclo do edital ou da pesquisa. | `2016`, `2022`, `2024`, `2026` |
| **`valor_bolsa`** | `float` | `0..1` | • `advisorships` (`Valor`) | Quantia monetária mensal (em BRL) repassada ao estudante bolsista. Nulo ou `0.0` para modalidades voluntárias. | `400.00`, `100.00`, `600.00`, `700.00` |
| **`data_inicio`** | `Date` | `1` | • `advisorships` (`Inicio`) | Data formal de início das atividades do bolsista/voluntário. Formato no bruto `dd-mm-yy`. | `2024-09-02` (na planilha: `"02-09-24"`) |
| **`data_fim`** | `Date` | `1` | • `advisorships` (`Fim`) | Data final prevista para a vigência do plano de trabalho discente. | `2025-08-31` (na planilha: `"31-08-25"`) |
| **`cancelado`** | `boolean` | `1` | • `advisorships` (`Cancelado`) | Indicador booleano que expressa se a orientação foi cancelada antecipadamente (por desistência, formatura ou desligamento). | `false`, `true` |
| **`nome_cancelador`** | `String` | `0..1` | • `advisorships` (`CanceladoPor`) | Nome do gestor ou autoridade institucional que homologou a interrupção precoce da bolsa. Extraído da string textual da coluna. | `"Gestor de Pesquisa da Silva"`, `"Coordenador Santos Oliveira"` *(exemplo fictício)* |
| **`data_cancelado`** | `Date` | `0..1` | • `advisorships` (`CanceladoPor`) | Data e hora em que ocorreu o registro formal do cancelamento no portal. | `2023-04-24 16:09:00`, `2022-09-06 13:18:00` |
| **`relatorio_enviado`** | `boolean` | `1` | • `advisorships` (`AvaliacaoRelatorio`) | Flag booleano derivado: `true` se o discente submeteu o relatório técnico final (`"Enviado"`, `"Aceito"`, `"Corrigir"`), e `false` se `"Não Enviado"`. | `true`, `false` |

* **Associações da Classe `Orientacao`:**
  * `orientador`: `Pesquisador [1]` (Docente responsável pela tutoria acadêmica, vindo de `advisorships.Orientador`).
  * `orientado`: `Estudante [1]` (Discente executor do plano de trabalho, vindo de `advisorships.Orientado`).
  * `possui`: `PlanoTrabalho [1]` (Plano de trabalho específico tutelado).
  * `pertence a`: `Campus [1]` (Campus de execução da orientação, vindo de `advisorships.CampusExecucao`).
  * `financia`: `AgenciaFinanciamento [0..1]` (Órgão pagador da bolsa, vindo de `advisorships.AgFinanciadora`).
  * Associação de Enumeração: `Modalidade [1]` (vinda de `advisorships.Modalidade`).
  * Associação de Enumeração: `Gerenciamento [1]` (vinda de `advisorships.Gerenciamento`).
  * Associação de Enumeração: `Programa [0..1]` (vinda de `advisorships.Programa`).

---

### 7. Classe: `PlanoTrabalho`
Representa a proposta científica e metodológica detalhada atribuída a um estudante, subordinada a um projeto de pesquisa mãe.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`codigo`** | `String` | `1` | • `advisorships` (`CodPT`) | Código alfanumérico identificador do Plano de Trabalho gerado pelo SIGPESq. | `"PT     18438"`, `"PT2022-0012"`, `"8448-1"` |
| **`titulo`** | `String` | `1` | • `advisorships` (`TituloPT`) | Título temático e descritivo das metas individuais de pesquisa do estudante. | `"Estudo do eletroposto, suas características técnicas e comerciais."`, `"Desenvolvimento de módulo IoT para sensoriamento"` |

* **Associações da Classe `PlanoTrabalho`:**
  * `possui`: `ProjetoPesquisa [1]` (Projeto-mãe ao qual o plano se subordina, vindo de `advisorships.CodPJ`).
  * `possui`: `Orientacao [0..*]` (Orientações que executaram ou deram continuidade ao plano).
  * `possui`: `Edital [0..1]` (Edital de seleção sob o qual o plano foi aprovado, vindo de `advisorships.Edital`).
  * `tem`: `AreaConhecimento [1]` (Área temática da pesquisa do discente).
  * Associação com `GrandeArea []` (Macro-área CNPq associada).

---

## 3. Organização Institucional e Acadêmica

### 8. Classe: `Campus`
Unidade acadêmica e administrativa territorial do Instituto Federal do Espírito Santo (Ifes).

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `research_group` (`Unidade`)<br>• `research_projects` (`CampusExecucao`)<br>• `advisorships` (`CampusExecucao`, `CampusOrientador`, `Campus`) | Nome oficial do Campus do Ifes onde o projeto, grupo ou orientação ocorre. | `"Serra"`, `"Vila Velha"`, `"Vitória"`, `"Colatina"`, `"Alegre"`, `"Itapina"`, `"Montanha"` |

---

### 9. Classe: `Curso`
Curso de formação técnica, graduação ou pós-graduação ofertado pelo Ifes no qual o estudante de pesquisa está matriculado.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `advisorships` (`Curso`) | Denominação oficial da habilitação discente. | `"Engenharia de Controle e Automação"`, `"Sistemas de Informação"`, `"Técnico em Informática"`, `"Licenciatura em Química"` |

---

### 10. Classe: `AreaConhecimento`
Classificação temática segundo a Árvore do Conhecimento oficial do CNPq (nível 2), organizando as competências de projetos, grupos e planos.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `research_group` (`AreaConhecimento`)<br>• `research_projects` (`AreaConhecimento`)<br>• `advisorships` (`AreaConhecimento`) | Denominação oficial da área de especialização do CNPq. | `"Engenharia Elétrica"`, `"Ciência da Computação"`, `"Educação"`, `"Engenharia Agrícola"`, `"Filosofia"` |

* **Associação:**
  * `possui`: `GrandeArea [0..1]` (Relação hierárquica taxonômica com o nível 1 da tabela CNPq).

---

### 11. Classe: `GrandeArea`
Nível macro (nível 1) da Árvore do Conhecimento do CNPq, reunindo áreas correlatas do saber.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `advisorships` (`GradeArea` - *sic*) | Nome da grande área cadastrada no CNPq. | `"Engenharias"`, `"Ciências Exatas e da Terra"`, `"Ciências Humanas"`, `"Multidisciplinar"`, `"Ciências Agrárias"` |

---

## 4. Agentes Externos, Parcerias e Fomento

### 12. Classe: `ParceiroDemandante`
Pessoa jurídica externa (empresa pública ou privada, indústria, fundação ou secretaria governamental) demandante ou beneficiária direta da pesquisa.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `research_projects` (`ParceiroDemandante`) | Razão social ou nome de fantasia da entidade demandante parceira do Ifes. | `"Coordenadoria Estadual de Proteção e Defesa Civil"`, `"Mogai Tecnologia da Informação"`, `"Vale S.A. e Gaintech Ltda."`, `"ArcelorMittal Brasil"` |

---

### 13. Classe: `GrupoPesquisaExterno`
Laboratório, grupo de pesquisa ou núcleo de inovação pertencente a outra universidade ou instituto parceiro em cooperação interinstitucional com o Ifes.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `research_projects` (`GrupoPesquisaExterno`) | Sigla ou denominação do grupo conveniado de outra instituição de ensino e pesquisa. | `"LABCISNE"`, `"LCAD"`, `"Inova E-Pq"`, `"NEES – Núcleo de Excelência em Tecnologias Sociais (UFAL)"` |

---

### 14. Classe: `AgenciaFinanciamento`
Entidade ou fundo responsável pelo aporte de recursos financeiros para pagamento das cotas de bolsa discente.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `advisorships` (`AgFinanciadora`) | Denominação da agência pública de fomento à pesquisa. Em modalidades não-remuneradas, a planilha preenche `"Voluntário"`. | `"CNPq"`, `"Fapes"`, `"Ifes"`, `"Finep"` |

---

### 15. Classe: `Edital`
Ato convocatório público institucional regulamentador do processo de submissão, seleção e concessão de cotas de pesquisa.

| Atributo | Tipo UML | Multiplicidade | Planilha Fonte / Coluna Original | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`titulo`** | `String` | `1` | • `advisorships` (`Edital`) | Identificação formal contendo número, ano e modalidade do edital institucional da PRPPG/Ifes. | `"06/2017 - Pibiti"`, `"05/2018 - Pibic"`, `"03/2023 - Picti"`, `"04/2020 - Pibic-Jr"` |

---

## 5. Tipos Enumerados (`<<enumeration>>`)

### 16. Enum: `SituacaoGrupo`
Status formal da situação do Grupo de Pesquisa junto à PRPPG e ao Diretório do CNPq.
* **Origem:** `research_group.ParecerDiretoria`
* **Literais no Modelo Astah:**
  * **`salvo`:** Grupo com proposta em elaboração ou rascunho no sistema.
  * **`recusado`:** Criação indeferida pela comissão técnica ou diretoria de pesquisa.
  * **`certificado`:** Grupo aprovado pelo Ifes e certificado como ativo na base nacional do CNPq.
  * **`excluidoCNPQ`:** Grupo que teve sua certificação cancelada ou foi descredenciado no CNPq por inatividade.

---

### 17. Enum: `NaturezaProjeto`
Classificação metodológica quanto ao direcionamento e aplicabilidade dos resultados da pesquisa.
* **Origem:** `research_projects.Natureza`
* **Literais no Modelo Astah:**
  * **`pesquisa_aplicada`:** Focada na geração de protótipos, processos, tecnologias e soluções para problemas concretos da sociedade e da indústria (na planilha bruta: `"Pesquisa Aplicada"`).
  * **`pesquisa_basica`:** Focada na aquisição de novos conhecimentos teóricos e avanços conceituais sem aplicação imediata predeterminada (na planilha bruta: `"Pesquisa Básica"`).

---

### 18. Enum: `ParecerDiretoria`
Etapa avaliativa do trâmite administrativo da proposta de projeto de pesquisa perante a Diretoria de Pesquisa / PRPPG.
* **Origem:** `research_projects.ParecerDiretoria`
* **Literais no Modelo Astah:**
  * **`aprovado`:** Proposta avaliada no mérito acadêmico e autorizada para execução formal (na planilha: `"Aprovado"`).
  * **`recusado`:** Proposta com parecer desfavorável ou não selecionada (na planilha: `"Recusado"`).
  * **`aprovacao_solicitada`:** Proposta submetida que se encontra aguardando julgamento (na planilha: `"Aprovação Solicitada"`).
  * **`salvo`:** Proposta ainda em preenchimento pelo coordenador, em fase de rascunho (na planilha: `"Salvo"`).

---

### 19. Enum: `Modalidade`
Condição de fomento financeiro vinculada à orientação discente.
* **Origem:** `advisorships.Modalidade`
* **Literais no Modelo Astah:**
  * **`bolsista`:** Discente com contraprestação financeira mensal (na planilha: `"Bolsista"`).
  * **`voluntario`:** Discente com vínculo formal sem pagamento pecuniário de bolsa (na planilha: `"Voluntário"`).

---

### 20. Enum: `Gerenciamento`
Instância de governança responsável pelo ciclo de gestão da orientação.
* **Origem:** `advisorships.Gerenciamento`
* **Literais no Modelo Astah:**
  * **`reitoria`:** Orientações oriundas de editais institucionais geridos pela PRPPG (na planilha: `"Reitoria"`).
  * **`independente`:** Orientações descentralizadas cadastradas em fluxo contínuo nos campi sem edital centralizado (na planilha: `"Independente"`).

---

### 21. Enum: `Programa`
Linha institucional ou política de Iniciação Científica e Tecnológica à qual a orientação está subordinada.
* **Origem:** `advisorships.Programa`
* **Literais no Modelo Astah:**
  * **`pibic`:** Programa Institucional de Bolsas de Iniciação Científica (graduação).
  * **`pibiti`:** Programa Institucional de Iniciação em Desenvolvimento Tecnológico e Inovação.
  * **`pibic_jr`:** Programa de Iniciação Científica Júnior para discentes do Ensino Médio/Técnico.
  * **`pibic_af`:** Iniciação Científica com reserva de vagas para Ações Afirmativas.
  * **`piviti`:** Programa Institucional de Voluntariado em Desenvolvimento Tecnológico e Inovação.
  * **`finep`:** Pesquisas financiadas através de chamadas da Financiadora de Estudos e Projetos.
  * **`propos`:** Programa institucional de apoio e fomento à Pós-Graduação (*Stricto Sensu*).
  *(Nota: valores legados como `"Pivic"`, `"Pibic-EM"` e `"JTC"` encontrados na base histórica são normalizados no pipeline para as respectivas categorias institucionais).*
