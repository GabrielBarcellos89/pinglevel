# Lab2 — aceite frontend local

Escopo: somente `work/frontend`. Nenhuma publicação ou alteração backend/produção. Dependências reutilizadas por symlink `node_modules` para `/workspace/pinglevel-lab2/frontend/node_modules` (sem instalar/modificar dependências compartilhadas).

## Resultado

- IPv4 livres em sub-redes inteiramente RFC1918, prefixos /8–/30; rejeição de rede/broadcast e sobreposição com 172.30.0.0/16. Mesma rede, mesmo prefixo e hosts diferentes para concluir. Contrato HTTP preservado, sem comandos/interface/usuário enviados pelo cliente.
- IPv4 e máscara inicialmente vazios. Exemplos opcionais, nenhuma resposta /24 obrigatória. Rede da missão exibida somente quando fornecida pelo servidor.
- Conferência compacta por PC com endereço observado, máscara decimal/prefixo, rede e estados em português. Saída técnica preservada em details fechado; ping bruto e fluxo mantidos.
- Conclusão é derivada exclusivamente de `conclusao.registrada` recebido do servidor, nunca de `missao.concluido` sozinho ou de localStorage. Após conclusão, timer/polling da LAN são removidos, campos e operações bloqueados. Encerramento só afirmado se `ativo:false` e `encerramento_pendente:false`.
- Limpeza pendente mantém conclusão, sem contador/edição; botão Encerrar permite nova tentativa. Reload só consulta GET, não repete POST ou nova concessão de XP. Treino novo volta a campos vazios; 409 preserva rascunhos.

## Evidências executadas

- `node --test tests/*.test.js`: **33/33**, incluindo paridade com **630 casos** de limites do backend (`tests/fixtures/lanEnderecos.json`). Saída: `refino-all-unit.log`.
- RED/GREEN real: `refino-unit-red*.log` / `refino-unit-green*.log`; Playwright `refino-blank-red.log`, `refino-cards-red.log`, `refino-completion-red.log`, `refino-pending-red.log`, `refino-livre-red.log` e respectivos GREEN/QA final.
- `npm run lint`: exit 0; sete warnings em arquivos preexistentes não modificados (Inicio, Laboratorio, PainelAdministrador, PainelProfessor, AuthContext). `refino-lint.log`.
- Lint direcionado aos arquivos JS/JSX alterados: exit 0, sem warnings. `refino-lint-escopo.log`.
- `npm run build`: exit 0, build Vite concluído. `refino-build.log`.
- Playwright principal e cleanup pendente: **PASS**, sem `pageerror`; APIs inteiramente interceptadas, AppLayout real. `refino-qa.json`, `refino-pending.json` e logs/capturas `refino*`.
- Mobile 390/320: laboratório sem overflow interno/fora do viewport, máscara/rede legíveis e vermelho computado exato #f02035. Existe overflow global preexistente fora do laboratório (`topbar-acoes`/`usuario-menu`), registrado nos relatórios; nenhum overflow global escondido por CSS.
- Inspeção visual das capturas desktop e card de 320px realizada.
- Vite local usado em loopback 4174; processo criado encerrado após QA e porta verificada fechada (`connect_ex=111`).

## Reprodução

```sh
node node_modules/vite/bin/vite.js . --host 127.0.0.1 --port 4174 --strictPort
# Em outro terminal, no diretório frontend:
PYTHONPATH=/workspace/pinglevel-qa-libs python tests/primeiraLAN.playwright.py
PYTHONPATH=/workspace/pinglevel-qa-libs python tests/primeiraLAN.playwright.py --case pending --report tests/refino-pending.json
node --test tests/*.test.js
npm run lint
npm run build
```

A instrumentação de intervalos filtra stack de `LaboratorioPrimeiraLAN`: o intervalo de 30 segundos do cliente HMR do Vite não é contador/polling da missão. Ao encerrar QA, finalize somente o PID Vite criado; o gerenciador pode finalizar o wrapper sem encerrar o filho Node, portanto confira a porta.

Limite do aceite: fixture de autenticação e APIs locais não valida login real, CORE real, persistência real em banco ou concessão real de XP. Esses aceites pertencem ao backend/integração real.
