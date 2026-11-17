"""Transforma a base usada em libertadores.ipynb no formato do dashboard."""

from argparse import ArgumentParser
from pathlib import Path
import re
import unicodedata

import pandas as pd


COLUNAS_OBRIGATORIAS = {
    'temporada', 'fase', 'instancia', 'fecha', 'pais_sede', 'ciudad_sede',
    'estadio', 'equipo_local', 'equipo_visitante', 'goles_local',
    'goles_visitante', 'penales', 'url_fuente',
}

FASES_PT = {
    'Cuartos de final': 'Quartas de final',
    'Octavos de final': 'Oitavas de final',
    'Semifinal': 'Semifinal',
    'Fase Preliminar': 'Fase preliminar',
    'Grupos': 'Fase de grupos',
    'Final': 'Final',
}

INSTANCIAS_PT = {
    'Vuelta': 'Volta',
    'Unico': 'Jogo único',
    'Llave G2': 'Chave G2',
}


def _slug(valor):
    texto = unicodedata.normalize('NFKD', str(valor)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', texto.lower()).strip('-')


def preparar_partidas_libertadores(bruta: pd.DataFrame) -> pd.DataFrame:
    """Filtra o Corinthians e padroniza as colunas usadas pelo dashboard."""
    ausentes = COLUNAS_OBRIGATORIAS - set(bruta.columns)
    if ausentes:
        raise ValueError('Colunas ausentes na base da Libertadores: ' + ', '.join(sorted(ausentes)))

    partidas = bruta[
        bruta['equipo_local'].eq('Corinthians')
        | bruta['equipo_visitante'].eq('Corinthians')
    ].copy()
    if partidas.empty:
        raise ValueError('A base não contém partidas do Corinthians.')

    mandante = partidas['equipo_local'].eq('Corinthians')
    partidas['data'] = pd.to_datetime(partidas['fecha'], errors='raise')
    partidas['adversario'] = partidas['equipo_visitante'].where(
        mandante, partidas['equipo_local'],
    )
    partidas['local'] = mandante.map({True: 'Mandante', False: 'Visitante'})
    partidas['gols_marcados'] = partidas['goles_local'].where(
        mandante, partidas['goles_visitante'],
    ).astype(int)
    partidas['gols_sofridos'] = partidas['goles_visitante'].where(
        mandante, partidas['goles_local'],
    ).astype(int)
    partidas['saldo_gols'] = partidas['gols_marcados'] - partidas['gols_sofridos']
    partidas['resultado'] = partidas['saldo_gols'].map(
        lambda saldo: 'Vitoria' if saldo > 0 else ('Derrota' if saldo < 0 else 'Empate')
    )
    partidas['pontos'] = partidas['resultado'].map({'Vitoria': 3, 'Empate': 1, 'Derrota': 0})
    partidas['competicao'] = 'Copa Libertadores'
    partidas['fase'] = partidas['fase'].replace(FASES_PT)
    partidas['instancia'] = (
        partidas['instancia'].replace(INSTANCIAS_PT)
        .str.replace(r'^Group ', 'Grupo ', regex=True)
    )
    partidas['arena'] = partidas['estadio']
    partidas.loc[
        mandante & partidas['temporada'].ge(2014),
        'arena',
    ] = 'Neo Química Arena'
    partidas['cidade_sede'] = partidas['ciudad_sede']
    partidas['fonte_url'] = partidas['url_fuente']
    partidas['ID'] = partidas.apply(
        lambda linha: 'LIB-{}-{}-{}-{}'.format(
            linha['data'].strftime('%Y%m%d'),
            _slug(linha['equipo_local']),
            _slug(linha['equipo_visitante']),
            int(linha.name),
        ),
        axis=1,
    )

    colunas = [
        'ID', 'competicao', 'temporada', 'data', 'fase', 'instancia',
        'adversario', 'local', 'arena', 'pais_sede', 'cidade_sede',
        'gols_marcados', 'gols_sofridos', 'saldo_gols', 'resultado',
        'pontos', 'penales', 'fonte_url',
    ]
    resultado = partidas[colunas].sort_values(['data', 'ID']).reset_index(drop=True)
    if resultado['ID'].duplicated().any():
        raise ValueError('Foram gerados identificadores duplicados para as partidas.')
    return resultado


def main():
    parser = ArgumentParser()
    parser.add_argument('entrada', type=Path, help='CSV matches.csv usado pelo notebook')
    parser.add_argument('saida', type=Path, help='CSV tratado para o dashboard')
    argumentos = parser.parse_args()

    bruta = pd.read_csv(argumentos.entrada)
    tratada = preparar_partidas_libertadores(bruta)
    argumentos.saida.parent.mkdir(parents=True, exist_ok=True)
    tratada.to_csv(argumentos.saida, index=False, encoding='utf-8-sig')
    print(f'{len(tratada)} partidas salvas em {argumentos.saida}')

if __name__ == '__main__':
    main()
