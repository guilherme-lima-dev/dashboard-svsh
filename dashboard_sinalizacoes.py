"""Bibliotecas necessárias para o dashboard de sinalizações."""
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# URL base para as imagens
URL_BASE_IMAGENS = "https://sgpgoinfra.com.br/imagensInventario/"

# Colocar set_page_config como o primeiro comando do script
st.set_page_config(page_title="Dashboard de Sinalizações", layout="wide")


# Carregar os dados de Sinalização Vertical e Horizontal
@st.cache_data
def carregar_dados_vertical():
    """Carregar dados de sinalizações verticais."""
    return pd.read_csv("sinalizacao_vertical.csv", sep=";")


@st.cache_data
def carregar_dados_horizontal():
    """Carregar dados de sinalizações horizontais."""
    return pd.read_csv("sinalizacao_horizontal.csv", sep=";")


# Função para limpar strings removendo espaços e caracteres especiais (para agrupar)
def limpar_string(texto):
    """Normalizar as strings, removendo caracteres especiais."""
    return re.sub(r'[^A-Za-z0-9]', '', texto.upper())


# Função para classificar condição como positiva ou negativa
def classificar_condicao(condicao):
    """
    Classificar as condições de uma sinalização como 'Boa', 'Ruim', 'Regular' ou 'Indeterminada'.
    A classificação é baseada em palavras-chave encontradas na descrição da condição.
    """
    condicao = condicao.upper()
    positivas = ["BOAS", "BOA", "BOM", "SIMPLES", "BOAS CONDIÇÕES", "EM BOAS CONDIÇÕES"]
    negativas = ["RUIM", "PÉSSIMO", "INADEQUADO", "QUEBRADA", "AMASSADA", "QUEIMADA"]
    regulares = ["REGULAR"]

    if any(palavra in condicao for palavra in positivas):
        return "Boa"
    if any(palavra in condicao for palavra in negativas):
        return "Ruim"
    if any(palavra in condicao for palavra in regulares):
        return "Regular"
    return "Indeterminada"


# Aplicar a classificação de condição nas colunas de condições e condicao
def classificar_condicoes(data_frame, coluna_condicao):
    """Aplicar a classificação de condição para uma coluna específica em um dataframe."""
    data_frame['classificacao'] = data_frame[coluna_condicao].apply(classificar_condicao)
    return data_frame


# Função para gerar o gráfico de pizza com base nas condições e cores fixas
def gerar_grafico_pizza(data_frame, tipo_sinalizacao):
    """Gerar um gráfico de pizza para as condições das sinalizações."""
    cores = {
        "Boa": "green",
        "Ruim": "red",
        "Regular": "#faa702",
        "Indeterminada": "gray"
    }
    fig = px.pie(
        data_frame,
        names='classificacao',
        title=f"Condições das Sinalizações ({tipo_sinalizacao})",
        color='classificacao',
        color_discrete_map=cores
    )
    return fig


# Função para gerar gráfico de barras com a contagem de tipos
def gerar_grafico_barras_tipos(data_frame, coluna, titulo):
    """Gerar um gráfico de barras para a distribuição de tipos."""
    data_frame['coluna_normalizada'] = data_frame[coluna].apply(limpar_string)
    contagem = data_frame['coluna_normalizada'].value_counts().reset_index()
    contagem.columns = [coluna, 'Quantidade']
    fig = px.bar(contagem, x=coluna, y='Quantidade', title=titulo)
    return fig


def adicionar_pontos_mapa_verticais(data_frame, mapa_vertical):
    """Adicionar pontos de sinalizações verticais no mapa com cores representando as condições."""
    for _, row in data_frame.iterrows():
        color = ("green" if row['classificacao'] == "Boa"
                 else "red" if row['classificacao'] == "Ruim"
                 else "#faa702" if row['classificacao'] == "Regular"
                 else "gray")
        popup_content = f"""
        <strong>Sinalização Vertical</strong><br>
        SRE: {row['sre']}<br>
        Data: {row['data']}<br>
        Pista: {row['pista']}<br>
        Tipo: {row['tipo'].upper()}<br>
        Material: {row['material']}<br>
        Categoria: {row['categoria_sinal']}<br>
        Condição: {row['condicoes']}
        """
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            popup=popup_content
        ).add_to(mapa_vertical)
    return mapa_vertical


# Função para gerar o mapa de sinalizações horizontais com linhas coloridas
def adicionar_pontos_mapa_horizontais(data_frame, mapa_horizontal):
    """Adicionar trechos de sinalizações horizontais no mapa."""
    for _, row in data_frame.iterrows():
        color = ("green" if row['classificacao'] == "Boa"
                 else "red" if row['classificacao'] == "Ruim"
                 else "#faa702" if row['classificacao'] == "Regular"
                 else "gray")
        coordinates = [
            [row['latitude_inicial'], row['longitude_inicial']],
            [row['latitude_final'], row['longitude_final']]
        ]
        popup_content = f"""
        <strong>Sinalização Horizontal</strong><br>
        SRE: {row['sre']}<br>
        Data: {row['data']}<br>
        Pista: {row['pista']}<br>
        Tipo: {row['tipo'].upper()}<br>
        Material: {row['material']}<br>
        Condição: {row['condicao']}
        """
        folium.PolyLine(
            locations=coordinates,
            color=color,
            weight=5,
            popup=popup_content
        ).add_to(mapa_horizontal)
    return mapa_horizontal


