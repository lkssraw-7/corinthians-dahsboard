from pathlib import Path

import streamlit as st

from components import (
    cabecalho_dashboard,
    cabecalho_secao,
    carregar_css,
    formatar_numero,
    marca_sidebar,
    painel_indicadores,
    resumo_filtros,
)
from src.charts import grafico_evolucao, grafico_resultados
from src.competition_views import etapas_para_exibicao, exibir_campanhas
from src.data import carregar_dados
from src.event_views import exibir_disciplina, exibir_gols
from src.events import filtrar_eventos
from src.metrics import calcular_indicadores
from src.predictive import exibir_analise_preditiva

st.set_page_config(
    page_title='Corinthians em Dados',
    page_icon='⚽️',
    layout='wide',
)

PASTA_PROJETO = Path(__file__).parent
carregar_css(PASTA_PROJETO / 'style.css')


def limpar_filtros():
    st.session_state['temporada'] = 'Todas'
    st.session_state['local'] = 'Todos'
    st.session_state['adversario'] = 'Todos'


def cor_resultado(resultado):
    cores = {'Vitória': "#0A89D2", 'Empate': '#686971', 'Derrota': '#B41629'}
    return f'color: {cores.get(resultado, "#202126")}; font-weight: 600'


try:
    competicoes, gols, cartoes = carregar_dados()
except FileNotFoundError as erro:
    st.error(
        f'Erro ao carregar os dados: {erro}. '
        'Verifique se os arquivos CSV estão na pasta "dados".'
    )
    st.stop()

# Filtros persistentes e acessíveis pela barra lateral, inclusive no celular.
with st.sidebar:
    marca_sidebar()
    cabecalho_secao('Explore o acervo', 'Escolha um recorte para atualizar toda a análise.')
    competicao_selecionada = st.selectbox(
        'Campeonato / copa', list(competicoes), key='competicao',
        on_change=limpar_filtros,
    )
    partidas = competicoes[competicao_selecionada]
    if partidas.empty:
        st.info('A base desta competição está vazia.')
        st.stop()
    temporadas = sorted(partidas['temporada'].dropna().unique().tolist())
    periodo = f'{temporadas[0]}–{temporadas[-1]}'
    ultima_partida = partidas['data'].max().strftime('%d/%m/%Y')
    temp_selecionada = st.selectbox('Temporada', ['Todas'] + temporadas, key='temporada')
    locais = sorted(partidas['local'].dropna().unique().tolist())
    local_selecionado = st.selectbox('Local', ['Todos'] + locais, key='local')
    adversarios = sorted(partidas['adversario'].dropna().unique().tolist())
    adv_selecionado = st.selectbox('Adversário', ['Todos'] + adversarios, key='adversario')
    st.button('Limpar filtros', on_click=limpar_filtros, width='stretch')
    st.divider()
    st.caption(f'{competicao_selecionada.upper()} · {periodo}')
    st.caption(f'{formatar_numero(len(partidas))} partidas · {len(adversarios)} adversários na base')
    if competicao_selecionada == 'Brasileirão — Série A':
        st.caption('Os filtros se aplicam à Visão geral, Gols e Disciplina. A Análise preditiva tem controles próprios.')
    else:
        st.caption('Os filtros se aplicam à Visão geral. Campanhas usa todo o histórico importado.')

dados_filtrados = partidas.copy()
if temp_selecionada != 'Todas':
    dados_filtrados = dados_filtrados[dados_filtrados['temporada'] == temp_selecionada]
if local_selecionado != 'Todos':
    dados_filtrados = dados_filtrados[dados_filtrados['local'] == local_selecionado]
if adv_selecionado != 'Todos':
    dados_filtrados = dados_filtrados[dados_filtrados['adversario'] == adv_selecionado]

cabecalho_dashboard(
    periodo,
    len(temporadas),
    len(partidas),
    ultima_partida,
    competicao_selecionada,
)
if competicao_selecionada == 'Brasileirão — Série A':
    gols_filtrados = filtrar_eventos(gols, temp_selecionada, local_selecionado, adv_selecionado)
    cartoes_filtrados = filtrar_eventos(cartoes, temp_selecionada, local_selecionado, adv_selecionado)
    aba_visao, aba_gols, aba_disciplina, aba_ml = st.tabs([
        'Visão geral', 'Gols', 'Disciplina', 'Análise preditiva',
    ])
