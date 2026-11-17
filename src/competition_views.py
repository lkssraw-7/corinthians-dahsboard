"""Visualizações específicas de competições em formato de copa."""

import pandas as pd
import streamlit as st

from components import cabecalho_secao, formatar_numero
from src.charts import grafico_desempenho_por_fase


ORDEM_FASES = {
    '1ª fase': 0,
    '2ª fase': 1,
    '3ª fase': 2,
    '4ª fase': 3,
    'Fase preliminar': 0,
    'Fase de grupos': 1,
    'Oitavas de final': 4,
    'Quartas de final': 5,
    'Semifinal': 6,
    'Final': 7,
}


def etapas_para_exibicao(partidas: pd.DataFrame) -> pd.Series:
    """Padroniza a etapa e omite o grupo quando a própria fase já o informa."""
    etapas = partidas['instancia'].astype('string').replace({
        'Vuelta': 'Volta',
        'Unico': 'Jogo único',
        'Llave G2': 'Chave G2',
    }).str.replace(r'^Group ', 'Grupo ', regex=True)
    etapas = etapas.fillna('Não informada')
    etapas.loc[partidas['fase'].eq('Fase de grupos')] = '—'
    return etapas


def resumo_campanhas(partidas: pd.DataFrame) -> pd.DataFrame:
    """Agrega cada edição e identifica a fase mais avançada presente na base."""
    linhas = []
    for temporada, jogos in partidas.groupby('temporada', sort=False):
        fases = jogos['fase'].dropna().unique().tolist()
        fase_maxima = max(fases, key=lambda fase: ORDEM_FASES.get(fase, -1)) if fases else 'Não informada'
        vitorias = int(jogos['resultado'].eq('Vitoria').sum())
        empates = int(jogos['resultado'].eq('Empate').sum())
        derrotas = int(jogos['resultado'].eq('Derrota').sum())
        linhas.append({
            'temporada': int(temporada),
            'fase_maxima': fase_maxima,
            'jogos': len(jogos),
            'vitorias': vitorias,
            'empates': empates,
            'derrotas': derrotas,
            'gols_marcados': int(jogos['gols_marcados'].sum()),
            'gols_sofridos': int(jogos['gols_sofridos'].sum()),
            'aproveitamento': (vitorias * 3 + empates) / (len(jogos) * 3) * 100,
        })
    return pd.DataFrame(linhas).sort_values('temporada', ascending=False)


def dados_linha_do_tempo(partidas: pd.DataFrame, temporada: int) -> pd.DataFrame:
    """Prepara os textos usados na linha do tempo de uma edição."""
    # Primeiro, pega somente os jogos do ano escolhido.
    campanha = partidas[partidas['temporada'].eq(temporada)].copy()
    campanha = campanha.sort_values('data').reset_index(drop=True)

    # Depois, cria textos simples para mostrar na tela.
    campanha['etapa_exibicao'] = etapas_para_exibicao(campanha)
    campanha['placar_exibicao'] = (
        campanha['gols_marcados'].astype(str)
        + ' × '
        + campanha['gols_sofridos'].astype(str)
    )
    campanha['resultado_exibicao'] = campanha['resultado'].replace({
        'Vitoria': 'Vitória',
        'Empate': 'Empate',
        'Derrota': 'Derrota',
    })
    return campanha


