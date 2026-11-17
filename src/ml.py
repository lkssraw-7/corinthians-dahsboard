"""Experimento pré-jogo com treino temporal e informações estritamente passadas.

Alvo: 0 = vitória do mandante, 1 = empate, 2 = vitória do visitante.
As features de um dia inteiro são calculadas antes de incorporar seus placares.
"""

from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

VERSAO_MODELO = '1.0'
CORTE_TESTE = '2023-01-01'
FIM_TESTE = '2026-01-01'
CATEGORICAS = ['mandante', 'visitante']
MEDIDAS = [
    'pontos_5', 'gols_marcados_10', 'gols_sofridos_10',
    'vitorias_10', 'jogos_10', 'dias_desde_ultimo',
]
NUMERICAS = [f'{lado}_{medida}' for lado in CATEGORICAS for medida in MEDIDAS]
FEATURES = CATEGORICAS + NUMERICAS
COLUNAS_PROB = ['prob_mandante', 'prob_empate', 'prob_visitante']
COLUNAS_BASE = ['base_mandante', 'base_empate', 'base_visitante']


@dataclass
class Experimento:
    modelo: Pipeline
    treino: pd.DataFrame
    teste: pd.DataFrame


def validar_partidas(original: pd.DataFrame) -> pd.DataFrame:
    colunas = ['ID', 'data', 'mandante', 'visitante', 'mandante_Placar', 'visitante_Placar']
    faltantes = set(colunas) - set(original.columns)
    if faltantes:
        raise ValueError('Colunas ausentes na base de treino: ' + ', '.join(sorted(faltantes)))
    jogos = original[colunas].copy()
    jogos['data'] = pd.to_datetime(jogos['data'], format='%d/%m/%Y', errors='coerce')
    for coluna in ['ID', 'mandante_Placar', 'visitante_Placar']:
        jogos[coluna] = pd.to_numeric(jogos[coluna], errors='coerce')
    if jogos.empty or jogos.isna().any().any():
        raise ValueError('A base de treino está vazia ou contém datas, clubes, IDs ou placares inválidos.')
    numeros = jogos[['ID', 'mandante_Placar', 'visitante_Placar']]
    if not np.isfinite(numeros.to_numpy()).all() or (numeros < 0).any().any() or (numeros % 1 != 0).any().any():
        raise ValueError('IDs e placares devem ser números inteiros não negativos.')
    if jogos['ID'].duplicated().any():
        raise ValueError('A base de treino contém IDs de partidas duplicados.')
    for coluna in CATEGORICAS:
        jogos[coluna] = jogos[coluna].astype(str).str.strip()
        if jogos[coluna].eq('').any():
            raise ValueError('A base de treino contém clubes sem nome.')
    if jogos['mandante'].eq(jogos['visitante']).any():
        raise ValueError('Uma partida não pode ter o mesmo clube nos dois lados.')
    jogos[numeros.columns] = numeros.astype(int)
    return jogos.sort_values(['data', 'ID']).reset_index(drop=True)


def _resumir_historico(historico, dia):
    # Desconsidera jogos antigos após longas ausências da Série A.
    recentes = [jogo for jogo in historico if (dia - jogo[0]).days <= 365]
    if not recentes:
        return dict(zip(MEDIDAS, [0.0, 0.0, 0.0, 0.0, 0, 120]))
    return {
        'pontos_5': float(np.mean([jogo[1] for jogo in recentes[-5:]])),
        'gols_marcados_10': float(np.mean([jogo[2] for jogo in recentes])),
        'gols_sofridos_10': float(np.mean([jogo[3] for jogo in recentes])),
        'vitorias_10': float(np.mean([jogo[1] == 3 for jogo in recentes])),
        'jogos_10': len(recentes),
        'dias_desde_ultimo': min((dia - recentes[-1][0]).days, 120),
    }


def preparar_features(original: pd.DataFrame) -> pd.DataFrame:
    jogos = validar_partidas(original)
    historicos = defaultdict(lambda: deque(maxlen=10))
    registros = []
    for dia, bloco in jogos.groupby('data', sort=True):
        partidas_dia = bloco.to_dict('records')
        for partida in partidas_dia:
            linha = partida.copy()
            for lado in CATEGORICAS:
                resumo = _resumir_historico(historicos[partida[lado]], dia)
                linha.update({f'{lado}_{chave}': valor for chave, valor in resumo.items()})
            gm, gv = partida['mandante_Placar'], partida['visitante_Placar']
            linha['alvo'] = 0 if gm > gv else (1 if gm == gv else 2)
            registros.append(linha)
        # Nenhuma partida do mesmo dia influencia as features das outras.
        for partida in partidas_dia:
            gm, gv = partida['mandante_Placar'], partida['visitante_Placar']
            pm = 3 if gm > gv else int(gm == gv)
            pv = 3 if gv > gm else int(gm == gv)
            historicos[partida['mandante']].append((dia, pm, gm, gv))
            historicos[partida['visitante']].append((dia, pv, gv, gm))
    return pd.DataFrame(registros)


