"""Filtros e indicadores para eventos de gols e cartões."""

import pandas as pd


def filtrar_eventos(
    eventos: pd.DataFrame,
    temporada="Todas",
    local="Todos",
    adversario="Todos",
) -> pd.DataFrame:
    """Aplica aos eventos os mesmos filtros usados na visão geral."""
    filtrados = eventos.copy()
    if temporada != "Todas":
        filtrados = filtrados[filtrados["temporada"].eq(temporada)]
    if local != "Todos":
        filtrados = filtrados[filtrados["local"].eq(local)]
    if adversario != "Todos":
        filtrados = filtrados[filtrados["adversario"].eq(adversario)]
    return filtrados


def indicadores_gols(gols: pd.DataFrame) -> dict:
    """Resume os gols do recorte sem inferir informações ausentes."""
    total = len(gols)
    artilheiros = int(gols["atleta"].nunique()) if total else 0
    penaltis = int(gols["tipo_de_gol"].eq("Pênalti").sum()) if total else 0
    gols_finais = int(gols["intervalo_gol"].isin(["76-90", "90+"]).sum()) if total else 0
    return {
        "total": total,
        "artilheiros": artilheiros,
        "penaltis": penaltis,
        "gols_finais": gols_finais,
    }


def indicadores_cartoes(cartoes: pd.DataFrame) -> dict:
    """Resume amarelos, vermelhos e atletas advertidos no recorte."""
    total = len(cartoes)
    amarelos = int(cartoes["tipo_cartao"].eq("Amarelo").sum()) if total else 0
    vermelhos = int(cartoes["tipo_cartao"].eq("Vermelho").sum()) if total else 0
    atletas = int(cartoes["atleta"].nunique()) if total else 0
    return {
        "total": total,
        "amarelos": amarelos,
        "vermelhos": vermelhos,
        "atletas": atletas,
    }
