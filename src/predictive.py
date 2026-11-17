"""Interface do experimento histórico, independente dos filtros da visão geral."""

from pathlib import Path

import pandas as pd
import streamlit as st

from components import cabecalho_secao, card_metrica, formatar_numero


@st.cache_resource(show_spinner=False)
def _carregar_experimento(caminho, modificacao_ns, tamanho, versao):
    # A assinatura do arquivo e a versão invalidam o treino em cache.
    from src.ml import treinar_experimento
    return treinar_experimento(pd.read_csv(caminho))


def _exibir_partida(jogos, experimento):
    cabecalho_secao('Antes de a bola rolar', 'Explore probabilidades de partidas que ficaram fora do treino.')
    col_adv, col_local = st.columns(2)
    with col_adv:
        adversario = st.selectbox(
            'Adversário no teste', ['Todos'] + sorted(jogos['adversario'].unique()),
            key='ml_adversario',
        )
    with col_local:
        local = st.selectbox('Local no teste', ['Todos', 'Mandante', 'Visitante'], key='ml_local')
    opcoes = jogos.copy()
    if adversario != 'Todos':
        opcoes = opcoes[opcoes['adversario'] == adversario]
    if local != 'Todos':
        opcoes = opcoes[opcoes['local'] == local]
    if opcoes.empty:
        st.info('Não há partidas no período de teste para essa combinação.')
        return

    rotulos = {
        int(linha.ID): f'{linha.data:%d/%m/%Y} · Corinthians × {linha.adversario} · {linha.local}'
        for linha in opcoes.itertuples()
    }
    # Trocas de adversário/local não podem deixar um ID fora das novas opções.
    if st.session_state.get('ml_partida') not in rotulos:
        st.session_state['ml_partida'] = next(iter(rotulos))
    partida_id = st.selectbox('Partida histórica', list(rotulos), format_func=rotulos.get, key='ml_partida')
    partida = opcoes.loc[opcoes['ID'].eq(partida_id)].iloc[0]
    st.caption('Probabilidades na perspectiva do Corinthians. Este é um teste retrospectivo, não uma previsão ao vivo.')
    for coluna, (titulo, chave, variante) in zip(st.columns(3), [
        ('Vitória', 'prob_vitoria', 'vitoria'),
        ('Empate', 'prob_empate', 'padrao'),
        ('Derrota', 'prob_derrota', 'derrota'),
    ]):
        with coluna:
            card_metrica(titulo, f'{formatar_numero(partida[chave] * 100, 1)}%', 'Probabilidade estimada', variante)
    st.caption('Os percentuais podem somar 99,9% ou 100,1% por arredondamento. Probabilidade não é garantia de resultado.')

    lado = 'mandante' if partida['local'] == 'Mandante' else 'visitante'
    outro = 'visitante' if lado == 'mandante' else 'mandante'
    contexto = [
        ('Pontos por jogo · últimos 5', 'pontos_5', 2),
        ('Gols marcados por jogo · últimos 10', 'gols_marcados_10', 2),
        ('Gols sofridos por jogo · últimos 10', 'gols_sofridos_10', 2),
        ('Partidas disponíveis no histórico recente', 'jogos_10', 0),
        ('Dias desde o último jogo na base · limite 120', 'dias_desde_ultimo', 0),
    ]
    with st.expander('Informações disponíveis antes da partida'):
        st.dataframe(pd.DataFrame([
            {
                'Indicador': titulo,
                'Corinthians': formatar_numero(partida[f'{lado}_{medida}'], casas),
                str(partida['adversario']): formatar_numero(partida[f'{outro}_{medida}'], casas),
            }
            for titulo, medida, casas in contexto
        ]), hide_index=True, width='stretch')
        st.caption('São considerados até 10 jogos anteriores na Série A, dentro dos últimos 365 dias. Se houver menos jogos, a média usa os disponíveis. Outras competições não entram.')
    if min(partida['mandante_jogos_10'], partida['visitante_jogos_10']) < 5:
        st.caption('Histórico recente limitado: pelo menos um clube tem menos de cinco partidas anteriores disponíveis.')
    clubes_treino = set(experimento.treino['mandante']) | set(experimento.treino['visitante'])
    if partida['adversario'] not in clubes_treino:
        st.caption('Este adversário não apareceu no treino. Sua identidade não tem um peso aprendido; a estimativa usa os demais atributos disponíveis.')

    with st.expander('Conferir resultado observado'):
        st.markdown(
            f"**Corinthians {int(partida['gols_marcados'])} × {int(partida['gols_sofridos'])} "
            f"{partida['adversario']}** — {partida['resultado']}."
        )
        st.caption('Esse placar é mostrado para comparação e não foi usado para prever esta partida.')


