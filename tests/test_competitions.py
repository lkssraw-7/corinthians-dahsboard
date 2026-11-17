"""Verificações da integração de múltiplas competições."""

import pandas as pd

from scripts.preparar_copa_brasil import (
    auditar_fonte,
    fase_da_partida,
    preparar_partidas_copa_brasil,
)
from src.competition_views import (
    dados_linha_do_tempo,
    etapas_para_exibicao,
    resumo_campanhas,
)
from src.data import carregar_dados


COMPETICOES, _, _ = carregar_dados()
LIBERTADORES = COMPETICOES['Copa Libertadores']
COPA_BRASIL = COMPETICOES['Copa do Brasil']
BRUTA_COPA_BRASIL = pd.read_csv('dados/brutos/copa_brasil_partidas.csv')


def test_competicoes_sao_carregadas_no_mesmo_formato():
    assert 'Brasileirão — Série A' in COMPETICOES
    assert len(LIBERTADORES) == 112
    for coluna in [
        'ID', 'temporada', 'data', 'adversario', 'local',
        'gols_marcados', 'gols_sofridos', 'resultado', 'pontos',
    ]:
        assert coluna in LIBERTADORES.columns


def test_totais_da_libertadores():
    assert int(LIBERTADORES['gols_marcados'].sum()) == 180
    assert int(LIBERTADORES['gols_sofridos'].sum()) == 107
    assert LIBERTADORES['resultado'].value_counts().to_dict() == {
        'Vitoria': 57, 'Derrota': 30, 'Empate': 25,
    }
    assert int(LIBERTADORES['penales'].notna().sum()) == 4


def test_campanha_de_2012_chegou_a_final_sem_derrotas():
    campanhas = resumo_campanhas(LIBERTADORES).set_index('temporada')
    assert campanhas.loc[2012, 'fase_maxima'] == 'Final'
    assert campanhas.loc[2012, 'jogos'] == 14
    assert campanhas.loc[2012, 'derrotas'] == 0


def test_etapa_da_fase_de_grupos_nao_exibe_grupo_ou_ausencia():
    grupos = LIBERTADORES[LIBERTADORES['fase'].eq('Fase de grupos')]
    assert set(etapas_para_exibicao(grupos)) == {'—'}


def test_etapas_do_mata_mata_sao_traduzidas():
    etapas = set(etapas_para_exibicao(LIBERTADORES))
    assert 'Volta' in etapas
    assert 'Vuelta' not in etapas


def test_estadio_da_libertadores_desde_2014():
    jogos = LIBERTADORES[
        LIBERTADORES['temporada'].ge(2014)
        & LIBERTADORES['local'].eq('Mandante')
    ]
    assert not jogos.empty
    assert set(jogos['arena']) == {'Neo Química Arena'}


def test_qualidade_da_fonte_da_copa_do_brasil():
    auditoria = auditar_fonte(BRUTA_COPA_BRASIL)
    assert auditoria['linhas'] == 1724
    assert auditoria['temporada_inicial'] == 2013
    assert auditoria['temporada_final'] == 2025
    for problema in [
        'ausentes_nucleo', 'duplicatas_codigo', 'duplicatas_partida',
        'placares_invalidos', 'mesma_equipe',
    ]:
        assert auditoria[problema] == 0
    assert len(COPA_BRASIL) == 84
    assert not COPA_BRASIL[['gols_marcados', 'gols_sofridos']].isna().any().any()
    assert not COPA_BRASIL['ID'].duplicated().any()


def test_totais_da_copa_do_brasil():
    assert int(COPA_BRASIL['gols_marcados'].sum()) == 104
    assert int(COPA_BRASIL['gols_sofridos'].sum()) == 67
    assert COPA_BRASIL['resultado'].value_counts().to_dict() == {
        'Vitoria': 39, 'Derrota': 24, 'Empate': 21,
    }


def test_fases_consideram_o_formato_da_temporada():
    assert fase_da_partida(2013, 143) == 'Oitavas de final'
    assert fase_da_partida(2014, 162) == 'Quartas de final'
    assert fase_da_partida(2016, 146) == 'Oitavas de final'
    assert fase_da_partida(2018, 120) == 'Final'
    assert fase_da_partida(2021, 71) == '3ª fase'
    assert fase_da_partida(2025, 122) == 'Final'


def test_transformacao_e_campanhas_da_copa_do_brasil():
    transformada = preparar_partidas_copa_brasil(BRUTA_COPA_BRASIL)
    pd.testing.assert_frame_equal(
        transformada.astype(object).where(transformada.notna(), '').reset_index(drop=True),
        COPA_BRASIL.astype(object).where(COPA_BRASIL.notna(), '').reset_index(drop=True),
        check_dtype=False,
    )
    campanhas = resumo_campanhas(COPA_BRASIL).set_index('temporada')
    assert campanhas.loc[2018, 'fase_maxima'] == 'Final'
    assert campanhas.loc[2018, 'jogos'] == 8
    assert campanhas.loc[2022, 'fase_maxima'] == 'Final'
    assert campanhas.loc[2025, 'fase_maxima'] == 'Final'
    assert campanhas.loc[2025, 'jogos'] == 10


def test_estadio_da_copa_do_brasil_desde_2014():
    jogos = COPA_BRASIL[
        COPA_BRASIL['temporada'].ge(2014)
        & COPA_BRASIL['local'].eq('Mandante')
    ]
    assert set(jogos['arena']) == {'Neo Química Arena'}


def test_linha_do_tempo_de_2025():
    campanha = dados_linha_do_tempo(COPA_BRASIL, 2025)
    assert len(campanha) == 10
    assert campanha['fase'].drop_duplicates().tolist() == [
        '3ª fase', 'Oitavas de final', 'Quartas de final', 'Semifinal', 'Final',
    ]
    assert campanha.iloc[-1]['adversario'] == 'Vasco da Gama'
    assert campanha.iloc[-1]['placar_exibicao'] == '2 × 1'
