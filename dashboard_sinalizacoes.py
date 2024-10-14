import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import re
import time

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
    positivas = ["BOAS", "BOA", "BOM", "ÓTIMO", "EXCELENTE", "ADEQUADO", "SIMPLES", "BOAS CONDIÇÕES",
                 "EM BOAS CONDIÇÕES"]
    negativas = ["RUIM", "REGULAR", "PÉSSIMO", "INADEQUADO", "QUEBRADA", "AMASSADA", "QUEIMADA"]

    if any(palavra in condicao for palavra in positivas):
        return "Boa"
    elif any(palavra in condicao for palavra in negativas):
        return "Ruim"
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
        "Indeterminada": "gray"
    }
    fig = px.pie(df, names='classificacao', title=f"Condições das Sinalizações ({tipo_sinalizacao})",
                 color='classificacao',
                 color_discrete_map=cores)
    return fig


# Função para gerar gráfico de barras com a contagem de tipos, agrupando valores semelhantes
def gerar_grafico_barras_tipos(df, coluna, titulo):
    df['coluna_normalizada'] = df[coluna].apply(limpar_string)
    contagem = df['coluna_normalizada'].value_counts().reset_index()
    contagem.columns = [coluna, 'Quantidade']
    fig = px.bar(contagem, x=coluna, y='Quantidade', title=titulo)
    return fig


# Função para gerar o mapa de sinalizações verticais com carregamento progressivo
def adicionar_pontos_mapa_verticais(df, mapa, marker_cluster, start_idx=0, batch_size=500):
    end_idx = min(start_idx + batch_size, len(df))

    for idx in range(start_idx, end_idx):
        row = df.iloc[idx]
        imagens = row['fotos'].strip('[]').replace('"', '').split(",")
        imagens_html = "".join(
            [f"<a href='{URL_BASE_IMAGENS}{img.strip()}' target='_blank'>Ver Imagem</a><br>" for img in imagens])

        popup_content = f"""
        <strong>Sinalização Vertical</strong><br>
        SRE: {row['sre']}<br>
        Data: {row['data']}<br>
        Pista: {row['pista']}<br>
        Tipo: {row['tipo'].upper()}<br>
        Material: {row['material']}<br>
        Categoria: {row['categoria_sinal']}<br>
        Condição: {row['condicoes']}<br>
        {imagens_html}
        """

        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=popup_content
        ).add_to(marker_cluster)

    return mapa