def _exibir_avaliacao(experimento):
    from src.ml import COLUNAS_PROB, avaliar_previsoes

    cabecalho_secao('O modelo acrescenta valor?', 'Comparação com uma referência simples no mesmo conjunto de teste.')
    escopo = st.radio('Recorte de avaliação', ['Todos os clubes', 'Somente Corinthians'], horizontal=True, key='ml_avaliacao')
    teste = experimento.teste
    if escopo == 'Somente Corinthians':
        teste = teste[teste['mandante'].eq('Corinthians') | teste['visitante'].eq('Corinthians')]
    if teste.empty:
        st.info('Não há partidas para avaliar nesse recorte.')
        return

    modelo = avaliar_previsoes(teste)
    base = avaliar_previsoes(teste, referencia=True)
    st.caption(f'{formatar_numero(len(teste))} partidas entre {teste.data.min():%d/%m/%Y} e {teste.data.max():%d/%m/%Y}. Esta avaliação usa todo o recorte acima, independentemente da partida selecionada.')
    comparacao = pd.DataFrame([
        {
            'Modelo': nome,
            'Acerto ↑': f"{formatar_numero(valores['acuracia'] * 100, 2)}%",
            'Log loss ↓': formatar_numero(valores['log_loss'], 4),
            'Brier ↓': formatar_numero(valores['brier'], 4),
        }
        for nome, valores in [('Regressão logística', modelo), ('Referência: frequências do treino', base)]
    ])
    st.dataframe(comparacao, width='stretch', hide_index=True)
    ganho = (base['log_loss'] - modelo['log_loss']) / base['log_loss'] * 100
    if ganho > 0:
        st.info(f'O modelo reduziu o log loss em {formatar_numero(ganho, 2)}% neste teste. Essa diferença é descritiva e não comprova vantagem em jogos futuros.')
    else:
        st.warning('Neste recorte, o modelo não superou a referência em log loss. As previsões devem ser tratadas como experimentais.')
    st.caption('Acerto: o resultado mais provável ocorreu? Log loss e Brier: menor é melhor para avaliar as probabilidades. Brier multiclasse usa a soma dos erros quadráticos, de 0 a 2.')

    with st.expander('Desempenho por ano e tipos de erro'):
        linhas = []
        for ano, grupo in teste.groupby(teste['data'].dt.year):
            a, b = avaliar_previsoes(grupo), avaliar_previsoes(grupo, referencia=True)
            linhas.append({
                'Ano': str(ano), 'Jogos': len(grupo),
                'Acerto do modelo': f"{formatar_numero(a['acuracia'] * 100, 2)}%",
                'Acerto da referência': f"{formatar_numero(b['acuracia'] * 100, 2)}%",
                'Log loss do modelo': formatar_numero(a['log_loss'], 4),
                'Log loss da referência': formatar_numero(b['log_loss'], 4),
            })
        st.dataframe(pd.DataFrame(linhas), hide_index=True, width='stretch')
        previsto = teste[COLUNAS_PROB].to_numpy().argmax(axis=1)
        matriz = pd.crosstab(
            teste['alvo'].to_numpy(), previsto,
            rownames=['Resultado observado'], colnames=['Resultado previsto'],
        ).reindex(index=[0, 1, 2], columns=[0, 1, 2], fill_value=0)
        nomes = {0: 'Vitória do mandante', 1: 'Empate', 2: 'Vitória do visitante'}
        st.dataframe(matriz.rename(index=nomes, columns=nomes), width='stretch')
        st.caption('Linhas: o que aconteceu. Colunas: o resultado mais provável. Aqui os rótulos seguem mandante e visitante, inclusive no recorte do Corinthians.')