def treinar_experimento(original: pd.DataFrame, corte=CORTE_TESTE, fim=FIM_TESTE) -> Experimento:
    preparadas = preparar_features(original)
    treino = preparadas[preparadas['data'] < pd.Timestamp(corte)].copy()
    teste = preparadas[
        (preparadas['data'] >= pd.Timestamp(corte)) & (preparadas['data'] < pd.Timestamp(fim))
    ].copy()
    if treino.empty or teste.empty:
        raise ValueError('É preciso haver partidas antes e depois do corte temporal.')
    if set(treino['alvo']) != {0, 1, 2}:
        raise ValueError('O treino precisa conter vitórias de mandante, empates e vitórias de visitante.')

    preprocessador = ColumnTransformer([
        ('numericas', StandardScaler(), NUMERICAS),
        ('clubes', OneHotEncoder(handle_unknown='ignore'), CATEGORICAS),
    ], remainder='drop')
    modelo = Pipeline([
        ('preparacao', preprocessador),
        ('classificador', LogisticRegression(C=1.0, max_iter=1000, solver='lbfgs', random_state=42)),
    ])
    # Tanto o escalonamento quanto o vocabulário dos clubes veem somente o treino.
    modelo.fit(treino[FEATURES], treino['alvo'])
    classes = list(modelo.classes_)
    probabilidades = modelo.predict_proba(teste[FEATURES])[:, [classes.index(c) for c in (0, 1, 2)]]
    referencia = treino['alvo'].value_counts(normalize=True).reindex([0, 1, 2]).to_numpy()
    teste[COLUNAS_PROB] = probabilidades
    teste[COLUNAS_BASE] = np.tile(referencia, (len(teste), 1))
    return Experimento(modelo=modelo, treino=treino, teste=teste.reset_index(drop=True))


def avaliar_previsoes(teste: pd.DataFrame, referencia=False) -> dict:
    if teste.empty:
        raise ValueError('O recorte de avaliação não contém partidas.')
    probabilidades = teste[COLUNAS_BASE if referencia else COLUNAS_PROB].to_numpy()
    alvos = teste['alvo'].to_numpy(dtype=int)
    observado = np.eye(3)[alvos]
    return {
        'jogos': len(teste),
        'acuracia': float(accuracy_score(alvos, probabilidades.argmax(axis=1))),
        'log_loss': float(log_loss(alvos, probabilidades, labels=[0, 1, 2])),
        # Brier multiclasse como soma dos erros quadráticos: intervalo de 0 a 2.
        'brier': float(np.mean(np.sum((probabilidades - observado) ** 2, axis=1))),
    }


def previsoes_corinthians(teste: pd.DataFrame) -> pd.DataFrame:
    jogos = teste[teste['mandante'].eq('Corinthians') | teste['visitante'].eq('Corinthians')].copy()
    em_casa = jogos['mandante'].eq('Corinthians')
    jogos['adversario'] = np.where(em_casa, jogos['visitante'], jogos['mandante'])
    jogos['local'] = np.where(em_casa, 'Mandante', 'Visitante')
    jogos['prob_vitoria'] = np.where(em_casa, jogos['prob_mandante'], jogos['prob_visitante'])
    jogos['prob_derrota'] = np.where(em_casa, jogos['prob_visitante'], jogos['prob_mandante'])
    jogos['gols_marcados'] = np.where(em_casa, jogos['mandante_Placar'], jogos['visitante_Placar'])
    jogos['gols_sofridos'] = np.where(em_casa, jogos['visitante_Placar'], jogos['mandante_Placar'])
    alvo_clube = np.where(em_casa, jogos['alvo'], 2 - jogos['alvo'])
    jogos['resultado'] = pd.Series(alvo_clube, index=jogos.index).map({0: 'Vitória', 1: 'Empate', 2: 'Derrota'})
    return jogos.sort_values(['data', 'ID'], ascending=False).reset_index(drop=True)
