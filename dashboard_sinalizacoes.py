import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import re

# URL base para as imagens
URL_BASE_IMAGENS = "https://sgpgoinfra.com.br/imagensInventario/"

# Colocar set_page_config como o primeiro comando do script
st.set_page_config(page_title="Dashboard de Sinalizações", layout="wide")


# Carregar os dados de Sinalização Vertical e Horizontal
@st.cache_data
def carregar_dados_vertical():
    return pd.read_csv("sinalizacao_vertical.csv", sep=";")


@st.cache_data
def carregar_dados_horizontal():
    return pd.read_csv("sinalizacao_horizontal.csv", sep=";")


# Função para limpar strings removendo espaços e caracteres especiais (para agrupar)
def limpar_string(texto):
    texto_limpo = re.sub(r'[^A-Za-z0-9]', '', texto.upper())
    return texto_limpo


# Função para classificar condição como positiva ou negativa
def classificar_condicao(condicao):
    condicao = condicao.upper()
    positivas = ["BOAS", "BOA", "BOM", "ÓTIMO", "EXCELENTE", "ADEQUADO", "SIMPLES", "BOAS CONDIÇÕES", "EM BOAS CONDIÇÕES"]
    negativas = ["RUIM", "PÉSSIMO", "INADEQUADO", "QUEBRADA", "AMASSADA", "QUEIMADA"]
    regulares = ["REGULAR"]

    if any(palavra in condicao for palavra in positivas):
        return "Boa"
    elif any(palavra in condicao for palavra in negativas):
        return "Ruim"
    elif any(palavra in condicao for palavra in regulares):
        return "Regular"
    else:
        return "Indeterminada"


# Aplicar a classificação de condição nas colunas de condições e condicao
def classificar_condicoes(df, coluna_condicao):
    df['classificacao'] = df[coluna_condicao].apply(classificar_condicao)
    return df


# Função para gerar o gráfico de pizza com base nas condições e cores fixas
def gerar_grafico_pizza(df, tipo_sinalizacao):
    cores = {
        "Boa": "green",
        "Ruim": "red",
        "Regular": "#faa702",
        "Indeterminada": "gray"
    }
    fig = px.pie(df, names='classificacao', title=f"Condições das Sinalizações ({tipo_sinalizacao})",
                 color='classificacao', color_discrete_map=cores)
    return fig


# Função para gerar gráfico de barras com a contagem de tipos, agrupando valores semelhantes
def gerar_grafico_barras_tipos(df, coluna, titulo):
    df['coluna_normalizada'] = df[coluna].apply(limpar_string)
    contagem = df['coluna_normalizada'].value_counts().reset_index()
    contagem.columns = [coluna, 'Quantidade']
    fig = px.bar(contagem, x=coluna, y='Quantidade', title=titulo)
    return fig


# Função para gerar o mapa de sinalizações verticais com círculos coloridos
def adicionar_pontos_mapa_verticais(df, mapa):
    for _, row in df.iterrows():
        color = "green" if row['classificacao'] == "Boa" else "red" if row['classificacao'] == "Ruim" else "#faa702" if row['classificacao'] == "Regular" else "gray"
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
        ).add_to(mapa)
    return mapa


# Função para gerar o mapa de sinalizações horizontais com linhas coloridas
def adicionar_pontos_mapa_horizontais(df, mapa):
    for _, row in df.iterrows():
        color = "green" if row['classificacao'] == "Boa" else "red" if row['classificacao'] == "Ruim" else "#faa702" if row['classificacao'] == "Regular" else "gray"
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
        ).add_to(mapa)
    return mapa


# Carregar dados
dados_vertical = carregar_dados_vertical()
dados_horizontal = carregar_dados_horizontal()

# Configuração inicial do Streamlit
st.title("Dashboard de Sinalizações Verticais e Horizontais")

# Layout de navegação
opcao_dashboard = st.sidebar.radio("Escolha o tipo de sinalização", ["Sinalização Vertical", "Sinalização Horizontal"])

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

    rodovia_filtro = col1.selectbox("Rodovia", ["Todos"] + sorted(dados_vertical_classificado['rodovia'].unique()))
    sre_filtro = col2.selectbox("SRE", ["Todos"] + sorted(dados_vertical_classificado['sre'].unique()))
    pista_filtro = col3.selectbox("Pista", ["Todos"] + sorted(dados_vertical_classificado['pista'].unique()))
    situacao_filtro = col4.selectbox("Situação", ["Todos", "Boa", "Ruim", "Regular", "Indeterminada"])

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
    fig_barras_tipos = gerar_grafico_barras_tipos(dados_filtrados, 'tipo', "Distribuição por Tipo")
    colBar1.plotly_chart(fig_barras_tipos)

    fig_barras_categorias = gerar_grafico_barras_tipos(dados_filtrados, 'categoria_sinal', "Distribuição por Categoria")
    colBar2.plotly_chart(fig_barras_categorias)

    if rodovia_filtro != "Todos":
        # Mapa sem cluster, com círculos coloridos
        st.subheader("Mapa de Sinalizações Verticais")
        mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)
        mapa = adicionar_pontos_mapa_verticais(dados_filtrados, mapa)
        st_folium(mapa, width=None, height=500)

elif opcao_dashboard == "Sinalização Horizontal":
    st.header("Sinalização Horizontal")

    dados_horizontal_classificado = classificar_condicoes(dados_horizontal, 'condicao')

    dados_horizontal_classificado['tipo'] = dados_horizontal_classificado['tipo'].str.upper()
    dados_horizontal_classificado['pista'] = dados_horizontal_classificado['pista'].str.upper()
    dados_horizontal_classificado['rodovia'] = dados_horizontal_classificado['sre'].str[:3].str.upper()
    dados_horizontal_classificado['sre'] = dados_horizontal_classificado['sre'].str.upper()

    col1, col2, col3, col4, col5 = st.columns(5)

    rodovia_filtro = col1.selectbox("Rodovia", ["Todos"] + sorted(dados_horizontal_classificado['rodovia'].unique()))
    sre_filtro = col2.selectbox("SRE", ["Todos"] + sorted(dados_horizontal_classificado['sre'].unique()))
    pista_filtro = col3.selectbox("Pista", ["Todos"] + sorted(dados_horizontal_classificado['pista'].unique()))
    situacao_filtro = col4.selectbox("Situação", ["Todos", "Boa", "Ruim", "Regular", "Indeterminada"])

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

    fig_barras_tipos = gerar_grafico_barras_tipos(dados_filtrados, 'tipo', "Distribuição por Tipo")
    colBar1.plotly_chart(fig_barras_tipos)

    fig_barras_material = gerar_grafico_barras_tipos(dados_filtrados, 'material', "Distribuição por Material")
    colBar2.plotly_chart(fig_barras_material)

    if rodovia_filtro != "Todos":
        # Mapa sem cluster, com linhas coloridas
        st.subheader("Mapa de Sinalizações Horizontais")
        mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)
        mapa = adicionar_pontos_mapa_horizontais(dados_filtrados, mapa)
        st_folium(mapa, width=None, height=500)
