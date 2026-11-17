"""Consolida e transforma os JSONs da Copa do Brasil para o dashboard."""

from argparse import ArgumentParser
import json
from pathlib import Path
import re
import unicodedata

import pandas as pd


TIME_CORINTHIANS = 'Corinthians / SP'
URL_BASE = 'https://github.com/BrazilianFootball/Data'
URL_ARQUIVO = (
    'https://raw.githubusercontent.com/BrazilianFootball/Data/main/'
    'results/processed/CdB_{temporada}_games.json'
)
COLUNAS_OBRIGATORIAS = {
    'season', 'game', 'Date', 'Time', 'Stadium', 'Home', 'Away', 'Result',
}


def _sem_acentos(valor):
    return unicodedata.normalize('NFKD', str(valor)).encode('ascii', 'ignore').decode()


def _slug(valor):
    return re.sub(r'[^a-z0-9]+', '-', _sem_acentos(valor).lower()).strip('-')


def carregar_jsons_fonte(pasta: Path) -> pd.DataFrame:
   #Achata os JSONs por temporada, mantendo só os campos de partida.
    linhas = []
    arquivos = sorted(Path(pasta).glob('CdB_*_games.json'))
    if not arquivos:
        raise ValueError(f'Nenhum arquivo CdB_*_games.json encontrado em {pasta}.')

    for arquivo in arquivos:
        correspondencia = re.fullmatch(r'CdB_(\d{4})_games\.json', arquivo.name)
        if not correspondencia:
            continue
        temporada = int(correspondencia.group(1))
        with arquivo.open(encoding='utf-8') as entrada:
            jogos = json.load(entrada)
        for codigo, jogo in jogos.items():
            linhas.append({
                'season': temporada,
                'game': str(codigo).zfill(3),
                'Date': jogo.get('Date'),
                'Time': jogo.get('Time'),
                'Stadium': jogo.get('Stadium'),
                'Home': jogo.get('Home'),
                'Away': jogo.get('Away'),
                'Result': jogo.get('Result'),
                'source_url': URL_ARQUIVO.format(temporada=temporada),
            })
    return pd.DataFrame(linhas).sort_values(['season', 'game']).reset_index(drop=True)


def auditar_fonte(bruta: pd.DataFrame) -> dict:
    """Resume problemas estruturais antes do recorte do Corinthians."""
    ausentes = COLUNAS_OBRIGATORIAS - set(bruta.columns)
    if ausentes:
        raise ValueError('Colunas ausentes na Copa do Brasil: ' + ', '.join(sorted(ausentes)))

    colunas_nucleo = ['Date', 'Home', 'Away', 'Result', 'Stadium']
    placares_validos = bruta['Result'].astype(str).str.match(r'^\s*\d+\s*[Xx]\s*\d+\s*$')
    return {
        'linhas': int(len(bruta)),
        'temporada_inicial': int(bruta['season'].min()),
        'temporada_final': int(bruta['season'].max()),
        'ausentes_nucleo': int(bruta[colunas_nucleo].isna().any(axis=1).sum()),
        'duplicatas_codigo': int(bruta.duplicated(['season', 'game']).sum()),
        'duplicatas_partida': int(bruta.duplicated(['season', 'Date', 'Home', 'Away']).sum()),
        'placares_invalidos': int((~placares_validos).sum()),
        'mesma_equipe': int(bruta['Home'].eq(bruta['Away']).sum()),
    }


