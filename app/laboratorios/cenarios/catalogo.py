from __future__ import annotations

from types import ModuleType

from laboratorios.cenarios import (conectando_redes, configure_terminal, desafio_empresa, dividindo_rede, enderecos_nomes,
    investigando_lan, planejando_empresa, primeiro_contato, primeira_lan, saindo_rede_local, suporte_remoto)


LABORATORIO_PADRAO = primeiro_contato.LABORATORIO_ID

_CENARIOS: dict[str, ModuleType] = {
    primeiro_contato.LABORATORIO_ID: primeiro_contato,
    primeira_lan.LABORATORIO_ID: primeira_lan,
    saindo_rede_local.LABORATORIO_ID: saindo_rede_local,
    configure_terminal.LABORATORIO_ID: configure_terminal,
    dividindo_rede.LABORATORIO_ID: dividindo_rede,
    planejando_empresa.LABORATORIO_ID: planejando_empresa,
    conectando_redes.LABORATORIO_ID: conectando_redes,
    investigando_lan.LABORATORIO_ID: investigando_lan,
    enderecos_nomes.LABORATORIO_ID: enderecos_nomes,
    desafio_empresa.LABORATORIO_ID: desafio_empresa,
    suporte_remoto.LABORATORIO_ID: suporte_remoto,
}


def obter_cenario(laboratorio_id: str | None = None) -> ModuleType:
    """Retorna o módulo responsável pelo cenário solicitado."""

    identificador = str(laboratorio_id or LABORATORIO_PADRAO).strip()

    try:
        return _CENARIOS[identificador]
    except KeyError as erro:
        raise ValueError(
            f"Laboratório desconhecido: {identificador}"
        ) from erro


def montar_estado_inicial(
    laboratorio_id: str | None = None,
) -> dict:
    """Monta o estado inicial público de um laboratório."""

    return obter_cenario(laboratorio_id).montar_estado()


def listar_cenarios() -> list[dict]:
    """Lista resumida dos laboratórios registrados."""

    return [
        {
            "id": cenario.LABORATORIO_ID,
            "titulo": cenario.TITULO,
            "descricao": cenario.DESCRICAO,
            "xp": cenario.XP,
            "tempo_limite": cenario.TEMPO_LIMITE,
            "tempo_extensao": cenario.TEMPO_EXTENSAO,
            "max_extensoes": cenario.MAX_EXTENSOES,
        }
        for cenario in _CENARIOS.values()
    ]
