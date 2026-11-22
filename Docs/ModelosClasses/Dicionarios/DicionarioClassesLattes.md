# Dicionário de Dados: Modelo de Classes Lattes

**Arquivo de Referência:** `Adito/Docs/ModelosClasses/ModeloClassesLattes.asta` (Diagrama de Classes UML `Lattes v4 - Modelo Conceitual Normalizado com Herança`)**Bases de Origem Analisadas:**

* Extração primária dos currículos Lattes em JSON: `horizon_etl/data/lattes_json/*.json` (126 currículos de pesquisadores do Ifes)
* Módulo de extração e regras de parse: `horizon_etl/src/adapters/sources/lattes_parser.py`

**Padrão:** Senior Data Architecture & ETL Documentation Standards
**Última Atualização:** 2026-11-11
**Status:** Auditado via Astah Java API e reconstruído do zero a partir dos 126 currículos Lattes reais extraídos pelo extrator do `horizon_etl`.

---

## 1. Visão Geral da Arquitetura do Modelo Lattes v4

O modelo `ModeloClassesLattes.asta` organiza os dados curriculares da **Plataforma Lattes / CNPq** estruturados em **23 classes conceituais** (incluindo hierarquia de herança com classes abstratas/generalizadas para organizações e produções intelectuais), **16 enumerações de domínio** e **24 associações relacionais**:

```mermaid
flowchart TD
    %% Entidade Central
    P["PESSOA (Pesquisador / Titular do CV)"]
  
    %% Atividades e Formação
    FA["FORMACAO_ACADEMICA"]
    AP["ATUACAO_PROFISSIONAL"]
    PRJ["PROJETO"]
    ORI["ORIENTACAO"]
    BE["BANCA_EXAMINADORA"]
    EC["EVENTO_CIENTIFICO"]
    IDI["IDIOMA"]
    PT["PREMIO_TITULO"]
    AA["AREA_ATUACAO"]
    LP["LINHA_PESQUISA"]
  
    %% Classes Associativas
    MP["MEMBRO_PROJETO (Associativa)"]
    PE["PARTICIPACAO_EVENTO (Associativa)"]
    PI["PROFICIENCIA_IDIOMA (Associativa)"]
    FP["FOMENTO_PROJETO (Associativa)"]

    %% Hierarquia de Organizações
    ORG["ORGANIZACAO (Superclasse)"]
    INS["INSTITUICAO"]
    IFIN["INSTITUICAO_FINANCIADORA"]

    %% Hierarquia de Produções
    PROD["PRODUCAO (Superclasse)"]
    ATE["ARTIGO_TRABALHO_EVENTO"]
    LC["LIVRO_CAPITULO"]
    PTAB["PRODUCAO_TECNICA_ARTISTICA_BIBLIOGRAFICA"]
    PAT["PATENTE_REGISTRO"]

    %% Herança e Especialização
    INS -->|especializa| ORG
    IFIN -->|especializa| ORG
    ATE -->|especializa| PROD
    LC -->|especializa| PROD
    PTAB -->|especializa| PROD
    PAT -->|especializa| PROD

    %% Relacionamentos de Pessoa
    P -->|1 : 0..*| FA
    P -->|1 : 0..*| AP
    P -->|1..* : 0..*| AA
    P -->|1..* : 0..*| LP
    P -->|1 : 0..*| PT
    P -->|1 : 0..*| ORI
    P -.->|0..1 orientando : 0..*| ORI
    P -->|1..* : 0..*| BE
    P -.->|1 candidato : 0..*| BE
    P -->|1..* : 0..*| PROD

    %% Relacionamentos Associativos
    P -->|1..* : 0..*| MP
    MP -->|1 : 0..*| PRJ
    
    P -->|1..* : 1..*| PE
    PE -->|1 : 0..*| EC
    
    P -->|1..* : 0..*| PI
    PI -->|1 : 0..*| IDI
    
    IFIN -->|0..* : 1..*| FP
    FP -->|1 : 0..*| PRJ

    %% Relacionamentos com Instituições
    INS -->|1 : 0..*| FA
    INS -->|1 : 0..*| AP
    INS -->|1 : 0..*| ORI
    INS -->|0..1 : 0..*| BE
    INS -->|1 : 0..*| PAT
    INS -->|0..1 : 0..*| PTAB
    IFIN -->|0..1 : 0..*| ORI
```

---

## 2. Dicionário Detalhado por Classe

---

### 2.1 Classe: `PESSOA`

Entidade raiz do currículo. Representa o pesquisador titular do currículo Lattes, bem como terceiros relacionados em produções (coautores), projetos (membros), bancas (examinadores e candidatos) e orientações (orientandos e orientadores).

| Nome do Atributo                    |    Tipo    | Multiplicidade | Origem no Extract                              | Significado do Atributo                                                                                                                                                                                                                                            | Exemplo Real                                                                                                                                                                                             |
| :---------------------------------- | :--------: | :------------: | :--------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`id_lattes`**             | `String` |     `1`     | `informacoes_pessoais.id_lattes`             | Identificador público permanente e único de 16 dígitos decimais atribuído pelo CNPq ao pesquisador (chave primária natural do currículo).🔒 **Privacidade:** Substituído por identificador sintético/fictício nos exemplos para desidentificação. | `"1234567890123456"`, `"9876543210987654"` *(fictício / anonimizado)*                                                                                                                             |
| **`nome_completo`**         | `String` |     `1`     | `informacoes_pessoais.nome_completo`         | Nome civil completo e oficial do pesquisador registrado no cadastro da Receita Federal e CNPq.🔒 **Privacidade (LGPD):** Nomes de pessoas físicas são estritamente anonimizados na documentação e dicionários de dados.                                 | `"Pesquisador(a) Titular A"` *(anonimizado)*, `"Docente Pesquisador(a) B"` *(anonimizado)*                                                                                                       |
| **`nome_citacoes`**         | `String` |     `1`     | `informacoes_pessoais.nome_citacoes`         | Variações bibliográficas e formatos de citação do nome do autor indexados em periódicos internacionais e anais de congressos, delimitados por ponto-e-vírgula.🔒 **Privacidade (LGPD):** Anonimizado com formato padrão ilustrativo.                 | `"SOBRENOME, Nome; SOBRENOME, N. M.; SOBRENOME, N."` *(anonimizado)*                                                                                                                                 |
| **`sexo`**                  |  `Sexo`  |     `1`     | `informacoes_pessoais.sexo`                  | Gênero autodeclarado pelo titular no cadastro individual do Lattes (`MASCULINO` / `FEMININO`).                                                                                                                                                                | `MASCULINO`, `FEMININO`                                                                                                                                                                              |
| **`texto_resumo`**          | `String` |     `1`     | `informacoes_pessoais.texto_resumo`          | Texto autobiográfico fornecido pelo pesquisador sintetizando sua trajetória acadêmica, titulação, cargos funcionais, linhas de pesquisa e destaques científicos.                                                                                             | `"Possui graduação em Química pela Universidade Federal do Espírito Santo (1998), mestrado em Produção Vegetal..."`                                                                              |
| **`bolsa_produtividade`**   | `String` |     `1`     | `informacoes_pessoais.bolsa_produtividade`   | Categoria e nível da bolsa de produtividade em pesquisa (PQ) ou desenvolvimento tecnológico (DT) outorgada pelo CNPq (vazio se o pesquisador não for bolsista ativo).                                                                                           | `"PQ Nível C"`, `"1D"`, `""`                                                                                                                                                                      |
| **`endereco_profissional`** | `String` |     `1`     | `informacoes_pessoais.endereco_profissional` | Endereço postal e de lotação funcional declarado pelo titular (instituição mantenedora, unidade/campus, rodovia ou rua, bairro, CEP, município, estado e telefone institucional).                                                                            | `"Instituto Federal de Educação, Ciência e Tecnologia do Espírito Santo, Campus São Mateus. Rodovia BR-101 Norte, Litorâneo, CEP 29932-540 - São Mateus, ES - Brasil Telefone: (27) 3771-****"` |
| **`url_curriculo`**         | `String` |     `1`     | `informacoes_pessoais.url`                   | Endereço web canônico e público para acesso direto ao currículo no portal oficial do CNPq.🔒 **Privacidade:** URL com identificador fictício/anonimizado.                                                                                               | `"http://lattes.cnpq.br/1234567890123456"` *(anonimizado)*                                                                                                                                           |
| **`data_atualizacao_cv`**   |  `Date`  |     `1`     | `informacoes_pessoais.atualizacao_cv`        | Data civil em que o pesquisador realizou e enviou a última sincronização de alterações cadastrais à base do CNPq (convertida do padrão `DD/MM/AAAA`).                                                                                                     | `2026-04-21` (de `"21/04/2026"`), `2026-09-29` (de `"29/09/2026"`)                                                                                                                               |

#### Associações da Classe `PESSOA`:

* **`possui formacao` $\rightarrow$ `FORMACAO_ACADEMICA [0..*]`:** Histórico de cursos de titulação obtidos pelo titular.
* **`atua em` $\rightarrow$ `ATUACAO_PROFISSIONAL [0..*]`:** Histórico de vínculos funcionais e empregatícios da pessoa.
* **`orienta` $\rightarrow$ `ORIENTACAO [0..*]`:** Orientações concluídas e em andamento onde a pessoa atuou como orientador principal ou coorientador.
* **`orientado em` $\rightarrow$ `ORIENTACAO [0..*]`:** Orientações em que a pessoa participou como estudante orientando.
* **`autor de` $\rightarrow$ `PRODUCAO [0..*]`:** Obras bibliográficas, técnicas, artísticas e patentes de autoria ou coautoria da pessoa.
* **`compoe banca` $\rightarrow$ `BANCA_EXAMINADORA [0..*]`:** Bancas examinadoras de titulação avaliadas pela pessoa.
* **`candidato em` $\rightarrow$ `BANCA_EXAMINADORA [0..*]`:** Bancas de defesa onde a pessoa atuou como candidato defendendo sua tese/dissertação.
* **`homenageado em` $\rightarrow$ `PREMIO_TITULO [0..*]`:** Prêmios, medalhas e distinções acadêmicas concedidas à pessoa.
* **`atua na area` $\rightarrow$ `AREA_ATUACAO [0..*]`:** Macro-áreas e especialidades de atuação científica do pesquisador.
* **`pesquisa em` $\rightarrow$ `LINHA_PESQUISA [0..*]`:** Eixos temáticos contínuos de investigação científica liderados ou integrados pela pessoa.
* **`MEMBRO_PROJETO` $\rightarrow$ `PROJETO [0..*]`:** Participação da pessoa em equipes de projetos (como coordenador ou integrante).
* **`PARTICIPACAO_EVENTO` $\rightarrow$ `EVENTO_CIENTIFICO [1..*]`:** Participação em congressos, simpósios e feiras (como participante, apresentador ou organizador).
* **`PROFICIENCIA_IDIOMA` $\rightarrow$ `IDIOMA [0..*]`:** Autoavaliação de competências de fala, leitura, escrita e compreensão em idiomas estrangeiros.

