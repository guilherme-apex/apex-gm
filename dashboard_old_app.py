import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import time
import sqlite3
from datetime import datetime
from fake_useragent import UserAgent

# ==============================================================================
# 1. CONFIGURAÇÃO & ESTILO
# ==============================================================================
st.set_page_config(page_title="Apex V28.1 ESPN Fix", layout="wide", page_icon="📡")

# URL BASE DA ESPN
ESPN_ROSTER_API = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/roster"
ESPN_GAMELOG_URL = "https://www.espn.com/nba/player/gamelog/_/id/{}/type/nba/year/2026"

DB_NAME = "nba_apex_espn.db"
ua = UserAgent()

st.markdown("""
<style>
    .block-container { padding-top: 3rem !important; padding-bottom: 5rem !important; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; color: #e0e0e0; }
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; color: #00ff41; }
    [data-testid="stMetricLabel"] { font-size: 14px; color: #a0a0a0; }
    .stSelectbox label { color: #00ff41 !important; font-weight: bold; font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. BANCO DE DADOS & CACHE
# ==============================================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS player_log_cache 
                 (player_id INTEGER PRIMARY KEY, data_json TEXT, last_updated TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_cache(table, key_val, df):
    conn = sqlite3.connect(DB_NAME)
    json_data = df.to_json()
    now = datetime.now()
    conn.execute(f'INSERT OR REPLACE INTO {table} (player_id, data_json, last_updated) VALUES (?, ?, ?)', 
                 (key_val, json_data, now))
    conn.commit()
    conn.close()

def get_cache(table, key_val):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'SELECT data_json FROM {table} WHERE player_id=?', (key_val,))
    row = cursor.fetchone()
    conn.close()
    return pd.read_json(row[0]) if row else None

init_db()

# ==============================================================================
# 3. MOTOR DE DADOS ESPN (COM BYPASS DE SEGURANÇA)
# ==============================================================================
def get_header():
    # Headers completos para parecer um navegador real
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

@st.cache_data(ttl=3600)
def fetch_espn_roster(team_espn_id):
    try:
        url = ESPN_ROSTER_API.format(team_espn_id)
        # Timeout curto pois API é rapida
        data = requests.get(url, headers=get_header(), timeout=10).json()
        players = []
        for item in data['athletes']:
            players.append({
                'name': item['fullName'],
                'id': item['id'], 
                'pos': item['position']['abbreviation'],
                'headshot': item.get('headshot', {}).get('href', None)
            })
        return players
    except: return []

def fetch_espn_gamelog(espn_player_id):
    """Raspa a tabela de jogos usando requests primeiro para evitar 403 Forbidden"""
    cached = get_cache('player_log_cache', espn_player_id)
    if cached is not None: return cached

    try:
        url = ESPN_GAMELOG_URL.format(espn_player_id)
        
        # --- CORREÇÃO AQUI: BAIXA O HTML PRIMEIRO COM HEADERS ---
        response = requests.get(url, headers=get_header(), timeout=15)
        
        if response.status_code != 200:
            print(f"Erro HTTP ESPN: {response.status_code}")
            return None
            
        # Passa o TEXTO do HTML para o Pandas, não a URL
        dfs = pd.read_html(response.text, header=0)
        
        df_log = pd.DataFrame()
        for df in dfs:
            # Procura a tabela certa (tem Data e Pontos)
            if 'Date' in df.columns and 'PTS' in df.columns:
                df_log = df
                break
        
        if df_log.empty: return None

        # Limpeza
        df_log = df_log[df_log['Date'] != 'Date']
        df_log['Date_Full'] = df_log['Date'] + " 2026" # Ajuste de ano
        df_log = df_log[~df_log['MIN'].isin(['DNP', '--'])] # Remove DNP
        
        cols_to_num = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO']
        for c in cols_to_num:
            df_log[c] = pd.to_numeric(df_log[c], errors='coerce').fillna(0)
            
        save_cache('player_log_cache', espn_player_id, df_log)
        return df_log
        
    except Exception as e:
        print(f"Erro Parsing ESPN: {e}")
        return None

# ==============================================================================
# 4. UI PRINCIPAL
# ==============================================================================
st.sidebar.title("📡 Apex V28.1 ESPN")

@st.cache_data(ttl=3600)
def get_daily_schedule(d):
    try:
        url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={d.strftime('%Y%m%d')}"
        data = requests.get(url, headers=get_header(), timeout=10).json()
        games = []
        for e in data['events']:
            h = e['competitions'][0]['competitors'][0]['team']
            a = e['competitions'][0]['competitors'][1]['team']
            games.append({
                'label': f"{a['displayName']} @ {h['displayName']}",
                'home_name': h['displayName'], 'home_id': h['id'],
                'away_name': a['displayName'], 'away_id': a['id']
            })
        return games
    except: return []

d = st.sidebar.date_input("Date", pd.to_datetime("today"))
games_list = get_daily_schedule(d)

if not games_list:
    st.sidebar.warning("No games found on ESPN.")
    st.stop()

# Menu de Jogos
game_labels = [g['label'] for g in games_list]
sel_label = st.sidebar.selectbox("Select Game:", game_labels)
selected_game = next(g for g in games_list if g['label'] == sel_label)

# ==============================================================================
# SNIPER MODE
# ==============================================================================
st.header("💸 Betting Sniper (ESPN Source)")

with st.spinner("Fetching Rosters..."):
    roster_h = fetch_espn_roster(selected_game['home_id'])
    roster_v = fetch_espn_roster(selected_game['away_id'])

all_players = []
for p in roster_v: all_players.append(f"{p['name']} ({selected_game['away_name']})")
for p in roster_h: all_players.append(f"{p['name']} ({selected_game['home_name']})")

c1, c2 = st.columns([3, 1])
target_str = c1.selectbox("🎯 Target Player:", all_players)
stat_options = {"Points": "PTS", "Rebounds": "REB", "Assists": "AST", "Steals": "STL", "Blocks": "BLK"}
stat_label = c2.selectbox("Stat:", list(stat_options.keys()))
stat_col = stat_options[stat_label]

if target_str:
    p_name = target_str.split(' (')[0]
    player_data = next((p for p in roster_h + roster_v if p['name'] == p_name), None)
    
    if player_data:
        with st.spinner(f"Scraping ESPN Logs for {p_name}..."):
            df_log = fetch_espn_gamelog(player_data['id'])
        
        if df_log is not None:
            st.markdown("---")
            col_head, col_info = st.columns([1, 4])
            if player_data['headshot']:
                col_head.image(player_data['headshot'], width=100)
            
            l10 = df_log.head(10)
            avg_val = l10[stat_col].mean()
            last_val = l10.iloc[0][stat_col]
            cv = (l10[stat_col].std() / avg_val * 100) if avg_val > 0 else 0
            
            with col_info:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("L10 Avg", f"{avg_val:.1f}")
                m2.metric("Last Game", f"{last_val:.0f}")
                m3.metric("Consistency", f"{cv:.0f}% CV")
                line = m4.number_input("Line:", value=float(round(avg_val, 1)), step=0.5)
            
            diff = avg_val - line
            if diff > 1.5: st.success(f"🔥 OVER EDGE (+{diff:.1f})")
            elif diff < -1.5: st.error(f"❄️ UNDER EDGE ({diff:.1f})")
            else: st.warning("⚖️ FAIR LINE")
            
            # Gráfico: Inverte para ficar cronológico (Antigo -> Recente)
            df_chart = l10.iloc[::-1]
            
            fig = px.line(df_chart, x='Date', y=stat_col, markers=True, title=None)
            fig.add_hline(y=line, line_dash="dash", line_color="#ff4b4b", annotation_text="Line")
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error("No game log data found (Possible connection error or rookie). Check console.")