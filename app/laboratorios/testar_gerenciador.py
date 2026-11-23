from laboratorios.gerenciador import GerenciadorLaboratorios


gerenciador = GerenciadorLaboratorios()
gerenciador.reconciliar_sessoes_anteriores()

try:
    aluno1 = gerenciador.criar(1, "user1")
    aluno2 = gerenciador.criar(2, "user2")

    print(f"user1: sessão {aluno1.session_id}, rede {aluno1.controlnet}")
    print(f"user2: sessão {aluno2.session_id}, rede {aluno2.controlnet}")

    for usuario_id in (1, 2):
        codigo, saida = gerenciador.executar(
            usuario_id, 1, "ping -c 2 10.0.0.21"
        )
        print(f"Usuário {usuario_id}: ping código {codigo}")
        if codigo != 0:
            raise RuntimeError(saida)

    gerenciador.encerrar(1, "teste de isolamento")
    codigo, saida = gerenciador.executar(2, 1, "hostname")
    if codigo != 0:
        raise RuntimeError(saida)

    print("TESTE APROVADO: user2 continuou após remover user1.")
finally:
    gerenciador.encerrar_todos("fim do teste isolado")