---

### 2.2 Classe: `ORGANIZACAO` (Superclasse Generalizada)

Superclasse que representa genericamente qualquer entidade jurídica (universidade, instituto de pesquisa, autarquia, agência governamental ou empresa) citada no currículo como promotora de ensino, vínculo empregatício, sede de execução ou financiadora.

| Nome do Atributo               |    Tipo    | Multiplicidade | Origem no Extract                                                                                                  | Significado do Atributo                                                                                               | Exemplo Real                                                                                                                                                                          |
| :----------------------------- | :--------: | :------------: | :----------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`nome_organizacao`** | `String` |     `1`     | `atuacao_profissional[].instituicao_nome`, `formacao_academica[].nome_instituicao` ou `financiadores[].nome` | Razão social ou nome institucional por extenso da universidade, instituto federal, empresa ou órgão governamental. | `"Universidade Federal de Minas Gerais"`, `"Instituto Federal de Educação, Ciência e Tecnologia do Espírito Santo"`, `"Fundação de Amparo a Pesquisa no Espírito Santo"` |
| **`sigla`**            | `String` |     `1`     | `atuacao_profissional[].instituicao_sigla` ou acrônimo entre vírgulas em `nome_instituicao`                  | Sigla oficial pela qual a organização é amplamente referenciada no meio acadêmico e corporativo.                  | `"UFMG"`, `"IFES"`, `"FAPES"`, `"UFES"`, `"CNPq"`                                                                                                                           |
| **`pais`**             | `String` |     `1`     | `atuacao_profissional[].instituicao_pais` ou país declarado ao final de `nome_instituicao`                    | País de origem ou sede administrativa da organização.                                                              | `"Brasil"`, `"Estados Unidos"`                                                                                                                                                    |

---

### 2.3 Classe: `INSTITUICAO` (Especialização de `ORGANIZACAO`)

Especialização de `ORGANIZACAO`. Modela entidades acadêmicas de ensino superior, institutos federais, centros de pesquisa e corporações parceiras onde o pesquisador estuda, atua, sedia bancas ou deposita ativos intelectuais.

* **Herança:** Herda todos os atributos de `ORGANIZACAO` (`nome_organizacao`, `sigla`, `pais`).

#### Associações da Classe `INSTITUICAO`:

* **`promove` $\rightarrow$ `FORMACAO_ACADEMICA [0..*]`:** Instituição promotora onde o titular cursou e obteve sua titulação.
* **`ocorre em` $\rightarrow$ `ATUACAO_PROFISSIONAL [0..*]`:** Instituição empregadora onde o vínculo funcional se desenvolve.
* **`ocorre em` $\rightarrow$ `ORIENTACAO [0..*]`:** Instituição de ensino vinculada à dissertação, tese ou TCC orientado.
* **`sediada em` $\rightarrow$ `BANCA_EXAMINADORA [0..*]`:** Universidade onde a sessão pública de defesa ocorreu.
* **`titular da patente` $\rightarrow$ `PATENTE_REGISTRO [0..*]`:** Instituição que figura como cotitular ou depositante da patente no INPI.
* **`sedia producao tecnica` $\rightarrow$ `PRODUCAO_TECNICA_ARTISTICA_BIBLIOGRAFICA [0..*]`:** Instituição parceira receptora ou coprodutora do produto técnico/software.

---

### 2.4 Classe: `INSTITUICAO_FINANCIADORA` (Especialização de `ORGANIZACAO`)

Especialização de `ORGANIZACAO`. Modela agências oficiais de fomento governamentais ou entidades privadas que fornecem auxílios orçamentários, financiamento de equipamentos ou cotas de bolsas para projetos e orientações.

* **Herança:** Herda todos os atributos de `ORGANIZACAO` (`nome_organizacao`, `sigla`, `pais`).

#### Associações da Classe `INSTITUICAO_FINANCIADORA`:

* **`FOMENTO_PROJETO` $\rightarrow$ `PROJETO [1..*]`:** Relação associativa com os projetos subsidiados com recursos orçamentários ou bolsas.
* **`financia orientacao` $\rightarrow$ `ORIENTACAO [0..*]`:** Agência concessora de bolsa de pós-graduação ou iniciação científica para o orientando.

---

### 2.5 Classe: `FORMACAO_ACADEMICA`

Histórico estruturado de cursos regulares de graduação, pós-graduação e aperfeiçoamento acadêmico concluídos ou em andamento pelo pesquisador.

