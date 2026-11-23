"""Teste de carga pela plataforma em produção, como alunos de verdade: login pelo site público, ambiente criado pelo
backend em execução (aparece no Painel de carga), roteiro do "Suporte remoto" pelo terminal e o ambiente mantido vivo
até o fim do teste. Não valida a missão (validar encerra o ambiente); no fim, encerra cada ambiente pela própria API.

Fases (uma por processo, todas param quando o arquivo --parar existir ou o tempo acabar):
  extras  --de 21 --ate 25   um laboratório diferente por aluno (Labs 2, 5, 6, 7 e 9), ativos em paralelo
  carga   --de 1 --ate 10    Teste de carga: todos iniciam juntos (ou a cada --intervalo s) e fazem SSH, gateway e impressão
A senha das contas vem de PINGLEVEL_SENHA_APRESENTACAO. Uso:
  PINGLEVEL_SENHA_APRESENTACAO=... python tools/qa/carga_real.py carga --de 1 --ate 10 --parar /caminho/parar
"""
import argparse
import json
import os
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# Pelo Nginx na rede local (o mesmo que serve o site): evita o Cloudflare e mede só o servidor. O Origin é o do site
# público, como num navegador; o cookie de sessão é guardado à mão porque ele pode vir marcado como Secure.
SITE = 'http://10.20.0.4:5173'
ORIGEM = 'https://teste.pinglevel.com.br'
EXTRAS = [('/api/lab2/', 'Lab 2'), ('/api/lab5/', 'Lab 5'), ('/api/lab6/', 'Lab 6'), ('/api/lab7/', 'Lab 7'), ('/api/lab9/', 'Lab 9')]
ROTEIRO = ['ping 192.168.20.21', 'ssh suporte@192.168.20.21', None, 'ip route', 'curl http://192.168.10.50',
           'ip route del default', 'ip route add default via 192.168.20.1', 'curl http://192.168.10.50', 'FOLHA']
saida_lock = threading.Lock()


def log(login, texto):
    with saida_lock:
        print(f'{time.strftime("%H:%M:%S")} {login:8} {texto}', flush=True)


class Aluno:
    def __init__(self, login, senha):
        self.login, self.senha = login, senha
        self.cookie = ''

    def pedir(self, metodo, rota, dados=None, timeout=120):
        corpo = None if dados is None else json.dumps(dados).encode()
        cabecalhos = {'Content-Type': 'application/json', 'Origin': ORIGEM}
        if self.cookie:
            cabecalhos['Cookie'] = self.cookie
        pedido = urllib.request.Request(SITE + rota, data=corpo, method=metodo, headers=cabecalhos)
        try:
            with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
                for valor in resposta.headers.get_all('Set-Cookie') or []:
                    self.cookie = valor.split(';', 1)[0]
                return resposta.status, json.loads(resposta.read() or b'{}')
        except urllib.error.HTTPError as erro:
            return erro.code, json.loads(erro.read() or b'{}')

    def entrar(self):
        codigo, corpo = self.pedir('POST', '/api/auth/login', {'login': self.login, 'senha': self.senha})
        if codigo != 200:
            raise RuntimeError(f'login {codigo}: {corpo.get("mensagem")}')

    def status(self, base):
        return self.pedir('GET', base + 'status')[1]

    def acao(self, base, acao, **extra):
        estado = self.status(base)
        dados = {'session_id': estado['laboratorio']['session_id'], 'revisao': estado['missao']['revisao'], **extra}
        return self.pedir('POST', base + acao, dados)