def normalizar_clube(valor):
    """Remove a UF e corrige variantes pontuais presentes na fonte."""
    correspondencia = re.match(r'^(.*?)\s*/\s*([A-Z]{2})$', str(valor).strip())
    if correspondencia:
        nome, uf = correspondencia.groups()
    else:
        nome, uf = str(valor), ''
    nome = nome.strip().rstrip('-').strip()

    aliases = {
        'America': 'América',
        'América F.c.': 'América',
        'Atletico Mineiro': 'Atlético Mineiro',
        'Atletico Goianiense': 'Atlético Goianiense',
        'Ceara': 'Ceará',
        'Gremio': 'Grêmio',
        'Gremio Novorizontino': 'Grêmio Novorizontino',
        'Leao do Vale - Cianorte': 'Cianorte',
        'Sao Bernardo': 'São Bernardo',
        'Sao Paulo': 'São Paulo',
    }
    nome = aliases.get(nome, nome)
    if nome in {'América', 'Atlético', 'Nacional'} and uf:
        return f'{nome}-{uf}'
    return nome


def fase_da_partida(temporada, codigo):
    """Deriva a fase pelas faixas de numeração oficial da CBF em cada formato."""
    temporada, codigo = int(temporada), int(codigo)
    if 2013 <= temporada <= 2015:
        limites = [80, 120, 142, 158, 166, 170, 172]
        fases = [
            '1ª fase', '2ª fase', '3ª fase', 'Oitavas de final',
            'Quartas de final', 'Semifinal', 'Final',
        ]
    elif temporada == 2016:
        limites = [80, 120, 140, 156, 164, 168, 170]
        fases = [
            '1ª fase', '2ª fase', '3ª fase', 'Oitavas de final',
            'Quartas de final', 'Semifinal', 'Final',
        ]
    elif 2017 <= temporada <= 2020:
        limites = [40, 60, 80, 90, 106, 114, 118, 120]
        fases = [
            '1ª fase', '2ª fase', '3ª fase', '4ª fase',
            'Oitavas de final', 'Quartas de final', 'Semifinal', 'Final',
        ]
    elif 2021 <= temporada <= 2025:
        limites = [40, 60, 92, 108, 116, 120, 122]
        fases = [
            '1ª fase', '2ª fase', '3ª fase', 'Oitavas de final',
            'Quartas de final', 'Semifinal', 'Final',
        ]
    else:
        raise ValueError(f'Temporada sem regra de fases: {temporada}')

    for limite, fase in zip(limites, fases):
        if codigo <= limite:
            return fase
    raise ValueError(f'Código {codigo} fora do formato da Copa do Brasil {temporada}.')


def _adicionar_instancia(partidas):
    """Marca ida/volta quando o confronto possui duas partidas na mesma fase."""
    partidas = partidas.sort_values('data').copy()
    grupo = partidas.groupby(['temporada', 'fase', 'adversario'])
    quantidade = grupo['ID'].transform('size')
    ordem = grupo.cumcount()
    partidas['instancia'] = 'Jogo único'
    partidas.loc[quantidade.eq(2) & ordem.eq(0), 'instancia'] = 'Ida'
    partidas.loc[quantidade.eq(2) & ordem.eq(1), 'instancia'] = 'Volta'
    return partidas


def _separar_estadio_cidade(valor):
    partes = str(valor).rsplit(' / ', 1)
    estadio = partes[0].strip()
    cidade = partes[1].strip() if len(partes) == 2 else pd.NA
    if estadio in {'', '- A Definir'}:
        estadio = pd.NA
    if cidade == '':
        cidade = pd.NA
    return estadio, cidade


