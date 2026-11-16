# Resultados da adaptação da interface do Adito

Implementação preparada localmente para a tarefa #48, aproveitando a paleta
institucional e as sugestões de perguntas de pesquisa e extensão já presentes
no repositório.

## Análise da interface

- A tela `/explorar` estava fora do menu e consultava `/api/projects`, com campos
  e consultas da demonstração de vendas.
- Os seletores de contexto, as restrições de colunas sensíveis e o acesso ao
  SQLite já existiam e foram reutilizados.
- O modelo UML unificado contém entidades como iniciativas, pessoas,
  organizações e produções. A classificação das relações analíticas pode ser
  informada pelo contexto conforme os fatos e dimensões disponibilizados.

## Alterações realizadas

- Identidade Adito no menu, cabeçalho, chat, título da página e janela desktop.
- Acesso a **Explorar dados** pelo menu lateral.
- Catálogo por contexto com fatos, dimensões e entidades, nomes de exibição e
  descrições configuráveis em `views.json`.
- Tabela com colunas dinâmicas, inspeção de tipos, seleção de colunas,
  ordenação, busca textual, filtro por valor exato e paginação.
- Gráfico de frequência com até 12 grupos, calculado sobre todos os registros
  filtrados.
- Estados de carregamento, ausência de dados, falha de conexão e nova tentativa.
- Cancelamento de consultas anteriores ao alterar os controles.
- Endpoints `/api/explorer/tables` e `/api/explorer/rows`, protegidos pela
  autenticação local e pelo contexto do usuário. As consultas são construídas
  com relações e colunas permitidas, parâmetros vinculados e conexão de leitura.
  As colunas sensíveis ficam fora do catálogo, dos registros e dos controles.
- Instruções de uso e configuração adicionadas ao README da aplicação.

## Identidade visual e ajustes do chat

O guia de identidade visual está salvo na documentação do projeto e reúne as
fontes, cores, proporções dos componentes e alterações solicitadas na interface.
[Consultar o documento de identidade visual](../design/Identidade-visual-Adito.md).

- Fontes IBM Plex Sans para a interface e IBM Plex Mono para SQL e dados
  numéricos, com arquivos e licenças incluídos no frontend.
- Tema claro com menu verde-floresta `#173F35`, fundo `#F6F7F2` e superfícies
  brancas.
- Remoção da opção **Editais e Bolsas** da entrada do chat. As cinco áreas
  disponíveis são Pesquisa, Extensão, Grupos CNPq, Produção Lattes e Pesquisadores.
- Cartões organizados em três opções na primeira linha e duas centralizadas na
  segunda, em telas a partir de 640 px.
- Cartões do chat escuro com fundo `#242930`, borda `#56616D`, subtítulo
  `#C0CAD4` e contorno de seleção `#68D388`.
- Restauração do tema anterior após a revisão do menu verde. A configuração
  final usa menu grafite `#171B20` e fundo `#121416` no tema escuro.
- Rótulos institucionais no menu, chat e painel pessoal, além dos ajustes de
  navegação da área administrativa registrados no guia.

## Validações

- Compilação de produção com `npm run build` aprovada, incluindo a checagem
  TypeScript. O Vite emite aviso sobre os bundles de gráficos acima de 500 kB.
- Dez testes da API aprovados, incluindo busca, filtros, paginação, agrupamentos,
  valores nulos e binários, isolamento de contextos, colunas sensíveis e acesso
  pelo token do desktop sem chave da Mistral.
- Verificações de estado do frontend aprovadas para inicialização, paginação,
  filtros, ordenação, seleção de colunas, gráfico, cancelamento de consultas e
  troca de relação.
- Regressão existente do núcleo SQLite aprovada em uma pasta temporária limpa,
  com 67 verificações aprovadas e nenhuma falha. Os 68 exemplos de consulta da
  demonstração também executaram com sucesso.
- `git diff --check` aprovado.

## Integração e pendências

A exploração utiliza os contextos carregados no `dados.db` SQLite do desktop.
Os metadados opcionais `kind` e `label` permitem identificar fatos, dimensões
e entidades do modelo unificado. O README contém um exemplo com `iniciativa`.
As consultas da nova API foram verificadas com uma base temporária de teste.
A validação com o conjunto institucional depende de disponibilizar suas relações
no SQLite e no contexto correspondente.

A inspeção visual no navegador e a execução da janela Tauri ficaram pendentes.
O serviço de acesso ao navegador estava indisponível nesta sessão.
