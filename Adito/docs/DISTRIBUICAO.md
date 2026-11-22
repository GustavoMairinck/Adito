# Distribuição e atualização do Adito

Como o app e os dados chegam ao usuário, conforme o [ADR-0006](../../Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md) e o [ADR-0007](../../Docs/ADR/ADR-0007-distribuicao-criptografada-dados-db.md).

**Em uma frase:** o instalador é público e não leva dados. Os dados vão trancados (AES-256-GCM) numa release separada do GitHub. O app junta os dois na máquina do usuário e, a cada abertura, confere se há versão nova de um ou de outro.

## Como funciona para o usuário

1. Instala o `.exe` (Windows, sem administrador) ou o `.AppImage` (Linux).
2. No primeiro uso, o Adito pede a **chave dos dados**. A chave fica guardada no cofre do sistema. O app baixa os dados, confere, destranca e segue.
3. A cada abertura, o app lê dois arquivos pequenos e abertos no GitHub, sem conta e sem chave:
   - `latest.json` do release mais recente → versão do app;
   - `manifest.json` da release `dados` → versão dos dados.
4. Se algum dos dois for mais novo, aparece um botão discreto **"Atualização disponível →"** no canto de baixo da barra lateral. Nada abre sozinho. Clicar mostra o que há de novo, com as opções **Atualizar** ou **Depois**.
   - App: baixa, confere a assinatura Ed25519, instala por cima e reinicia.
   - Dados: baixa, confere tamanho e SHA-256, destranca com a chave do cofre e troca só o `dados.db`. O `app.db` (chat, RAG, painéis) não é tocado.
   - Se a chave mudou (rotação), o painel pede a nova antes de atualizar.

## Configuração única (quem mantém o projeto)

### 1. Chaves de assinatura do app (Ed25519)

```bash
cd Adito/app/frontend-vue && npx tauri signer generate -w ~/.tauri/adito.key
```

- Chave **privada** e senha → *Settings → Secrets → Actions* do repositório `SmartIdea-ifes-serra/Adito`: `TAURI_SIGNING_PRIVATE_KEY` (conteúdo do arquivo) e `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`.
- Chave **pública** (`~/.tauri/adito.key.pub`) → `Adito/app/src-tauri/tauri.conf.json`, em `plugins.updater.pubkey`, no lugar de `SUBSTITUIR_PELA_CHAVE_PUBLICA_DO_TAURI_SIGNER`. Enquanto o placeholder estiver lá, o workflow de release falha de propósito.

Perder a chave privada impede atualizar quem já instalou: guarde uma cópia num cofre da equipe.

### 2. Chave institucional dos dados (256 bits)

```bash
make chave-dados
```

O comando imprime 64 caracteres hexadecimais. Guarde a chave num cofre da equipe e repasse só por canal interno. Ela **não** vai para o GitHub nem para o código.

## Publicar uma carga nova dos dados

Depois de rodar o ETL e o `popular_banco.py`:

```bash
ADITO_DADOS_CHAVE=<chave> make publicar-dados
```

O script ([`Adito/scripts/publicar_dados.sh`](../scripts/publicar_dados.sh)) faz o seguinte:
1. tranca o `Adito/app/data/dados.db`;
2. gera o `manifest.json` (versão = data de hoje, SHA-256 e `chave_id`);
3. sobe tudo na release `dados`, marcada como pré-lançamento para nunca virar o "release mais recente" do app.

O pacote novo sobe antes do manifesto e o anterior é mantido, então ninguém que esteja no meio de um download quebra. Outro arquivo ou outra versão: `make publicar-dados ARGS="caminho/dados.db 2026-12-01"`.

**Trocar a chave** (vazamento ou rotina): gere outra com `make chave-dados` e publique com ela. Quem tiver a chave antiga vê o pedido da nova no painel de atualização.

## Publicar uma versão nova do app

```bash
git tag v0.2.0 && git push upstream v0.2.0
```

O workflow [`release-app.yml`](../../.github/workflows/release-app.yml) gera os instaladores de Windows e Linux, assina cada um e monta o `latest.json`. Tudo cai num **release em rascunho**. Os usuários só recebem o aviso depois que alguém revisa e clica em *Publish release*.

O workflow também confere duas coisas:
- se a chave pública está configurada;
- se nenhum arquivo de dados entrou no instalador.

## O núcleo Python dentro do instalador (US-011)

O chat e os painéis rodam no núcleo Python. Para o usuário não precisar instalar Python, o núcleo vira um executável único, `adito-backend`, feito pelo PyInstaller ([`backend/adito-backend.spec`](../app/backend/adito-backend.spec)). O Tauri leva esse executável junto (`externalBin`) e o sobe ao abrir o app.

- O `externalBin` só entra nos builds de instalador (CI e `make instalador`), pelo `--config`. Assim o `cargo run` e o `tauri dev` continuam usando o `.venv`, sem precisar empacotar nada.
- O PyInstaller não faz build cruzado: o `.exe` do núcleo sai do runner Windows do CI, e o Linux sai do runner Linux.
- O [`scripts/empacotar_nucleo.py`](../app/scripts/empacotar_nucleo.py) roda o PyInstaller, sobe o executável para conferir se ele responde, e o copia para `src-tauri/binaries/` com o nome que o Tauri exige.

Gerar os instaladores Linux nesta máquina (precisa do `.venv` do app e do `node_modules` do front):

```bash
make instalador
```

Os arquivos saem em `Adito/app/src-tauri/target/release/bundle/` (`deb/` e `appimage/`).

## Pendências conhecidas

- **Compactação:** o ADR-0007 fala em compactar antes de cifrar. Hoje o pacote só é cifrado (~7,6 MB). Compactar exige mais uma biblioteca e fica para quando o tamanho pesar.
- **`.deb` e `.msi`:** o atualizador do Tauri cobre `.exe` (NSIS) e `.AppImage`. Quem instalou por `.deb`/`.msi` vê o erro no painel e precisa baixar manualmente da página de releases.

## Onde está no código

| Parte | Arquivo |
|---|---|
| Trancar, abrir, conferir e trocar os dados | `Adito/app/src-tauri/src/dados.rs` |
| Comandos `dados_status`, `dados_verificar` e `dados_instalar` | `Adito/app/src-tauri/src/lib.rs` |
| Gerar a chave e empacotar (CLI) | `Adito/app/src-tauri/examples/empacotar_dados.rs` |
| Atualizador do app | `tauri.conf.json` → `plugins.updater`; `capabilities/default.json` |
| Estado das atualizações no front | `frontend-vue/src/common/composables/useAtualizacoes.ts` |
| Botão do canto e tela do primeiro uso | `AtualizacaoDisponivel.vue`, `PrimeiroUsoDados.vue` |
