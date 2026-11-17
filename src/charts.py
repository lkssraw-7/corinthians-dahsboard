"""Gráficos com a identidade visual do dashboard."""

import plotly.graph_objects as go

from src.metrics import desempenho_por_temporada

CORES_RESULTADOS = ['#292B31', '#AAABB3', '#C8192E']
COR_TINTA = '#292B31'
COR_VERMELHO = '#C8192E'
COR_AMARELO = '#D6A514'


def _aplicar_tema(figura, altura=290):
    figura.update_layout(
        template='plotly_white',
        height=altura,
        margin=dict(l=12, r=20, t=20, b=16),
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#FFFFFF',
        font=dict(family='Arial, sans-serif', size=11, color='#686971'),
        hoverlabel=dict(bgcolor='#202126', font_color='#FFFFFF', bordercolor='#202126'),
        showlegend=False,
        separators=',.',
    )
    figura.update_xaxes(showline=False, zeroline=False, fixedrange=True)
    figura.update_yaxes(showline=False, zeroline=False, fixedrange=True)
    return figura


def grafico_resultados(indicadores):
    valores = [indicadores[chave] for chave in ('vitorias', 'empates', 'derrotas')]
    jogos = indicadores['total_jogos']
    proporcoes = [valor / jogos * 100 if jogos else 0 for valor in valores]
    textos = [
        f"{valor}  ·  {percentual:.1f}%".replace('.', ',')
        for valor, percentual in zip(valores, proporcoes)
    ]
    figura = go.Figure(go.Bar(
        x=valores,
        y=['Vitórias', 'Empates', 'Derrotas'],
        orientation='h',
        marker_color=CORES_RESULTADOS,
        text=textos,
        textposition='outside',
        textfont=dict(size=12, color='#202126'),
        cliponaxis=False,
        customdata=proporcoes,
        hovertemplate='%{y}<br>%{x} partidas · %{customdata:.1f}%<extra></extra>',
        width=0.48,
    ))
    _aplicar_tema(figura)
    figura.update_xaxes(
        title=None, showticklabels=False, showgrid=False,
        range=[0, max(max(valores), 1) * 1.6],
    )
    figura.update_yaxes(autorange='reversed', showgrid=False, tickfont_color='#393B43')
    return figura


def grafico_evolucao(partidas):
    resumo = desempenho_por_temporada(partidas)
    figura = go.Figure(go.Scatter(
        x=resumo['temporada'].tolist(),
        y=resumo['aproveitamento'].tolist(),
        customdata=resumo['jogos'].tolist(),
        mode='lines+markers',
        connectgaps=False,
        line=dict(color='#C8192E', width=2.5),
        marker=dict(size=6, color='#C8192E', line=dict(color='#FFFFFF', width=1)),
        fill='tozeroy',
        fillcolor='rgba(200, 25, 46, 0.06)',
        hovertemplate='Temporada %{x}<br>%{y:.1f}% de aproveitamento<br>%{customdata:.0f} partidas<extra></extra>',
    ))
    _aplicar_tema(figura)
    anos = resumo['temporada'].tolist()
    if anos:
        # Mostra poucos rótulos, mas mantém todos os pontos e lacunas no gráfico.
        passo = max(1, (len(anos) + 5) // 6)
        rotulos = sorted(set(anos[::passo] + [anos[-1]]))
        figura.update_xaxes(tickmode='array', tickvals=rotulos, tickformat='d')
        if len(anos) == 1:
            figura.update_xaxes(range=[anos[0] - 0.5, anos[0] + 0.5])
    figura.update_xaxes(showgrid=False)
    figura.update_yaxes(range=[0, 105], dtick=25, ticksuffix='%', gridcolor='#EEEEEC')
    return figura


def grafico_artilheiros(gols, limite=10):
    """Ranking horizontal dos atletas com mais gols no recorte."""
    ranking = (
        gols.groupby('atleta', as_index=False)
        .size().rename(columns={'size': 'gols'})
        .sort_values(['gols', 'atleta'], ascending=[False, True])
        .head(limite).sort_values('gols')
    )
    figura = go.Figure(go.Bar(
        x=ranking['gols'], y=ranking['atleta'], orientation='h',
        marker_color=COR_TINTA,
        text=ranking['gols'], textposition='outside', cliponaxis=False,
        hovertemplate='%{y}<br>%{x} gols<extra></extra>',
    ))
    altura = max(300, 34 * len(ranking) + 70)
    _aplicar_tema(figura, altura=altura)
    maior = int(ranking['gols'].max()) if not ranking.empty else 1
    figura.update_xaxes(
        title=None, showgrid=False, showticklabels=False,
        range=[0, max(1, maior) * 1.18],
    )
    figura.update_yaxes(title=None, showgrid=False, tickfont_color='#393B43')
    return figura


def grafico_gols_por_intervalo(gols):
    """Distribuição dos gols em faixas cronológicas da partida."""
    ordem = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '90+']
    contagem = gols['intervalo_gol'].value_counts().reindex(ordem, fill_value=0)
    figura = go.Figure(go.Bar(
        x=ordem, y=contagem.values,
        marker_color=[COR_TINTA] * 5 + [COR_VERMELHO] * 2,
        text=contagem.values, textposition='outside', cliponaxis=False,
        hovertemplate='Minutos %{x}<br>%{y} gols<extra></extra>',
    ))
    _aplicar_tema(figura, altura=370)
    maior = int(contagem.max()) if len(contagem) else 1
    figura.update_xaxes(title='Minuto da partida', showgrid=False)
    figura.update_yaxes(
        title='Gols', showticklabels=False, showgrid=True,
        gridcolor='#EEEEEC', range=[0, max(1, maior) * 1.18],
    )
    return figura


