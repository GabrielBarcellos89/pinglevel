# Ambiente de testes

Tudo roda localmente em `/opt/packetlab/.qa/` (fora do Git). Nenhum script deste diretório
usa o CORE, o banco real ou os serviços; só `publicar_frontend.sh` altera `frontend/dist`.

| Script | O que faz |
|---|---|
| `preparar.sh` | Cria `.qa/`: venv de testes (pytest + Playwright, lendo os pacotes do venv de produção sem alterá-lo), Chromium e jsdom. Idempotente. |
| `rodar.sh` | Backend (pytest e HTTP), frontend (unidade, aula IPv4 com jsdom), lint, build candidato em `.qa/dist`, navegador do Lab 3 e capturas. `--rapido` pula navegador e capturas. |
| `capturar_lab3.py` | Capturas da topologia do Lab 3 em 1600, 1280, 1024 e 390 px, antes e depois de consultar o roteador, com `geometria.json`. |
| `publicar_frontend.sh` | Publica `.qa/dist` no `frontend/dist` servido pelo Nginx: recusa build mais antigo que as fontes, faz backup em `~/backups-pinglevel`, troca `index.html` por último e confere tudo. |

Fluxo de uma mudança de interface:

```bash
tools/qa/rodar.sh                 # testes + build candidato + capturas em .qa/capturas
tools/qa/publicar_frontend.sh     # depois de revisar as capturas
```

Mudanças de backend exigem parar e iniciar `pinglevel-web.service` (sudo, feito pelo Gabriel).
