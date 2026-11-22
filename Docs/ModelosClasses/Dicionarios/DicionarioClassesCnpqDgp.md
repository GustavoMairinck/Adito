# Dicionário de Dados do Modelo de Classes CNPq DGP

**Arquivo de Referência:** `Adito/Docs/ModelosClasses/ModeloClassesCnpqDgp.asta` (Diagrama de Classes UML do CNPq DGP)  
**Bases de Origem (Extração Bruta do ETL Horizon):** Registros de extração bruta do crawler do DGP armazenados no framework de tracking do pipeline em:
* `horizon_etl/data/exports/source_records_canonical.json` (registros brutos do tipo `cnpq_group_payload`, `cnpq_group_member`, `cnpq_research_line`)
* Coleção de payloads do crawler espelho em `Adito/Etls/Horizon/Etl/validacao_mock/dados/cnpq_espelhos/*.json`
* Extrator do crawler oficial: `horizon_etl/src/adapters/sources/cnpq_crawler.py` (`dgp_cnpq_lib`)

---

## Sumário das Classes, Associações e Enums do Modelo

1. **Entidade Central do Grupo e Localização:**
   * [`GRUPO_PESQUISA`](#1-classe-grupo_pesquisa)
   * [`ENDERECO`](#2-classe-endereco)
   * [`CONTATO`](#3-classe-contato)
2. **Pessoas, Membros e Formação Acadêmica:**
   * [`PESSOA`](#4-classe-pessoa) (Superclasse)
   * [`Pesquisador`](#5-classe-pesquisador) (Especialização de `PESSOA`)
   * [`Estudante`](#6-classe-estudante) (Especialização de `PESSOA`)
   * [`MEMBRO_GRUPO`](#7-classe-associativa-membro_grupo) (Classe Associativa $N:N$)
   * [`Titulacao`](#8-classe-titulacao)
3. **Linhas de Pesquisa e Infraestrutura:**
   * [`LINHA_PESQUISA`](#9-classe-linha_pesquisa)
   * [`GRUPO_PESQUISA_LINHA`](#10-classe-associativa-grupo_pesquisa_linha) (Classe Associativa $N:N$)
   * [`EQUIPAMENTO_SOFTWARE`](#11-classe-equipamento_software)
4. **Instituição, Campus e Parcerias Externas:**
   * [`INSTITUICAO`](#12-classe-instituicao)
   * [`INSTITUICAO_PARCEIRA`](#13-classe-instituicao_parceira) (Especialização de `INSTITUICAO`)
   * [`PARCERIA_GRUPO`](#14-classe-associativa-parceria_grupo) (Classe Associativa $N:N$)
   * [`Campus`](#15-classe-campus)
   * [`AREA_PREDOMINANTE`](#16-classe-area_predominante)
5. **Canais Específicos de Contato:**
   * [`Telefone`](#17-classes-especificas-de-contato-telefone-fax-email-website), [`Fax`](#17-classes-especificas-de-contato-telefone-fax-email-website), [`Email`](#17-classes-especificas-de-contato-telefone-fax-email-website), [`website`](#17-classes-especificas-de-contato-telefone-fax-email-website)
6. **Tipos Enumerados (`<<enumeration>>`):**
   * [`SituacaoGrupo`](#18-enum-situacaogrupo), [`PapelMembro`](#19-enum-papelmembro), [`StatusParticipacao`](#20-enum-statusparticipacao)
   * [`NivelTitulacao`](#21-enum-niveltitulacao), [`NivelTreinamento`](#22-enum-niveltreinamento), [`tipo_titulado`](#23-enum-tipo_titulado)
   * [`GrandeAreaCNPq`](#24-enum-grandeareacnpq), [`TipoInfraestrutura`](#25-enum-tipoinfraestrutura), [`TipoParceria`](#26-enum-tipoparceria), [`UF`](#27-enum-uf)

---

## 1. Entidade Central do Grupo e Localização

### 1. Classe: `GRUPO_PESQUISA`
Entidade nuclear que representa a unidade básica de produção científica certificada pela instituição mantenedora no Diretório dos Grupos de Pesquisa do CNPq (DGP).

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome_grupo`** | `String` | `1` | `nome_grupo`<br>*(no espelho bruto: cabeçalho ou legenda)* | Denominação oficial do grupo chancelada pelo CNPq. Quando o crawler extrai `"CNPq"` por artefato de topo do portal, o pipeline correlaciona o nome original do grupo. | `"Grupo de Pesquisa em Processamento de Sinais"`, `"Linguagens, Culturas e Ensino"` |
| **`situacao_do_grupo`** | `SituacaoGrupo` | `1` | `identificacao.situacao_do_grupo` | Estado cadastral do grupo no CNPq: homologado ativo (`CERTIFICADO`), com mais de 12 meses sem atualização (`CERTIFICADO_NAO_ATUALIZADO`), em elaboração (`EM_PREENCHIMENTO`) ou aguardando homologação (`AGUARDANDO_CERTIFICACAO`). | `CERTIFICADO` (no payload: `"Certificado"`) |
| **`ano_de_formacao`** | `Integer` | `1` | `identificacao.ano_de_formacao` | Ano de fundação e início formal das pesquisas do coletivo. | `2022`, `2014`, `2013` |
| **`data_da_situacao`** | `DateTime` | `1` | `identificacao.data_da_situacao` | Data e hora em que a situação cadastral vigente foi homologada pela autoridade institucional/CNPq (padrão `"DD/MM/YYYY HH:MM"`). | `2022-06-26 18:42:00` (no payload: `"26/06/2022 18:42"`) |
| **`data_do_ultimo_envio`** | `DateTime` | `1` | `identificacao.data_do_ultimo_envio` | Carimbo de data e hora em que o líder submeteu pela última vez o espelho atualizado do grupo ao CNPq. | `2026-05-25 08:35:00` (no payload: `"25/05/2026 08:35"`) |
| **`repercussoes`** | `String` | `0..1` | `repercussoes.descricao` | Texto síntese redigido pelos líderes sobre as principais contribuições científicas, patentes, produtos e impactos sociais gerados pelo grupo. | `"O grupo desenvolve pesquisas sobre práticas de linguagem..."`, `"Repercussões fictícias do grupo..."` |
| **`link_espelho_dgp`** | `String` | `1` | URL do espelho (`source_file` / `source_path`) | Endereço URL público e permanente de acesso ao espelho do grupo no portal do CNPq (`http://dgp.cnpq.br/dgp/espelhogrupo/<id_16_digitos>`). | `"http://dgp.cnpq.br/dgp/espelhogrupo/4099181037333209"`, `"http://dgp.cnpq.br/dgp/espelhogrupo/9115112132091239"` |

* **Associações da Classe `GRUPO_PESQUISA`:**
  * `localizacao_contato`: `ENDERECO [0..1]` (Sede física cadastrada).
  * `possui`: `CONTATO [1..*]` (Canais de comunicação agregados).
  * `Acessa`: `EQUIPAMENTO_SOFTWARE [0..*]` (Equipamentos e softwares de grande porte declarados).
  * `MEMBRO_GRUPO`: `PESSOA [1..*]` (Quadro humano via classe associativa `MEMBRO_GRUPO`).
  * `GRUPO_PESQUISA_LINHA`: `LINHA_PESQUISA [1..*]` (Linhas ativas via classe associativa `GRUPO_PESQUISA_LINHA`).
  * `PARCERIA_GRUPO`: `INSTITUICAO_PARCEIRA [1..*]` (Convênios via classe associativa `PARCERIA_GRUPO`).
  * `POSSUI`: `AREA_PREDOMINANTE [0..1]` (Eixo temático do conhecimento CNPq).
  * `Pertence`: `INSTITUICAO [1]` (Entidade mantenedora do grupo, e.g. Ifes).
  * `Ocorre`: `Campus [1]` (Campus físico onde as atividades do grupo acontecem).
  * Canais diretos: `Telefone [1..*]`, `Fax [1..*]`, `Email [1..*]`, `website [0..*]`.

---

### 2. Classe: `ENDERECO`
Representa a localização predial e geográfica da sede do grupo de pesquisa no campus institucional.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`logradouro`** | `String` | `1` | `endereco_contato.logradouro` | Nome oficial do logradouro público (rua, avenida, rodovia). | `"Avenida Sabiás"`, `"Rodovia ES-010 De 1 Até 99999, Km 6"` |
| **`numero`** | `String` | `0..1` | `endereco_contato.numero` | Numeração predial da entrada da unidade ou campus. Vazio quando `"s/n"`. | `"330"`, `"5"`, `""` |
| **`complemento`** | `String` | `0..1` | `endereco_contato.complemento` | Detalhamento interno no campus (prédio, bloco, laboratório). | `"Ifes (campus Serra)"`, `"Bloco 2, Sala 10"`, `""` |
| **`bairro`** | `String` | `1` | `endereco_contato.bairro` | Bairro ou distrito municipal da sede. | `"Morada de Laranjeiras"`, `"Manguinhos"` |
| **`localidade`** | `String` | `1` | `endereco_contato.localidade` | Município sede do campus. | `"Serra"`, `"Vitória"`, `"Vila Velha"` |
| **`uf`** | `UF` | `1` | `endereco_contato.uf` | Unidade Federativa da sede do grupo (mapeado para enum `UF`). | `ES` |
| **`cep`** | `String` | `1` | `endereco_contato.cep` | Código de Endereçamento Postal oficial dos Correios (apenas dígitos). | `"29166630"`, `"29173087"` |
| **`caixa_postal`** | `String` | `0..1` | `endereco_contato.caixa_postal` | Caixa postal contratada para correspondência postal. | `"29166-630"`, `""` |
| **`latitude`** | `String` | `0..1` | `endereco_contato.latitude` | Coordenada geográfica de latitude para georreferenciamento. | `"-20.1920861"`, `"0.0"` |
| **`longitude`** | `String` | `0..1` | `endereco_contato.longitude` | Coordenada geográfica de longitude para georreferenciamento. | `"-40.198090699999966"`, `"0.0"` |

---

### 3. Classe: `CONTATO`
Canais telemáticos de atendimento, divulgação e correspondência oficial do grupo.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`telefone`** | `String` | `0..1` | `endereco_contato.telefone` | Telefone fixo institucional ou ramal direto da secretaria/laboratório. | `"(27) 3348-0000"` *(exemplo fictício)*, `null` |
| **`fax`** | `String` | `0..1` | `endereco_contato.fax` | Número de fax legado da unidade. | `null` |
| **`contato_do_grupo`** | `String` | `0..1` | `endereco_contato.contato_do_grupo` | Endereço de correio eletrônico institucional do grupo ou do líder (no pipeline de extração pode receber máscara LGPD). | `"grupo.pesquisa@ifes.edu.br"`, `"contato.grupo@anon.lgpd"` *(exemplo fictício)* |
| **`website`** | `String` | `0..1` | `endereco_contato.website` | Página web ou portal institucional do laboratório/grupo. | `"serra.ifes.edu.br"`, `"sr.ifes.edu.br"`, `""` |

---

## 2. Pessoas, Membros e Formação Acadêmica

### 4. Classe: `PESSOA`
Superclasse que modela qualquer participante do quadro de recursos humanos do grupo de pesquisa.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | • `recursos_humanos.pesquisadores[].pesquisadores`<br>• `recursos_humanos.estudantes[].estudantes`<br>• `recursos_humanos.tecnicos[].nome`<br>• `identificacao.lideres_do_grupo` | Nome civil completo do integrante, limpo de tags HTML e elementos decorativos de interface (e.g. `"ui-button"`). | `"Ana Beatriz Rodrigues"`, `"Carlos Eduardo da Silva"`, `"Juliana Santos Ferreira"`, `"Lucas Mendes Pereira"` *(exemplo fictício)* |

* **Associações da Classe `PESSOA`:**
  * `MEMBRO_GRUPO`: `GRUPO_PESQUISA [1..*]` (Associação com o grupo de pesquisa).
  * `Possui`: `Titulacao` (Vínculo com seu nível de titulação formal).

---

### 5. Classe: `Pesquisador`
Especialização de `PESSOA`. Representa o membro pesquisador (docente ou técnico de nível superior com titulação acadêmica).

* **Herança:** Herda o atributo `nome` de `PESSOA`.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`titulacao_maxima`** | `NivelTitulacao` | `0..1` | `recursos_humanos.pesquisadores[].titulacao_maxima` | Maior grau acadêmico concluído e declarado pelo pesquisador no CNPq. | `DOUTORADO` (no payload: `"Doutorado"`), `MESTRADO` (no payload: `"Mestrado"`), `GRADUACAO` |

---

### 6. Classe: `Estudante`
Especialização de `PESSOA`. Representa o discente em treinamento científico ou tecnológico participante da equipe do grupo.

* **Herança:** Herda o atributo `nome` de `PESSOA`.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nivel_treinamento`** | `NivelTreinamento` | `0..1` | `recursos_humanos.estudantes[].nivel_de_treinamento` | Nível de escolaridade/curso em que o estudante atua na pesquisa. | `GRADUACAO` (no payload: `"Graduação"`), `MESTRADO`, `ENSINO_MEDIO_2O_GRAU` |

---

### 7. Classe Associativa: `MEMBRO_GRUPO`
Classe associativa que materializa a relação $N:N$ entre `PESSOA` e `GRUPO_PESQUISA`, armazenando o histórico e atributos temporais da participação.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`papel`** | `PapelMembro` | `1` | Inferido pela seção do payload:<br>• `identificacao.lideres_do_grupo`<br>• `recursos_humanos.pesquisadores`<br>• `recursos_humanos.estudantes`<br>• `recursos_humanos.tecnicos` | Papel formal ou função hierárquica desempenhada no grupo: líder principal (`LIDER`), segundo líder (`VICE_LIDER`), técnico de apoio (`TECNICO`), estrangeiro (`COLABORADOR_ESTRANGEIRO`) ou pesquisador/estudante geral. | `LIDER`, `TECNICO`, `COLABORADOR_ESTRANGEIRO` |
| **`status`** | `StatusParticipacao` | `1` | Inferido pela tabela de origem no payload:<br>• `ATIVO` se vier das tabelas regulares de RH<br>• `EGRESSO` se vier das tabelas `egressos_*` | Condição de vínculo do membro: participando ativamente dos projetos (`ATIVO`) ou ex-membro desligado da equipe (`EGRESSO`). | `ATIVO`, `EGRESSO` |
| **`data_inicio`** | `Date` | `1` | `recursos_humanos.*[].data_inicio` ou `data_inclusao` | Data formal de ingresso do membro na equipe de pesquisa do grupo. No caso de cadastros históricos legados, o DGP traz textualmente `"Anterior a abril de 2014"`, tratado pelo ETL como data sentinela. | `2022-06-20` (no payload: `"20/06/2022"`), `"Anterior a abril de 2014"` |
| **`data_fim`** | `Date` | `0..1` | `recursos_humanos.egressos_*[].data_fim` ou `data_egresso` | Data oficial de término da participação do integrante. Nulo (`null`) para membros ativos. | `2025-12-04` (no payload: `"04/12/2025"`), `2024-10-22`, `null` |

---

### 8. Classe: `Titulacao`
Representa a qualificação acadêmica formal de uma pessoa cadastrada no CNPq.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nivel_titulacao`** | `NivelTitulacao` | `1` | `recursos_humanos.pesquisadores[].titulacao_maxima` ou indicadores de RH | Grau de titulação acadêmica concluído. | `DOUTORADO`, `MESTRADO`, `ESPECIALIZACAO`, `GRADUACAO` |
| **`tipo_titulado`** | `tipo_titulado` | `1` | Inferido pela categoria de pertencimento da pessoa | Classifica a natureza do indivíduo portador da titulação. | `PESQUISADOR`, `ESTUDANTE` |

* **Associação:** `Possui`: `PESSOA` (Pessoa titular da habilitação).

---

## 3. Linhas de Pesquisa e Infraestrutura

### 9. Classe: `LINHA_PESQUISA`
Eixo temático e metodológico contínuo em torno do qual se estruturam os projetos de investigação do grupo.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`descricao_linha`** | `String` | `1` | `linhas_de_pesquisa.linhas[].nome_da_linha_de_pesquisa` | Título ou descrição formal da linha de pesquisa cadastrada no CNPq. | `"Comunicação"`, `"Educação no campo"`, `"Sistemas Analógicos e Digitais"`, `"Ciências dos Materiais aplicada a Engenharia"` |

* **Associação:** `GRUPO_PESQUISA_LINHA`: `GRUPO_PESQUISA [1..*]` (Associação $N:N$ com grupos).

---

### 10. Classe Associativa: `GRUPO_PESQUISA_LINHA`
Materializa o relacionamento $N:N$ entre `GRUPO_PESQUISA` e `LINHA_PESQUISA`, permitindo que um grupo desenvolva múltiplas linhas e que uma mesma linha possa congregar diferentes grupos em rede.

---

### 11. Classe: `EQUIPAMENTO_SOFTWARE`
Equipamento científico de grande porte (valor de aquisição relevante) ou software especializado licenciado para uso exclusivo ou compartilhado em atividades de P&D do grupo.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | `equipamentos_e_softwares_relevantes.items[][].equipamentos` ou `softwares` | Denominação comercial, marca ou modelo do ativo técnico declarado. | `"Espectrometro Raman"`, `"Servidor Dell PowerEdge R740"`, `"ArcGIS"` |
| **`tipo`** | `TipoInfraestrutura` | `1` | Mapeado conforme a subseção da tabela afirmativa de origem | Natureza do bem de infraestrutura tecnológica. | `EQUIPAMENTO`, `SOFTWARE` |

* **Associação:** `Acessa`: `GRUPO_PESQUISA [1]` (Grupo que opera o equipamento/software).

---

## 4. Instituição, Campus e Parcerias Externas

### 12. Classe: `INSTITUICAO`
Pessoa jurídica ou órgão educacional ao qual o grupo se subordina hierárquica e formalmente.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome_instituicao`** | `String` | `1` | `identificacao.instituicao_do_grupo` | Razão social ou nome institucional por extenso da entidade mantenedora. | `"Instituto Federal de Educação, Ciência e Tecnologia do Espírito Santo - IFES"` |

* **Associação:** `Pertence`: `GRUPO_PESQUISA [1..*]` (Grupos pertencentes à instituição).

---

### 13. Classe: `INSTITUICAO_PARCEIRA`
Especialização de `INSTITUICAO`. Entidade conveniada externa (empresa, universidade ou instituto de pesquisa) que mantém acordos de cooperação técnica ou financeira com o grupo.

* **Herança:** Herda o atributo `nome_instituicao` de `INSTITUICAO` (originário de `instituicoes_parceiras_relatadas_pelo_grupo.items[][].nome_da_instituicao_parceira`).

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`sigla`** | `String` | `0..1` | `instituicoes_parceiras_relatadas_pelo_grupo.items[][].sigla` | Sigla corporativa ou acrônimo da organização parceira. | `"UFES"`, `"ARCELORMITTAL"`, `"CVRD"`, `"UAH"` |
| **`uf`** | `UF` | `0..1` | `instituicoes_parceiras_relatadas_pelo_grupo.items[][].uf` | Unidade Federativa da sede da instituição. Nulo ou valor `EXTERIOR` quando se trata de instituição estrangeira. | `ES`, `MG`, `RJ`, `EXTERIOR` |

---

### 14. Classe Associativa: `PARCERIA_GRUPO`
Materializa a associação $N:N$ entre `GRUPO_PESQUISA` e `INSTITUICAO_PARCEIRA`.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`tipo_parceria`** | `TipoParceria` | `1` | Inferido pela seção do payload:<br>• `instituicoes_parceiras_relatadas_pelo_grupo`<br>• `incts_parceiras_relatadas_pelo_grupo` | Classificação da modalidade da cooperação institucional: convênio com entidade parceira (`INSTITUICAO_PARCEIRA`) ou rede nacional de pesquisa (`INCT_PARCEIRO`). | `INSTITUICAO_PARCEIRA`, `INCT_PARCEIRO` |

---

### 15. Classe: `Campus`
Unidade descentralizada de ensino e pesquisa do Ifes onde o grupo está sediado.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`nome`** | `String` | `1` | `identificacao.unidade` | Nome do campus ou centro tecnológico sede do grupo. | `"Instituto Federal do Espírito Santo - Campus Serra"`, `"Unidade Serra"` |

* **Associação:** `Ocorre`: `GRUPO_PESQUISA [1..*]` (Grupos abrigados no campus).

---

### 16. Classe: `AREA_PREDOMINANTE`
Eixo temático do conhecimento CNPq que concentra o núcleo vocacional de pesquisa do grupo.

| Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico e Regra de Negócio | Exemplo Real Concreto |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`eixo`** | `String` | `1` | `identificacao.area_predominante` | String contendo a Grande Área e Área do CNPq separadas por ponto-e-vírgula. | `"Lingüística, Letras e Artes; Letras"`, `"Engenharias; Engenharia Elétrica"`, `"Ciências Exatas e da Terra; Ciência da Computação"` |

* **Associação:** `POSSUI`: `GRUPO_PESQUISA` (Grupo de pesquisa classificado no eixo).

---

## 5. Classes Específicas de Contato (`Telefone`, `Fax`, `Email`, `website`)

O modelo de classes do CNPq DGP contempla classes dedicadas para cada canal de comunicação direta associado ao `GRUPO_PESQUISA`:

| Classe | Atributo | Tipo UML | Multiplicidade | Origem no Payload de Extração | Significado Semântico | Exemplo Real Concreto |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **`Telefone`** | **`Numero`** | `int` | `1` | `endereco_contato.telefone` | Dígitos do número telefônico de contato institucional do laboratório/secretaria. | `33480000` *(exemplo fictício)* |
| **`Fax`** | **`numero`** | `String` | `1` | `endereco_contato.fax` | Número do aparelho de fac-símile institucional (campo legado). | `"3348-0001"` *(exemplo fictício)*, `null` |
| **`Email`** | **`endereco`** | `String` | `1` | `endereco_contato.contato_do_grupo` | Endereço de correio eletrônico institucional do grupo de pesquisa. | `"grupo.pesquisa@ifes.edu.br"` *(exemplo fictício)* |
| **`website`** | **`url`** | `String` | `1` | `endereco_contato.website` | Endereço URL da página ou blog do laboratório/grupo. | `"serra.ifes.edu.br"`, `"sr.ifes.edu.br"` |

---

## 6. Tipos Enumerados (`<<enumeration>>`)

### 18. Enum: `SituacaoGrupo`
Status formal da situação do certificado do grupo no CNPq.
* **Origem:** `identificacao.situacao_do_grupo`
* **Literais no Modelo Astah:**
  * **`CERTIFICADO`:** Grupo com dados atualizados e validado pela instituição mantenedora.
  * **`CERTIFICADO_NAO_ATUALIZADO`:** Grupo que permaneceu sem submissão de atualização por mais de 12 meses.
  * **`EM_PREENCHIMENTO`:** Proposta de grupo em elaboração pelo líder.
  * **`AGUARDANDO_CERTIFICACAO`:** Proposta enviada à Pró-Reitoria de Pesquisa aguardando parecer.

---

### 19. Enum: `PapelMembro`
Função hierárquica e acadêmica desempenhada pelo indivíduo na equipe do grupo.
* **Origem:** Seções de recursos humanos do espelho CNPq
* **Literais no Modelo Astah:**
  * **`LIDER`:** Pesquisador líder do grupo chancelado no portal.
  * **`VICE_LIDER`:** Pesquisador segundo líder formalmente designado.
  * **`TECNICO`:** Servidor técnico de suporte operacional/laboratorial.
  * **`COLABORADOR_ESTRANGEIRO`:** Pesquisador visitante de instituição do exterior em cooperação.

---

### 20. Enum: `StatusParticipacao`
Condição de exercício do integrante no grupo.
* **Origem:** Tabelas ativas vs tabelas de histórico (`egressos_*`)
* **Literais no Modelo Astah:**
  * **`ATIVO`:** Integrante com atuação vigente nos projetos e publicações.
  * **`EGRESSO`:** Ex-membro que se desligou da equipe de pesquisa.

---

### 21. Enum: `NivelTitulacao`
Maior formação acadêmica concluída pelo pesquisador ou membro.
* **Origem:** `recursos_humanos.pesquisadores[].titulacao_maxima`
* **Literais no Modelo Astah:**
  * `DOUTORADO`, `MESTRADO`, `MESTRADO_PROFISSIONAL`, `ESPECIALIZACAO`, `GRADUACAO`, `ENSINO_MEDIO_TECNICO`, `OUTRA`, `POS_DOUTORADO`

---

### 22. Enum: `NivelTreinamento`
Grau de ensino em que os discentes atuam no grupo.
* **Origem:** `recursos_humanos.estudantes[].nivel_de_treinamento`
* **Literais no Modelo Astah:**
  * `POS_DOUTORADO`, `DOUTORADO`, `MESTRADO`, `MESTRADO_PROFISSIONAL`, `MBA`, `ESPECIALIZACAO`, `GRADUACAO`, `ENSINO_PROFISSIONAL_TECNICO`, `ENSINO_MEDIO_2O_GRAU`

---

### 23. Enum: `tipo_titulado`
Classificação da categoria acadêmica da pessoa titulada.
* **Literais no Modelo Astah:**
  * `PESQUISADOR`
  * `ESTUDANTE`

---

### 24. Enum: `GrandeAreaCNPq`
Nove macro-áreas regulamentadas na taxonomia do conhecimento do CNPq.
* **Literais no Modelo Astah:**
  * `CIENCIAS_EXATAS_E_DA_TERRA`, `CIENCIAS_BIOLOGICAS`, `ENGENHARIAS`, `CIENCIAS_DA_SAUDE`, `CIENCIAS_AGRARIAS`, `CIENCIAS_SOCIAIS_APLICADAS`, `CIENCIAS_HUMANAS`, `LINGUISTICA_LETRAS_E_ARTES`, `MULTIDISCIPLINAR`

---

### 25. Enum: `TipoInfraestrutura`
Classificação do ativo de P&D do grupo.
* **Literais no Modelo Astah:**
  * `EQUIPAMENTO`
  * `SOFTWARE`

---

### 26. Enum: `TipoParceria`
Modalidade institucional de convênio com terceiros.
* **Literais no Modelo Astah:**
  * `INSTITUICAO_PARCEIRA`
  * `INCT_PARCEIRO`

---

### 27. Enum: `UF`
Unidades Federativas brasileiras (e opção internacional) aplicáveis aos endereços e instituições parceiras.
* **Literais no Modelo Astah:**
  * `AC`, `AL`, `AP`, `AM`, `BA`, `CE`, `DF`, `ES`, `GO`, `MA`, `MT`, `MS`, `MG`, `PA`, `PB`, `PR`, `PE`, `PI`, `RJ`, `RN`, `RS`, `RO`, `RR`, `SC`, `SP`, `SE`, `TO`, `EXTERIOR`
