"""Imports"""
import pytest
import pandas as pd
import folium
from dashboard_sinalizacoes import (
    classificar_condicao,
    limpar_string,
    classificar_condicoes,
    adicionar_pontos_mapa_verticais,
    gerar_grafico_pizza
)


@pytest.mark.parametrize("condicao, expected", [
    ("BOA", "Boa"),
    ("RUIM", "Ruim"),
    ("REGULAR", "Regular"),
    ("CONDIÇÃO INDETERMINADA", "Indeterminada"),
    ("EM BOAS CONDIÇÕES", "Boa"),
    ("AMASSADA", "Ruim"),
    ("CONDIÇÃO NORMAL", "Indeterminada")
])
def test_classificar_condicao(condicao, expected):
    """Testa a função que classifica as condições de sinalização."""
    assert classificar_condicao(condicao) == expected


@pytest.mark.parametrize("texto, expected", [
    ("Texto Com Caracteres Especiais!", "TEXTOCOMCARACTERESESPECIAIS"),
    ("Texto com 123", "TEXTOCOM123"),
    ("CARRO", "CARRO"),
    ("Espaços   Extras", "ESPAOSEXTRAS")
])
def test_limpar_string(texto, expected):
    """Testa a função que limpa strings, removendo espaços e caracteres especiais."""
    assert limpar_string(texto) == expected


def test_classificar_condicoes():
    """Testa a função de aplicar a classificação de condições a um DataFrame."""
    data = {
        'condicoes': ["BOA", "RUIM", "REGULAR", "INDETERMINADA"],
        'outra_coluna': [1, 2, 3, 4]
    }
    data_frame = pd.DataFrame(data)

    resultado = classificar_condicoes(data_frame, 'condicoes')

    assert resultado['classificacao'].tolist() == ["Boa", "Ruim", "Regular", "Indeterminada"]


# Para os gráficos e mapas, faremos testes focados na lógica
def test_gerar_grafico_pizza():
    """Testa a função que gera o gráfico de pizza."""
    data_frame = pd.DataFrame({
        'classificacao': ['Boa', 'Ruim', 'Boa', 'Regular', 'Indeterminada']
    })
    fig = gerar_grafico_pizza(data_frame, "Vertical")

    # Verifica se o gráfico foi criado com as categorias corretas
    assert set(fig.data[0]['labels']) == {'Boa', 'Ruim', 'Regular', 'Indeterminada'}


def test_adicionar_pontos_mapa_verticais():
    """Testa a função de adicionar pontos ao mapa para sinalizações verticais."""
    data_frame = pd.DataFrame({
        'latitude': [-15.77972, -15.78000],
        'longitude': [-47.92972, -47.93000],
        'classificacao': ['Boa', 'Ruim'],
        'sre': ['001', '002'],
        'data': ['2023-10-01', '2023-10-02'],
        'pista': ['A', 'B'],
        'tipo': ['Placa', 'Sinal'],
        'material': ['Metal', 'Madeira'],
        'categoria_sinal': ['Categoria 1', 'Categoria 2'],
        'condicoes': ['BOA', 'RUIM']
    })
    mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)

    # Adiciona os pontos ao mapa
    mapa = adicionar_pontos_mapa_verticais(data_frame, mapa)

    assert isinstance(mapa, folium.Map), "A função não retornou um objeto folium.Map"
