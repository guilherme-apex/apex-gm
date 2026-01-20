import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIG
# ==============================================================================
st.set_page_config(page_title="Global Market Radar (FantasyPros)", layout="wide", page_icon="🏀")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    div.stButton > button:first-child {
        background-color: #0099ff;
        color: white;
        height: 50px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ENGINE: FANTASYPROS SCRAPER
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_fantasypros_data():
    # URL de Rankings "Rest of Season" (Geralmente contém Ownership)
    url = "https://www.fantasypros.com/nba/rankings/ros-overall.php"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, f"Erro HTTP FantasyPros: {r.status_code}"
            
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Procura a tabela principal
        table = soup.find('table', {'id': 'ranking-table'})
        if not table:
            # Tenta fallback para classe genérica
            table = soup.find('table', {'class': 'table'})
            
        if not table:
            return None, "Tabela não encontrada no FantasyPros."

        # Identificar índice da coluna "Own"
        headers_row = table.find('thead').find('tr')
        headers = [th.text.strip() for th in headers_row.find_all('th')]
        
        own_index = -1
        for i, h in enumerate(headers):
            if "Own" in h or "%" in h:
                own_index = i
                break
        
        if own_index == -1:
            # Fallback: Geralmente é uma das últimas colunas
            own_index = len(headers) - 1
            
        players = []
        rows = table.find('tbody').find_all('tr')
        
        for row in rows:
            # Ignora linhas de propaganda/tiers
            if 'tier-row' in row.get('class', []): continue
            
            cols = row.find_all('td')
            if not cols: continue
            
            try:
                # Nome do Jogador (Geralmente dentro de uma div com classe player-name ou link)
                name_tag = row.find('a', {'class': 'player-name'})
                if not name_tag:
                    name_tag = row.find('div', {'class': 'player-name'})
                
                if not name_tag: continue
                full_name = name_tag.text.strip()
                
                # Time (Geralmente texto pequeno perto do nome)
                team = "FA"
                team_tag = row.find('span', {'class': 'team-name'}) # Ajuste conforme layout
                if team_tag: team = team_tag.text.strip()

                # Ownership
                # Tenta pegar da coluna identificada
                if own_index < len(cols):
                    own_text = cols[own_index].text.strip()
                    if "%" in own_text:
                        val = float(own_text.replace('%', ''))
                    else:
                        val = 0.0 # Se não tiver %, ignora
                else:
                    val = 0.0
                
                players.append({
                    "Player": full_name,
                    "Team": team,
                    "Rostered %": val
                })
            except: continue
            
        return pd.DataFrame(players), None

    except Exception as e:
        return None, str(e)

# ==============================================================================
# UI
# ==============================================================================
st.title("🌎 Global Market Radar (via FantasyPros)")
st.caption("Dados Globais de Ownership % (Consenso Yahoo/ESPN)")

filter_option = st.selectbox(
    "Perfil Barutha:",
    [
        "💎 Deep Leagues (< 10% Rostered)",
        "⚖️ Standard Leagues (< 33% Rostered)",
        "🌟 All Players"
    ]
)

if st.button("🚀 Rastrear Mercado Global"):
    with st.spinner("Extraindo dados do FantasyPros..."):
        df, error = fetch_fantasypros_data()
        
        if error:
            st.error(f"Falha: {error}")
            st.info("O FantasyPros pode ter bloqueado o robô temporariamente.")
        elif df is None or df.empty:
            st.warning("Tabela encontrada, mas nenhum jogador extraído. O layout do site pode ter mudado.")
        else:
            # Filtros
            if "Deep" in filter_option:
                filtered = df[df['Rostered %'] < 10.0]
            elif "Standard" in filter_option:
                filtered = df[df['Rostered %'] < 33.0]
            else:
                filtered = df
            
            # Ordena: Menor ownership primeiro (Gemas)
            filtered = filtered.sort_values(by="Rostered %", ascending=True)
            
            st.success(f"Encontrados {len(filtered)} jogadores.")
            
            st.dataframe(
                filtered,
                column_config={
                    "Rostered %": st.column_config.ProgressColumn(
                        format="%.1f%%", min_value=0, max_value=100
                    )
                },
                use_container_width=True,
                hide_index=True
            )