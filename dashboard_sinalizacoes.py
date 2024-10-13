import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import re  # Biblioteca para expressões regulares

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
    # Converter para maiúsculas, remover espaços e caracteres especiais
    texto_limpo = re.sub(r'[^A-Za-z0-9]', '', texto.upper())
    return texto_limpo


# Função para classificar condição como positiva ou negativa
def classificar_condicao(condicao):
    condicao = condicao.upper()
    # Palavras que indicam condição positiva
    positivas = ["BOAS", "BOA", "BOM", "ÓTIMO", "EXCELENTE", "ADEQUADO", "SIMPLES", "BOAS CONDIÇÕES", "EM BOAS CONDIÇÕES",]
    # Palavras que indicam condição negativa
    negativas = ["RUIM", "REGULAR", "PÉSSIMO", "INADEQUADO", "QUEBRADA", "AMASSADA", "QUEIMADA"]

    # Classificar como positivo ou negativo com base nas palavras
    if any(palavra.upper() in condicao for palavra in positivas):
        return "Positiva"
    elif any(palavra.upper() in condicao for palavra in negativas):
        return "Negativa"
    else:
        return "Indeterminada"


# Aplicar a classificação de condição nas colunas de condições e condicao
def classificar_condicoes(df, coluna_condicao):
    df['classificacao'] = df[coluna_condicao].apply(classificar_condicao)
    return df


# Função para gerar o gráfico de pizza com base nas condições e cores fixas
def gerar_grafico_pizza(df, tipo_sinalizacao):
    # Definindo as cores: Positiva em verde, Negativa em vermelho, Indeterminada em cinza
    cores = {
        "Positiva": "green",
        "Negativa": "red",
        "Indeterminada": "gray"
    }
    fig = px.pie(df, names='classificacao', title=f"Condições das Sinalizações ({tipo_sinalizacao})",
                 color='classificacao',
                 color_discrete_map=cores)
    return fig


# Função para gerar gráfico de barras com a contagem de tipos, agrupando valores semelhantes
def gerar_grafico_barras_tipos(df, coluna, titulo):
    # Normalizar a coluna removendo caracteres especiais e convertendo para maiúsculas
    df['coluna_normalizada'] = df[coluna].apply(limpar_string)

    # Contar a quantidade de cada valor na coluna normalizada
    contagem = df['coluna_normalizada'].value_counts().reset_index()
    contagem.columns = [coluna, 'Quantidade']

    # Gerar gráfico de barras (usando o valor original como label)
    fig = px.bar(contagem, x=coluna, y='Quantidade', title=titulo)
    return fig


# Função para gerar o mapa de sinalizações verticais (pontos)
def gerar_mapa_sinalizacoes_verticais(df):
    mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)
    marker_cluster = MarkerCluster().add_to(mapa)

    for _, row in df.iterrows():
        # Montar a URL completa da imagem
        imagens = row['fotos'].strip('[]').replace('"', '').split(",")
        imagens_html = "".join([f"<img src='{URL_BASE_IMAGENS}{img.strip()}' width='150'><br>" for img in imagens])

        # Criar Popup com as informações da sinalização
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

        # Adicionar marcador ao mapa
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=popup_content
        ).add_to(marker_cluster)

    return mapa


