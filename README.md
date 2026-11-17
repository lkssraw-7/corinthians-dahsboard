# Corinthians em Dados

Dashboard em Streamlit com histórico do Corinthians na Série A, na Copa
Libertadores e na Copa do Brasil, análises visuais de gols e disciplina e um experimento de
probabilidades pré-jogo. Dados do Brasileirão disponíveis até 07/12/2025; o
recorte importado da Libertadores cobre as edições presentes entre 1996 e 2023.
O recorte da Copa do Brasil usa os arquivos do projeto BrazilianFootball/Data de
2013 a 2025.

## Executar

Na pasta do projeto, com o ambiente desejado ativado (versão testada: Python 3.9):

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Publicar no Streamlit Community Cloud

Ao criar o aplicativo, abra **Advanced settings** e selecione **Python 3.12**.
As versões fixadas em `requirements.txt` foram validadas nesse runtime. Evite
Python 3.14 com essas dependências, pois `numpy==2.0.2` e
`scikit-learn==1.6.1` podem ser compilados a partir do código-fonte em vez de
usar pacotes binários, tornando o deploy lento ou fazendo a instalação falhar.

Use `main` como branch e `app.py` como arquivo de entrada.

## Organização

- `app.py`: filtros, navegação entre abas e visão geral.
- `components.py`, `style.css`, `.streamlit/config.toml`: componentes e tema.
- `assets/corinthians_escudo.png`: imagem fornecida para o projeto.
- `src/data.py`, `src/metrics.py`, `src/charts.py`: dados, indicadores e gráficos.
- `src/events.py`, `src/event_views.py`: filtros, indicadores e interface das
  análises de gols e cartões.
- `src/competition_views.py`: histórico por fase e campanhas das copas.
- `scripts/preparar_libertadores.py`: transforma a fonte usada no notebook no
  formato comum do dashboard.
- `scripts/preparar_copa_brasil.py`: consolida, audita e transforma os JSONs da
  Copa do Brasil.
- `copa_brasil.ipynb`: análise reproduzível da qualidade e do desempenho por
  temporada, adversário, fase e mando.
- `src/ml.py`: validação, atributos pré-jogo, treino e avaliação.
- `src/predictive.py`: interface da análise preditiva e cache do experimento.
- `tests/test_ml.py`: verificações de vazamento temporal e probabilidades.
- `tests/test_events.py`: verificações dos filtros, indicadores e gráficos de eventos.
- `tests/test_competitions.py`: totais, esquema e campanhas das competições.
- `dados/campeonato-brasileiro-full.csv`: cópia da base original de todos os clubes.
- `dados/partidas_libertadores.csv`: 112 partidas tratadas a partir da fonte usada
  em `libertadores.ipynb`.
- `dados/brutos/copa_brasil_partidas.csv`: consolidação local dos campos de partida
  dos JSONs públicos de 2013–2025.
- `dados/partidas_copa_brasil.csv`: 84 partidas tratadas do Corinthians entre
  2013 e 2025.

## Competições

O seletor **Campeonato / copa** na barra lateral alterna todo o recorte da visão
geral. Libertadores e Copa do Brasil também possuem a aba **Campanhas**, com
desempenho por fase e resumo de cada edição. Gols por jogador, cartões e análise
preditiva aparecem somente no Brasileirão, pois as fontes das copas foram
integradas no nível de partida.

## Experimento de machine learning — versão 1.0

A aba **Análise preditiva** permite selecionar adversário, mando e uma partida
histórica do Corinthians. As probabilidades sempre seguem a perspectiva do clube.
Os filtros laterais afetam apenas a **Visão geral**. Os filtros da partida histórica
não alteram o conjunto de treino nem o recorte escolhido no painel de avaliação.

O modelo é uma regressão logística multinomial, com regularização L2, C=1,
solver `lbfgs` e máximo de 1.000 iterações. A identidade dos clubes usa one-hot
encoding; os atributos numéricos usam StandardScaler. Ambos são ajustados
exclusivamente no treino. Não há ajuste de hiperparâmetros nem calibração usando
o teste.

Separação fixa, por data real da partida (não por rótulo de temporada):

| Etapa | Datas disponíveis | Jogos |
| --- | --- | ---: |
| Treino | 29/03/2003 a 13/11/2022 | 8.025 |
| Teste | 15/04/2023 a 07/12/2025 | 1.140 |
| Corinthians dentro do teste | 2023–2025 | 114 |

Resultados da primeira execução, com a base fornecida:

| Recorte | Acerto do modelo | Acerto da referência | Log loss do modelo | Log loss da referência |
| --- | ---: | ---: | ---: | ---: |
| Todos os clubes | 48,42% | 48,16% | 1,0392 | 1,0529 |
| Corinthians | 47,37% | 47,37% | 1,0473 | 1,0528 |

O ganho é pequeno e não constitui evidência de vantagem em previsões futuras.
A interface recalcula essas métricas a partir da base local do experimento.

Os atributos de cada equipe usam apenas partidas de dias anteriores: pontos por
jogo nos últimos 5; gols marcados, sofridos e frequência de vitórias nos últimos
10; número de partidas disponíveis; dias desde o último jogo registrado, limitado
a 120. O histórico é limitado também a 365 dias, para não tratar campanhas muito
antigas como forma recente. Sem histórico, médias e contagens recebem zero e
o intervalo recebe 120; a contagem distingue ausência de um desempenho zerado.

Todas as partidas de um dia têm seus atributos calculados antes da incorporação
dos placares desse dia. Durante o teste, resultados de dias anteriores alimentam
o histórico, mas o modelo permanece fixo. Os placares da própria partida, técnico,
formação, posse, chutes e demais estatísticas posteriores não são entradas.

A referência retorna as frequências dos resultados no treino, na perspectiva do
mandante. As métricas são acurácia (maior é melhor), log loss e Brier multiclasse
(menor é melhor). O Brier usa a soma dos erros quadráticos nas três classes e
varia de 0 a 2. Uma diferença numérica no teste não comprova superioridade
estatística. A interface mostra também resultados por ano e uma matriz de erros.

Limitações: nomes dos clubes seguem a fonte; não há informação de escalações,
lesões, odds ou outras competições. Probabilidades não foram calibradas
separadamente. A base original pode ter lacunas e não é atualizada em tempo real.
O ano de 2008 do Corinthians na Série B não integra esse recorte da Série A.
Esta versão não oferece previsões de partidas atuais ou futuras.

O treino roda localmente e fica em memória via cache do Streamlit, sem carregar
arquivos pickle externos. O cache considera caminho, data de modificação, tamanho
da base e versão do experimento. Alterações no método devem incrementar
`VERSAO_MODELO`. O corte de teste continua fixo mesmo se a base ganhar jogos de
2026; uma nova janela deve ser definida explicitamente como outro experimento.

Referências técnicas: [regressão logística](https://scikit-learn.org/1.6/modules/generated/sklearn.linear_model.LogisticRegression.html),
[prevenção de vazamento de dados](https://scikit-learn.org/1.6/common_pitfalls.html) e
[log loss](https://scikit-learn.org/1.6/modules/generated/sklearn.metrics.log_loss.html).

## Verificar

```bash
python -m pytest -q
```

Os testes verificam a exclusão de resultados futuros e do mesmo dia, a
independência do treino em relação aos placares do teste, o pré-processamento,
a expiração do histórico e a conversão entre mando e perspectiva do Corinthians.
