# Atualização semanal da base

`../atualizar_base_semanal.sh` roda o ETL inteiro e monta o `dados.db`. Depois publica
`manifest.json` + `dados-<versão>.db.gz` numa pasta privada. O botão **Atualizar base** do app lê
essa pasta. Etapas: SRC → SigPesq → CNPq → Lattes → cruzar → verificar-pii → popular-banco → publicar.

- Uma etapa com falha parcial (código 1) gera aviso, e a carga usa o que veio.
- Um erro (código 2: credencial, dado pessoal encontrado...) para tudo e não publica nada.
- Se os dados forem iguais aos da semana anterior, nada é publicado (`publicar_base.py --se-mudou`),
  e o app não oferece uma "atualização" igual à base que o usuário já tem.

## Instalar (timer de usuário do systemd)

Pré-requisito: o ETL já roda à mão nessa máquina (`Muninn/etl/.venv` e `Muninn/etl/.env` configurados).

```bash
MUNINN="$HOME/caminho/para/Muninn"          # ajuste
mkdir -p ~/.config/systemd/user ~/.config/muninn
sed "s#@MUNINN@#$MUNINN#" "$MUNINN/scripts/systemd/muninn-base-semanal.service" > ~/.config/systemd/user/muninn-base-semanal.service
cp "$MUNINN/scripts/systemd/muninn-base-semanal.timer" ~/.config/systemd/user/
cp "$MUNINN/scripts/systemd/semanal.env.exemplo" ~/.config/muninn/semanal.env && chmod 600 ~/.config/muninn/semanal.env
# edite ~/.config/muninn/semanal.env
systemctl --user daemon-reload
systemctl --user enable --now muninn-base-semanal.timer
sudo loginctl enable-linger "$USER"          # roda mesmo sem ninguém logado
```

## Operar

```bash
systemctl --user list-timers muninn-base-semanal.timer   # próxima execução
systemctl --user start muninn-base-semanal.service       # rodar agora
journalctl --user -u muninn-base-semanal -f              # log
```

Sem systemd, um cron faz o mesmo:
`0 3 * * 1 set -a; . ~/.config/muninn/semanal.env; /caminho/Muninn/scripts/atualizar_base_semanal.sh >> ~/.cache/muninn-semanal/log 2>&1`

## Apontar o app para a pasta privada

Sirva a pasta por HTTPS (servidor do campus ou VPN) e defina no computador do usuário
`MUNINN_DADOS_MANIFEST_URL=https://<servidor>/dados/manifest.json`. Por enquanto o padrão do
app é a base fictícia do Pages.
