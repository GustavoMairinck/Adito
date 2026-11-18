# Identidade visual do Adito

Guia de aplicação e registro das alterações • 11 de novembro de 2026

O Adito reúne consultas e análises de pesquisa e extensão do IFES Campus Serra. Este guia registra a identidade aplicada à interface e orienta a continuidade do design pela equipe de desenvolvimento.

# **Direção visual**

A composição usa verde-floresta, superfícies claras com tom de papel e bordas discretas. O nome Adito ganha presença no menu e na entrada do chat. A identificação Pesquisa e extensão e a referência ao Campus Serra situam o produto no contexto institucional.

A marca gráfica foi adaptada da imagem fornecida pela equipe, com círculo vermelho, peças verdes e barra horizontal em uma base arredondada. A versão clara usa fundo claro e borda sálvia. A escura usa fundo grafite e peças mais claras, acompanhando o tema selecionado.

# **Tipografia da interface**

| Família | Aplicação | Pesos |
| :---- | :---- | :---- |
| IBM Plex Sans | Títulos, navegação, textos, formulários e rótulos | 400, 500, 600 e 700 |
| IBM Plex Mono | SQL, códigos e números em tabelas | 400 e 500 |

A família IBM Plex já era usada na aplicação e foi mantida. Os arquivos e as licenças SIL Open Font License passam a acompanhar o frontend em public/fonts. O carregamento local permite usar as fontes também sem acesso ao Google Fonts. O navegador usa as fontes de sistema como alternativa durante o carregamento.

# **Paleta do tema claro**

| Cor | HEX | Uso |
| :---- | :---- | :---- |
| Floresta | \#173F35 | Menu lateral e presença da marca |
| Verde principal | \#23634A | Botões principais e ações |
| Papel | \#F6F7F2 | Fundo da aplicação |
| Branco | \#FFFFFF | Cartões, tabelas e formulários |
| Sálvia clara | \#EDF1E9 | Superfícies de apoio e cabeçalhos |
| Texto principal | \#1F302B | Títulos e conteúdo |
| Texto secundário | \#465C51 | Descrições e rótulos |
| Borda | \#DDE5DD | Separação entre componentes |
| Bronze | \#B98A3C | Token de cor secundária |

# **Tema escuro e estados**

O tema escuro usa fundos grafite e superfícies cinza para separar as áreas da aplicação. Os cartões do chat têm fundo \#242930, borda \#56616D e subtítulo \#C0CAD4. A seleção mantém fundo cinza e recebe contorno verde \#68D388. Os botões principais usam \#2B7A42 com texto branco.

| Elemento | Valor | Aplicação |
| :---- | :---- | :---- |
| Fundo | \#121416 | Plano de fundo |
| Superfície | \#1C1F23 | Cartões e áreas de conteúdo |
| Superfície elevada | \#262B31 | Cabeçalhos e áreas de apoio |
| Menu | \#171B20 | Navegação lateral |
| Texto | \#F0F4F1 | Leitura principal |
| Destaque | \#389653 | Textos de ação e seleção |
| Ação principal | \#2B7A42 | Botões e ações no tema escuro |
| Cartão do chat | \#242930 | Superfície destacada sobre o fundo grafite |
| Erro | \#C50707 / \#F04444 | Tema claro / escuro |
| Aviso | \#E65100 | Mensagens de atenção |

# **Componentes e proporções**