def rodar(aluno, base, nome, roteiro, parar, limite, resultados):
    inicio = time.time()
    try:
        aluno.entrar()
        codigo, corpo = aluno.pedir('POST', base + 'iniciar', {}, timeout=300)
        if codigo != 200 or not corpo.get('ativo'):
            raise RuntimeError(f'iniciar {codigo}: {corpo.get("mensagem") or corpo.get("erro")}')
        criado = time.time() - inicio
        resultados[aluno.login] = {'criacao': criado}
        log(aluno.login, f'{nome}: ambiente pronto em {criado:.1f} s')
        if roteiro:
            for comando in ROTEIRO:
                time.sleep(random.uniform(3, 8))  # um aluno de verdade lê e digita
                texto = os.environ['PINGLEVEL_SENHA_SSH'] if comando is None else \
                    f'curl -d "texto=Folha do {aluno.login}" http://192.168.10.50/imprimir' if comando == 'FOLHA' else comando
                codigo, corpo = aluno.acao(base, 'terminal', comando=texto, pc='ti')
                ultimo = (corpo.get('missao') or {}).get('terminal', [{}])[-1]
                if codigo != 200:
                    raise RuntimeError(f'{comando or "senha"} → {codigo}: {corpo.get("mensagem")}')
                log(aluno.login, f'$ {comando or "(senha)"} → código {ultimo.get("codigo")}')
            resultados[aluno.login]['etapa'] = corpo['missao'].get('proxima_etapa')
            log(aluno.login, f'roteiro feito; folha impressa; etapa {resultados[aluno.login]["etapa"]}')
        while not parar.exists() and time.time() - inicio < limite:
            time.sleep(20)
            aluno.status(base)  # mantém o ambiente vivo (heartbeat)
    except Exception as erro:  # noqa: BLE001
        resultados.setdefault(aluno.login, {})['erro'] = str(erro)
        log(aluno.login, f'FALHOU: {erro}')
    finally:
        try:
            codigo, corpo = aluno.acao(base, 'encerrar')
            log(aluno.login, f'encerrado ({codigo})')
        except Exception as erro:  # noqa: BLE001
            log(aluno.login, f'encerrar falhou: {erro}')


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('fase', choices=('extras', 'carga'))
    p.add_argument('--de', type=int, required=True)
    p.add_argument('--ate', type=int, required=True)
    p.add_argument('--parar', type=Path, required=True, help='o teste termina quando este arquivo existir')
    p.add_argument('--limite', type=int, default=1500, help='segundos até encerrar sozinho (padrão 25 min)')
    p.add_argument('--intervalo', type=float, default=0, help='segundos entre um aluno e o próximo no Teste de carga (0 = juntos)')
    args = p.parse_args()
    senha = os.environ.get('PINGLEVEL_SENHA_APRESENTACAO')
    if not senha or not os.environ.get('PINGLEVEL_SENHA_SSH'):
        sys.exit('Defina PINGLEVEL_SENHA_APRESENTACAO e PINGLEVEL_SENHA_SSH.')
    resultados, threads = {}, []
    for i, numero in enumerate(range(args.de, args.ate + 1)):
        aluno = Aluno(f'aluno{numero:02d}', senha)
        base, nome, roteiro = (*EXTRAS[i % len(EXTRAS)], False) if args.fase == 'extras' else ('/api/carga/', 'Teste de carga', True)
        t = threading.Thread(target=rodar, args=(aluno, base, nome, roteiro, args.parar, args.limite, resultados))
        threads.append(t)
        t.start()
        if args.fase == 'extras':
            time.sleep(random.uniform(20, 40))  # chegam em momentos diferentes
        elif args.intervalo:
            time.sleep(args.intervalo)
    for t in threads:
        t.join()
    tempos = sorted(r['criacao'] for r in resultados.values() if 'criacao' in r)
    falhas = {k: r['erro'] for k, r in resultados.items() if 'erro' in r}
    print(f'\nRESUMO {args.fase} aluno{args.de:02d}–aluno{args.ate:02d}: {len(tempos)} ambientes'
          + (f', criação {tempos[0]:.1f}–{tempos[-1]:.1f} s' if tempos else '') + f', falhas: {falhas or "nenhuma"}', flush=True)


if __name__ == '__main__':
    main()
