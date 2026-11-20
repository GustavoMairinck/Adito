# ADR 0007: Distribuição e Atualização Criptografada do Banco `dados.db`

**Status:** Aceito  
**Data:** 20/11/2026

## Contexto/Problema
O banco analítico local do Muninn (`dados.db`, SQLite, ~7,6 MB) consolida dados de pesquisa e extensão do IFES Campus Serra (SigPesq, Lattes, CNPq/DGP e SRC). Embora os testes anti-PII do ETL já removam CPF, e-mail e telefone, a base contém **nomes reais** de servidores e estudantes; por cautela com a **LGPD**, o arquivo não pode ser publicado em texto claro em repositório público.

Simultaneamente, o projeto precisa atender três restrições operacionais fortes:
1. **Zero servidor próprio:** a equipe não mantém VM, storage autenticado ou backend dedicado no IFES/LEDS para servir o banco.
2. **Sem conta GitHub para o usuário final:** gestores, professores e coordenadores não-técnicos não devem precisar criar conta no GitHub nem gerar tokens.
3. **Sem distribuição manual de arquivos:** evitar envio do `.db` por Google Drive ou e-mail, garantindo atualização pela própria interface do aplicativo quando a equipe rodar um novo ETL.

## Decisão Tomada
Separar completamente a distribuição do aplicativo da distribuição dos dados e adotar **criptografia *client-side* em GitHub Releases público**:

1. **Instalador limpo (sem PII):** o executável do Muninn nunca embute `dados.db`, permitindo publicação aberta e *auto-update* simples ([ADR 0006](./ADR-0006-empacotamento-e-auto-update-desktop.md)).
2. **Publicação cifrada pelo ETL:** o pipeline de dados compacta e criptografa `dados.db` com **AES-256-GCM**, gerando `dados.db.enc` e um `manifest.json` (versão da carga, data e hash **SHA-256**), publicados no GitHub Releases público.
3. **Onboarding com chave institucional única:** no primeiro acesso, o usuário informa uma **chave institucional de alta entropia (256 bits)** entregue pela equipe. O Tauri armazena essa chave no **cofre do sistema operacional** (`keyring`), baixa `dados.db.enc`, valida o SHA-256 e descriptografa `dados.db` localmente em `app_local_data_dir`.
4. **Atualização pela interface:** ao abrir o app, o Muninn consulta o `manifest.json` e permite atualizar apenas o `dados.db` pela UI quando houver nova carga, sem reinstalar o executável.

## Justificativa
1. **Única alternativa que satisfaz todas as restrições simultaneamente:** atende privacidade (conteúdo cifrado em AES-256-GCM), **zero servidor próprio**, **zero conta GitHub** para usuários não-técnicos e **atualização automatizada pela UI** (sem Drive/e-mail).
2. **Desacoplamento entre código e dados:** atualizações periódicas do ETL (~7,6 MB) não exigem recompilar nem redistribuir ~80–150 MB do executável completo.
3. **Baixa sobrecarga operacional:** uma chave institucional única elimina manutenção manual cada vez que um novo usuário interno passa a usar o app.

## Alternativas Consideradas
* **App limpo + envio manual de `dados.db` por Drive/Nextcloud/e-mail + importação na UI:** descartada pela UX ruim para usuários finais e alto risco de desorganização de versões.
* **Híbrido (`dados.db` embutido em instalador privado + troca futura por canal interno manual):** descartada porque contamina o instalador inteiro com PII (inviabilizando GitHub Releases público e *auto-update*) e mantém o fluxo manual nas atualizações futuras.
* **Somente embutido no instalador privado:** descartada por obrigar recompilação e redistribuição de ~80–150 MB a cada atualização de 7,6 MB de dados, além de tornar o instalador privado.
* **Endpoint estático na rede interna do IFES/LEDS (intranet/VPN):** descartada pela restrição definitiva de **zero servidor próprio** (embora seja o caminho natural caso a instituição disponibilize infraestrutura dedicada no futuro).
* **GitHub Releases em repositório privado + OAuth Device Flow no app:** descartada por exigir que todos os usuários não-técnicos tenham conta no GitHub e gestão de acesso na organização; embutir um token read-only do GitHub no binário também foi descartado por ser inseguro (facilmente extraível do executável).
* **`dados.db.enc` no GitHub Releases público com envelope de chaves por usuário (`age`/multi-destinatário):** descartada pela sobrecarga operacional de emitir chaves e republicar o manifesto a cada entrada ou saída de usuário, sem eliminar o risco retroativo em versões já baixadas.

## Consequências
* **Positivas:** custo zero de infraestrutura; instalador livre de PII; experiência automatizada para o usuário final sem conta GitHub nem Drive/e-mail; atualização independente da base; integridade verificada por SHA-256 e AES-256-GCM.
* **Negativas:** o arquivo cifrado (`.enc`) fica hospedado em infraestrutura de terceiros (GitHub público); requer digitação da chave institucional uma vez no onboarding inicial; adiciona uma etapa de criptografia no ETL e rotina de download/descriptografia no app.
* **Riscos:**
  - *Sem revogação retroativa em caso de vazamento da chave:* se uma chave vazar, quem já tiver baixado aquela versão específica do `dados.db.enc` conseguirá descriptografá-la. **Mitigação:** usar chave forte de 256 bits, garantir via testes automatizados anti-PII que `dados.db` nunca contenha CPF/e-mail/telefone, e **rotacionar a chave** na próxima carga do ETL para bloquear acesso a atualizações futuras.
  - *Indisponibilidade do cofre do SO em ambientes Linux mínimos:* mitigado pelo mecanismo de detecção `store_available` já presente em `src-tauri/src/lib.rs`, exibindo aviso claro ao usuário.

## Referências
* [ADR 0001: Migração da Camada de Dados para 100% SQLite](./ADR-0001-migracao-dados-100-sqlite.md)
* [ADR 0002: Separação Física entre `dados.db` e `app.db`](./ADR-0002-separacao-dados-db-app-db.md)
* [ADR 0006: Empacotamento Desktop sem Privilégio de Admin e Auto-Update Assistido](./ADR-0006-empacotamento-e-auto-update-desktop.md)
* Estudo comparativo completo: [`Muninn/docs/resultados/estrategia-distribuicao-muninn.pdf`](../../Muninn/docs/resultados/estrategia-distribuicao-muninn.pdf)