# Função para gerar ranking das rodovias
def gerar_ranking_rodovias(data_frame):
    """Gerar ranking das 10 melhores e piores rodovias com base nas sinalizações boas e ruins."""
    # Contagem de sinalizações boas e ruins por rodovia
    ranking_boas = (data_frame[data_frame['classificacao'] == 'Boa'].
                    groupby('rodovia').size().reset_index(name='boas'))
    ranking_ruins = (data_frame[data_frame['classificacao'] == 'Ruim'].
                     groupby('rodovia').size().reset_index(name='ruins'))

    # Juntar os dois rankings
    ranking_rodovias = pd.merge(ranking_boas, ranking_ruins, on='rodovia', how='outer').fillna(0)

    # Ordenar pelas 10 melhores (mais sinalizações boas)
    melhores_rodovias_sort = ranking_rodovias.sort_values(by='boas', ascending=False).head(10)

    # Ordenar pelas 10 piores (mais sinalizações ruins)
    piores_rodovias_sort = ranking_rodovias.sort_values(by='ruins', ascending=False).head(10)

    return melhores_rodovias_sort, piores_rodovias_sort


# Carregar dados
dados_vertical = carregar_dados_vertical()
dados_horizontal = carregar_dados_horizontal()

# Configuração inicial do Streamlit
st.title("Dashboard de Sinalizações Verticais e Horizontais")

# Layout de navegação
opcao_dashboard = st.sidebar.radio(
    "Escolha o tipo de sinalização",
    ["Sinalização Vertical", "Sinalização Horizontal"]
)

if opcao_dashboard == "Sinalização Vertical":
    st.header("Sinalização Vertical")

    # Classificar condições
    dados_vertical_classificado = classificar_condicoes(dados_vertical, 'condicoes')

    # Filtros
    dados_vertical_classificado['tipo'] = dados_vertical_classificado['tipo'].str.upper()
    dados_vertical_classificado['pista'] = dados_vertical_classificado['pista'].str.upper()
    dados_vertical_classificado['rodovia'] = dados_vertical_classificado['sre'].str[:3].str.upper()
    dados_vertical_classificado['sre'] = dados_vertical_classificado['sre'].str.upper()

    col1, col2, col3, col4, col5 = st.columns(5)

    rodovia_filtro = col1.selectbox(
        "Rodovia",
        ["Todos"] + sorted(dados_vertical_classificado['rodovia'].unique())
    )
    sre_filtro = col2.selectbox(
        "SRE",
        ["Todos"] + sorted(dados_vertical_classificado['sre'].unique())
    )
    pista_filtro = col3.selectbox(
        "Pista",
        ["Todos"] + sorted(dados_vertical_classificado['pista'].unique())
    )
    situacao_filtro = col4.selectbox(
        "Situação",
        ["Todos", "Boa", "Ruim", "Regular", "Indeterminada"]
    )

    data_min = pd.to_datetime(dados_vertical_classificado['data']).min()
    data_max = pd.to_datetime(dados_vertical_classificado['data']).max()
    data_filtro = col5.date_input("Filtrar por intervalo de data", [data_min, data_max])

    dados_filtrados = dados_vertical_classificado
    if rodovia_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['rodovia'] == rodovia_filtro]
    if sre_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['sre'] == sre_filtro]
    if pista_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['pista'] == pista_filtro]
    if situacao_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['classificacao'] == situacao_filtro]
    dados_filtrados = dados_filtrados[
        (pd.to_datetime(dados_filtrados['data']) >= pd.to_datetime(data_filtro[0])) &
        (pd.to_datetime(dados_filtrados['data']) <= pd.to_datetime(data_filtro[1]))
        ]

    col1, col2 = st.columns([2, 2])  # Ajustar a proporção entre colunas para 3:1

    with col1:
        fig_pizza = gerar_grafico_pizza(dados_filtrados, "Vertical")
        st.plotly_chart(fig_pizza)

    with col2:
        total_sinalizacoes = len(dados_filtrados)
        st.markdown(
            f"""
            <div style="text-align: center; font-size: 24px; padding: 6em; width:100%;">
                <strong>Total de Sinalizações</strong><br>
                <span style="font-size: 40px;">{total_sinalizacoes}</span>
            </div>
            """, unsafe_allow_html=True
        )
    colBar1, colBar2 = st.columns(2)
    fig_barras_tipos = gerar_grafico_barras_tipos(
        dados_filtrados,
        'tipo',
        "Distribuição por Tipo"
    )
    colBar1.plotly_chart(fig_barras_tipos)

    fig_barras_categorias = gerar_grafico_barras_tipos(
        dados_filtrados,
        'categoria_sinal',
        "Distribuição por Categoria"
    )
    colBar2.plotly_chart(fig_barras_categorias)

    if rodovia_filtro != "Todos":
        # Mapa sem cluster, com círculos coloridos
        st.subheader("Mapa de Sinalizações Verticais")
        mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)
        mapa = adicionar_pontos_mapa_verticais(dados_filtrados, mapa)
        st_folium(mapa, width=None, height=500)

    # Ranking das rodovias
    st.subheader("Ranking das Rodovias")
    melhores_rodovias, piores_rodovias = gerar_ranking_rodovias(dados_filtrados)

    col1, col2 = st.columns(2)

    with col1:
        st.write("10 Melhores Rodovias")
        st.dataframe(melhores_rodovias)

    with col2:
        st.write("10 Piores Rodovias")
        st.dataframe(piores_rodovias)