# Função para gerar o mapa de sinalizações horizontais (trechos)
def gerar_mapa_sinalizacoes_horizontais(df):
    # Criar um novo mapa para garantir que os dados de pontos não sejam reutilizados
    mapa = folium.Map(location=[-15.77972, -47.92972], zoom_start=6)

    for _, row in df.iterrows():
        # Definir coordenadas do trecho (linha)
        coordinates = [
            [row['latitude_inicial'], row['longitude_inicial']],
            [row['latitude_final'], row['longitude_final']]
        ]

        # Montar a URL completa da imagem
        imagens = row['fotos'].strip('[]').replace('"', '').split(",")
        imagens_html = "".join([f"<img src='{URL_BASE_IMAGENS}{img.strip()}' width='150'><br>" for img in imagens])

        # Criar Popup com as informações da sinalização
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

        # Adicionar linha ao mapa
        folium.PolyLine(
            locations=coordinates,
            color="blue",  # Cor da linha (pode ser customizada)
            weight=5,  # Espessura da linha
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

# Mostrar diferentes dashboards com base na seleção
if opcao_dashboard == "Sinalização Vertical":
    st.header("Sinalização Vertical")

    # Classificar condições
    dados_vertical_classificado = classificar_condicoes(dados_vertical, 'condicoes')

    # Converter todos os tipos, rodovia e SRE para maiúsculas
    dados_vertical_classificado['tipo'] = dados_vertical_classificado['tipo'].str.upper()
    dados_vertical_classificado['pista'] = dados_vertical_classificado['pista'].str.upper()
    dados_vertical_classificado['rodovia'] = dados_vertical_classificado['sre'].str[:3].str.upper()
    dados_vertical_classificado['sre'] = dados_vertical_classificado['sre'].str.upper()

    # Filtros
    rodovia_filtro = st.selectbox("Rodovia", ["Todos"] + sorted(dados_vertical_classificado['rodovia'].unique()))
    sre_filtro = st.selectbox("SRE", ["Todos"] + sorted(dados_vertical_classificado['sre'].unique()))
    pista_filtro = st.selectbox("Pista", ["Todos"] + sorted(dados_vertical_classificado['pista'].unique()))
    situacao_filtro = st.selectbox("Situação", ["Todos", "Positiva", "Negativa", "Indeterminada"])

    # Filtro por data
    data_min = pd.to_datetime(dados_vertical_classificado['data']).min()
    data_max = pd.to_datetime(dados_vertical_classificado['data']).max()
    data_filtro = st.date_input("Filtrar por intervalo de data", [data_min, data_max])

    # Aplicar os filtros
    dados_filtrados = dados_vertical_classificado
    if rodovia_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['rodovia'] == rodovia_filtro]

    if sre_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['sre'] == sre_filtro]

    if pista_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['pista'] == pista_filtro]

    if situacao_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['classificacao'] == situacao_filtro]

    # Filtro de intervalo de datas
    dados_filtrados = dados_filtrados[
        (pd.to_datetime(dados_filtrados['data']) >= pd.to_datetime(data_filtro[0])) &
        (pd.to_datetime(dados_filtrados['data']) <= pd.to_datetime(data_filtro[1]))
    ]

    # Gráfico de pizza para condições
    fig_pizza = gerar_grafico_pizza(dados_filtrados, "Vertical")
    st.plotly_chart(fig_pizza)

    # Gráfico de barras com a contagem de tipos
    fig_barras_tipos = gerar_grafico_barras_tipos(dados_filtrados, 'tipo', "Distribuição por Tipo")
    st.plotly_chart(fig_barras_tipos)

    # Gráfico de barras com a contagem de categorias
    fig_barras_categorias = gerar_grafico_barras_tipos(dados_filtrados, 'categoria_sinal', "Distribuição por Categoria")
    st.plotly_chart(fig_barras_categorias)

    # Mapa de sinalizações verticais
    st.subheader("Mapa de Sinalizações Verticais")
    mapa_vertical = gerar_mapa_sinalizacoes_verticais(dados_filtrados)
    st_folium(mapa_vertical, width=800, height=500)

elif opcao_dashboard == "Sinalização Horizontal":
    st.header("Sinalização Horizontal")

    # Classificar condições
    dados_horizontal_classificado = classificar_condicoes(dados_horizontal, 'condicao')

    # Converter todos os tipos e rodovia para maiúsculas
    dados_horizontal_classificado['tipo'] = dados_horizontal_classificado['tipo'].str.upper()
    dados_horizontal_classificado['pista'] = dados_horizontal_classificado['pista'].str.upper()
    dados_horizontal_classificado['rodovia'] = dados_horizontal_classificado['sre'].str[:3].str.upper()
    dados_horizontal_classificado['sre'] = dados_horizontal_classificado['sre'].str.upper()

    # Filtros
    rodovia_filtro = st.selectbox("Rodovia", ["Todos"] + sorted(dados_horizontal_classificado['rodovia'].unique()))
    sre_filtro = st.selectbox("SRE", ["Todos"] + sorted(dados_horizontal_classificado['sre'].unique()))
    pista_filtro = st.selectbox("Pista", ["Todos"] + sorted(dados_horizontal_classificado['pista'].unique()))
    situacao_filtro = st.selectbox("Situação", ["Todos", "Positiva", "Negativa", "Indeterminada"])

    # Filtro por data
    data_min = pd.to_datetime(dados_horizontal_classificado['data']).min()
    data_max = pd.to_datetime(dados_horizontal_classificado['data']).max()
    data_filtro = st.date_input("Filtrar por intervalo de data", [data_min, data_max])

    # Aplicar os filtros
    dados_filtrados = dados_horizontal_classificado
    if rodovia_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['rodovia'] == rodovia_filtro]

    if sre_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['sre'] == sre_filtro]

    if pista_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['pista'] == pista_filtro]

    if situacao_filtro != "Todos":
        dados_filtrados = dados_filtrados[dados_filtrados['classificacao'] == situacao_filtro]

    # Filtro de intervalo de datas
    dados_filtrados = dados_filtrados[
        (pd.to_datetime(dados_filtrados['data']) >= pd.to_datetime(data_filtro[0])) &
        (pd.to_datetime(dados_filtrados['data']) <= pd.to_datetime(data_filtro[1]))
    ]

    # Gráfico de pizza para condições
    fig_pizza = gerar_grafico_pizza(dados_filtrados, "Horizontal")
    st.plotly_chart(fig_pizza)

    # Gráfico de barras com a contagem de tipos
    fig_barras_tipos = gerar_grafico_barras_tipos(dados_filtrados, 'tipo', "Distribuição por Tipo")
    st.plotly_chart(fig_barras_tipos)

    # Gráfico de barras com a contagem de materiais
    fig_barras_material = gerar_grafico_barras_tipos(dados_filtrados, 'material', "Distribuição por Material")
    st.plotly_chart(fig_barras_material)

    # Mapa de sinalizações horizontais (com trechos)
    st.subheader("Mapa de Sinalizações Horizontais")
    mapa_horizontal = gerar_mapa_sinalizacoes_horizontais(dados_filtrados)
    st_folium(mapa_horizontal, width=800, height=500)
