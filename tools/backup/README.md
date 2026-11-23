# Backup do banco

`data/auth/pinglevel_auth.db` guarda usuários (senhas em PBKDF2), turmas, sessões (só o hash do token),
progresso, XP e auditoria. É o único dado do PingLevel que não pode ser recriado.

`backup_banco.py` roda uma vez por dia pelo cron do usuário `gabriel` (instalado manualmente):

```
17 3 * * * /usr/bin/python3 /opt/packetlab/tools/backup/backup_banco.py >> /home/gabriel/backups-pinglevel/banco/backup.log 2>&1
```

- Destino: `/home/gabriel/backups-pinglevel/banco/pinglevel_auth-AAAAMMDD-HHMMSS.db.gz` (pasta 700, arquivos 600).
- Usa a API de backup do SQLite: a cópia é consistente com o site no ar e inclui o que ainda está no WAL.
- Cada arquivo é conferido duas vezes (`integrity_check` e contagem por tabela, antes e depois de compactar).
- Rotação: os 14 mais recentes e o primeiro de cada mês dos últimos 12 meses.
- Cada execução acrescenta uma linha a `backup.log` (`ok` ou `FALHA`).

## Restaurar

Restaurar substitui todo o progresso posterior ao backup. Só com a decisão do Gabriel.

```bash
# 1. Conferir o backup escolhido numa cópia temporária
gunzip -c /home/gabriel/backups-pinglevel/banco/pinglevel_auth-AAAAMMDD-HHMMSS.db.gz > /tmp/restaurar.db
python3 -c "import sqlite3; print(sqlite3.connect('/tmp/restaurar.db').execute('PRAGMA integrity_check').fetchone())"

# 2. Parar o backend (encerra treinos ativos) e guardar o banco atual
sudo -n systemctl stop pinglevel-web.service
cp -p /opt/packetlab/data/auth/pinglevel_auth.db /home/gabriel/backups-pinglevel/banco/antes-restauracao-$(date +%Y%m%d-%H%M%S).db
rm -f /opt/packetlab/data/auth/pinglevel_auth.db-wal /opt/packetlab/data/auth/pinglevel_auth.db-shm

# 3. Colocar o backup no lugar, com as permissões originais, e iniciar
install -m 640 /tmp/restaurar.db /opt/packetlab/data/auth/pinglevel_auth.db && rm /tmp/restaurar.db
sudo -n systemctl start pinglevel-web.service
```