def preparar_partidas_copa_brasil(bruta: pd.DataFrame) -> pd.DataFrame:
    """Filtra os jogos do Corinthians e padroniza o esquema do dashboard."""
    auditoria = auditar_fonte(bruta)
    problemas = {
        chave: auditoria[chave]
        for chave in (
            'ausentes_nucleo', 'duplicatas_codigo', 'duplicatas_partida',
            'placares_invalidos', 'mesma_equipe',
        )
        if auditoria[chave]
    }
    if problemas:
        raise ValueError(f'A fonte possui inconsistências estruturais: {problemas}')

    partidas = bruta[
        bruta['Home'].eq(TIME_CORINTHIANS)
        | bruta['Away'].eq(TIME_CORINTHIANS)
    ].copy()
    if partidas.empty:
        raise ValueError('A base não contém partidas do Corinthians.')

    mandante = partidas['Home'].eq(TIME_CORINTHIANS)
    placar = partidas['Result'].str.extract(r'(\d+)\s*[Xx]\s*(\d+)').astype(int)
    partidas['data'] = pd.to_datetime(partidas['Date'], format='%d/%m/%Y', errors='raise')
    partidas['temporada'] = partidas['season'].astype(int)
    partidas['adversario'] = partidas['Away'].where(mandante, partidas['Home']).map(normalizar_clube)
    partidas['local'] = mandante.map({True: 'Mandante', False: 'Visitante'})
    partidas['gols_marcados'] = placar[0].where(mandante, placar[1]).astype(int)
    partidas['gols_sofridos'] = placar[1].where(mandante, placar[0]).astype(int)
    partidas['saldo_gols'] = partidas['gols_marcados'] - partidas['gols_sofridos']
    partidas['resultado'] = partidas['saldo_gols'].map(
        lambda saldo: 'Vitoria' if saldo > 0 else ('Derrota' if saldo < 0 else 'Empate')
    )
    partidas['pontos'] = partidas['resultado'].map({'Vitoria': 3, 'Empate': 1, 'Derrota': 0})
    partidas['competicao'] = 'Copa do Brasil'
    partidas['fase'] = partidas.apply(
        lambda linha: fase_da_partida(linha['temporada'], linha['game']), axis=1,
    )

    estadio_cidade = partidas['Stadium'].map(_separar_estadio_cidade)
    partidas['arena'] = estadio_cidade.map(lambda item: item[0])
    partidas['cidade_sede'] = estadio_cidade.map(lambda item: item[1])
    partidas.loc[mandante & partidas['temporada'].ge(2014), 'arena'] = 'Neo Química Arena'
    partidas.loc[mandante & partidas['temporada'].ge(2014), 'cidade_sede'] = 'São Paulo'
    partidas['pais_sede'] = 'Brasil'
    partidas['penales'] = pd.NA
    partidas['fonte_url'] = partidas.get('source_url', URL_BASE)
    partidas['ID'] = partidas.apply(
        lambda linha: f"CDB-{int(linha['temporada'])}-{str(linha['game']).zfill(3)}",
        axis=1,
    )
    partidas = _adicionar_instancia(partidas)

    colunas = [
        'ID', 'competicao', 'temporada', 'data', 'fase', 'instancia',
        'adversario', 'local', 'arena', 'pais_sede', 'cidade_sede',
        'gols_marcados', 'gols_sofridos', 'saldo_gols', 'resultado',
        'pontos', 'penales', 'fonte_url',
    ]
    resultado = partidas[colunas].sort_values(['data', 'ID']).reset_index(drop=True)
    if resultado['ID'].duplicated().any():
        raise ValueError('Foram gerados identificadores duplicados.')
    return resultado


def main():
    parser = ArgumentParser()
    parser.add_argument('entrada', type=Path, help='Pasta com CdB_AAAA_games.json')
    parser.add_argument('saida_bruta', type=Path, help='CSV consolidado da fonte')
    parser.add_argument('saida_tratada', type=Path, help='CSV tratado para o dashboard')
    argumentos = parser.parse_args()

    bruta = carregar_jsons_fonte(argumentos.entrada)
    tratada = preparar_partidas_copa_brasil(bruta)
    argumentos.saida_bruta.parent.mkdir(parents=True, exist_ok=True)
    argumentos.saida_tratada.parent.mkdir(parents=True, exist_ok=True)
    bruta.to_csv(argumentos.saida_bruta, index=False, encoding='utf-8-sig')
    tratada.to_csv(argumentos.saida_tratada, index=False, encoding='utf-8-sig')
    print(
        f'{len(bruta)} partidas da fonte consolidadas; '
        f'{len(tratada)} jogos do Corinthians salvos em {argumentos.saida_tratada}'
    )


if __name__ == '__main__':
    main()
