"""Componentes visuais reutilizáveis do dashboard."""

from base64 import b64encode
from html import escape
from pathlib import Path

import streamlit as st


def carregar_css(caminho):
    """Carrega os estilos definidos em um arquivo CSS."""
    css = Path(caminho).read_text(encoding='utf-8')
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)


def formatar_numero(valor, casas=0):
    """Formata números com separadores brasileiros, sem depender do sistema."""
    return f'{valor:,.{casas}f}'.translate(str.maketrans(',.', '.,'))


def _html_card(titulo, valor, detalhe='', variante='padrao'):
    if variante not in {'padrao', 'vitoria', 'derrota', 'destaque'}:
        variante = 'padrao'
    return (
        f'<article class="metric-card metric-card--{variante}">'
        f'<div class="metric-title">{escape(str(titulo))}</div>'
        f'<div class="metric-value">{escape(str(valor))}</div>'
        f'<div class="metric-detail">{escape(str(detalhe))}</div>'
        '</article>'
    )


def card_metrica(titulo, valor, detalhe='', variante='padrao'):
    """Exibe um card individual; mantém compatibilidade com as chamadas antigas."""
    st.markdown(_html_card(titulo, valor, detalhe, variante), unsafe_allow_html=True)


def painel_cards(cards):
    """Exibe até quatro métricas no mesmo padrão visual do dashboard."""
    st.markdown(
        '<div class="metric-grid">'
        + ''.join(_html_card(*card) for card in cards)
        + '</div>',
        unsafe_allow_html=True,
    )


def painel_indicadores(indicadores):
    """Organiza os sete indicadores em uma grade responsiva."""
    jogos = indicadores['total_jogos']

    def participacao(chave):
        if not jogos:
            return 'Sem partidas no recorte'
        percentual = indicadores[chave] / jogos * 100
        return f'{formatar_numero(percentual, 1)}% das partidas'

    def media(chave):
        if not jogos:
            return 'Sem partidas no recorte'
        return f'{formatar_numero(indicadores[chave] / jogos, 2)} por jogo'

    primeira_linha = [
        ('Jogos', formatar_numero(jogos), 'Partidas no recorte', 'padrao'),
        ('Vitórias', formatar_numero(indicadores['vitorias']), participacao('vitorias'), 'vitoria'),
        ('Empates', formatar_numero(indicadores['empates']), participacao('empates'), 'padrao'),
        ('Derrotas', formatar_numero(indicadores['derrotas']), participacao('derrotas'), 'derrota'),
    ]
    segunda_linha = [
        ('Gols marcados', formatar_numero(indicadores['gols_marcados']), media('gols_marcados'), 'padrao'),
        ('Gols sofridos', formatar_numero(indicadores['gols_sofridos']), media('gols_sofridos'), 'padrao'),
        (
            'Aproveitamento',
            f"{formatar_numero(indicadores['aproveitamento'], 2)}%" if jogos else '—',
            f"{formatar_numero(indicadores['pontos'])} de {formatar_numero(jogos * 3)} pontos possíveis",
            'destaque',
        ),
    ]
    st.markdown(
        '<div class="metric-grid">'
        + ''.join(_html_card(*card) for card in primeira_linha)
        + '</div><div class="metric-grid metric-grid--three">'
        + ''.join(_html_card(*card) for card in segunda_linha)
        + '</div>',
        unsafe_allow_html=True,
    )


def _fonte_escudo():
    #Compartilha a mesma imagem entre o cabeçalho e a barra lateral
    caminho_escudo = Path(__file__).resolve().parent / 'assets' / 'corinthians_escudo.png'
    escudo_base64 = b64encode(caminho_escudo.read_bytes()).decode('ascii')
    return f'data:image/png;base64,{escudo_base64}'


def cabecalho_dashboard(periodo, temporadas, ultima_partida, competicao):
    """Exibe o escudo original junto ao título e à cobertura do acervo."""
    preposicao = 'no' if competicao.startswith('Brasileirão') else 'na'
    st.markdown(
        '<header class="dashboard-hero">'
        '<div class="hero-identity">'
        f'<img class="hero-crest" src="{_fonte_escudo()}" '
        'alt="Escudo do Sport Club Corinthians Paulista" width="395" height="500">'
        '<div class="hero-copy">'
        '<div class="eyebrow">O TIMÃO, JOGO A JOGO</div>'
        '<h1>Corinthians <span>em dados.</span></h1>'
        f'<p>Uma leitura da nossa história {preposicao} {escape(competicao)}.</p>'
        '</div></div><div class="hero-archive">'
        '<div class="archive-label">ACERVO HISTÓRICO</div>'
        f'<div class="archive-period">{escape(periodo)}</div>'
        f'<div class="archive-detail">{temporadas} temporadas na base</div>'
        f'<div class="archive-detail">Última partida: {escape(ultima_partida)}</div>'
        '</div></header>',
        unsafe_allow_html=True,
    )


def marca_sidebar():
    st.markdown(
        '<div class="sidebar-brand">'
        f'<img class="sidebar-crest" src="{_fonte_escudo()}" '
        'alt="Escudo do Sport Club Corinthians Paulista" width="395" height="500">'
        '<div><strong>Corinthians</strong><small>EM DADOS</small></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def resumo_filtros(temporada, local, adversario, total):
    rotulos = [
        'Todas as temporadas' if temporada == 'Todas' else f'Temporada {temporada}',
        'Casa e fora' if local == 'Todos' else local,
        'Todos os adversários' if adversario == 'Todos' else adversario,
    ]
    chips = ''.join(f'<span class="filter-chip">{escape(str(rotulo))}</span>' for rotulo in rotulos)
    st.markdown(
        '<div class="filter-summary"><div class="filter-chips">'
        + chips
        + f'</div><span class="filter-count">{formatar_numero(total)} partidas selecionadas</span></div>',
        unsafe_allow_html=True,
    )


def cabecalho_secao(titulo, descricao):
    st.markdown(
        f'<div class="section-heading"><h2>{escape(titulo)}</h2>'
        f'<p>{escape(descricao)}</p></div>',
        unsafe_allow_html=True,
    )