| Componente | Padrão aplicado |
| :---- | :---- |
| Marca tipográfica | IBM Plex Sans 600, espaçamento entre letras de −0,055 em. Nome de 26 px no menu e 36 px na entrada do chat. Distância de 8 px entre a logo e o nome no menu, cabeçalho móvel e chat. |
| Títulos | Título do chat de 24 px em telas estreitas e 30 px a partir de 640 px. Peso 600 e entrelinha compacta. |
| Cartões | Bordas de 1 px e cantos de 12 px. No chat escuro, cartões cinza com sombras e bordas claras. A seleção usa contorno verde. |
| Botões | Cantos de 8 px, tamanho de texto de 14 px e peso 500\. Ações principais com verde e texto branco. |
| Espaçamento | Ritmo de 4, 8, 12, 16, 24 e 32 px nas áreas ajustadas, com separação maior entre blocos de conteúdo. |
| Ícones | Lucide já utilizado no projeto. Ícones de áreas do chat em recipientes de 40 px com cantos arredondados. |
| Foco e movimento | Contorno de foco de 2 px, deslocado 3 px. Redução de animações e transições conforme a preferência de movimento do sistema. |

# **Organização do chat**

A entrada apresenta Adito e o título Explore a pesquisa e a extensão do Campus Serra. Os cartões mantêm as cinco áreas disponíveis. Em telas a partir de 640 px, há três cartões na primeira linha e dois centralizados na segunda. Em telas menores, o arranjo usa duas colunas com a última opção centralizada.

O campo de pergunta recebe cantos de 16 px e identificação acessível. O botão de envio possui nome acessível. Os cartões comunicam a seleção também por aria-pressed.

# **Registro das alterações**

| Área | Alteração aplicada |
| :---- | :---- |
| Navegação | Logo fornecida pela equipe aplicada ao menu, cabeçalho móvel e chat. Troca automática entre as versões clara e escura, incluindo o ícone da aba. Nome Adito, rodapé IFES Campus Serra e item Meu painel. |
| Chat | Nova apresentação da marca e título institucional. Cartões maiores, subtítulos mais legíveis, ícones com recipientes quadrados e seleção com borda e fundo. |
| Áreas do chat | Opção Editais e Bolsas removida. Permanecem Pesquisa, Extensão, Grupos CNPq, Produção Lattes e Pesquisadores. |
| Composição dos cartões | Centralização das linhas incompletas preservada, incluindo as duas opções inferiores no desktop. |
| Campo de pergunta | Cantos de 16 px, sombra discreta e rótulos acessíveis para o campo e para o envio. |
| Painel pessoal | Título Meu painel e descrição das análises salvas. Cartões de métrica com título de 14 px, rótulo de 10 px e valor de 18 a 24 px conforme a largura, com espaçamento compacto. |
| Administração | Aba Contextos de dados, ação Carregar e indexar contextos e Histórico de carregamento. Base de conhecimento substitui o rótulo Governanca IA. |
| Exploração de dados | Recebe a nova paleta, tipografia local, foco visível e padrões compartilhados de botões e superfícies. |
| Tema escuro | Restaurada a versão anterior após a revisão do menu verde. Configuração final com menu grafite \#171B20 e fundo \#121416. Cartões cinza com bordas claras, ícones neutros e contorno verde na seleção. |
| Fontes e metadados | Removidas as importações externas redundantes. Fontes locais, licenças, descrição do produto e cor do navegador incluídas. |

# **Referências de implementação**

src/style.css centraliza os tokens de cores, superfícies, tipografia e componentes compartilhados. public/fonts/fonts.css declara as fontes locais. index.html carrega essa folha e define os metadados da aplicação.

As telas ajustadas incluem SidebarNav.vue, ChatConversation.vue, ChatInputArea.vue, MeuDashboardView.vue e AdminView.vue. BrandIcon.vue compartilha a logo de public/brand/adito-light.png e adito-dark.png. As classes adito-wordmark e adito-topic definem a assinatura textual e os cartões do chat.

# **Continuidade do design**

Use os tokens semânticos de fundo, texto, borda e ação ao criar componentes. Reserve a família monoespaçada para SQL, identificadores e dados numéricos. Escreva rótulos em português e nomeie ações de acordo com o resultado que produzem.

Ao alterar uma tela, confira temas claro e escuro, navegação por teclado e comportamento em telas estreitas. A compilação valida a estrutura e os tipos. A revisão visual deve conferir quebras de linha, recortes, contraste e alinhamento dos componentes em uso.