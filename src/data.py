"""Leitura e preparação das bases tratadas do Corinthians."""

from pathlib import Path

import pandas as pd
import streamlit as st

PASTA_DADOS = Path(__file__).resolve().parent.parent / 'dados'
ARQUIVOS_DADOS = (
    'partidas_corinthians.csv',
    'partidas_libertadores.csv',
    'partidas_copa_brasil.csv',
    'gols_corinthians.csv',
    'cartoes_corinthians.csv',
)


@st.cache_data
def _carregar_dados_cache(assinatura):
    """Lê os CSVs; a assinatura faz o cache acompanhar alterações nos arquivos."""
    brasileirao = pd.read_csv(PASTA_DADOS / 'partidas_corinthians.csv')
    libertadores = pd.read_csv(PASTA_DADOS / 'partidas_libertadores.csv')
    copa_brasil = pd.read_csv(PASTA_DADOS / 'partidas_copa_brasil.csv')
    gols = pd.read_csv(PASTA_DADOS / 'gols_corinthians.csv')
    cartoes = pd.read_csv(PASTA_DADOS / 'cartoes_corinthians.csv')

    for partidas in (brasileirao, libertadores, copa_brasil):
        partidas['data'] = pd.to_datetime(partidas['data'], errors='coerce')
        partidas['temporada'] = partidas['temporada'].astype(int)
        partidas['pontos'] = partidas['resultado'].map({
            'Vitoria': 3,
            'Empate': 1,
            'Derrota': 0,
        })

    competicoes = {
        'Brasileirão — Série A': brasileirao,
        'Copa Libertadores': libertadores,
        'Copa do Brasil': copa_brasil,
    }
    return competicoes, gols, cartoes


def carregar_dados():
    """Lê as competições e invalida o cache quando algum CSV é alterado."""
    assinatura = tuple(
        (nome, (PASTA_DADOS / nome).stat().st_mtime_ns, (PASTA_DADOS / nome).stat().st_size)
        for nome in ARQUIVOS_DADOS
    )
    return _carregar_dados_cache(assinatura)
