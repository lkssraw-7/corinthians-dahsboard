"""Seções visuais de gols e disciplina do dashboard."""

import pandas as pd
import streamlit as st

from components import cabecalho_secao, formatar_numero, painel_cards
from src.charts import (
    grafico_artilheiros,
    grafico_cartoes_por_atleta,
    grafico_cartoes_por_temporada,
    grafico_gols_por_intervalo,
)
from src.events import indicadores_cartoes, indicadores_gols


CONFIG_GRAFICO = {'displayModeBar': False, 'responsive': True, 'displaylogo': False}


def _cobertura(eventos: pd.DataFrame) -> str:
    inicio = int(eventos['temporada'].min())
    fim = int(eventos['temporada'].max())
    return str(inicio) if inicio == fim else f'{inicio}–{fim}'


def _contexto_filtros(temporada, local, adversario):
    partes = [
        'todas as temporadas' if temporada == 'Todas' else f'temporada {temporada}',
        'casa e fora' if local == 'Todos' else local.lower(),
        'todos os adversários' if adversario == 'Todos' else adversario,
    ]
    return ' · '.join(partes)


def exibir_gols(gols, gols_filtrados, temporada, local, adversario):
    """Renderiza indicadores e visualizações da base de gols."""
    cabecalho_secao('Gols', 'Quem marcou, quando marcou e como os gols se distribuem nas partidas.')
    st.caption(
        f'Cobertura da base de autores dos gols: {_cobertura(gols)}. '
        f'Recorte atual: {_contexto_filtros(temporada, local, adversario)}.'
    )
    if gols_filtrados.empty:
        st.info(
            'Não há gols detalhados para este recorte. A identificação dos autores '
            f'está disponível entre {_cobertura(gols)}.'
        )
        return

    indicadores = indicadores_gols(gols_filtrados)
    percentual_final = indicadores['gols_finais'] / indicadores['total'] * 100
    painel_cards([
        ('Gols registrados', formatar_numero(indicadores['total']), 'Com autoria identificada no recorte', 'destaque'),
        ('Artilheiros', formatar_numero(indicadores['artilheiros']), 'Jogadores diferentes com gol', 'padrao'),
        ('De pênalti', formatar_numero(indicadores['penaltis']), 'Tipo informado pela fonte', 'padrao'),
        ('Após os 75 min', formatar_numero(indicadores['gols_finais']), f'{formatar_numero(percentual_final, 1)}% dos gols', 'derrota'),
    ])

    limite = st.segmented_control(
        'Quantidade de artilheiros', options=[5, 10, 15], default=10,
        format_func=lambda valor: f'Top {valor}', key='gols_limite',
    )
    limite = limite or 10
    col_artilheiros, col_minutos = st.columns([1.15, 1], gap='medium')
    with col_artilheiros:
        with st.container(border=True, key='artilheiros'):
            cabecalho_secao('Artilheiros do recorte', 'Ranking por número de gols marcados.')
            st.plotly_chart(
                grafico_artilheiros(gols_filtrados, limite), theme=None,
                use_container_width=True, config=CONFIG_GRAFICO, key='grafico_artilheiros',
            )
    with col_minutos:
        with st.container(border=True, key='minutos_gols'):
            cabecalho_secao('Quando saem os gols', 'Distribuição por faixa de minuto.')
            st.plotly_chart(
                grafico_gols_por_intervalo(gols_filtrados), theme=None,
                use_container_width=True, config=CONFIG_GRAFICO, key='grafico_minutos_gols',
            )
            st.caption('Acréscimos do segundo tempo aparecem em “90+”.')

    tabela = gols_filtrados.sort_values(['data', 'minuto_numerico'], ascending=False).copy()
    tabela['data'] = pd.to_datetime(tabela['data'], errors='coerce')
    tabela['tipo_de_gol'] = tabela['tipo_de_gol'].replace({'Gol normal': 'Gol normal'})
    with st.container(border=True, key='lista_gols'):
        cabecalho_secao('Gol a gol', 'Os registros mais recentes do recorte selecionado.')
        st.dataframe(
            tabela[['data', 'temporada', 'atleta', 'adversario', 'local', 'minuto_original', 'tipo_de_gol']],
            column_config={
                'data': st.column_config.DateColumn('Data', format='DD/MM/YYYY'),
                'temporada': st.column_config.NumberColumn('Temporada', format='%d'),
                'atleta': st.column_config.TextColumn('Autor'),
                'adversario': st.column_config.TextColumn('Adversário'),
                'local': st.column_config.TextColumn('Local'),
                'minuto_original': st.column_config.TextColumn('Minuto'),
                'tipo_de_gol': st.column_config.TextColumn('Tipo'),
            },
            width='stretch', height=390, hide_index=True,
        )


