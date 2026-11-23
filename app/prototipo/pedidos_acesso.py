"""Pedidos de acesso (23/11/2026). Ainda não há cadastro aberto: quem quer acesso preenche um formulário na tela de
login. O pedido fica salvo para o administrador (painel) e, se o envio estiver configurado no ambiente, também chega
por e-mail em acesso@pinglevel.com.br. A conta continua sendo criada pelo administrador.

Envio por e-mail (opcional; sem ele o pedido só fica no painel), variáveis de ambiente:
PINGLEVEL_SMTP_HOST, PINGLEVEL_SMTP_PORTA (587), PINGLEVEL_SMTP_USUARIO, PINGLEVEL_SMTP_SENHA,
PINGLEVEL_SMTP_REMETENTE (padrão: o usuário) e PINGLEVEL_EMAIL_ACESSO (padrão: acesso@pinglevel.com.br).
"""
from __future__ import annotations

import os
import re
import smtplib
import sqlite3
import ssl
import time
from email.message import EmailMessage

from autenticacao import BANCO

LIMITES = {'nome': (3, 80), 'email': (6, 120), 'instituicao': (2, 120), 'mensagem': (0, 1000)}
EMAIL = re.compile(r'[^@\s]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
CONTROLE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
MAXIMO_PENDENTES = 300  # contra enchente: acima disso, novos pedidos esperam o administrador atender os antigos


def _conectar():
    conexao = sqlite3.connect(BANCO, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute('PRAGMA foreign_keys = ON')
    return conexao


def inicializar_banco():
    with _conectar() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS pedidos_acesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL,
                instituicao TEXT NOT NULL,
                mensagem TEXT NOT NULL DEFAULT '',
                origem TEXT NOT NULL DEFAULT '',
                criado_em INTEGER NOT NULL,
                atendido_em INTEGER,
                atendido_por INTEGER,
                FOREIGN KEY (atendido_por) REFERENCES usuarios(id)
            );

            CREATE INDEX IF NOT EXISTS idx_pedidos_acesso_criado ON pedidos_acesso(criado_em DESC);
            """
        )


def validar(dados) -> dict:
    """Campos limpos do formulário; ValueError com a mensagem para quem preencheu."""
    if not isinstance(dados, dict):
        raise ValueError('Envie o formulário completo.')
    limpos = {}
    for campo, (minimo, maximo) in LIMITES.items():
        valor = dados.get(campo, '')
        if not isinstance(valor, str):
            raise ValueError('Preencha os campos com texto.')
        valor = valor.strip()
        if CONTROLE.search(valor) or (campo != 'mensagem' and ('\n' in valor or '\r' in valor)):
            raise ValueError('Há caracteres não permitidos no formulário.')
        if campo != 'mensagem':
            valor = ' '.join(valor.split())
        if not minimo <= len(valor) <= maximo:
            nomes = {'nome': 'o nome', 'email': 'o e-mail', 'instituicao': 'a instituição ou o curso', 'mensagem': 'a mensagem'}
            raise ValueError(f'Confira {nomes[campo]}: entre {minimo} e {maximo} caracteres.' if minimo
                             else f'A mensagem pode ter até {maximo} caracteres.')
        limpos[campo] = valor
    if not EMAIL.fullmatch(limpos['email']):
        raise ValueError('Confira o e-mail: ele é usado para responder o seu pedido.')
    limpos['email'] = limpos['email'].lower()
    return limpos


def registrar(dados, origem='') -> dict:
    pedido = validar(dados)
    with _conectar() as conexao:
        pendentes = conexao.execute('SELECT COUNT(*) FROM pedidos_acesso WHERE atendido_em IS NULL').fetchone()[0]
        if pendentes >= MAXIMO_PENDENTES:
            raise OverflowError('Recebemos muitos pedidos agora. Tente de novo mais tarde.')
        agora = int(time.time())
        cursor = conexao.execute(
            'INSERT INTO pedidos_acesso (nome, email, instituicao, mensagem, origem, criado_em) VALUES (?, ?, ?, ?, ?, ?)',
            (pedido['nome'], pedido['email'], pedido['instituicao'], pedido['mensagem'], str(origem)[:80], agora))
    return {**pedido, 'id': cursor.lastrowid, 'criado_em': agora}


def listar(limite=100) -> list[dict]:
    with _conectar() as conexao:
        return [dict(linha) for linha in conexao.execute(
            """SELECT p.id, p.nome, p.email, p.instituicao, p.mensagem, p.criado_em, p.atendido_em, u.nome AS atendido_por_nome
               FROM pedidos_acesso p LEFT JOIN usuarios u ON u.id = p.atendido_por
               ORDER BY p.atendido_em IS NOT NULL, p.id DESC LIMIT ?""", (int(limite),))]


def marcar_atendido(administrador_id, pedido_id, atendido=True):
    if not isinstance(pedido_id, int) or isinstance(pedido_id, bool):
        raise ValueError('Pedido inválido.')
    with _conectar() as conexao:
        cursor = conexao.execute(
            'UPDATE pedidos_acesso SET atendido_em = ?, atendido_por = ? WHERE id = ?',
            (int(time.time()) if atendido else None, administrador_id if atendido else None, pedido_id))
        if cursor.rowcount != 1:
            raise ValueError('Pedido não encontrado.')


def configuracao_email():
    """Configuração do envio, ou None quando o ambiente não tem as credenciais (o pedido fica só no painel)."""
    host, usuario, senha = (os.environ.get(f'PINGLEVEL_SMTP_{n}', '').strip() for n in ('HOST', 'USUARIO', 'SENHA'))
    if not (host and usuario and senha):
        return None
    return {'host': host, 'porta': int(os.environ.get('PINGLEVEL_SMTP_PORTA', '587') or 587), 'usuario': usuario,
            'senha': senha, 'remetente': os.environ.get('PINGLEVEL_SMTP_REMETENTE', '').strip() or usuario,
            'destino': os.environ.get('PINGLEVEL_EMAIL_ACESSO', '').strip() or 'acesso@pinglevel.com.br'}


def montar_email(pedido, remetente, destino) -> EmailMessage:
    mensagem = EmailMessage()
    mensagem['Subject'] = f"Pedido de acesso ao PingLevel: {pedido['nome']}"
    mensagem['From'] = f'PingLevel <{remetente}>'
    mensagem['To'] = destino
    mensagem['Reply-To'] = pedido['email']
    mensagem.set_content(
        'Novo pedido de acesso pelo formulário do login.\n\n'
        f"Nome: {pedido['nome']}\nE-mail: {pedido['email']}\nInstituição ou curso: {pedido['instituicao']}\n\n"
        f"Mensagem:\n{pedido['mensagem'] or '(sem mensagem)'}\n\n"
        'Responder este e-mail responde direto a quem pediu. O pedido também está no painel do administrador.\n')
    return mensagem


def avisar_por_email(pedido, smtp=smtplib.SMTP) -> bool:
    """Envia o aviso; devolve False sem configuração ou em falha (o pedido já está salvo e aparece no painel)."""
    config = configuracao_email()
    if config is None:
        return False
    try:
        with smtp(config['host'], config['porta'], timeout=15) as cliente:
            cliente.starttls(context=ssl.create_default_context())
            cliente.login(config['usuario'], config['senha'])
            cliente.send_message(montar_email(pedido, config['remetente'], config['destino']))
        return True
    except (OSError, smtplib.SMTPException) as erro:
        print(f"Aviso por e-mail do pedido de acesso {pedido.get('id')} falhou: {type(erro).__name__}", flush=True)
        return False


inicializar_banco()