elif opcao_dashboard == "Sinalização Horizontal":
    st.header("Sinalização Horizontal")

    dados_horizontal_classificado = classificar_condicoes(dados_horizontal, 'condicao')

    dados_horizontal_classificado['tipo'] = dados_horizontal_classificado['tipo'].str.upper()
    dados_horizontal_classificado['pista'] = dados_horizontal_classificado['pista'].str.upper()
    dados_horizontal_classificado['rodovia'] = (
        dados_horizontal_classificado['sre'].str[:3].str.upper()
    )
    dados_horizontal_classificado['sre'] = dados_horizontal_classificado['sre'].str.upper()

    col1, col2, col3, col4, col5 = st.columns(5)

    rodovia_filtro = col1.selectbox(
        "Rodovia",
        ["Todos"] + sorted(dados_horizontal_classificado['rodovia'].unique())
    )
    sre_filtro = col2.selectbox(
        "SRE",
        ["Todos"] + sorted(dados_horizontal_classificado['sre'].unique())
    )
    pista_filtro = col3.selectbox(
        "Pista",
        ["Todos"] + sorted(dados_horizontal_classificado['pista'].unique())
    )
    situacao_filtro = col4.selectbox(
        "Situação",
        ["Todos", "Boa", "Ruim", "Regular", "Indeterminada"]
    )

    data_min = pd.to_datetime(dados_horizontal_classificado['data']).min()
    data_max = pd.to_datetime(dados_horizontal_classificado['data']).max()
    data_filtro = col5.date_input("Filtrar por intervalo de data", [data_min, data_max])

    dados_filtrados = dados_horizontal_classificado
    if rodovia_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['rodovia'] == rodovia_filtro]
    if sre_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['sre'] == sre_filtro]
    if pista_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['pista'] == pista_filtro]
    if situacao_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['classificacao'] == situacao_filtro]
    dados_filtrados = dados_filtrados[
        (pd.to_datetime(dados_filtrados['data']) >= pd.to_datetime(data_filtro[0])) &
        (pd.to_datetime(dados_filtrados['data']) <= pd.to_datetime(data_filtro[1]))
        ]

    # Layout de gráfico de pizza + card com total de sinalizações
    col1, col2 = st.columns(2)

    with col1:
        fig_pizza = gerar_grafico_pizza(dados_filtrados, "Horizontal")
        st.plotly_chart(fig_pizza)

    with col2:
        total_sinalizacoes = len(dados_filtrados)
        st.markdown(
            f"""
                    <div style="text-align: center; font-size: 24px; padding: 6em; width:100%;">
                        <strong>Total de Sinalizações</strong><br>
                        <span style="font-size: 40px;">{total_sinalizacoes}</span>
                    </div>
                    """, unsafe_allow_html=True
        )

    colBar1, colBar2 = st.columns(2)

    fig_barras_tipos = gerar_grafico_barras_tipos(
        dados_filtrados,
        'tipo',
        "Distribuição por Tipo"
    )
    colBar1.plotly_chart(fig_barras_tipos)

    fig_barras_material = gerar_grafico_barras_tipos(
        dados_filtrados,
        'material',
        "Distribuição por Material"
    )
    colBar2.plotly_chart(fig_barras_material)

    if rodovia_filtro != "Todos":
        # Mapa sem cluster, com linhas coloridas
        st.subheader("Mapa de Sinalizações Horizontais")
        mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)
        mapa = adicionar_pontos_mapa_horizontais(dados_filtrados, mapa)
        st_folium(mapa, width=None, height=500)

    # Ranking das rodovias
    st.subheader("Ranking das Rodovias")
    melhores_rodovias, piores_rodovias = gerar_ranking_rodovias(dados_filtrados)

    col1, col2 = st.columns(2)

    with col1:
        st.write("10 Melhores Rodovias")
        st.dataframe(melhores_rodovias)

    with col2:
        st.write("10 Piores Rodovias")
        st.dataframe(piores_rodovias)
