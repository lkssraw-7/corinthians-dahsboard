"""Verificações de separação temporal e interpretação das probabilidades."""

import numpy as np
import pandas as pd
import pytest

from src.ml import (
    COLUNAS_BASE,
    COLUNAS_PROB,
    FEATURES,
    NUMERICAS,
    avaliar_previsoes,
    preparar_features,
    previsoes_corinthians,
    treinar_experimento,
    validar_partidas,
)


def base_sintetica():
    clubes = ['Corinthians', 'Santos', 'Palmeiras']
    placares = [(2, 0), (1, 1), (0, 1)]
    return pd.DataFrame([
        {
            'ID': indice + 1,
            'data': data.strftime('%d/%m/%Y'),
            'mandante': clubes[indice % 3],
            'visitante': clubes[(indice + 1) % 3],
            'mandante_Placar': placares[indice % 3][0],
            'visitante_Placar': placares[indice % 3][1],
        }
        for indice, data in enumerate(pd.date_range('2022-12-15', periods=36))
    ])


ORIGINAL = base_sintetica()
EXPERIMENTO = treinar_experimento(ORIGINAL)


def test_placar_da_propria_partida_nao_entra_nas_features():
    antes = preparar_features(ORIGINAL)
    alterada = ORIGINAL.copy()
    alterada.loc[20, ['mandante_Placar', 'visitante_Placar']] = [9, 0]
    depois = preparar_features(alterada)
    pd.testing.assert_frame_equal(antes.loc[:20, FEATURES], depois.loc[:20, FEATURES])


def test_acrescentar_o_futuro_nao_altera_o_passado():
    parcial = preparar_features(ORIGINAL.iloc[:20])
    completa = preparar_features(ORIGINAL)
    pd.testing.assert_frame_equal(parcial, completa.iloc[:20])


def test_nenhum_jogo_do_mesmo_dia_entra_no_historico():
    jogos = pd.DataFrame([
        [1, '01/12/2022', 'Corinthians', 'Santos', 2, 0],
        [2, '05/12/2022', 'Palmeiras', 'Corinthians', 1, 1],
        [3, '05/12/2022', 'Corinthians', 'Sao Paulo', 3, 0],
    ], columns=['ID', 'data', 'mandante', 'visitante', 'mandante_Placar', 'visitante_Placar'])
    features = preparar_features(jogos).set_index('ID')
    assert features.loc[2, 'visitante_jogos_10'] == 1
    assert features.loc[3, 'mandante_jogos_10'] == 1
    assert features.loc[3, 'mandante_pontos_5'] == 3
    assert features.loc[3, 'mandante_gols_marcados_10'] == 2


def test_historico_expira_apos_um_ano():
    jogos = ORIGINAL.iloc[:2].copy()
    jogos.loc[1, 'data'] = '01/01/2025'
    features = preparar_features(jogos)
    assert features.loc[1, 'mandante_jogos_10'] == 0
    assert features.loc[1, 'mandante_dias_desde_ultimo'] == 120


def test_recusa_ids_duplicados_e_dados_invalidos():
    with pytest.raises(ValueError):
        validar_partidas(pd.concat([ORIGINAL, ORIGINAL.iloc[:1]]))

    for coluna, valor in [
        ('data', 'invalida'),
        ('mandante_Placar', -1),
        ('visitante_Placar', 1.5),
    ]:
        invalida = ORIGINAL.copy().astype({coluna: object})
        invalida.loc[0, coluna] = valor
        with pytest.raises(ValueError):
            validar_partidas(invalida)


def test_treino_e_teste_sao_disjuntos_e_probabilidades_somam_um():
    assert EXPERIMENTO.treino.data.max() < EXPERIMENTO.teste.data.min()
    assert not set(EXPERIMENTO.treino.ID) & set(EXPERIMENTO.teste.ID)

    probabilidades = EXPERIMENTO.teste[COLUNAS_PROB].to_numpy()
    assert ((probabilidades >= 0) & (probabilidades <= 1)).all()
    np.testing.assert_allclose(probabilidades.sum(axis=1), 1)

    referencia = (
        EXPERIMENTO.treino.alvo.value_counts(normalize=True)
        .reindex([0, 1, 2]).to_numpy()
    )
    np.testing.assert_allclose(EXPERIMENTO.teste[COLUNAS_BASE].iloc[0], referencia)


def test_alterar_placares_do_teste_nao_muda_modelo_nem_referencia():
    alterada = ORIGINAL.copy()
    teste = pd.to_datetime(alterada.data, format='%d/%m/%Y') >= pd.Timestamp('2023-01-01')
    alterada.loc[teste, ['mandante_Placar', 'visitante_Placar']] = [5, 0]
    novo = treinar_experimento(alterada)
    np.testing.assert_allclose(
        EXPERIMENTO.modelo.named_steps['classificador'].coef_,
        novo.modelo.named_steps['classificador'].coef_,
    )
    np.testing.assert_allclose(EXPERIMENTO.teste[COLUNAS_BASE], novo.teste[COLUNAS_BASE])


def test_padronizacao_e_vocabulario_veem_somente_treino():
    jogos = ORIGINAL.copy()
    jogos.loc[len(jogos) - 1, 'mandante'] = 'Clube Futuro'
    resultado = treinar_experimento(jogos)
    preparacao = resultado.modelo.named_steps['preparacao']
    np.testing.assert_allclose(
        preparacao.named_transformers_['numericas'].mean_,
        resultado.treino[NUMERICAS].mean().to_numpy(),
    )
    categorias = preparacao.named_transformers_['clubes'].categories_
    assert all('Clube Futuro' not in categoria for categoria in categorias)


def test_perspectiva_do_corinthians_inverte_vitoria_e_derrota_fora():
    jogos = pd.DataFrame([
        dict(
            ID=1, data=pd.Timestamp('2025-01-01'),
            mandante='Santos', visitante='Corinthians',
            mandante_Placar=2, visitante_Placar=0, alvo=0,
            prob_mandante=0.6, prob_empate=0.25, prob_visitante=0.15,
        ),
        dict(
            ID=2, data=pd.Timestamp('2025-01-02'),
            mandante='Corinthians', visitante='Santos',
            mandante_Placar=2, visitante_Placar=0, alvo=0,
            prob_mandante=0.6, prob_empate=0.25, prob_visitante=0.15,
        ),
    ])
    previsoes = previsoes_corinthians(jogos).set_index('ID')
    assert previsoes.loc[1, 'prob_vitoria'] == 0.15
    assert previsoes.loc[1, 'prob_derrota'] == 0.6
    assert previsoes.loc[1, 'resultado'] == 'Derrota'
    assert previsoes.loc[1, 'gols_marcados'] == 0
    assert previsoes.loc[2, 'prob_vitoria'] == 0.6
    assert previsoes.loc[2, 'resultado'] == 'Vitória'


def test_metricas_de_probabilidades_perfeitas():
    perfeito = pd.DataFrame({
        'alvo': [0, 1, 2],
        'prob_mandante': [1, 0, 0],
        'prob_empate': [0, 1, 0],
        'prob_visitante': [0, 0, 1],
    })
    metricas = avaliar_previsoes(perfeito)
    assert metricas['acuracia'] == 1
    assert metricas['brier'] == 0
    assert np.isclose(metricas['log_loss'], 0)