| Nome do Atributo                |       Tipo       | Multiplicidade | Origem no Extract                                                                       | Significado do Atributo                                                                                                                                                                                                 | Exemplo Real                                                                                                                                                                     |
| :------------------------------ | :--------------: | :------------: | :-------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`tipo_formacao`**     | `TipoFormacao` |     `1`     | `formacao_academica[].tipo` (grau antes do conectivo `" em "`)                      | Grau ou nível acadêmico do curso realizado (`DOUTORADO`, `MESTRADO`, `GRADUACAO`, `ESPECIALIZACAO`, `POS_DOUTORADO`, `APERFEICOAMENTO`).                                                                  | `DOUTORADO`, `MESTRADO`, `GRADUACAO`                                                                                                                                       |
| **`curso`**             |    `String`    |     `1`     | `formacao_academica[].tipo` (extraído após `" em "`)                              | Nome oficial do curso, programa de pós-graduação ou área de titulação concluída.                                                                                                                                 | `"Ciências Química"`, `"Produção Vegetal"`, `"Química"`, `"Informática"`                                                                                           |
| **`ano_inicio`**        |   `Integer`   |     `1`     | `formacao_academica[].ano_inicio`                                                     | Ano civil de ingresso formal e início dos estudos no curso.                                                                                                                                                            | `2012`, `1998`, `2015`                                                                                                                                                     |
| **`ano_conclusao`**     |   `Integer`   |     `1`     | `formacao_academica[].ano_conclusao`                                                  | Ano civil de conclusão curricular, aprovação da defesa ou homologação do diploma (nulo se em andamento).                                                                                                           | `2016`, `2001`, `2019`                                                                                                                                                     |
| **`titulo_trabalho`**   |    `String`    |     `1`     | `formacao_academica[].descricao` (extraído via regex `Título:\s*(.+?)(?:, Ano       | ,\s*Orientador                                                                                                                                                                                                          | \.                                                                                                                                                                               |
| **`descricao`**         |    `String`    |     `1`     | `formacao_academica[].descricao`                                                      | Bloco textual descritivo completo da formação, sintetizando título, ano de obtenção, orientadores, palavras-chave e áreas CNPq.🔒 **Privacidade (LGPD):** Nomes dos orientadores anonimizados nos exemplos. | `"Título: Alcaloides indólicos... , Ano de obtenção: 2016. Orientador: [Docente Orientador A]. Coorientador: [Docente Coorientador B]. Grande área: Ciências Exatas..."` |
| **`nome_orientador`**   |    `String`    |     `1`     | `formacao_academica[].descricao` (extraído via regex `Orientador:\s*([^,.\n]+)`)   | Nome civil completo do orientador acadêmico do titular no curso.🔒 **Privacidade (LGPD):** Anonimizado nos exemplos.                                                                                             | `"[Docente Orientador A]"` *(anonimizado)*, `"[Docente Orientador B]"` *(anonimizado)*                                                                                   |
| **`nome_coorientador`** |    `String`    |     `1`     | `formacao_academica[].descricao` (extraído via regex `Coorientador:\s*([^,.\n]+)`) | Nome civil do coorientador formal participante da orientação (se houver).🔒 **Privacidade (LGPD):** Anonimizado nos exemplos.                                                                                   | `"[Docente Coorientador A]"` *(anonimizado)*                                                                                                                                 |

#### Associações da Classe `FORMACAO_ACADEMICA`:

* **`possui formacao` $\rightarrow$ `PESSOA [1]`:** Pesquisador titular a quem pertence o histórico formativo.
* **`promove` $\rightarrow$ `INSTITUICAO [1]`:** Universidade ou centro acadêmico outorgante do título.

---

### 2.6 Classe: `ATUACAO_PROFISSIONAL`

Registra os vínculos funcionais, cargos, empregos, contratos docentes ou de gestão ocupados pelo pesquisador ao longo de sua vida profissional.

| Nome do Atributo              |    Tipo    | Multiplicidade | Origem no Extract                                                                                | Significado do Atributo                                                                                     | Exemplo Real                                                                                                           |
| :---------------------------- | :---------: | :------------: | :----------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------- |
| **`ano_inicio`**      | `Integer` |     `1`     | `atuacao_profissional[].ano_inicio`                                                            | Ano civil de início formal das atividades funcionais na instituição.                                     | `1997`, `2006`, `2016`                                                                                           |
| **`ano_fim`**         | `Integer` |     `1`     | `atuacao_profissional[].ano_fim` (inteiro ou nulo se `"Atual"`)                              | Ano civil de rescisão ou término do vínculo profissional (nulo se o vínculo estiver ativo).             | `1999`, `2012`                                                                                                     |
| **`atual`**           | `Boolean` |     `1`     | `atuacao_profissional[].ano_fim` (se `"Atual"` ou `"Atualmente"` $\rightarrow$ `true`) | Indicador booleano que expressa se o pesquisador permanece em atividade na organização.                   | `true`, `false`                                                                                                    |
| **`vinculo`**         | `String` |     `1`     | `atuacao_profissional[].vinculo`                                                               | Regime jurídico ou classificação institucional do relacionamento de trabalho.                            | `"Servidor Público"`, `"Professor"`, `"Colaborador"`                                                            |
| **`enquadramento`**   | `String` |     `1`     | `atuacao_profissional[].enquadramento`                                                         | Cargo ou enquadramento na carreira funcional perante o plano de cargos da instituição.                    | `"Professor de Ensino Básico, Técnico e Tecnológico"`, `"Professor do Magistério Superior"`, `"Pesquisador"` |
| **`cargo_funcao`**    | `String` |     `1`     | `atuacao_profissional[].cargo_funcao`                                                          | Cargo comissionado, função gratificada ou encargo diretivo desempenhado no período.                      | `"Coordenador de Curso"`, `"Diretor de Pesquisa e Pós-Graduação"`                                               |
| **`regime_trabalho`** | `String` |     `1`     | `atuacao_profissional[].regime`                                                                | Carga horária semanal e regime contratual perante a instituição mantenedora.                             | `"Dedicação exclusiva"`, `"40 horas semanais"`, `"20 horas semanais"`                                          |
| **`atividades`**      | `String` |     `1`     | `atuacao_profissional[].tipo` e subseções de linhas de atuação declaradas                  | Tipologia de atuação desenvolvida na entidade (Ensino, Pesquisa, Extensão, Direção e Administração). | `"Ensino, Pós-Graduação"`, `"Pesquisa e Desenvolvimento"`                                                       |
| **`disciplinas`**     | `String` |     `1`     | `atuacao_profissional[].disciplinas` (quando descritas sob atividades de ensino)               | Relação textual de disciplinas teóricas ou práticas lecionadas pelo docente nos cursos da entidade.     | `"Química Geral"`, `"Redes de Computadores"`, `"Algoritmos e Estruturas de Dados"`                              |

#### Associações da Classe `ATUACAO_PROFISSIONAL`:

* **`atua em` $\rightarrow$ `PESSOA [1]`:** Pesquisador que exerceu o vínculo profissional.
* **`ocorre em` $\rightarrow$ `INSTITUICAO [1]`:** Instituição empregadora ou promotora das atividades.

---

### 2.7 Classe: `PROJETO`

Representa o esforço temporário estruturado com metas científicas, pedagógicas ou tecnológicas registradas no Lattes (projetos de pesquisa, extensão universitária e desenvolvimento tecnológico).

| Nome do Atributo            |      Tipo      | Multiplicidade | Origem no Extract                                                                                                                                                                                              | Significado do Atributo                                                                           | Exemplo Real                                                                                                                            |
| :-------------------------- | :-------------: | :------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------- |
| **`nome`**          |   `String`   |     `1`     | `projetos_pesquisa[].nome`, `projetos_extensao[].nome` ou `projetos_desenvolvimento[].nome`                                                                                                              | Título oficial completo do projeto registrado pelo pesquisador no Lattes.                        | `"Jogos Didáticos no Ensino de Química: Aprendizagem Lúdica e Inclusiva."`, `"PolKA: Roteamento na Fonte Baseado em RNS"`        |
| **`tipo_projeto`**  | `TipoProjeto` |     `1`     | Chave de origem no JSON (`projetos_pesquisa` $\rightarrow$ `PESQUISA`, `projetos_extensao` $\rightarrow$ `EXTENSAO`, `projetos_desenvolvimento` $\rightarrow$ `DESENVOLVIMENTO_TECNOLOGICO`) | Classificação do projeto quanto à sua finalidade acadêmica e institucional.                   | `PESQUISA`, `EXTENSAO`, `DESENVOLVIMENTO_TECNOLOGICO`                                                                             |
| **`ano_inicio`**    |   `Integer`   |     `1`     | `projetos_*.ano_inicio`                                                                                                                                                                                      | Ano civil de início da vigência do plano de trabalho do projeto.                                | `2011`, `2020`, `2024`                                                                                                            |
| **`ano_conclusao`** |   `Integer`   |     `1`     | `projetos_*.ano_conclusao` (inteiro ou nulo se em andamento/atual)                                                                                                                                           | Ano civil previsto ou efetivo de encerramento do projeto.                                         | `2012`, `2023`                                                                                                                      |
| **`situacao`**      | `StatusCiclo` |     `1`     | `projetos_*.descricao` (extraído após `"Situação: "`)                                                                                                                                                  | Estado do ciclo de vida operacional do projeto (`EM_ANDAMENTO`, `CONCLUIDO`, `DESATIVADO`). | `EM_ANDAMENTO`, `CONCLUIDO`                                                                                                         |
| **`descricao`**     |   `String`   |     `1`     | `projetos_*.descricao` (texto da sinopse limpo de prefixos/sufixos)                                                                                                                                          | Resumo do plano técnico-científico do projeto contemplando escopo, metodologia e metas.         | `"Elaborar, Confeccionar, Aplicar e Avaliar jogos didáticos no ensino de Química, destinados a corroborar o processo educativo..."` |

#### Associações da Classe `PROJETO`:

* **`MEMBRO_PROJETO` $\rightarrow$ `PESSOA [1..*]`:** Pesquisadores que compõem a equipe de execução.
* **`FOMENTO_PROJETO` $\rightarrow$ `INSTITUICAO_FINANCIADORA [0..*]`:** Financiadores institucionais que outorgaram recursos ao projeto.

---

### 2.8 Classe: `MEMBRO_PROJETO` (Classe Associativa)

Modela a participação de uma pessoa física na equipe de um projeto, qualificando seu encargo executivo formal.

| Nome do Atributo    |       Tipo       | Multiplicidade | Origem no Extract                  | Significado do Atributo                                                                                                 | Exemplo Real                    |
| :------------------ | :--------------: | :------------: | :--------------------------------- | :---------------------------------------------------------------------------------------------------------------------- | :------------------------------ |
| **`papel`** | `PapelProjeto` |     `1`     | `projetos_*.integrantes[].papel` | Papel executivo desempenhado pelo participante na equipe do projeto (`COORDENADOR`, `INTEGRANTE`, `COLABORADOR`). | `COORDENADOR`, `INTEGRANTE` |

---

### 2.9 Classe: `FOMENTO_PROJETO` (Classe Associativa)

Modela a associação de financiamento entre uma agência ou empresa fomentadora e um projeto apoiado.

| Nome do Atributo         |            Tipo            | Multiplicidade | Origem no Extract                         | Significado do Atributo                                                                                                    | Exemplo Real                      |
| :----------------------- | :------------------------: | :------------: | :---------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- | :-------------------------------- |
| **`tipo_apoio`** | `TipoApoioFinanciamento` |     `1`     | `projetos_*.financiadores[].tipo_apoio` | Modalidade do apoio financeiro provido pela agência (`AUXILIO_FINANCEIRO`, `BOLSA`, `COOPERACAO`, `REMUNERACAO`). | `AUXILIO_FINANCEIRO`, `BOLSA` |

---

### 2.10 Classe: `PRODUCAO` (Superclasse Generalizada)

Superclasse que unifica todas as manifestações de produção intelectual, bibliográfica, técnica, artística ou tecnológica geradas pelo pesquisador.

| Nome do Atributo        |    Tipo    | Multiplicidade | Origem no Extract                                                                                           | Significado do Atributo                                                                                                                                     | Exemplo Real                                                                                                                     |
| :---------------------- | :---------: | :------------: | :---------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------- |
| **`titulo`**    | `String` |     `1`     | `producao_bibliografica.*[].titulo`, `producao_tecnica.*[].titulo` ou `patentes_registros.*[].titulo` | Título formal completo da obra intelectual ou ativo tecnológico.                                                                                          | `"Twice-Exceptionality (ASD and Giftedness) and Invisibility..."`, `"Do Despertar a Ascensão - Ciência e Espiritualidade"` |
| **`ano`**       | `Integer` |     `1`     | `*.ano`                                                                                                   | Ano civil em que a produção foi veiculada, publicada, concedida ou apresentada.                                                                           | `2026`, `2022`, `2017`                                                                                                     |
| **`descricao`** | `String` |     `1`     | `*.descricao` ou texto de referência bibliográfica padronizada                                          | Referência bibliográfica ou detalhamento da produção intelectual.🔒 **Privacidade (LGPD):** Nomes de autores e coautores anonimizados no exemplo. | `"AUTOR, A. B.; COAUTOR, C. D. Twice-Exceptionality (ASD and Giftedness) and Invisibility..."`                                 |

#### Associações da Classe `PRODUCAO`:

* **`autor de` $\rightarrow$ `PESSOA [1..*]`:** Pesquisadores que compartilham a autoria ou coautoria da obra.
* **`distingue` $\rightarrow$ `PREMIO_TITULO [0..*]`:** Prêmios ou láureas científicas outorgadas especificamente a esta produção.

---

### 2.11 Classe: `ARTIGO_TRABALHO_EVENTO` (Especialização de `PRODUCAO`)

Especialização de `PRODUCAO` que modela artigos científicos publicados em periódicos indexados, trabalhos completos em anais de congressos, resumos e artigos aceitos.

* **Herança:** Herda `titulo`, `ano` e `descricao` de `PRODUCAO`.

| Nome do Atributo                     |         Tipo         | Multiplicidade | Origem no Extract                                                                                                                                                           | Significado do Atributo                                                                                | Exemplo Real                                                                                                                          |
| :----------------------------------- | :------------------: | :------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| **`tipo_publicacao`**        | `TipoArtigoEvento` |     `1`     | Subseção sob `producao_bibliografica` (`artigos_periodicos`, `trabalhos_completos_congressos`, `resumos_expandidos`, `resumos_congressos`, `artigos_aceitos`) | Classificação do veículo de circulação científica da publicação.                               | `ARTIGO_PERIODICO`, `TRABALHO_COMPLETO_CONGRESSO`, `RESUMO_EXPANDIDO`                                                           |
| **`veiculo_revista_evento`** |      `String`      |     `1`     | `revista` (em periódicos) ou `evento` (em anais de congressos)                                                                                                         | Nome do periódico científico ou do congresso/simpósio onde o trabalho foi divulgado.                | `"RCMOS - Revista Científica Multidisciplinar O Saber"`, `"ChileCon"`, `"IEEE Transactions on Network and Service Management"` |
| **`doi`**                    |      `String`      |     `1`     | `doi`                                                                                                                                                                     | Digital Object Identifier (identificador numérico persistente da publicação na web).                | `"http://dx.doi.org/10.51473/rcmos.v1i1.2026.1948"`, `"10.1109/TNSM.2021.3115998"`                                                |
| **`issn_isbn`**              |      `String`      |     `1`     | `issn` (em periódicos) ou `isbn` (em anais de eventos)                                                                                                                 | Código serial padronizado internacional da publicação (ISSN para revistas; ISBN para livros/anais). | `"2675-9128"`, `"978-85-8203-057-8"`                                                                                              |
| **`volume`**                 |      `String`      |     `1`     | `volume`                                                                                                                                                                  | Tomo ou volume da publicação seriada.                                                                | `"1"`, `"42"`, `"B"`                                                                                                            |
| **`numero`**                 |      `String`      |     `1`     | `numero`                                                                                                                                                                  | Fascículo ou número da edição do periódico científico.                                           | `"1"`, `"4"`, `"Edição Especial"`                                                                                             |
| **`paginas`**                |      `String`      |     `1`     | `paginas`                                                                                                                                                                 | Intervalo de páginas ocupado pelo artigo na edição ou código de e-location.                        | `"1-19"`, `"41-62"`, `"e102435"`                                                                                                |
| **`cidade`**                 |      `String`      |     `1`     | `cidade`                                                                                                                                                                  | Cidade onde a revista é editada ou cidade-sede de realização do congresso científico.              | `"Belo Horizonte"`, `"Rio de Janeiro"`, `"Santiago"`                                                                            |
| **`data_publicacao`**        |      `String`      |     `1`     | `data` (em textos em jornais) ou data completa informada no Lattes                                                                                                        | Data civil exata de publicação e circulação do texto científico.                                  | `"22 fev. 1994"`, `"2026-05-15"`                                                                                                  |
| **`natureza`**               |      `String`      |     `1`     | Subtipo da publicação no Lattes (`"Completo"`, `"Resumo"`, `"Artigo"`)                                                                                              | Qualificação quanto à extensão e ao aprofundamento do texto divulgado.                             | `"Completo"`, `"Resumo Expandido"`                                                                                                |

---

### 2.12 Classe: `LIVRO_CAPITULO` (Especialização de `PRODUCAO`)

Especialização de `PRODUCAO` que modela livros inteiros publicados ou organizados e capítulos de livros com conselho editorial.

* **Herança:** Herda `titulo`, `ano` e `descricao` de `PRODUCAO`.

| Nome do Atributo           |         Tipo         | Multiplicidade | Origem no Extract                                                                                                                                              | Significado do Atributo                                                                              | Exemplo Real                                                                           |
| :------------------------- | :-------------------: | :------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------- |
| **`tipo`**         | `TipoLivroCapitulo` |     `1`     | Subseção sob `producao_bibliografica` (`livros_publicados` $\rightarrow$ `LIVRO_PUBLICADO`, `capitulos_livros` $\rightarrow$ `CAPITULO_LIVRO`) | Categoria de produção monográfica editorial.                                                      | `LIVRO_PUBLICADO`, `CAPITULO_LIVRO`                                                |
| **`titulo_livro`** |      `String`      |     `1`     | `titulo_livro` (em capítulos de livros)                                                                                                                     | Título da obra monográfica que reúne os capítulos ou do livro editado.                           | `"A pesquisa-ação no contexto da escola pública"`, `"Do Despertar a Ascensão"` |
| **`editora`**      |      `String`      |     `1`     | `editora`                                                                                                                                                    | Casa publicadora, selo comercial ou editora universitária promotora da tiragem.                     | `"Edifes"`, `"Editora Universitária"`, `"Elsevier"`, `"Springer"`             |
| **`cidade`**       |      `String`      |     `1`     | `cidade`                                                                                                                                                     | Município sede da editora onde a obra foi impressa ou disponibilizada digitalmente.                 | `"Vitória"`, `"São Paulo"`, `"Campinas"`                                       |
| **`isbn`**         |      `String`      |     `1`     | `isbn`                                                                                                                                                       | International Standard Book Number (código internacional padronizado de identificação de livros). | `"978-85-8203-057-8"`, `""`                                                        |
| **`edicao`**       |      `String`      |     `1`     | `edicao` ou extraído da descrição editorial                                                                                                               | Número ordinal da edição da obra.                                                                 | `"1ª edição"`, `"2"`, `"Revisada"`                                            |
| **`volume`**       |      `String`      |     `1`     | `volume`                                                                                                                                                     | Tomo ou volume da coletânea.                                                                        | `"1"`, `"II"`                                                                      |
| **`paginas`**      |      `String`      |     `1`     | `paginas`                                                                                                                                                    | Intervalo de páginas do capítulo ou total de páginas do livro.                                    | `"41-62"`, `"180 p."`                                                              |

---

### 2.13 Classe: `PRODUCAO_TECNICA_ARTISTICA_BIBLIOGRAFICA` (Especialização de `PRODUCAO`)

Especialização de `PRODUCAO` que modela softwares registrados ou sem patente, produtos tecnológicos, processos técnicos, trabalhos técnicos e apresentações de cursos e oficinas.

* **Herança:** Herda `titulo`, `ano` e `descricao` de `PRODUCAO`.

| Nome do Atributo         |             Tipo             | Multiplicidade | Origem no Extract                                                                                                                                                                     | Significado do Atributo                                                                        | Exemplo Real                                                                              |
| :----------------------- | :--------------------------: | :------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------- |
| **`categoria`**  | `CategoriaProducaoTecnica` |     `1`     | Chave sob `producao_tecnica` (`softwares_sem_patente`, `produtos_tecnologicos`, `processos_tecnicas`, `trabalhos_tecnicos`, `entrevistas`, `outras_producoes_tecnicas`) | Categoria formal da produção técnica ou tecnológica.                                       | `SOFTWARE`, `PRODUTO_TECNOLOGICO`, `PROCESSO_TECNICA`, `TRABALHO_TECNICO`         |
| **`subtipo`**    |          `String`          |     `1`     | `tipo` em `producao_tecnica`                                                                                                                                                      | Subclassificação ou especificação do formato de entrega do produto.                        | `"Produto tecnológico"`, `"Trabalho técnico"`, `"Software sem patente"`           |
| **`natureza`**   |          `String`          |     `1`     | `natureza` ou campo de modalidade no Lattes                                                                                                                                         | Propósito de aplicação prática do produto técnico.                                        | `"Técnica"`, `"Pedagógica"`, `"Didática"`                                        |
| **`finalidade`** |          `String`          |     `1`     | `finalidade`                                                                                                                                                                        | Descrição da destinação prática e do impacto operacional ou industrial do produto gerado. | `"REPLICABILIDADE DE DATASETS DE REDE A PARTIR DA REUTILIZAÇÃO DE TRACES DE PACOTES"` |

#### Associações da Classe `PRODUCAO_TECNICA_ARTISTICA_BIBLIOGRAFICA`:

* **`sedia producao tecnica` $\rightarrow$ `INSTITUICAO [0..1]`:** Instituição executora ou parceira beneficiária do produto técnico.

---

### 2.14 Classe: `PATENTE_REGISTRO` (Especialização de `PRODUCAO`)

Especialização de `PRODUCAO` que modela ativos formais de propriedade industrial protegidos perante o INPI ou escritórios internacionais (patentes de invenção, modelos de utilidade, programas de computador e desenhos industriais).

* **Herança:** Herda `titulo`, `ano` e `descricao` de `PRODUCAO`.

| Nome do Atributo                 |          Tipo          | Multiplicidade | Origem no Extract                                                                                   | Significado do Atributo                                                                   | Exemplo Real                                                          |
| :------------------------------- | :---------------------: | :------------: | :-------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------- | :-------------------------------------------------------------------- |
| **`tipo`**               | `TipoPatenteRegistro` |     `1`     | Chave sob `patentes_registros` (`patentes`, `programas_computador`, `desenhos_industriais`) | Categoria jurídica do título de propriedade intelectual.                                | `PATENTE_INVENCAO`, `PROGRAMA_COMPUTADOR`, `DESENHO_INDUSTRIAL` |
| **`modalidade_patente`** |       `String`       |     `1`     | Subtipo de registro no INPI                                                                         | Modalidade específica do pedido patentário (PI ou MU).                                  | `"Privilégio de Invenção (PI)"`, `"Modelo de Utilidade (MU)"`  |
| **`pais`**               |       `String`       |     `1`     | País de depósito informado                                                                        | Jurisdição nacional onde o depósito formal foi requerido.                              | `"Brasil"`, `"Estados Unidos"`                                    |
| **`data_registro`**      |       `String`       |     `1`     | Data de depósito ou de expedição do registro                                                     | Data civil de protocolo do pedido ou concessão da patente.                               | `"15/08/2021"`, `"2023-01-10"`                                    |
| **`codigo_registro`**    |       `String`       |     `1`     | Número de processo ou registro no INPI                                                             | Código alfanumérico oficial do depósito ou expedição perante o órgão de custódia. | `"BR 10 2021 015842 0"`, `"BR 51 2023 000124-5"`                  |

#### Associações da Classe `PATENTE_REGISTRO`:

* **`titular da patente` $\rightarrow$ `INSTITUICAO [1]`:** Entidade ou universidade titular do ativo tecnológico.

---

### 2.15 Classe: `ORIENTACAO`

Histórico de acompanhamento e formação acadêmica conduzido pelo pesquisador sobre estudantes e pós-graduandos em planos de iniciação científica, TCC, especialização, mestrado e doutorado.

| Nome do Atributo               |           Tipo           | Multiplicidade | Origem no Extract                                                                                                                                          | Significado do Atributo                                                                   | Exemplo Real                                                                                                                             |
| :----------------------------- | :----------------------: | :------------: | :--------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------- |
| **`titulo`**           |        `String`        |     `1`     | `orientacoes.*.*[].titulo`                                                                                                                               | Título do trabalho de conclusão de curso, dissertação, tese ou plano de IC orientado. | `"Nas tramas do hipertexto: a escrita colaborativa através dos contos de mistério"`, `"Planejamento de Redes Ópticas Elásticas"` |
| **`modalidade`**       | `ModalidadeOrientacao` |     `1`     | Subseção de grau sob `orientacoes` (`mestrado`, `doutorado`, `iniciacao_cientifica`, `tcc`, `especializacao`, `pos_doutorado`, `outros`) | Nível acadêmico da orientação tutorial.                                               | `MESTRADO`, `DOUTORADO`, `INICIACAO_CIENTIFICA`, `TCC`, `ESPECIALIZACAO`                                                       |
| **`papel_orientacao`** |   `PapelOrientacao`   |     `1`     | Designação do papel docente (`Orientador` ou `Coorientador`)                                                                                         | Encargo formal exercido perante o colegiado acadêmico.                                   | `ORIENTADOR_PRINCIPAL`, `COORIENTADOR`                                                                                               |
| **`status`**           |     `StatusCiclo`     |     `1`     | Seção pai sob `orientacoes` (`concluidas` $\rightarrow$ `CONCLUIDO`, `em_andamento` $\rightarrow$ `EM_ANDAMENTO`)                          | Estado temporal da orientação perante a defesa do estudante.                            | `CONCLUIDO`, `EM_ANDAMENTO`                                                                                                          |
| **`ano_inicio`**       |       `Integer`       |     `1`     | `ano_inicio`                                                                                                                                             | Ano civil em que as atividades de tutoria acadêmica tiveram início.                     | `2015`, `2020`, `2025`                                                                                                             |
| **`ano_conclusao`**    |       `Integer`       |     `1`     | `ano_conclusao` (inteiro ou nulo se em andamento)                                                                                                        | Ano civil da homologação da defesa pública ou aprovação do trabalho final.           | `2015`, `2022`, `null`                                                                                                             |
| **`curso`**            |        `String`        |     `1`     | `curso`                                                                                                                                                  | Nome do programa de pós-graduação ou curso de graduação no qual o orientado estuda.  | `"Mestrado em Letras"`, `"Engenharia de Controle e Automação"`, `"Química"`                                                     |
| **`tipo_trabalho`**    |        `String`        |     `1`     | `tipo_trabalho`                                                                                                                                          | Documento acadêmico resultante da orientação.                                          | `"Dissertação"`, `"Tese"`, `"Monografia"`, `"Trabalho de Conclusão de Curso"`                                                 |

#### Associações da Classe `ORIENTACAO`:

* **`orienta` $\rightarrow$ `PESSOA [1]`:** Docente pesquisador que exerceu a orientação.
* **`orientado em` $\rightarrow$ `PESSOA [0..1]`:** Estudante orientado pelo docente.
* **`ocorre em` $\rightarrow$ `INSTITUICAO [1]`:** Universidade promotora do curso onde a orientação se deu.
* **`financia orientacao` $\rightarrow$ `INSTITUICAO_FINANCIADORA [0..1]`:** Agência de fomento outorgante da bolsa ao estudante.

---

### 2.16 Classe: `BANCA_EXAMINADORA`

Registra a participação do pesquisador em bancas examinadoras de defesa de teses, dissertações, exames de qualificação e trabalhos de graduação.

| Nome do Atributo              |        Tipo        | Multiplicidade | Origem no Extract                                                                                                                    | Significado do Atributo                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Exemplo Real                                                                                                                                                                                                                                                                                                                            |
| :---------------------------- | :-----------------: | :------------: | :----------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`modalidade`**      | `ModalidadeBanca` |     `1`     | Chave sob `bancas` (`mestrado`, `doutorado`, `qualificacao_mestrado`, `qualificacao_doutorado`, `graduacao`, `outras`) | Modalidade ou tipo de avaliação da banca examinadora.                                                                                                                                                                                                                                                                                                                                                                                                                     | `MESTRADO`, `DOUTORADO`, `QUALIFICACAO_MESTRADO`, `GRADUACAO`, `OUTRAS`                                                                                                                                                                                                                                                       |
| **`titulo_trabalho`** |     `String`     |     `1`     | `bancas.*[].titulo_trabalho`                                                                                                       | Título oficial da tese, dissertação, monografia ou TCC defendido pelo candidato perante a banca examinadora.ℹ️ **Comportamento em Bancas de Concurso:** Nas bancas sob a modalidade `outras` (comissões julgadoras de concurso público docente, processos seletivos ou comissões de heteroidentificação), este atributo vem vazio (`""`), pois não há avaliação de trabalho monográfico, mas sim julgamento de provas ou documentos de candidatos. | • **Defesa de Mestrado:** `"Aprendizagem de Química na Educação Básica: uma sequência didática utilizando textos de divulgação científica"`• **Defesa de Graduação (TCC):** `"Introdução a Modelagem Molecular usando o software Avogadro"`• **Banca de Concurso/Comissão (`outras`):** `""` |
| **`ano`**             |     `Integer`     |     `1`     | `bancas.*[].ano`                                                                                                                   | Ano civil em que a defesa perante a banca examinadora foi realizada.                                                                                                                                                                                                                                                                                                                                                                                                        | `2018`, `2022`, `2025`                                                                                                                                                                                                                                                                                                            |
| **`curso`**           |     `String`     |     `1`     | `bancas.*[].curso`                                                                                                                 | Programa de pós-graduação ou curso no qual a defesa da banca foi agendada.                                                                                                                                                                                                                                                                                                                                                                                               | `"Dissertação (Mestrado em Ensino na Educação Básica)"`, `"Trabalho de Conclusão de Curso (Graduação em Abi - Química)"`                                                                                                                                                                                                   |
| **`descricao`**       |     `String`     |     `1`     | `bancas.*[].descricao`                                                                                                             | Citação descritiva completa gerada pelo CNPq contendo examinadores, candidato, título, ano e universidade.🔒 **Privacidade (LGPD):** Nomes dos membros examinadores e discente avaliado anonimizados no exemplo.                                                                                                                                                                                                                                                   | `"Examinador A, M. H.; Examinador B, G.; Avaliador C, N. M. Participação em banca de [Discente Candidato A]..."`                                                                                                                                                                                                                    |

#### Associações da Classe `BANCA_EXAMINADORA`:

* **`compoe banca` $\rightarrow$ `PESSOA [1..*]`:** Pesquisadores membros da banca avaliadora.
* **`candidato em` $\rightarrow$ `PESSOA [1]`:** Candidato/aluno avaliado defendendo o trabalho.
* **`sediada em` $\rightarrow$ `INSTITUICAO [0..1]`:** Universidade promotora da sessão de defesa.

---

### 2.17 Classe: `EVENTO_CIENTIFICO`

Representa o congresso, simpósio, semana de ciência e tecnologia, fórum ou feira acadêmica.

| Nome do Atributo                   |    Tipo    | Multiplicidade | Origem no Extract                                                       | Significado do Atributo                                                    | Exemplo Real                                                                     |
| :--------------------------------- | :---------: | :------------: | :---------------------------------------------------------------------- | :------------------------------------------------------------------------- | :------------------------------------------------------------------------------- |
| **`nome_evento`**          | `String` |     `1`     | `eventos.participacoes[].evento` ou `eventos.organizacoes[].evento` | Nome oficial do congresso científico, simpósio ou encontro comunitário. | `"20 SEMANA NACIONAL DE CIÊNCIA E TECNOLOGIA"`, `"ChileCon"`, `"EnANPAD"` |
| **`natureza_tipo_evento`** | `String` |     `1`     | `tipo_evento` ou `natureza` sob `eventos`                         | Tipologia acadêmica do encontro.                                          | `"Oficina"`, `"Congresso"`, `"Seminário"`, `"Simpósio"`                |
| **`ano`**                  | `Integer` |     `1`     | `eventos.*[].ano`                                                     | Ano civil de realização do evento acadêmico.                            | `2023`, `2019`, `2012`                                                     |

---

### 2.18 Classe: `PARTICIPACAO_EVENTO` (Classe Associativa)

Modela a participação formal de uma pessoa física em um evento científico, qualificando o papel assumido e a apresentação realizada.

| Nome do Atributo                  |      Tipo      | Multiplicidade | Origem no Extract                                                                                                                                                           | Significado do Atributo                                                                                      | Exemplo Real                                                                                                                                                        |
| :-------------------------------- | :-------------: | :------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`papel_evento`**        | `PapelEvento` |     `1`     | `tipo` em `eventos` (`"Participação em evento"` $\rightarrow$ `PARTICIPANTE` / `APRESENTADOR`, `"Organização de evento"` $\rightarrow$ `ORGANIZADOR`) | Papel exercido pelo pesquisador no evento.                                                                   | `PARTICIPANTE`, `APRESENTADOR`, `ORGANIZADOR`                                                                                                                 |
| **`titulo_apresentacao`** |   `String`   |     `1`     | `eventos.participacoes[].apresentacao`                                                                                                                                    | Título da comunicação oral, oficina ministrada, pôster ou palestra proferida pelo pesquisador no evento. | `"A Química do cérebro: ondas gamma e efeitos da dimetiltriptamina de plantas medicinais/ roda de chá"`, `"Linear Time Optimal Amplifier Placement on OTNs"` |

---

### 2.19 Classe: `IDIOMA`

Representa a língua ou idioma estrangeiro cadastrado no currículo.

| Nome do Atributo          |    Tipo    | Multiplicidade | Origem no Extract  | Significado do Atributo                               | Exemplo Real                                                                                   |
| :------------------------ | :--------: | :------------: | :----------------- | :---------------------------------------------------- | :--------------------------------------------------------------------------------------------- |
| **`nome_idioma`** | `String` |     `1`     | `idiomas[].nome` | Nome da língua ou idioma autodeclarado pelo titular. | `"Inglês"`, `"Espanhol"`, `"Português"`, `"Francês"`, `"Italiano"`, `"Alemão"` |

---

### 2.20 Classe: `PROFICIENCIA_IDIOMA` (Classe Associativa)

Modela o nível de fluência e proficiência em quatro competências linguísticas autodeclaradas pelo pesquisador para um idioma.

| Nome do Atributo         |         Tipo         | Multiplicidade | Origem no Extract        | Significado do Atributo                                                                                | Exemplo Real                          |
| :----------------------- | :-------------------: | :------------: | :----------------------- | :----------------------------------------------------------------------------------------------------- | :------------------------------------ |
| **`compreende`** | `NivelProficiencia` |     `1`     | `idiomas[].compreende` | Competência em compreensão auditiva da língua (`POUCO`, `RAZOAVELMENTE`, `BEM`, `FLUENTE`). | `BEM`, `RAZOAVELMENTE`, `POUCO` |
| **`fala`**       | `NivelProficiencia` |     `1`     | `idiomas[].fala`       | Competência na produção oral e diálogo na língua.                                                 | `BEM`, `RAZOAVELMENTE`, `POUCO` |
| **`le`**         | `NivelProficiencia` |     `1`     | `idiomas[].le`         | Competência em leitura e compreensão de textos escritos na língua.                                  | `BEM`, `RAZOAVELMENTE`, `POUCO` |
| **`escreve`**    | `NivelProficiencia` |     `1`     | `idiomas[].escreve`    | Competência na escrita e redação de textos científicos na língua.                                 | `BEM`, `RAZOAVELMENTE`, `POUCO` |

---

### 2.21 Classe: `PREMIO_TITULO`

Modela distinções acadêmicas, menções honrosas, prêmios científicos, láureas e títulos honoríficos concedidos ao pesquisador.

| Nome do Atributo               |    Tipo    | Multiplicidade | Origem no Extract               | Significado do Atributo                                                                         | Exemplo Real                                                                                                                                                |
| :----------------------------- | :---------: | :------------: | :------------------------------ | :---------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`descricao_titulo`** | `String` |     `1`     | `premios_titulos[].descricao` | Descrição oficial da láurea, prêmio, honraria ou título honorífico e entidade concedente. | `"Primeiro lugar PLANTAS MEDICINAIS E SUSTENTABILIDADE: SABÃO MEDICINAL COM EXTRATOS E ÓLEOS ESSENCIAIS, 20 Semana Nacional de Ciência e Tecnologia."` |
| **`ano`**              | `Integer` |     `1`     | `premios_titulos[].ano`       | Ano civil em que o prêmio ou distinção foi formalmente conferido.                            | `2023`, `2018`, `2015`                                                                                                                                |

#### Associações da Classe `PREMIO_TITULO`:

* **`homenageado em` $\rightarrow$ `PESSOA [1]`:** Pesquisador laureado.
* **`distingue` $\rightarrow$ `PRODUCAO [0..1]`:** Produção científica premiada pela láurea (se o prêmio foi concedido a uma obra específica).

---

### 2.22 Classe: `AREA_ATUACAO`

Classifica as especialidades técnico-científicas do pesquisador com base na taxonomia oficial do CNPq em quatro níveis hierárquicos.

| Nome do Atributo            |        Tipo        | Multiplicidade | Origem no Extract                    | Significado do Atributo                                                                                                              | Exemplo Real                                                                                                  |
| :-------------------------- | :----------------: | :------------: | :----------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| **`grande_area`**   | `GrandeAreaCNPq` |     `1`     | `areas_de_atuacao[].grande_area`   | Macro-área do conhecimento segundo a árvore do CNPq (`CIENCIAS_EXATAS_E_DA_TERRA`, `ENGENHARIAS`, `CIENCIAS_HUMANAS`, etc.). | `CIENCIAS_EXATAS_E_DA_TERRA`, `ENGENHARIAS`                                                               |
| **`area`**          |     `String`     |     `1`     | `areas_de_atuacao[].area`          | Área de conhecimento disciplinar intermediária do CNPq.                                                                            | `"Química"`, `"Engenharia Elétrica"`, `"Ciência da Computação"`                                    |
| **`subarea`**       |     `String`     |     `1`     | `areas_de_atuacao[].subarea`       | Subárea especializada de atuação disciplinar do CNPq.                                                                             | `"Química Orgânica"`, `"Telecomunicações"`, `"Metodologia e Técnicas da Computação"`             |
| **`especialidade`** |     `String`     |     `1`     | `areas_de_atuacao[].especialidade` | Especialidade disciplinar estrita de concentração de pesquisa do pesquisador.                                                      | `"Química dos Produtos Naturais"`, `"Sistemas de Telecomunicações"`, `"Linguagens de Programação"` |

#### Associações da Classe `AREA_ATUACAO`:

* **`atua na area` $\rightarrow$ `PESSOA [1..*]`:** Pesquisadores que declaram atuação nesta especialidade científica.

---

### 2.23 Classe: `LINHA_PESQUISA`

Representa o eixo temático contínuo de investigação e produção do pesquisador ou grupo acadêmico.

| Nome do Atributo       |    Tipo    | Multiplicidade | Origem no Extract                 | Significado do Atributo                                                                       | Exemplo Real                                                                                                                                                |
| :--------------------- | :--------: | :------------: | :-------------------------------- | :-------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`nome`**     | `String` |     `1`     | `linhas_de_pesquisa[].nome`     | Título ou designação do eixo investigativo temático continuado.                           | `"Planejamento de Redes Ópticas"`, `"Química de Produtos Naturais"`, `"Processamento de Sinais Biomédicos"`                                        |
| **`objetivo`** | `String` |     `1`     | `linhas_de_pesquisa[].objetivo` | Descrição formal dos propósitos científicos, teóricos ou aplicados da linha de pesquisa. | `"Modelagem Matemática e Otimização."`, `"Isolamento e identificação de substâncias bioativas a partir de plantas medicinais da flora capixaba."` |

#### Associações da Classe `LINHA_PESQUISA`:

* **`pesquisa em` $\rightarrow$ `PESSOA [1..*]`:** Pesquisadores vinculados à condução desta linha de pesquisa.

---

## 3. Tipos Enumerados (Enums de Domínio)

As 16 enumerações modeladas no Astah foram auditadas e mapeadas diretamente a partir das ocorrências concretas observadas nos 126 currículos Lattes da pasta `horizon_etl/data/lattes_json/`:

---

### 3.1 Enum: `Sexo`

* **Origem no Extract:** `informacoes_pessoais.sexo`
* **Significado:** Gênero autodeclarado pelo titular no cadastro da Plataforma Lattes.

| Literal do Enum         | Significado de Negócio      | Frequência Relativa na Base Real                 | Exemplo Concreto no Lattes                     |
| :---------------------- | :--------------------------- | :------------------------------------------------ | :--------------------------------------------- |
| **`MASCULINO`** | Gênero masculino declarado. | Maioria na base de docentes pesquisadores (~68%). | `"Docente Pesquisador A"` *(anonimizado)*  |
| **`FEMININO`**  | Gênero feminino declarado.  | Pesquisadoras titulares cadastradas (~32%).       | `"Docente Pesquisadora B"` *(anonimizado)* |

---

### 3.2 Enum: `TipoFormacao`

* **Origem no Extract:** Prefixo de grau na chave `formacao_academica[].tipo`
* **Significado:** Grau ou titulação acadêmica obtida em cursos regulares de ensino.

| Literal do Enum               | Significado de Negócio                                                              | Frequência Relativa na Base Real | Exemplo Concreto no Lattes                                |
| :---------------------------- | :----------------------------------------------------------------------------------- | :-------------------------------- | :-------------------------------------------------------- |
| **`GRADUACAO`**       | Curso superior de graduação (Bacharelado ou Licenciatura).                         | 145 ocorrências na base.         | `"Graduação em Química"`                             |
| **`MESTRADO`**        | Pós-graduação *stricto sensu* em nível de mestrado acadêmico ou profissional. | 109 ocorrências na base.         | `"Mestrado em Produção Vegetal"`                      |
| **`DOUTORADO`**       | Pós-graduação *stricto sensu* em nível de doutorado.                           | 90 ocorrências na base.          | `"Doutorado em Ciências Química"`                     |
| **`ESPECIALIZACAO`**  | Pós-graduação *lato sensu* de especialização técnica/profissional.           | 83 ocorrências na base.          | `"Especialização em Educação Profissional"`         |
| **`POS_DOUTORADO`**   | Estágio de pós-doutoramento ou pesquisa sênior pós-titulação.                  | 4 ocorrências na base.           | `"Pós-Doutorado em Engenharia Elétrica"`              |
| **`APERFEICOAMENTO`** | Cursos de aperfeiçoamento e extensão de curta/média duração.                    | 11 ocorrências na base.          | `"Aperfeiçoamento em Instrumentação Analítica"`     |
| **`CURSO_TECNICO`**   | Formação profissional de nível técnico de ensino médio.                         | 36 ocorrências na base.          | `"Curso técnico/profissionalizante em Eletrotécnica"` |

---

### 3.3 Enum: `TipoProjeto`

* **Origem no Extract:** Chaves primárias de projeto no JSON (`projetos_pesquisa`, `projetos_extensao`, `projetos_desenvolvimento`)
* **Significado:** Natureza institucional da ação e iniciativa de trabalho do projeto.

| Literal do Enum                           | Significado de Negócio                                             | Frequência Relativa na Base Real | Exemplo Concreto no Lattes                            |
| :---------------------------------------- | :------------------------------------------------------------------ | :-------------------------------- | :---------------------------------------------------- |
| **`PESQUISA`**                    | Projeto de investigação científica básica ou aplicada.          | 612 projetos na base (59,6%).     | `"Jogos Didáticos no Ensino de Química"`          |
| **`EXTENSAO`**                    | Projeto de interação dialógica e transferência com a sociedade. | 262 projetos na base (25,5%).     | `"Capacitação de Professores em Robótica Livre"` |
| **`DESENVOLVIMENTO_TECNOLOGICO`** | Projeto voltado à engenharia, inovação de produto e processo.    | 153 projetos na base (14,9%).     | `"PolKA: Roteamento na Fonte Baseado em RNS"`       |

---

### 3.4 Enum: `StatusCiclo`

* **Origem no Extract:** `"Situação: "` dentro de `descricao` em projetos e chave pai em `orientacoes`
* **Significado:** Estado do ciclo de vida operacional e temporal do projeto ou orientação.

| Literal do Enum            | Significado de Negócio                                                   | Ocorrência no Lattes                                                                          |
| :------------------------- | :------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------- |
| **`EM_ANDAMENTO`** | Atividades do projeto ou orientação ativas e em execução no período. | Projetos com `"Situação: Em andamento"` ou orientações sob `orientacoes.em_andamento`. |
| **`CONCLUIDO`**    | Atividades e metas integralmente finalizadas e relatório homologado.     | Projetos com `"Situação: Concluído"` ou orientações sob `orientacoes.concluidas`.     |
| **`DESATIVADO`**   | Projeto interrompido, cancelado ou descontinuado administrativamente.     | Projetos com `"Situação: Desativado"`.                                                     |

---

### 3.5 Enum: `PapelProjeto`

* **Origem no Extract:** `projetos_*.integrantes[].papel`
* **Significado:** Responsabilidade executiva desempenhada pelo pesquisador no projeto.

| Literal do Enum           | Significado de Negócio                                             | Frequência Relativa na Base Real | Exemplo Concreto                                               |
| :------------------------ | :------------------------------------------------------------------ | :-------------------------------- | :------------------------------------------------------------- |
| **`COORDENADOR`** | Pesquisador líder responsável técnico e financeiro pelo projeto. | 1.032 membros coordenadores.      | `"Coordenador(a) Docente A - Coordenador"` *(anonimizado)* |
| **`INTEGRANTE`**  | Pesquisador, colaborador, técnico ou aluno participante da equipe. | 3.346 membros integrantes.        | `"Membro Integrante B - Integrante"` *(anonimizado)*       |
| **`COLABORADOR`** | Colaborador institucional ou participante externo parceiro.         | Ocorrências pontuais no Lattes.  | `"Colaborador externo"`                                      |

---

### 3.6 Enum: `TipoApoioFinanciamento`

* **Origem no Extract:** `projetos_*.financiadores[].tipo_apoio`
* **Significado:** Modalidade do suporte de fomento concedido pela agência ao projeto.

| Literal do Enum                  | Significado de Negócio                                                   | Frequência Relativa na Base Real | Exemplo Concreto                         |
| :------------------------------- | :------------------------------------------------------------------------ | :-------------------------------- | :--------------------------------------- |
| **`AUXILIO_FINANCEIRO`** | Recursos orçamentários de custeio e capital (equipamentos e consumo).   | 173 auxílios registrados.        | FAPES / CNPq - `"Auxílio financeiro"` |
| **`BOLSA`**              | Concessão de cotas de bolsas para pesquisadores ou alunos executores.    | 113 registros de bolsas.          | FAPES / CAPES - `"Bolsa"`              |
| **`COOPERACAO`**         | Cooperação técnica ou institucional sem repasse financeiro direto.     | 13 cooperações registradas.     | `"Cooperação"` técnico-científica  |
| **`REMUNERACAO`**        | Remuneração ou contrapartida financeira direta de consultoria/serviço. | Ocorrências específicas.        | `"Remuneração"`                      |

---

### 3.7 Enum: `ModalidadeOrientacao`

* **Origem no Extract:** Subchaves de grau sob `orientacoes.concluidas` e `orientacoes.em_andamento`
* **Significado:** Nível acadêmico da tutoria desenvolvida pelo orientador.

| Literal do Enum                    | Significado de Negócio                                                          | Contagem Total na Base | Exemplo Concreto                                    |
| :--------------------------------- | :------------------------------------------------------------------------------- | :--------------------- | :-------------------------------------------------- |
| **`TCC`**                  | Trabalho de Conclusão de Curso de graduação ou técnico.                      | 1.061 orientações.   | `"Caralumma fimbriata"`                           |
| **`INICIACAO_CIENTIFICA`** | Iniciação científica e tecnológica júnior ou de graduação (PIBIC/PIBITI). | 729 orientações.     | `"Análise e Interpretação Estatística"`       |
| **`MESTRADO`**             | Dissertação de mestrado acadêmico ou profissional.                            | 515 orientações.     | `"Nas tramas do hipertexto..."`                   |
| **`ESPECIALIZACAO`**       | Monografia de especialização *lato sensu*.                                   | 480 orientações.     | `"A Potencialização do Ensino a Distância..."` |
| **`OUTROS`**               | Orientações de outra natureza (estágio, monitoria, projetos de ensino).       | 340 orientações.     | `"Núcleo Incubador do Ifes"`                     |
| **`DOUTORADO`**            | Tese de doutorado acadêmico ou profissional.                                    | 21 orientações.      | `"Path-Aware Network by Residue Number System"`   |
| **`POS_DOUTORADO`**        | Supervisão de estágio de pós-doutorado.                                       | 4 supervisões.        | Supervisão de Pós-Doutorado no Ifes               |

---

### 3.8 Enum: `PapelOrientacao`

* **Origem no Extract:** Identificação em `orientacoes` e `descricao` da formação
* **Significado:** Encargo docente exercido perante o estudante.

| Literal do Enum                    | Significado de Negócio                                                | Exemplo Concreto                                            |
| :--------------------------------- | :--------------------------------------------------------------------- | :---------------------------------------------------------- |
| **`ORIENTADOR_PRINCIPAL`** | Docente responsável primário pela condução acadêmica do trabalho. | `"Orientador: Docente Titular A"` *(anonimizado)*       |
| **`COORIENTADOR`**         | Docente que divide a tutela e orientação técnica do estudante.      | `"Coorientador: Docente Colaborador B"` *(anonimizado)* |

---

### 3.9 Enum: `TipoArtigoEvento`

* **Origem no Extract:** Subseções sob `producao_bibliografica`
* **Significado:** Tipologia do veículo editorial do artigo ou trabalho científico.

| Literal do Enum                           | Significado de Negócio                                                  | Contagem Total na Base | Exemplo Concreto                                                 |
| :---------------------------------------- | :----------------------------------------------------------------------- | :--------------------- | :--------------------------------------------------------------- |
| **`TRABALHO_COMPLETO_CONGRESSO`** | Trabalho técnico-científico completo publicado em anais de congressos. | 1.984 publicações.   | `"Linear Time Optimal Amplifier Placement on OTNs"`            |
| **`ARTIGO_PERIODICO`**            | Artigo publicado em periódico ou revista científica indexada.          | 697 artigos.           | `"Twice-Exceptionality (ASD and Giftedness) and Invisibility"` |
| **`RESUMO_CONGRESSO`**            | Resumo simples publicado em anais de encontros científicos.             | 232 resumos.           | `"Gênero Rauvolfia: Espécies e Alcaloides"`                  |
| **`RESUMO_EXPANDIDO`**            | Resumo expandido publicado em anais de simpósios.                       | 129 resumos.           | `"Gestão participativa: o caso de uma escola pública"`       |
| **`ARTIGO_ACEITO`**               | Artigo aceito pelo corpo editorial aguardando impressão final.          | 14 artigos.            | `"Monitoramento de Tráfego via Honeypot Virtual"`             |

---

### 3.10 Enum: `TipoLivroCapitulo`

* **Origem no Extract:** Subseções sob `producao_bibliografica` (`livros_publicados` e `capitulos_livros`)
* **Significado:** Modalidade da produção monográfica e editorial.

| Literal do Enum               | Significado de Negócio                                        | Contagem Total na Base | Exemplo Concreto                                            |
| :---------------------------- | :------------------------------------------------------------- | :--------------------- | :---------------------------------------------------------- |
| **`CAPITULO_LIVRO`**  | Capítulo publicado em livro organizado por comitê editorial. | 283 capítulos.        | `"A pesquisa-ação no contexto da escola pública"`      |
| **`LIVRO_PUBLICADO`** | Livro completo publicado, organizado ou traduzido com ISBN.    | 130 livros.            | `"Do Despertar a Ascensão - Ciência e Espiritualidade"` |

---

### 3.11 Enum: `CategoriaProducaoTecnica`

* **Origem no Extract:** Chaves sob `producao_tecnica` e apresentações em `producao_bibliografica`
* **Significado:** Categoria formal do produto técnico gerado pelo pesquisador.

| Literal do Enum                      | Significado de Negócio                                                      | Contagem Total na Base | Exemplo Concreto                                              |
| :----------------------------------- | :--------------------------------------------------------------------------- | :--------------------- | :------------------------------------------------------------ |
| **`APRESENTACAO_TRABALHO`**  | Apresentação oral de trabalho, conferência ou palestra em evento.         | 947 apresentações.   | `"Oficina de saboaria"`                                     |
| **`OUTRA_PRODUCAO_TECNICA`** | Demais tipos de produção técnica cadastrados.                             | 443 produções.       | `"Do Sensorial ao Tecnológico: Extração de Óleos"`      |
| **`TRABALHO_TECNICO`**       | Pareceres periciais, relatórios técnicos, laudos e consultorias.           | 405 trabalhos.         | `"Atuação Técnica em Fiscalização e Gestão de Obras"` |
| **`ENTREVISTA`**             | Entrevistas veiculadas em mídias, mesas redondas e programas.               | 146 entrevistas.       | `"Pesquisa capixaba patenteia substâncias contra câncer"` |
| **`SOFTWARE`**               | Programas de computador e softwares sem ou com patente.                      | 107 softwares.         | `"Replicabilidade de Datasets de Rede via Traces"`          |
| **`PRODUTO_TECNOLOGICO`**    | Protótipos funcionais, dispositivos e compostos químicos desenvolvidos.    | 28 produtos.           | `"Fitoquímica: Fundamentos Teóricos e Práticos"`         |
| **`PROCESSO_TECNICA`**       | Métodos operacionais e formulações patenteáveis ou de domínio público. | 12 processos.          | `"AOD Task Mirex 2018 Submission - Kflux2"`                 |

---

### 3.12 Enum: `TipoPatenteRegistro`

* **Origem no Extract:** Chaves sob `patentes_registros` (`patentes`, `programas_computador`, `desenhos_industriais`)
* **Significado:** Categoria jurídica do título de proteção industrial.

| Literal do Enum                   | Significado de Negócio                                                    | Exemplo Concreto                                     |
| :-------------------------------- | :------------------------------------------------------------------------- | :--------------------------------------------------- |
| **`PATENTE_INVENCAO`**    | Patente de Invenção (PI) ou Modelo de Utilidade (MU) depositada no INPI. | Patente de formulação fitoquímica antineoplásica |
| **`PROGRAMA_COMPUTADOR`** | Registro oficial de software no INPI com código-fonte protegido.          | Registro de software de roteamento SDN               |
| **`DESENHO_INDUSTRIAL`**  | Registro de design, padrão visual ou forma plástica industrial.          | Registro de carcaça de dispositivo IoT              |

---

### 3.13 Enum: `ModalidadeBanca`

* **Origem no Extract:** Chaves sob `bancas` no JSON
* **Significado:** Modalidade do exame de qualificação ou defesa final avaliada.

| Literal do Enum                      | Significado de Negócio                                           | Contagem Total na Base | Exemplo Concreto                                         |
| :----------------------------------- | :---------------------------------------------------------------- | :--------------------- | :------------------------------------------------------- |
| **`GRADUACAO`**              | Banca de Trabalho de Conclusão de Curso (TCC) de graduação.    | 1.461 bancas.          | `"Introdução a Modelagem Molecular usando Avogadro"` |
| **`OUTRAS`**                 | Bancas de comissões julgadoras, concursos e processos seletivos. | 590 bancas.            | Banca de processo seletivo docente                       |
| **`MESTRADO`**               | Banca de defesa pública de dissertação de mestrado.            | 486 bancas.            | `"Aprendizagem de Química na Educação Básica"`     |
| **`QUALIFICACAO_MESTRADO`**  | Sessão de exame de qualificação de mestrado.                   | 221 bancas.            | Exame de qualificação em Engenharia de Controle        |
| **`DOUTORADO`**              | Banca de defesa pública de tese de doutorado.                    | 97 bancas.             | `"Sagrada poesia maldita: cosmovisão homoerótica"`   |
| **`QUALIFICACAO_DOUTORADO`** | Sessão de exame de qualificação de doutorado.                  | 4 bancas.              | Exame de qualificação em Engenharia Elétrica          |

---

### 3.14 Enum: `PapelEvento`

* **Origem no Extract:** `tipo` sob `eventos.participacoes` e `eventos.organizacoes`
* **Significado:** Atribuição do pesquisador no evento acadêmico.

| Literal do Enum            | Significado de Negócio                                         | Contagem Total na Base      | Exemplo Concreto                                                |
| :------------------------- | :-------------------------------------------------------------- | :-------------------------- | :-------------------------------------------------------------- |
| **`PARTICIPANTE`** | Congressista, ouvinte ou participante regular de minicursos.    | 1.815 participações.      | `"Participação em evento"`                                  |
| **`APRESENTADOR`** | Autor com apresentação oral ou pôster de trabalho no evento. | Mapeado em apresentações. | `"A Química do cérebro: ondas gamma..."`                    |
| **`ORGANIZADOR`**  | Membro da comissão coordenadora ou organizadora do evento.     | 415 organizações.         | `"Organização de evento - Semana de Ciência e Tecnologia"` |

---

### 3.15 Enum: `NivelProficiencia`

* **Origem no Extract:** Valores nos campos `compreende`, `fala`, `le` e `escreve` em `idiomas`
* **Significado:** Escala autodeclarada de domínio e fluência linguística.

| Literal do Enum             | Significado de Negócio                                 | Frequência Relativa na Base Real             |
| :-------------------------- | :------------------------------------------------------ | :-------------------------------------------- |
| **`BEM`**           | Domínio proficiente da competência linguística.      | Nível mais autodeclarado (428 ocorrências). |
| **`RAZOAVELMENTE`** | Domínio intermediário funcional da competência.      | Segunda maior ocorrência (282 ocorrências). |
| **`POUCO`**         | Conhecimento elementar ou básico da competência.      | Terceira ocorrência (174 ocorrências).      |
| **`FLUENTE`**       | Domínio materno ou pleno da competência linguística. | Mapeado para fluência completa.              |

---

### 3.16 Enum: `GrandeAreaCNPq`

* **Origem no Extract:** `areas_de_atuacao[].grande_area`
* **Significado:** Macro-área formal do conhecimento segundo a taxonomia oficial do CNPq.

| Literal do Enum                          | Significado de Negócio                                            | Contagem Total na Base | Exemplo Concreto                                    |
| :--------------------------------------- | :----------------------------------------------------------------- | :--------------------- | :-------------------------------------------------- |
| **`CIENCIAS_EXATAS_E_DA_TERRA`** | Matemática, Computação, Física, Química e Geociências.       | 170 áreas declaradas. | `"Ciências Exatas e da Terra / Química"`        |
| **`ENGENHARIAS`**                | Engenharia Elétrica, Mecânica, Civil, Produção e Metalúrgica. | 126 áreas declaradas. | `"Engenharias / Engenharia Elétrica"`            |
| **`CIENCIAS_HUMANAS`**           | Educação, Filosofia, História, Geografia e Sociologia.          | 39 áreas declaradas.  | `"Ciências Humanas / Educação"`                |
| **`CIENCIAS_SOCIAIS_APLICADAS`** | Administração, Economia, Direito e Ciência da Informação.     | 32 áreas declaradas.  | `"Ciências Sociais Aplicadas / Administração"` |
| **`LINGUISTICA_LETRAS_E_ARTES`** | Letras, Linguística e Artes Visuais/Música.                      | 11 áreas declaradas.  | `"Lingüística, Letras e Artes / Letras"`        |
| **`CIENCIAS_BIOLOGICAS`**        | Biologia Geral, Genética, Botânica e Zoologia.                   | 5 áreas declaradas.   | `"Ciências Biológicas / Botânica"`             |
| **`CIENCIAS_DA_SAUDE`**          | Medicina, Enfermagem, Farmácia e Saúde Coletiva.                 | 4 áreas declaradas.   | `"Ciências da Saúde / Saúde Coletiva"`         |
| **`OUTROS`**                     | Áreas multidisciplinares e transversais do CNPq.                  | 6 áreas declaradas.   | `"Outros / Defesa"`                               |

---

## 4. Matriz de Relacionamentos e Associações UML

A tabela abaixo sintetiza todas as 24 associações presentes no arquivo `ModeloClassesLattes.asta`, explicitando as entidades de extremidade, multiplicidades nos dois sentidos, nomes das associações e papéis desempenhados:

| Nome da Associação                 | Entidade Origem                              | Multiplicidade Origem | Entidade Destino         | Multiplicidade Destino | Papel de Origem / Destino                              | Regra de Negócio e Descrição Semântica                                                                 |
| :----------------------------------- | :------------------------------------------- | :-------------------: | :----------------------- | :--------------------: | :----------------------------------------------------- | :--------------------------------------------------------------------------------------------------------- |
| **`possui formacao`**        | `PESSOA`                                   |         `1`         | `FORMACAO_ACADEMICA`   |        `0..*`        | `pessoa` / `formacoes`                             | Um pesquisador registra zero ou várias titulações de graduação e pós-graduação.                    |
| **`promove`**                | `FORMACAO_ACADEMICA`                       |       `0..*`       | `INSTITUICAO`          |         `1`         | `formacao` / `instituicao`                         | Toda formação acadêmica é obrigatoriamente promovida e diplomada por 1 instituição de ensino.        |
| **`atua em`**                | `PESSOA`                                   |         `1`         | `ATUACAO_PROFISSIONAL` |        `0..*`        | `pessoa` / `vinculos`                              | O pesquisador possui um histórico cronológico de zero ou vários vínculos de trabalho.                  |
| **`ocorre em`**              | `ATUACAO_PROFISSIONAL`                     |       `0..*`       | `INSTITUICAO`          |         `1`         | `atuacao` / `instituicao`                          | Todo vínculo profissional ocorre perante exatamente 1 instituição empregadora/parceira.                 |
| **`orienta`**                | `PESSOA`                                   |         `1`         | `ORIENTACAO`           |        `0..*`        | `orientador` / `orientacoes_conduzidas`            | O docente atua na tutoria/orientação de zero ou múltiplos estudantes.                                   |
| **`orientado em`**           | `PESSOA`                                   |       `0..1`       | `ORIENTACAO`           |        `0..*`        | `orientando` / `orientacoes_recebidas`             | O estudante orientado vincula-se ao seu histórico de orientações acadêmicas recebidas.                 |
| **`ocorre em`**              | `ORIENTACAO`                               |       `0..*`       | `INSTITUICAO`          |         `1`         | `orientacao` / `instituicao`                       | Toda orientação acadêmica vincula-se ao programa de 1 instituição promotora.                          |
| **`financia orientacao`**    | `INSTITUICAO_FINANCIADORA`                 |       `0..1`       | `ORIENTACAO`           |        `0..*`        | `agencia_fomento` / `orientacoes_financiadas`      | A orientação de pesquisa pode usufruir de bolsa concedida por 1 agência financiadora.                   |
| **`autor de`**               | `PESSOA`                                   |       `1..*`       | `PRODUCAO`             |        `0..*`        | `autores` / `producoes`                            | Relação $N:N$: uma produção pode ter múltiplos coautores; um pesquisador é autor de várias obras. |
| **`distingue`**              | `PRODUCAO`                                 |       `0..1`       | `PREMIO_TITULO`        |        `0..*`        | `producao_premiada` / `laureas`                    | Uma produção científica destacada pode ser objeto de uma ou várias distinções/prêmios.              |
| **`homenageado em`**         | `PESSOA`                                   |         `1`         | `PREMIO_TITULO`        |        `0..*`        | `pessoa` / `premios_titulos`                       | O pesquisador é o destinatário de zero ou vários prêmios e títulos honoríficos.                      |
| **`compoe banca`**           | `PESSOA`                                   |       `1..*`       | `BANCA_EXAMINADORA`    |        `0..*`        | `avaliador` / `bancas_avaliadas`                   | Uma comissão julgadora de banca é composta por um colegiado de múltiplos avaliadores.                   |
| **`candidato em`**           | `PESSOA`                                   |         `1`         | `BANCA_EXAMINADORA`    |        `0..*`        | `candidato_defesa` / `bancas_defendidas`           | Toda sessão de banca avalia a defesa pública de exatamente 1 estudante candidato.                        |
| **`sediada em`**             | `BANCA_EXAMINADORA`                        |       `0..*`       | `INSTITUICAO`          |        `0..1`        | `bancas` / `universidade_promotora`                | A banca examinadora é promovida perante o programa de uma universidade ou ICT.                            |
| **`titular da patente`**     | `PATENTE_REGISTRO`                         |       `0..*`       | `INSTITUICAO`          |         `1`         | `patentes_depositadas` / `instituicao_depositante` | O ativo patentário possui obrigatoriamente a titularidade formal de 1 instituição mantenedora.          |
| **`sedia producao tecnica`** | `PRODUCAO_TECNICA_ARTISTICA_BIBLIOGRAFICA` |       `0..*`       | `INSTITUICAO`          |        `0..1`        | `producoes_tecnicas` / `instituicao_executora`     | A produção técnica ou software foi desenvolvido no âmbito de uma dada instituição.                   |
| **`MEMBRO_PROJETO`**         | `PESSOA`                                   |       `1..*`       | `PROJETO`              |        `0..*`        | `membro_equipe` / `equipe`                         | Classe associativa que qualifica o encargo do pesquisador na equipe do projeto (`papel`).                |
| **`FOMENTO_PROJETO`**        | `INSTITUICAO_FINANCIADORA`                 |       `0..*`       | `PROJETO`              |        `1..*`        | `financiador` / `financiado`                       | Classe associativa que qualifica o tipo de recurso concedido pela agência ao projeto (`tipo_apoio`).    |
| **`PARTICIPACAO_EVENTO`**    | `PESSOA`                                   |       `1..*`       | `EVENTO_CIENTIFICO`    |        `1..*`        | `partcipante` / `evento`                           | Classe associativa que qualifica o papel no evento e a comunicação/palestra apresentada.                 |
| **`PROFICIENCIA_IDIOMA`**    | `PESSOA`                                   |       `1..*`       | `IDIOMA`               |        `0..*`        | `falante` / `código`                              | Classe associativa que documenta a fluência linguística em 4 competências avaliadas.                    |
| **`atua na area`**           | `PESSOA`                                   |       `1..*`       | `AREA_ATUACAO`         |        `0..*`        | `pesquisadores` / `areas_atuacao`                  | Pesquisadores vinculam-se a suas áreas e especialidades declaradas no CNPq.                               |
| **`pesquisa em`**            | `PESSOA`                                   |       `1..*`       | `LINHA_PESQUISA`       |        `0..*`        | `pesquisadores` / `linhas_pesquisa`                | Pesquisadores conduzem ou integram eixos contínuos de investigação científica.                         |

---

## 5. Mapeamento de Extração e Integração Inter-Bases

Conforme as diretrizes arquiteturais de unificação (`Adito/Docs/ModelosClasses/PossiveisPontosIntegracao.md`), o modelo Lattes v4 atua como a base mestra curricular da produção técnico-científica dos docentes do Ifes:

1. **Chave Mestra de Integração de Pessoas (`PESSOA`):**

   * O atributo `PESSOA.id_lattes` (16 dígitos) constitui a chave primária natural mais forte da pesquisa nacional.
   * Conecta-se diretamente aos líderes e pesquisadores do SigPesq e aos grupos de pesquisa do CNPq DGP via `link_espelho_dgp` / `url_cnpq`.
   * Permite conciliação com o SRC via `PESSOA.nome_completo` e cruzamento de CPF/e-mail obtido no crawler.
2. **Cruzamento de Projetos e Iniciativas:**

   * A entidade `PROJETO.nome` correlaciona-se com `ProjetoPesquisa.titulo` do SigPesq e `Acao.titulo` do SRC, consolidando a atuação simultânea em pesquisa e extensão dos servidores do campus.
3. **Padronização Taxonômica de Conhecimento:**

   * A enumeração `GrandeAreaCNPq` do Lattes unifica de forma precisa a classificação do CNPq DGP (`GRUPO_PESQUISA.grande_area_predominante`), do SigPesq (`GrandeArea.nome`) e as inferências FORPROEX do SRC.
