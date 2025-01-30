import streamlit as st
import polars as pl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# Set page configuration
st.set_page_config(page_title="Football Stats Analysis", layout="wide")

# Translation dictionary
COLUMN_TRANSLATIONS = {
    'Class.': 'Classificação',
    'País': 'País',
    'LgRk': 'Posição na Liga',
    'MP': 'Jogos Disputados',
    'V': 'Vitórias',
    'E': 'Empates',
    'D': 'Derrotas',
    'GP': 'Gols pró',
    'GC': 'Gols contra',
    'GD': 'Diferença de Gols',
    'Pt': 'Pontos',
    'Pts/PPJ': 'Pontos/Partida',
    'xG': 'Gols previstos',
    'xGA': 'xG sofrido',
    'xGD': 'Diferença xG',
    'xGD/90': 'Diferença xG/90',
    'Últimos 5': 'Últimas cinco partidas',
    'Público': 'Comparecimento/Jogo'
}

# Season configuration
SEASONS = {
    "2023-2024 (Atual)": None,
    "2022-2023": "2022-2023",
    "2021-2022": "2021-2022",
    "2020-2021": "2020-2021",
    "2019-2020": "2019-2020",
    "2018-2019": "2018-2019"
}


@st.cache_data
def load_data(season_code):
    """Load and process data from the appropriate URL"""
    if season_code:
        url = f"https://fbref.com/pt/comps/Big5/{season_code}/{season_code}-Maiores-5-Ligas-Europeias-Estatisticas"
    else:
        url = "https://fbref.com/pt/comps/Big5/Maiores-5-Ligas-Europeias-Estatisticas"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}

    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(response.text)
        df_pd = tables[0]

        if isinstance(df_pd.columns, pd.MultiIndex):
            df_pd.columns = [' '.join(col).strip() for col in df_pd.columns.values]
        df_pd = df_pd.rename(columns=COLUMN_TRANSLATIONS)

        df = pl.from_pandas(df_pd).drop_nulls()
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None


def home_page():
    st.title("Análise das Maiores Ligas Europeias de Futebol")
    st.markdown("""
    ## Bem-vindo ao Painel Estatístico de Futebol

    Este projeto oferece uma análise detalhada das cinco maiores ligas europeias de futebol:
    - Premier League (Inglaterra)
    - La Liga (Espanha)
    - Serie A (Itália)
    - Bundesliga (Alemanha)
    - Ligue 1 (França)

    **Funcionalidades:**
    - Dados históricos desde 2018
    - Comparação entre temporadas
    - Visualizações interativas
    - Análise por time e país

    Utilize o menu lateral para selecionar a temporada e explorar os dados!
    """)
    st.image("https://images.unsplash.com/photo-1579952363873-27f3bade9f55", use_container_width=True)


def main():
    # Page navigation
    page = st.sidebar.selectbox("Navegação", ["Home", "Visão Geral", "Visualização de Dados"])
    
    # Season selection in sidebar
    selected_season = st.sidebar.selectbox("Selecione a Temporada", list(SEASONS.keys()))
    season_code = SEASONS[selected_season]

    # Load data with selected season
    df = load_data(season_code)

    if df is None:
        st.stop()

    if page == "Home":
        home_page()

    elif page == "Visão Geral":
        st.title(f"Estatísticas das 5 Maiores Ligas Europeias - {selected_season}")

        # Country filter
        st.sidebar.header("Filtros")
        countries = df['País'].unique().to_list()
        selected_country = st.sidebar.selectbox("Selecione o País", countries, index=0)

        # Filter and display data
        filtered_df = df.filter(pl.col("País") == selected_country)
        st.dataframe(filtered_df, use_container_width=True, height=600)

    elif page == "Visualização de Dados":
        st.title(f"Visualização Interativa de Dados - {selected_season}")

        # Chart selection
        chart_type = st.selectbox(
            "Selecione o Tipo de Gráfico",
            ["Barra", "Dispersão", "Radar", "Boxplot"]
        )

        numeric_cols = df.select(pl.selectors.numeric()).columns
        categorical_cols = df.select(pl.selectors.by_dtype(pl.Utf8)).columns

        # Visualization logic
        if chart_type == "Barra":
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("Eixo X", ["País","Equipe"])
            with col2:
                y_axis = st.selectbox("Eixo Y", numeric_cols)
            with col3:
                color = st.selectbox("Cor", [None] + ["País","Equipe"])

            fig = px.bar(df, x=x_axis, y=y_axis, color=color, title=f"{y_axis} por {x_axis} - {selected_season}")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "Dispersão":
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("Eixo X", numeric_cols, index=6)
            with col2:
                y_axis = st.selectbox("Eixo Y", numeric_cols, index=11)
            with col3:
                color = st.selectbox("Cor", [None] + ["País"],index=1)

            fig = px.scatter(df, x=x_axis, y=y_axis, color=color, hover_data=["Equipe", "Posição na Liga"],
                             title=f"{y_axis} vs {x_axis} - {selected_season}")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "Radar":
            col1, col2 = st.columns(2)
            with col1:
                teams = df["Equipe"].unique().sort().to_list()
                selected_teams = st.multiselect("Selecione os Times", teams, default=[teams[0]])
            with col2:
                attributes = st.multiselect("Selecione os Atributos", numeric_cols)

            if selected_teams and len(attributes) >= 3:
                fig = go.Figure()
                for team in selected_teams:
                    team_data = df.filter(pl.col("Equipe") == team).to_pandas().iloc[0]
                    fig.add_trace(go.Scatterpolar(
                        r=team_data[attributes],
                        theta=attributes,
                        fill='toself',
                        name=team
                    ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    title=f"Comparação de Times - {selected_season}"
                )
                st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "Boxplot":
            col1, col2 = st.columns(2)
            with col1:
                numerical_col = st.selectbox("Selecione a Métrica", numeric_cols)
            with col2:
                category_col = st.selectbox("Agrupar por", ["País", "Equipe"])

            fig = px.box(df, x=category_col, y=numerical_col,
                         title=f"Distribuição de {numerical_col} - {selected_season}",
                         color=category_col)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