def exibir_linha_do_tempo(partidas: pd.DataFrame, competicao: str):
    """Mostra uma campanha fase por fase usando componentes simples do Streamlit."""
    # O ano mais recente aparece primeiro no seletor.
    temporadas = sorted(partidas['temporada'].unique(), reverse=True)

    with st.container(border=True, key='linha_tempo_campanha'):
        cabecalho_secao(
            'Linha do tempo da campanha',
            'Escolha uma edição para acompanhar a trajetória fase por fase.',
        )
        temporada = st.selectbox(
            'Edição',
            temporadas,
            key=f'linha_tempo_{competicao}',
        )
        campanha = dados_linha_do_tempo(partidas, temporada)

        # Números gerais da campanha selecionada.
        vitorias = int(campanha['resultado'].eq('Vitoria').sum())
        empates = int(campanha['resultado'].eq('Empate').sum())
        derrotas = int(campanha['resultado'].eq('Derrota').sum())
        fase_maxima = campanha.iloc[-1]['fase']

        coluna_fase, coluna_jogos, coluna_campanha, coluna_gols = st.columns(4)
        coluna_fase.metric('Fase alcançada', fase_maxima)
        coluna_jogos.metric('Jogos', len(campanha))
        coluna_campanha.metric('Campanha', f'{vitorias}V · {empates}E · {derrotas}D')
        coluna_gols.metric(
            'Gols',
            f"{int(campanha['gols_marcados'].sum())} × {int(campanha['gols_sofridos'].sum())}",
        )

        # Percorre as fases na ordem em que aconteceram.
        fases = campanha['fase'].drop_duplicates().tolist()
        for numero, fase in enumerate(fases, start=1):
            jogos_fase = campanha[campanha['fase'].eq(fase)]
            gols_marcados = int(jogos_fase['gols_marcados'].sum())
            gols_sofridos = int(jogos_fase['gols_sofridos'].sum())

            with st.container(border=True, key=f'fase_{temporada}_{numero}'):
                st.markdown(f'#### {numero}. {fase}')
                st.caption(
                    f'{len(jogos_fase)} jogo(s) · '
                    f'{gols_marcados} × {gols_sofridos} em gols na fase'
                )

                # Mostra uma linha para cada partida da fase.
                for _, jogo in jogos_fase.iterrows():
                    data, confronto, detalhe, placar = st.columns([1, 2.2, 1.4, 1.2])
                    data.write(jogo['data'].strftime('%d/%m/%Y'))
                    confronto.write(f"**{jogo['adversario']}**")
                    etapa = jogo['etapa_exibicao']
                    complemento = jogo['local'] if etapa == '—' else f"{etapa} · {jogo['local']}"
                    detalhe.write(complemento)
                    placar.write(
                        f"**{jogo['placar_exibicao']}** · {jogo['resultado_exibicao']}"
                    )

            if numero < len(fases):
                st.markdown('**↓ Próxima fase**')


def exibir_campanhas(partidas, competicao):
    """Renderiza o histórico por fase e por edição de uma copa."""
    nome_curto = 'Libertadores' if competicao == 'Copa Libertadores' else competicao
    cabecalho_secao(
        f'Campanhas na {nome_curto}',
        'Uma leitura por fase e por edição, usando somente a cobertura do arquivo importado.',
    )
    exibir_linha_do_tempo(partidas, competicao)

    with st.container(border=True, key='fases_libertadores'):
        cabecalho_secao('Desempenho por fase', 'Aproveitamento histórico nas etapas presentes na base.')
        st.plotly_chart(
            grafico_desempenho_por_fase(partidas), theme=None,
            use_container_width=True,
            config={'displayModeBar': False, 'responsive': True, 'displaylogo': False},
            key='grafico_fases_libertadores',
        )
        st.caption(
            'Empates permanecem empates no resultado oficial da partida; '
            'a fonte pode não informar o placar da disputa por pênaltis.'
        )

    resumo = resumo_campanhas(partidas)
    exibicao = resumo.copy()
    exibicao['aproveitamento'] = exibicao['aproveitamento'].map(
        lambda valor: f'{formatar_numero(valor, 1)}%',
    )
    with st.container(border=True, key='edicoes_libertadores'):
        cabecalho_secao('Edição por edição', 'Resultados e fase mais avançada registrada em cada campanha.')
        st.dataframe(
            exibicao,
            column_config={
                'temporada': st.column_config.NumberColumn('Edição', format='%d'),
                'fase_maxima': st.column_config.TextColumn('Fase mais avançada'),
                'jogos': st.column_config.NumberColumn('J'),
                'vitorias': st.column_config.NumberColumn('V'),
                'empates': st.column_config.NumberColumn('E'),
                'derrotas': st.column_config.NumberColumn('D'),
                'gols_marcados': st.column_config.NumberColumn('GM'),
                'gols_sofridos': st.column_config.NumberColumn('GS'),
                'aproveitamento': st.column_config.TextColumn('Aproveitamento'),
            },
            width='stretch', hide_index=True,
        )
