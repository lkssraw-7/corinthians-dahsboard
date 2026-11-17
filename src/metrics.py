"""Cálculo dos indicadores a partir das partidas selecionadas."""

import pandas as pd


def calcular_indicadores(partidas: pd.DataFrame) -> dict:
    """Retorna os totais e o aproveitamento (de 0 a 100) do recorte.

    Recebe as partidas preparadas por carregar_dados(), já filtradas.
    Um recorte sem partidas retorna todos os indicadores zerados.
    """
    total_jogos = len(partidas)
    vitorias = int((partidas['resultado'] == 'Vitoria').sum())
    empates = int((partidas['resultado'] == 'Empate').sum())
    derrotas = int((partidas['resultado'] == 'Derrota').sum())
    gols_marcados = int(partidas['gols_marcados'].sum())
    gols_sofridos = int(partidas['gols_sofridos'].sum())
    pontos = int(partidas['pontos'].sum())

    if total_jogos > 0:
        aproveitamento = pontos / (total_jogos * 3) * 100
    else:
        aproveitamento = 0.0

    return {
        'total_jogos': total_jogos,
        'vitorias': vitorias,
        'empates': empates,
        'derrotas': derrotas,
        'gols_marcados': gols_marcados,
        'gols_sofridos': gols_sofridos,
        'pontos': pontos,
        'aproveitamento': aproveitamento,
    }


def desempenho_por_temporada(partidas: pd.DataFrame) -> pd.DataFrame:
    """Agrega pontos e jogos; mantém lacunas em temporadas sem registros."""
    if partidas.empty:
        return pd.DataFrame(columns=['temporada', 'jogos', 'pontos', 'aproveitamento'])

    resumo = partidas.groupby('temporada').agg(
        jogos=('ID', 'size'),
        pontos=('pontos', 'sum'),
    )
    temporadas = range(int(resumo.index.min()), int(resumo.index.max()) + 1)
    resumo = resumo.reindex(temporadas)
    resumo['aproveitamento'] = resumo['pontos'] / (resumo['jogos'] * 3) * 100
    return resumo.rename_axis('temporada').reset_index()
