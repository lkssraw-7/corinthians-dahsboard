"""Testes dos filtros e indicadores das abas de eventos."""

import pandas as pd

from src.charts import (
    grafico_artilheiros,
    grafico_cartoes_por_atleta,
    grafico_cartoes_por_temporada,
    grafico_gols_por_intervalo,
)
from src.events import filtrar_eventos, indicadores_cartoes, indicadores_gols


def bases_eventos():
    gols = pd.DataFrame([
        dict(temporada=2023, local='Mandante', adversario='Santos', atleta='A', tipo_de_gol='Gol normal', intervalo_gol='0-15'),
        dict(temporada=2023, local='Mandante', adversario='Santos', atleta='A', tipo_de_gol='Pênalti', intervalo_gol='76-90'),
        dict(temporada=2024, local='Visitante', adversario='Palmeiras', atleta='B', tipo_de_gol='Gol normal', intervalo_gol='90+'),
    ])
    cartoes = pd.DataFrame([
        dict(temporada=2023, local='Mandante', adversario='Santos', atleta='A', tipo_cartao='Amarelo'),
        dict(temporada=2023, local='Mandante', adversario='Santos', atleta='A', tipo_cartao='Vermelho'),
        dict(temporada=2024, local='Visitante', adversario='Palmeiras', atleta='B', tipo_cartao='Amarelo'),
    ])
    return gols, cartoes


def test_filtros_podem_ser_combinados():
    gols, _ = bases_eventos()
    resultado = filtrar_eventos(gols, 2023, 'Mandante', 'Santos')
    assert len(resultado) == 2
    assert set(resultado['atleta']) == {'A'}


def test_todas_nao_remove_eventos():
    gols, _ = bases_eventos()
    pd.testing.assert_frame_equal(filtrar_eventos(gols), gols)


def test_indicadores_de_gols():
    gols, _ = bases_eventos()
    assert indicadores_gols(gols) == {
        'total': 3, 'artilheiros': 2, 'penaltis': 1, 'gols_finais': 2,
    }


def test_indicadores_de_cartoes():
    _, cartoes = bases_eventos()
    assert indicadores_cartoes(cartoes) == {
        'total': 3, 'amarelos': 2, 'vermelhos': 1, 'atletas': 2,
    }


def test_indicadores_vazios_retornam_zero():
    gols, cartoes = bases_eventos()
    assert indicadores_gols(gols.iloc[0:0])['total'] == 0
    assert indicadores_cartoes(cartoes.iloc[0:0])['total'] == 0


def test_graficos_sao_gerados_com_o_recorte():
    gols, cartoes = bases_eventos()
    assert len(grafico_artilheiros(gols).data) == 1
    assert len(grafico_gols_por_intervalo(gols).data[0].x) == 7
    assert len(grafico_cartoes_por_atleta(cartoes).data) == 2
    assert len(grafico_cartoes_por_temporada(cartoes).data) == 2