def exibir_analise_preditiva(caminho):
    cabecalho_secao('Análise preditiva', 'Experimento histórico · Campeonato Brasileiro — Série A')
    st.caption('Esta aba tem controles próprios. Os filtros da barra lateral afetam somente a Visão geral.')
    try:
        from src.ml import VERSAO_MODELO, previsoes_corinthians

        caminho = Path(caminho)
        assinatura = caminho.stat()
        with st.spinner('Preparando o histórico e treinando o modelo…'):
            experimento = _carregar_experimento(
                str(caminho), assinatura.st_mtime_ns, assinatura.st_size, VERSAO_MODELO,
            )
    except ImportError:
        st.error('As bibliotecas de machine learning não estão disponíveis neste ambiente. Instale as dependências do projeto e reinicie o dashboard.')
        st.code('python -m pip install -r requirements.txt', language='bash')
        return
    except (FileNotFoundError, ValueError) as erro:
        st.error(f'Não foi possível preparar a análise preditiva: {erro}')
        return

    treino, teste = experimento.treino, experimento.teste
    st.info(
        f'Treino: {treino.data.min():%d/%m/%Y} a {treino.data.max():%d/%m/%Y} '
        f'({formatar_numero(len(treino))} jogos). Teste: '
        f'{teste.data.min():%d/%m/%Y} a {teste.data.max():%d/%m/%Y} '
        f'({formatar_numero(len(teste))} jogos). O modelo fica fixo durante o teste.'
    )
    jogos = previsoes_corinthians(teste)
    with st.container(border=True):
        if jogos.empty:
            st.info('O conjunto de teste não contém partidas do Corinthians.')
        else:
            _exibir_partida(jogos, experimento)
    with st.container(border=True):
        _exibir_avaliacao(experimento)

    if not jogos.empty:
        colunas = ['ID', 'data', 'adversario', 'local', 'prob_vitoria', 'prob_empate', 'prob_derrota', 'resultado']
        exportacao = jogos[colunas].copy()
        exportacao['modelo'] = f'Regressão logística v{VERSAO_MODELO}'
        exportacao['fim_treino'] = treino.data.max().strftime('%Y-%m-%d')
        st.download_button(
            'Baixar previsões históricas do Corinthians',
            data=exportacao.to_csv(index=False).encode('utf-8-sig'),
            file_name='corinthians_previsoes_teste_2023_2025.csv', mime='text/csv',
            on_click='ignore', key='ml_download',
        )
        st.caption('O download inclui todas as partidas do Corinthians no teste. Probabilidades no CSV vão de 0 a 1.')

    with st.expander('Como o experimento funciona e quais são seus limites'):
        st.markdown(
            '- **Modelo:** regressão logística multinomial com regularização L2, C=1. '
            'Clubes são codificados por identidade e variáveis numéricas são padronizadas apenas com o treino.\n'
            '- **Informações pré-jogo:** mando, identidade dos clubes, pontos recentes, médias de gols, '
            'frequência de vitórias, quantidade de jogos disponíveis e intervalo desde o último jogo na base.\n'
            '- **Separação temporal:** treino anterior a 2023; teste entre 2023 e 2025. '
            'Nenhum placar do dia da partida ou de datas futuras entra nos seus atributos. '
            'Durante o teste, o histórico recebe apenas resultados dos dias anteriores; os pesos do modelo não mudam.\n'
            '- **Referência:** probabilidades constantes dos três resultados, calculadas somente no treino. '
            'Como os resultados são relativos ao mandante, a referência já incorpora a frequência histórica do mando.\n'
            '- **Histórico curto:** médias usam até 5 ou 10 jogos anteriores, limitados a 365 dias. '
            'Sem histórico, as médias recebem zero e a quantidade de jogos informa essa ausência; '
            'o intervalo recebe 120 dias. Nomes de clubes seguem a fonte.\n'
            '- **Limites:** não há escalações, lesões, odds ou jogos de outras competições. '
            'A base termina em 2025; as probabilidades não foram calibradas separadamente '
            'e não houve ajuste de parâmetros com o conjunto de teste. '
            'Este é um primeiro experimento, sem comprovação de superioridade estatística.'
        )