# Função para gerar o mapa de sinalizações horizontais com simplificação
def adicionar_pontos_mapa_horizontais(df, mapa, marker_cluster, start_idx=0, batch_size=500):
    end_idx = min(start_idx + batch_size, len(df))

    for idx in range(start_idx, end_idx):
        row = df.iloc[idx]
        coordinates = [
            [row['latitude_inicial'], row['longitude_inicial']],
            [row['latitude_final'], row['longitude_final']]
        ]
        imagens = row['fotos'].strip('[]').replace('"', '').split(",")
        imagens_html = "".join(
            [f"<a href='{URL_BASE_IMAGENS}{img.strip()}' target='_blank'>Ver Imagem</a><br>" for img in imagens])

        popup_content = f"""
        <strong>Sinalização Horizontal</strong><br>
        SRE: {row['sre']}<br>
        Data: {row['data']}<br>
        Pista: {row['pista']}<br>
        Tipo: {row['tipo'].upper()}<br>
        Material: {row['material']}<br>
        Condição: {row['condicao']}<br>
        {imagens_html}
        """

        folium.PolyLine(
            locations=coordinates,
            color="blue",
            weight=5,
            popup=popup_content
        ).add_to(marker_cluster)

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

    rodovia_filtro = st.selectbox("Rodovia", ["Todos"] + sorted(dados_vertical_classificado['rodovia'].unique()))
    sre_filtro = st.selectbox("SRE", ["Todos"] + sorted(dados_vertical_classificado['sre'].unique()))
    pista_filtro = st.selectbox("Pista", ["Todos"] + sorted(dados_vertical_classificado['pista'].unique()))
    situacao_filtro = st.selectbox("Situação", ["Todos", "Boa", "Ruim", "Indeterminada"])

    data_min = pd.to_datetime(dados_vertical_classificado['data']).min()
    data_max = pd.to_datetime(dados_vertical_classificado['data']).max()
    data_filtro = st.date_input("Filtrar por intervalo de data", [data_min, data_max])

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

    fig_pizza = gerar_grafico_pizza(dados_filtrados, "Vertical")
    st.plotly_chart(fig_pizza)

    fig_barras_tipos = gerar_grafico_barras_tipos(dados_filtrados, 'tipo', "Distribuição por Tipo")
    st.plotly_chart(fig_barras_tipos)

    fig_barras_categorias = gerar_grafico_barras_tipos(dados_filtrados, 'categoria_sinal', "Distribuição por Categoria")
    st.plotly_chart(fig_barras_categorias)

    # Mapa com carregamento progressivo
    st.subheader("Mapa de Sinalizações Verticais")
    mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)
    marker_cluster = MarkerCluster().add_to(mapa)

    # Placeholder para o texto de progresso
    progress_text = st.empty()

    # Carregar e adicionar os pontos em lotes
    batch_size = 500
    total_batches = (len(dados_filtrados) // batch_size) + 1

    for i in range(total_batches):
        mapa = adicionar_pontos_mapa_verticais(dados_filtrados, mapa, marker_cluster, start_idx=i * batch_size,
                                               batch_size=batch_size)
        time.sleep(0.5)  # Simular o carregamento progressivo
        st_folium(mapa, width=800, height=500)

elif opcao_dashboard == "Sinalização Horizontal":
    st.header("Sinalização Horizontal")

    dados_horizontal_classificado = classificar_condicoes(dados_horizontal, 'condicao')

    dados_horizontal_classificado['tipo'] = dados_horizontal_classificado['tipo'].str.upper()
    dados_horizontal_classificado['pista'] = dados_horizontal_classificado['pista'].str.upper()
    dados_horizontal_classificado['rodovia'] = dados_horizontal_classificado['sre'].str[:3].str.upper()
    dados_horizontal_classificado['sre'] = dados_horizontal_classificado['sre'].str.upper()

    rodovia_filtro = st.selectbox("Rodovia", ["Todos"] + sorted(dados_horizontal_classificado['rodovia'].unique()))
    sre_filtro = st.selectbox("SRE", ["Todos"] + sorted(dados_horizontal_classificado['sre'].unique()))
    pista_filtro = st.selectbox("Pista", ["Todos"] + sorted(dados_horizontal_classificado['pista'].unique()))
    situacao_filtro = st.selectbox("Situação", ["Todos", "Boa", "Ruim", "Indeterminada"])

    data_min = pd.to_datetime(dados_horizontal_classificado['data']).min()
    data_max = pd.to_datetime(dados_horizontal_classificado['data']).max()
    data_filtro = st.date_input("Filtrar por intervalo de data", [data_min, data_max])

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

    fig_pizza = gerar_grafico_pizza(dados_filtrados, "Horizontal")
    st.plotly_chart(fig_pizza)

    fig_barras_tipos = gerar_grafico_barras_tipos(dados_filtrados, 'tipo', "Distribuição por Tipo")
    st.plotly_chart(fig_barras_tipos)

    fig_barras_material = gerar_grafico_barras_tipos(dados_filtrados, 'material', "Distribuição por Material")
    st.plotly_chart(fig_barras_material)

    # Mapa com carregamento progressivo
    st.subheader("Mapa de Sinalizações Horizontais")
    mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)
    marker_cluster = MarkerCluster().add_to(mapa)

    # Placeholder para o texto de progresso
    progress_text = st.empty()

    # Carregar e adicionar os pontos em lotes
    batch_size = 500
    total_batches = (len(dados_filtrados) // batch_size) + 1

    for i in range(total_batches):
        mapa = adicionar_pontos_mapa_horizontais(dados_filtrados, mapa, marker_cluster, start_idx=i * batch_size,
                                                 batch_size=batch_size)
        time.sleep(0.5)  # Simular o carregamento progressivo
        st_folium(mapa, width=800, height=500)