def exibir_disciplina(cartoes, cartoes_filtrados, temporada, local, adversario):
    """Renderiza indicadores e visualizações da base disciplinar."""
    cabecalho_secao('Disciplina', 'Cartões por jogador, tipo e temporada.')
    st.caption(
        f'Cobertura da base individual de cartões: {_cobertura(cartoes)}. '
        f'Recorte atual: {_contexto_filtros(temporada, local, adversario)}.'
    )
    if cartoes_filtrados.empty:
        st.info(
            'Não há cartões detalhados para este recorte. Os registros individuais '
            f'estão disponíveis entre {_cobertura(cartoes)}.'
        )
        return

    indicadores = indicadores_cartoes(cartoes_filtrados)
    percentual_vermelhos = indicadores['vermelhos'] / indicadores['total'] * 100
    painel_cards([
        ('Cartões', formatar_numero(indicadores['total']), 'Advertências no recorte', 'destaque'),
        ('Amarelos', formatar_numero(indicadores['amarelos']), 'Registros individuais', 'padrao'),
        ('Vermelhos', formatar_numero(indicadores['vermelhos']), f'{formatar_numero(percentual_vermelhos, 1)}% dos cartões', 'derrota'),
        ('Atletas advertidos', formatar_numero(indicadores['atletas']), 'Jogadores diferentes', 'padrao'),
    ])

    limite = st.segmented_control(
        'Quantidade de jogadores', options=[5, 10, 15], default=10,
        format_func=lambda valor: f'Top {valor}', key='cartoes_limite',
    )
    limite = limite or 10
    col_jogadores, col_temporadas = st.columns([1.15, 1], gap='medium')
    with col_jogadores:
        with st.container(border=True, key='ranking_cartoes'):
            cabecalho_secao('Mais advertidos', 'Amarelos e vermelhos por atleta.')
            st.plotly_chart(
                grafico_cartoes_por_atleta(cartoes_filtrados, limite), theme=None,
                use_container_width=True, config=CONFIG_GRAFICO, key='grafico_cartoes_atleta',
            )
    with col_temporadas:
        with st.container(border=True, key='temporadas_cartoes'):
            cabecalho_secao('Disciplina por temporada', 'Evolução dos cartões registrados.')
            st.plotly_chart(
                grafico_cartoes_por_temporada(cartoes_filtrados), theme=None,
                use_container_width=True, config=CONFIG_GRAFICO, key='grafico_cartoes_temporada',
            )

    tabela = cartoes_filtrados.sort_values(['data', 'minuto'], ascending=False).copy()
    tabela['data'] = pd.to_datetime(tabela['data'], errors='coerce')
    tabela['posicao'] = tabela['posicao'].fillna('Não informada')
    with st.container(border=True, key='lista_cartoes'):
        cabecalho_secao('Cartão a cartão', 'Os registros mais recentes do recorte selecionado.')
        st.dataframe(
            tabela[['data', 'temporada', 'atleta', 'posicao', 'adversario', 'local', 'minuto', 'tipo_cartao']],
            column_config={
                'data': st.column_config.DateColumn('Data', format='DD/MM/YYYY'),
                'temporada': st.column_config.NumberColumn('Temporada', format='%d'),
                'atleta': st.column_config.TextColumn('Atleta'),
                'posicao': st.column_config.TextColumn('Posição'),
                'adversario': st.column_config.TextColumn('Adversário'),
                'local': st.column_config.TextColumn('Local'),
                'minuto': st.column_config.TextColumn('Minuto'),
                'tipo_cartao': st.column_config.TextColumn('Cartão'),
            },
            width='stretch', height=390, hide_index=True,
        )