else:
    aba_visao, aba_campanhas = st.tabs(['Visão geral', 'Campanhas'])

with aba_visao:
    resumo_filtros(temp_selecionada, local_selecionado, adv_selecionado, len(dados_filtrados))
    if dados_filtrados.empty:
        st.info('Nenhuma partida encontrada para essa combinação. Ajuste os filtros ou use “Limpar filtros” na barra lateral.')
    else:
        indicadores = calcular_indicadores(dados_filtrados)
        painel_indicadores(indicadores)

        # Os gráficos compartilham tema, proporções e o mesmo recorte dos indicadores.
        col_resultados, col_evolucao = st.columns([1, 1.45], gap='medium')
        config_grafico = {'displayModeBar': False, 'responsive': True, 'displaylogo': False}
        with col_resultados:
            with st.container(border=True, key='resultados'):
                cabecalho_secao('O balanço em campo', 'Vitórias, empates e derrotas no recorte.')
                st.plotly_chart(
                    grafico_resultados(indicadores), theme=None,
                    use_container_width=True, config=config_grafico, key='grafico_resultados',
                )
                st.caption('Os percentuais consideram todas as partidas selecionadas.')

        with col_evolucao:
            with st.container(border=True, key='evolucao'):
                cabecalho_secao('Temporada a temporada', 'Evolução do aproveitamento de pontos.')
                st.plotly_chart(
                    grafico_evolucao(dados_filtrados), theme=None,
                    use_container_width=True, config=config_grafico, key='grafico_evolucao',
                )
                st.caption('Lacunas indicam temporadas sem partidas no recorte.')

        # Formatação restrita à tabela de exibição; o download mantém os campos da base.
        tabela = dados_filtrados.sort_values('data', ascending=False).copy()
        tabela['placar'] = tabela['gols_marcados'].astype(str) + ' × ' + tabela['gols_sofridos'].astype(str)
        tabela['resultado'] = tabela['resultado'].replace({'Vitoria': 'Vitória'})
        if competicao_selecionada != 'Brasileirão — Série A':
            com_penaltis = tabela['penales'].notna()
            if com_penaltis.any():
                tabela.loc[com_penaltis, 'placar'] += (
                    ' (' + tabela.loc[com_penaltis, 'penales'].astype('string')
                    .str.replace('Penales:', 'pên.', regex=False) + ')'
                )
            tabela['instancia'] = etapas_para_exibicao(tabela)
            tabela['arena'] = tabela['arena'].fillna('Não informada')
            colunas_tabela = [
                'data', 'temporada', 'fase', 'instancia', 'adversario',
                'local', 'placar', 'resultado', 'arena',
            ]
        else:
            tabela['tecnico'] = tabela['tecnico'].fillna('Não informado')
            colunas_tabela = ['data', 'temporada', 'adversario', 'local', 'placar', 'resultado', 'tecnico']

        with st.container(border=True, key='partidas'):
            col_titulo, col_download = st.columns([3, 1], vertical_alignment='center')
            with col_titulo:
                cabecalho_secao('Jogo a jogo', 'O detalhe de cada partida, da mais recente à mais antiga.')
            with col_download:
                st.download_button(
                    'Baixar CSV',
                    data=dados_filtrados.sort_values('data', ascending=False).to_csv(index=False).encode('utf-8-sig'),
                    file_name={
                        'Brasileirão — Série A': 'corinthians_brasileirao_filtrado.csv',
                        'Copa Libertadores': 'corinthians_libertadores_filtrada.csv',
                        'Copa do Brasil': 'corinthians_copa_brasil_filtrada.csv',
                    }[competicao_selecionada],
                    mime='text/csv',
                    on_click='ignore',
                    width='stretch',
                )
            st.caption('Placar: gols do Corinthians primeiro, tanto em casa quanto fora.')
            st.dataframe(
                tabela[colunas_tabela].style.map(cor_resultado, subset=['resultado']),
                column_config={
                    'data': st.column_config.DateColumn('Data', format='DD/MM/YYYY'),
                    'temporada': st.column_config.NumberColumn('Temporada', format='%d'),
                    'fase': st.column_config.TextColumn('Fase'),
                    'instancia': st.column_config.TextColumn('Etapa'),
                    'adversario': st.column_config.TextColumn('Adversário'),
                    'local': st.column_config.TextColumn('Local'),
                    'placar': st.column_config.TextColumn('Placar'),
                    'resultado': st.column_config.TextColumn('Resultado'),
                    'tecnico': st.column_config.TextColumn('Técnico'),
                    'arena': st.column_config.TextColumn('Estádio'),
                },
                width='stretch',
                height=420,
                hide_index=True,
                row_height=38,
            )

        with st.expander('Sobre os números e a cobertura da base'):
            st.markdown(
                '**Aproveitamento:** pontos conquistados ÷ pontos possíveis × 100. '
                'Cada vitória vale 3 pontos; cada empate, 1. '
                'As médias de gols usam o número de partidas do recorte.'
            )
            if competicao_selecionada == 'Copa Libertadores':
                st.markdown(
                    f'**Fonte:** arquivo utilizado em `libertadores.ipynb`, com '
                    f'{formatar_numero(len(partidas))} jogos entre {periodo}. '
                    f'A última partida registrada é de {ultima_partida}.'
                )
                st.caption(
                    'Este arquivo cobre as participações presentes entre 1996 e 2023; '
                    'não representa todo o histórico do Corinthians na competição.'
                )
                st.caption('Estádios, cidades e links ausentes são exibidos como não informados; nenhum valor foi estimado.')
            elif competicao_selecionada == 'Copa do Brasil':
                st.markdown(
                    f'**Fonte:** BrazilianFootball/Data, com {formatar_numero(len(partidas))} '
                    f'jogos do Corinthians entre {periodo}. '
                    f'A última partida registrada é de {ultima_partida}.'
                )
                st.caption(
                    'Os arquivos processados usados cobrem 2013–2025. O próprio repositório '
                    'sinaliza cobertura parcial do torneio em 2013–2016 e 121 de 122 jogos em 2025.'
                )
                st.caption('A origem informa estádios e cidades, mas não o placar das disputas por pênaltis.')
                st.caption(
                    'Nos jogos como mandante a partir de 2014, o estádio foi padronizado '
                    'como Neo Química Arena conforme a regra do projeto.'
                )
            else:
                st.markdown(
                    f'**Fonte:** base histórica de partidas fornecida para este projeto, '
                    f'com {formatar_numero(len(partidas))} jogos entre {periodo}. '
                    f'A última partida registrada é de {ultima_partida}.'
                )
            ausentes = sorted(set(range(temporadas[0], temporadas[-1] + 1)) - set(temporadas))
            if competicao_selecionada == 'Brasileirão — Série A' and 2008 in ausentes:
                st.caption('2008: o Corinthians disputou a Série B, fora do recorte desta base da Série A.')
                ausentes.remove(2008)
            if ausentes:
                st.caption('Temporadas sem registros na base: ' + ', '.join(map(str, ausentes)) + '. Não foram estimados resultados para esses anos.')
            if competicao_selecionada == 'Brasileirão — Série A':
                st.caption('“Não informado” identifica técnicos sem registro na fonte. Os dados não são atualizados em tempo real.')

if competicao_selecionada == 'Brasileirão — Série A':
    with aba_gols:
        exibir_gols(
            gols, gols_filtrados,
            temp_selecionada, local_selecionado, adv_selecionado,
        )

    with aba_disciplina:
        exibir_disciplina(
            cartoes, cartoes_filtrados,
            temp_selecionada, local_selecionado, adv_selecionado,
        )

    with aba_ml:
        exibir_analise_preditiva(PASTA_PROJETO / 'dados' / 'campeonato-brasileiro-full.csv')
else:
    with aba_campanhas:
        exibir_campanhas(partidas, competicao_selecionada)
