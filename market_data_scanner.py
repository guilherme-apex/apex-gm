import streamlit as st
import pandas as pd

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Apex Market DB", layout="wide", page_icon="💎")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    .stMetric { background-color: #1e1e1e; padding: 10px; border-radius: 5px; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 📂 BANCO DE DADOS (Extraído das suas 22 Páginas)
# ==============================================================================
# Aqui estão os jogadores < 30% Rostered extraídos do seu texto
MARKET_DATA = {
    # --- STANDARD LEAGUE GEMS (10% - 30%) ---
    "Kyshawn George": 27.3, "Ausar Thompson": 26.5, "Donovan Clingan": 25.3,
    "Kel'el Ware": 25.3, "John Collins": 24.9, "Anthony Black": 23.5,
    "Jordan Poole": 23.1, "Matas Buzelis": 23.0, "Draymond Green": 22.1,
    "Jalen Suggs": 21.8, "Reed Sheppard": 21.4, "Jabari Smith Jr.": 21.1,
    "Anfernee Simons": 21.0, "Jaime Jaquez Jr.": 20.3, "Peyton Watson": 20.1,
    "Devin Vassell": 19.7, "Collin Gillespie": 19.4, "Cam Thomas": 17.9,
    "Jakob Poeltl": 17.9, "Dillon Brooks": 17.5, "Kyrie Irving": 17.2,
    "Tobias Harris": 16.9, "Malik Monk": 16.6, "Toumani Camara": 16.5,
    "P.J. Washington": 16.2, "Bennedict Mathurin": 15.8, "Ajay Mitchell": 14.5,
    "Grayson Allen": 14.4, "Bobby Portis": 14.3, "Keegan Murray": 13.4,
    "Jerami Grant": 13.3, "Christian Braun": 12.7, "T.J. McConnell": 12.1,
    "Kelly Oubre Jr.": 10.8, "D'Angelo Russell": 10.8, "Daniel Gafford": 10.8,
    "Jusuf Nurkic": 10.5, "Cedric Coward": 10.1, "Quentin Grimes": 10.0,
    "Walker Kessler": 10.0,

    # --- DEEP LEAGUE GEMS (< 10%) ---
    "Egor Demin": 9.9, "Tre Jones": 9.8, "Tari Eason": 9.6,
    "Davion Mitchell": 9.4, "Naji Marshall": 9.4, "Neemias Queta": 9.0,
    "Collin Sexton": 8.8, "Zach Edey": 8.6, "Cam Spencer": 8.2,
    "Ayo Dosunmu": 8.0, "Luke Kornet": 7.9, "Bradley Beal": 7.7,
    "Luguentz Dort": 7.6, "Day'Ron Sharpe": 7.3, "Maxime Raynaud": 7.2,
    "Harrison Barnes": 7.2, "Kevin Huerter": 7.1, "Tyus Jones": 7.0,
    "Scoot Henderson": 7.0, "Precious Achiuwa": 6.7, "Max Christie": 6.4,
    "Jalen Smith": 6.2, "Alex Caruso": 6.2, "Sam Merrill": 6.2,
    "Kyle Filipowski": 6.0, "Mitchell Robinson": 5.9, "Sandro Mamukelashvili": 5.7,
    "Jock Landale": 5.6, "Duncan Robinson": 5.1, "Andre Drummond": 5.1,
    "Marcus Smart": 5.0, "Fred VanVleet": 4.8, "Marvin Bagley III": 4.6,
    "Yves Missi": 4.5, "Brandon Williams": 4.4, "Steven Adams": 4.4,
    "Caris LeVert": 4.3, "Justin Champagnie": 4.0, "Tyrese Haliburton": 3.7,
    "Lonzo Ball": 3.7, "Moses Moody": 3.6, "Jordan Clarkson": 3.3,
    "Nikola Jovic": 3.3, "Khris Middleton": 3.3, "Ryan Nembhard": 3.1,
    "Keon Ellis": 3.1, "Jamal Shead": 3.0, "Gradey Dick": 2.9,
    "Jaylen Wells": 2.9, "Al Horford": 2.8, "De'Anthony Melton": 2.8,
    "Sam Hauser": 2.7, "Walter Clayton Jr.": 2.5, "Bronny James": 2.5,
    "Kris Dunn": 2.5, "Cole Anthony": 2.3, "Jordan Walsh": 2.3,
    "Jalen Pickett": 2.3, "Kentavious Caldwell-Pope": 2.1, "Jarace Walker": 2.0,
    "Baylor Scheierman": 0.1, "Xavier Tillman": 0.1, "Joe Ingles": 0.1,
    "Sidy Cissoko": 0.1, "Ben Saraf": 0.1
}

# ==============================================================================
# UI & LÓGICA
# ==============================================================================
st.title("💎 Apex Market DB (Dados Verificados)")
st.caption("Base de dados limpa extraída da ESPN (Temporada 2026)")

# Sidebar para adicionar manualmente se precisar
with st.sidebar.expander("➕ Adicionar Jogador Manual"):
    new_name = st.text_input("Nome")
    new_pct = st.number_input("% Rostered", 0.0, 100.0, step=0.1)
    if st.button("Inserir"):
        MARKET_DATA[new_name] = new_pct
        st.success(f"{new_name} adicionado!")

# Processamento do Dict para DataFrame
df = pd.DataFrame(list(MARKET_DATA.items()), columns=["Player", "Rostered %"])

# Categorização
def categorize(pct):
    if pct < 10.0: return "💎 Deep (<10%)"
    if pct < 33.0: return "⚖️ Standard (<33%)"
    return "🌟 Rostered"

df["Category"] = df["Rostered %"].apply(categorize)

# Métricas
col1, col2, col3 = st.columns(3)
col1.metric("Total Jogadores", len(df))
col2.metric("Deep Gems", len(df[df["Category"]=="💎 Deep (<10%)"]))
col3.metric("Standard", len(df[df["Category"]=="⚖️ Standard (<33%)"]))

st.divider()

# TABS
t1, t2, t3 = st.tabs(["💎 Deep Gems", "⚖️ Standard", "📋 Lista Completa"])

def show_data(dframe):
    st.dataframe(
        dframe.sort_values(by="Rostered %", ascending=True),
        column_order=["Player", "Rostered %", "Category"],
        column_config={
            "Rostered %": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0, max_value=100
            )
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )

with t1:
    st.info("Jogadores esquecidos com alto potencial.")
    show_data(df[df["Category"] == "💎 Deep (<10%)"])

with t2:
    st.info("Jogadores de rotação disponíveis na maioria das ligas.")
    show_data(df[df["Category"] == "⚖️ Standard (<33%)"])

with t3:
    show_data(df)