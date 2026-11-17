from unittest.mock import patch

from components import cabecalho_dashboard


def test_cabecalho_dashboard_exibe_cobertura_completa():
    with (
        patch('components._fonte_escudo', return_value='data:image/png;base64,escudo'),
        patch('components.st.markdown') as markdown,
    ):
        cabecalho_dashboard(
            '2003–2025',
            23,
            857,
            '07/12/2025',
            'Brasileirão — Série A',
        )

    html = markdown.call_args.args[0]
    assert '23 temporadas na base' in html
    assert '857 partidas no acervo' in html
    assert 'Última partida: 07/12/2025' in html