def grafico_cartoes_por_atleta(cartoes, limite=10):
    """Ranking empilhado de cartões amarelos e vermelhos por atleta."""
    ranking = (
        cartoes.groupby(['atleta', 'tipo_cartao']).size()
        .unstack(fill_value=0).reindex(columns=['Amarelo', 'Vermelho'], fill_value=0)
    )
    ranking['total'] = ranking.sum(axis=1)
    ranking = ranking.sort_values(['total', 'atleta'], ascending=[False, True]).head(limite)
    ranking = ranking.sort_values('total')
    figura = go.Figure()
    for tipo, cor in [('Amarelo', COR_AMARELO), ('Vermelho', COR_VERMELHO)]:
        figura.add_bar(
            x=ranking[tipo], y=ranking.index, name=tipo,
            orientation='h', marker_color=cor,
            hovertemplate=f'%{{y}}<br>{tipo}: %{{x}}<extra></extra>',
        )
    figura.update_traces(textposition='none')
    altura = max(300, 34 * len(ranking) + 85)
    _aplicar_tema(figura, altura=altura)
    figura.update_layout(
        barmode='stack', showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='left', x=0),
    )
    figura.update_xaxes(title='Cartões', showgrid=True, gridcolor='#EEEEEC', dtick=10)
    figura.update_yaxes(title=None, showgrid=False, tickfont_color='#393B43')
    return figura


def grafico_cartoes_por_temporada(cartoes):
    """Evolução anual dos cartões, separada por tipo."""
    resumo = (
        cartoes.groupby(['temporada', 'tipo_cartao']).size()
        .unstack(fill_value=0).reindex(columns=['Amarelo', 'Vermelho'], fill_value=0)
        .sort_index()
    )
    figura = go.Figure()
    for tipo, cor in [('Amarelo', COR_AMARELO), ('Vermelho', COR_VERMELHO)]:
        figura.add_bar(
            x=resumo.index, y=resumo[tipo], name=tipo, marker_color=cor,
            hovertemplate=f'Temporada %{{x}}<br>{tipo}: %{{y}}<extra></extra>',
        )
    _aplicar_tema(figura, altura=370)
    figura.update_layout(
        barmode='stack', showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='left', x=0),
    )
    figura.update_xaxes(title='Temporada', showgrid=False, tickformat='d', dtick=1)
    figura.update_yaxes(title='Cartões', showgrid=True, gridcolor='#EEEEEC')
    return figura


def grafico_desempenho_por_fase(partidas):
    """Compara resultados e aproveitamento nas fases de uma copa."""
    ordem = [
        '1ª fase', '2ª fase', '3ª fase', '4ª fase',
        'Fase preliminar', 'Fase de grupos', 'Oitavas de final',
        'Quartas de final', 'Semifinal', 'Final',
    ]
    resumo = partidas.groupby('fase').agg(
        jogos=('ID', 'size'),
        pontos=('pontos', 'sum'),
    )
    resumo['aproveitamento'] = resumo['pontos'] / (resumo['jogos'] * 3) * 100
    presentes = [fase for fase in ordem if fase in resumo.index]
    resumo = resumo.reindex(presentes)
    figura = go.Figure(go.Bar(
        x=resumo['aproveitamento'], y=resumo.index, orientation='h',
        marker_color=[COR_VERMELHO if fase in {'Semifinal', 'Final'} else COR_TINTA for fase in resumo.index],
        text=[f'{valor:.1f}%'.replace('.', ',') for valor in resumo['aproveitamento']],
        textposition='outside', cliponaxis=False,
        customdata=resumo['jogos'],
        hovertemplate='%{y}<br>%{x:.1f}% de aproveitamento<br>%{customdata} jogos<extra></extra>',
    ))
    _aplicar_tema(figura, altura=max(320, 48 * len(resumo) + 75))
    figura.update_xaxes(
        title='Aproveitamento', ticksuffix='%', range=[0, 108],
        showgrid=True, gridcolor='#EEEEEC',
    )
    figura.update_yaxes(title=None, showgrid=False, autorange='reversed')
    return figura
