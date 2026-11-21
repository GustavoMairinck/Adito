# ADR 0006: Empacotamento Desktop sem Privilégio de Admin e Auto-Update Assistido

**Status:** Aceito  
**Data:** 20/11/2026

## Contexto/Problema
O Muninn é distribuído como aplicativo desktop local (Tauri v2 + Vue 3 + sidecar Python via `stdin/stdout`) para o público interno do IFES Campus Serra. A maioria dos usuários utiliza máquinas institucionais **sem privilégio de administrador** (sem UAC no Windows e sem `sudo` no Linux), embora alguns também utilizem notebooks pessoais ou máquinas gerenciadas pela TI. Além disso, o projeto opera com **zero servidor próprio** e precisa garantir que novas versões do executável cheguem aos usuários sem exigir contas no GitHub nem causar acúmulo de múltiplos instaladores na pasta Downloads.

## Decisão Tomada
Adotar uma estratégia de distribuição baseada em **GitHub Releases público** (com o executável 100% livre de dados pessoais, conforme [ADR 0007](./ADR-0007-distribuicao-criptografada-dados-db.md)) combinando:

1. **Formatos de executáveis (mantendo os 4 targets do `tauri.conf.json`):**
   - **Windows — padrão recomendado:** instalador `.exe` (NSIS) configurado explicitamente em modo `installMode: "currentUser"`, instalando em `%LOCALAPPDATA%` **sem exigir privilégio de administrador**, criando atalho no Menu Iniciar e suportando *auto-update*.
   - **Windows — secundário (TI):** pacote `.msi` (WiX) mantido como alternativa para eventual deploy corporativo em lote pela TI do IFES (GPO/Intune).
   - **Linux — padrão recomendado:** `.AppImage` portátil, executável **sem `sudo`**, compatível com múltiplas distros e com *auto-update* nativo (documentando o fallback `--appimage-extract-and-run` para distros como Ubuntu 22.04+ sem `libfuse2`).
   - **Linux — secundário (máquinas pessoais):** pacote `.deb` mantido para usuários Debian/Ubuntu com permissão de administrador.
2. **Política de atualizações:**
   - **Auto-update assistido** via `tauri-plugin-updater` apontando para o arquivo `latest.json` publicado no GitHub Releases.
   - Assinatura criptográfica gratuita **Ed25519** (`tauri signer generate`), com chave privada armazenada nos Secrets do GitHub Actions e chave pública embutida no `tauri.conf.json`.
   - Ao abrir o app, a checagem ocorre em segundo plano e exibe um banner discreto (*"Nova versão disponível — Atualizar agora / Depois"*). Ao confirmar, o app baixa, valida a assinatura Ed25519, substitui a instalação no lugar certo e reinicia.
   - Para instalações `.deb` e `.msi`, oferecer link de fallback para download manual.

## Justificativa
1. **Compatibilidade com o ambiente real do IFES:** `.exe` (NSIS `currentUser`) e `.AppImage` eliminam o bloqueio de privilégio de administrador sem depender de chamados à TI, enquanto `.msi` e `.deb` já fazem parte da matriz do Tauri e cobrem deploy corporativo e máquinas pessoais sem custo extra relevante no CI.
2. **Experiência limpa e previsível:** o *auto-update* assistido substitui o aplicativo no local original (evitando múltiplos `Muninn_v0.1`, `v0.2`, `v0.3` em Downloads), ao mesmo tempo em que respeita o momento do usuário — não reinicia o app no meio de uma consulta ou reunião nem consome ~80–150 MB de banda sem aviso.
3. **Zero infraestrutura própria:** GitHub Releases público + assinatura Ed25519 gratuita eliminam a necessidade de manter servidor de updates.

## Alternativas Consideradas
* **Windows somente `.exe` | Linux `.AppImage` + `.deb`:** descartada porque, caso a TI do IFES opte por instalar o Muninn em laboratórios via GPO/Intune, exigiria reintroduzir o target `.msi` posteriormente.
* **Mínimo absoluto (somente `.exe` e `.AppImage`):** descartada porque usuários Linux pessoais em Ubuntu 22.04+ sem `libfuse2` ficariam sem a alternativa nativa do `.deb`, e a TI sem o `.msi`.
* **Windows `.zip` portátil + Linux `.AppImage`:** descartada por oferecer UX inferior (extração manual, sem atalho no Menu Iniciar nem desinstalador) e não integrar nativamente com o `tauri-plugin-updater`.
* **Auto-update silencioso em segundo plano:** descartada pelo risco de interromper/reiniciar o app durante apresentações ou reuniões e baixar ~80–150 MB (com sidecar Python) sem ciência do usuário em redes lentas.
* **Somente aviso na UI + download manual:** descartada por gerar acúmulo de múltiplos executáveis/instaladores na pasta Downloads e aumentar a fragmentação de versões.
* **Atualização 100% manual (sem verificação no app):** descartada pelo alto esforço de comunicação da equipe e dificuldade para propagar correções.

## Consequências
* **Positivas:** instalação self-service sem admin no Windows e Linux; atualizações em 1 clique com verificação criptográfica Ed25519; cobertura completa para usuários comuns, máquinas pessoais e TI; zero custo de servidor.
* **Negativas:** exige configuração inicial única no CI (par de chaves Ed25519, Secrets do GitHub Actions e geração de `.sig` + `latest.json`); mais artefatos listados no Release (exige rotulagem clara do download recomendado para o usuário comum).
* **Riscos:**
  - *Alerta do Windows SmartScreen:* sem certificado pago Windows EV Authenticode, a primeira instalação do `.exe`/`.msi` pode exibir aviso do SmartScreen (mitigado com instruções curtas no guia de instalação; updates subsequentes são autenticados via Ed25519).
  - *Ausência de `libfuse2` no Ubuntu 22.04+:* `.AppImage` pode falhar ao abrir sem FUSE2 (mitigado documentando o uso de `--appimage-extract-and-run` e oferecendo `.deb` para quem tem `sudo`).
  - *Limitação de auto-update em `.deb`/`.msi`:* mitigado exibindo link direto de download manual quando o formato instalado não suporta substituição sem privilégio elevado.

## Referências
* [ADR 0005: Nome do produto passa a ser Muninn](./ADR-0005-nome-muninn.md)
* [ADR 0007: Distribuição e Atualização Criptografada do Banco `dados.db`](./ADR-0007-distribuicao-criptografada-dados-db.md)
* Configuração atual do bundle: [`Muninn/app/src-tauri/tauri.conf.json`](../../Muninn/app/src-tauri/tauri.conf.json)
* Estudo comparativo completo: [`Muninn/docs/resultados/estrategia-distribuicao-muninn.pdf`](../../Muninn/docs/resultados/estrategia-distribuicao-muninn.pdf)
