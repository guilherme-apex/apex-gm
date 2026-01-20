import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import io
import requests
from datetime import datetime, timedelta
from fake_useragent import UserAgent

# ==============================================================================
# 1. CONFIG & STYLES
# ==============================================================================
st.set_page_config(
    page_title="Apex Content Engine", 
    layout="wide", 
    page_icon="🏀",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    div.stButton > button:first-child {
        background-color: #00b4d8; color: white; font-weight: bold;
        height: 50px; width: 100%; border-radius: 8px; border: none;
    }
    div.stButton > button:first-child:hover { background-color: #0096c7; }
    th { text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. DADOS REAIS TRANSCRITOS DA SUA IMAGEM (BETTINGPROS)
# ==============================================================================
# PTS ALLOWED (Quanto mais alto, PIOR a defesa = ALVO FÁCIL)
REAL_STATS_FROM_IMAGE = {
    'UTA': 25.15, 'WSH': 24.65, 'NO': 24.22, 'CHI': 23.93, 'SAC': 23.92,
    'ATL': 23.71, 'IND': 23.56, 'POR': 23.52, 'MIA': 23.51, 'CLE': 23.36,
    'LAL': 23.34, 'DEN': 23.17, 'DAL': 23.12, 'CHA': 23.11, 'MEM': 23.09,
    'MIL': 23.03, 'NY': 22.97, 'ORL': 22.86, 'MIN': 22.77, 'BKN': 22.74,
    'PHI': 22.71, 'GS': 22.54, 'SA': 22.54, 'LAC': 22.50, 'PHX': 22.29,
    'TOR': 22.23, 'BOS': 22.02, 'DET': 21.95, 'HOU': 21.78, 'OKC': 21.35
}

# ==============================================================================
# 3. NORMALIZAÇÃO (TRADUTOR DE SIGLAS)
# ==============================================================================
def normalize_abbr(team_name):
    t = str(team_name).upper().strip()
    mapping = {
        'ATLANTA': 'ATL', 'HAWKS': 'ATL',
        'BOSTON': 'BOS', 'CELTICS': 'BOS',
        'BROOKLYN': 'BKN', 'NETS': 'BKN', 'BRK': 'BKN',
        'CHARLOTTE': 'CHA', 'HORNETS': 'CHA', 'CHO': 'CHA',
        'CHICAGO': 'CHI', 'BULLS': 'CHI',
        'CLEVELAND': 'CLE', 'CAVALIERS': 'CLE',
        'DALLAS': 'DAL', 'MAVERICKS': 'DAL',
        'DENVER': 'DEN', 'NUGGETS': 'DEN',
        'DETROIT': 'DET', 'PISTONS': 'DET',
        'GOLDEN STATE': 'GS', 'WARRIORS': 'GS', 'GSW': 'GS',
        'HOUSTON': 'HOU', 'ROCKETS': 'HOU',
        'INDIANA': 'IND', 'PACERS': 'IND',
        'CLIPPERS': 'LAC', 'LA CLIPPERS': 'LAC', 'LAC': 'LAC',
        'LAKERS': 'LAL', 'LA LAKERS': 'LAL', 'LAL': 'LAL',
        'MEMPHIS': 'MEM', 'GRIZZLIES': 'MEM',
        'MIAMI': 'MIA', 'HEAT': 'MIA',
        'MILWAUKEE': 'MIL', 'BUCKS': 'MIL',
        'MINNESOTA': 'MIN', 'TIMBERWOLVES': 'MIN',
        'NEW ORLEANS': 'NO', 'PELICANS': 'NO', 'NOP': 'NO', 'N.O.': 'NO',
        'NEW YORK': 'NY', 'KNICKS': 'NY', 'NYK': 'NY',
        'OKLAHOMA CITY': 'OKC', 'THUNDER': 'OKC',
        'ORLANDO': 'ORL', 'MAGIC': 'ORL',
        'PHILADELPHIA': 'PHI', '76ERS': 'PHI',
        'PHOENIX': 'PHX', 'SUNS': 'PHX', 'PHO': 'PHX',
        'PORTLAND': 'POR', 'TRAIL BLAZERS': 'POR',
        'SACRAMENTO': 'SAC', 'KINGS': 'SAC',
        'SAN ANTONIO': 'SA', 'SPURS': 'SA', 'SAS': 'SA',
        'TORONTO': 'TOR', 'RAPTORS': 'TOR',
        'UTAH': 'UTAH', 'JAZZ': 'UTAH', 'UTA': 'UTA',
        'WASHINGTON': 'WSH', 'WIZARDS': 'WSH', 'WAS': 'WSH'
    }
    if t in mapping: return mapping[t]
    for key, val in mapping.items():
        if key in t: return val
    return t[:3]

ua = UserAgent()
def get_header(): return {'User-Agent': ua.random}

# ==============================================================================
# 4. DATA ENGINE (ESPN BASE)
# ==============================================================================
ESPN_TEAMS = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
ESPN_SCOREBOARD = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"
ESPN_ROSTER = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/roster"
ESPN_GAMELOG = "https://www.espn.com/nba/player/gamelog/_/id/{}/type/nba/year/2026"
TEAM_LOGO_URL = "https://a.espncdn.com/i/teamlogos/nba/500/{}.png"

@st.cache_data(ttl=86400)
def get_all_nba_teams():
    try:
        data = requests.get(ESPN_TEAMS, headers=get_header(), timeout=5).json()
        teams = []
        for t in data['sports'][0]['leagues'][0]['teams']:
            teams.append({'id': t['team']['id'], 'name': t['team']['displayName'], 'abbr': normalize_abbr(t['team']['abbreviation'])})
        return teams
    except: return []

# ==============================================================================
# 5. DVP ENGINE (REAL DATA FROM IMAGE)
# ==============================================================================
def get_dvp_ranks_from_image():
    """
    Transforma os Pontos Cedidos (Imagem) em Ranks (1-30).
    """
    df = pd.DataFrame(list(REAL_STATS_FROM_IMAGE.items()), columns=['Team', 'PTS'])
    # ORDENAÇÃO: Maior PTS = Rank 1 (Alvo Fácil)
    df = df.sort_values(by='PTS', ascending=False).reset_index(drop=True)
    ranks = {}
    for idx, row in df.iterrows():
        ranks[row['Team']] = idx + 1 # Rank 1 a 30
    return ranks

def get_dvp_score(opp_abbr, rank_data):
    opp = normalize_abbr(opp_abbr)
    rank = rank_data.get(opp, 15)
    
    # Lógica Visual (SEM EMOJIS, APENAS TEXTO)
    if rank <= 8:
        return 4.0, f"Easy (#{rank})"    # Rank 1-8 (Verde)
    elif rank <= 12:
        return 2.0, f"Good (#{rank})"    # Rank 9-12 (Verde)
    elif rank >= 25:
        return -2.5, f"Hard (#{rank})"   # Rank 25-30 (Vermelho)
    elif rank >= 20:
        return -1.0, f"Tough (#{rank})"  # Rank 20-24 (Vermelho)
    
    return 0.0, f"Avg (#{rank})"       # Rank 13-19 (Amarelo)

# ==============================================================================
# 6. RESTO DO SISTEMA
# ==============================================================================
def get_matchups_for_date(target_date):
    try:
        date_str = target_date.strftime("%Y%m%d")
        next_day = (target_date + timedelta(days=1)).strftime("%Y%m%d")
        url = ESPN_SCOREBOARD.format(f"{date_str}-{next_day}")
        data = requests.get(url, headers=get_header(), timeout=5).json()
        matchups = {}
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        for ev in data.get('events', []):
            raw_date = ev['date']
            game_dt_utc = datetime.strptime(raw_date, "%Y-%m-%dT%H:%MZ")
            game_fantasy_dt = game_dt_utc - timedelta(hours=4)
            game_fantasy_date = game_fantasy_dt.strftime("%Y-%m-%d")
            
            if game_fantasy_date == target_date_str:
                comp = ev['competitions'][0]
                t1 = normalize_abbr(comp['competitors'][0]['team']['abbreviation'])
                t2 = normalize_abbr(comp['competitors'][1]['team']['abbreviation'])
                matchups[t1] = {'opp': t2, 'loc': 'vs'}
                matchups[t2] = {'opp': t1, 'loc': '@'}
        return matchups
    except: return {}

async def fetch_url(session, url):
    try:
        async with session.get(url, headers=get_header(), timeout=10) as response:
            if response.status == 200:
                if "apis/site/v2" in url: return await response.json()
                return await response.text()
    except: return None

async def fetch_rosters_global(team_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, ESPN_ROSTER.format(tid)) for tid in team_ids]
        return await asyncio.gather(*tasks)

async def fetch_gamelogs(player_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, ESPN_GAMELOG.format(pid)) for pid in player_ids]
        return await asyncio.gather(*tasks)

def analyze_player_performance(html_text):
    if not html_text: return None, None
    try:
        dfs = pd.read_html(io.StringIO(html_text), header=0)
        df = next((d for d in dfs if 'Date' in d.columns and 'PTS' in d.columns), pd.DataFrame())
        if df.empty: return None, None
        df = df[df['Date'] != 'Date']
        df['MIN'] = pd.to_numeric(df['MIN'], errors='coerce')
        df = df.dropna(subset=['MIN'])
        df = df[df['MIN'] > 0]
        cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO']
        for c in cols: 
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['FPTS'] = df['PTS'] + 1.2*df['REB'] + 1.5*df['AST'] + 3*df['STL'] + 3*df['BLK'] - df['TO']
        avg_season = df['FPTS'].mean()
        if avg_season >= 30.0: return None, None
        df['FPPM'] = df['FPTS'] / df['MIN']
        last_5 = df.head(5)
        stats = {
            "Proj": (last_5['FPTS'].mean() * 0.70) + (avg_season * 0.30),
            "Trend": last_5['FPTS'].mean() - avg_season,
            "FPPM": last_5['FPPM'].mean(),
            "MIN": last_5['MIN'].mean()
        }
        history = last_5[['Date', 'FPTS']].iloc[::-1].to_dict('records')
        return stats, history
    except: return None, None

# ==============================================================================
# 7. VISUAL ENGINE (PANDAS STYLER)
# ==============================================================================
def color_matchup(val):
    # Cores de Fundo
    bg_green = 'background-color: #1b5e20; color: white; border-radius: 5px; padding: 4px;'
    bg_red = 'background-color: #b71c1c; color: white; border-radius: 5px; padding: 4px;'
    bg_yellow = 'background-color: #f57f17; color: white; border-radius: 5px; padding: 4px;' # AMARELO PARA AVG
    bg_neutral = ''

    s_val = str(val)
    if 'Easy' in s_val or 'Good' in s_val:
        return bg_green
    elif 'Hard' in s_val or 'Tough' in s_val:
        return bg_red
    elif 'Avg' in s_val:
        return bg_yellow # Aplica o amarelo
    
    return bg_neutral

# ==============================================================================
# 8. INTERFACE
# ==============================================================================
st.title("Apex Content Engine")

with st.expander("Analysis Settings", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    teams_data = get_all_nba_teams()
    team_options = ["All Teams"] + [t['name'] for t in teams_data]
    with c1: selected_teams = st.multiselect("Teams", team_options, default="All Teams")
    with c2: analysis_date = st.date_input("Matchup Date", datetime.now())
    with c3: 
        st.write("") 
        scan_btn = st.button("RUN SCAN")

st.divider()

if 'market_df' not in st.session_state:
    st.session_state['market_df'] = None

if scan_btn:
    with st.spinner("Processing Real Data..."):
        dvp_ranks = get_dvp_ranks_from_image()
        daily_matchups = get_matchups_for_date(analysis_date)
        
        if "All Teams" in selected_teams or not selected_teams:
            target_ids = [t['id'] for t in teams_data]
        else:
            target_ids = [t['id'] for t in teams_data if t['name'] in selected_teams]
            
        rosters_json = asyncio.run(fetch_rosters_global(target_ids))
        
        players_to_check = []
        for r in rosters_json:
            if not r: continue
            team_abbr = normalize_abbr(r.get('team', {}).get('abbreviation', ''))
            for ath in r.get('athletes', []):
                if ath.get('status', {}).get('type') == 'active': 
                    players_to_check.append({
                        'id': ath['id'],
                        'name': ath['fullName'],
                        'team': team_abbr,
                        'pos': ath.get('position', {}).get('abbreviation', 'UTIL')
                    })
        
        logs_html = asyncio.run(fetch_gamelogs([p['id'] for p in players_to_check]))
        
        results = []
        for i, html in enumerate(logs_html):
            p_base = players_to_check[i]
            stats, history = analyze_player_performance(html)
            
            if stats:
                m_info = daily_matchups.get(p_base['team'])
                matchup_display = "OFF"
                
                if m_info:
                    opp_abbr = m_info['opp']
                    dvp_bonus, dvp_text = get_dvp_score(opp_abbr, dvp_ranks)
                    apex_score = stats['Proj'] + dvp_bonus
                    matchup_display = f"{m_info['loc']} {opp_abbr} | {dvp_text}"
                else:
                    apex_score = -500
                
                trend_val = stats['Trend']
                icon = "🔥" if trend_val >= 5.0 else ("❄️" if trend_val < 0 else "➖")
                if trend_val >= 5.0: apex_score += 4.0
                elif trend_val < 0: apex_score -= 1.0

                results.append({
                    "Player": f"{p_base['name']} ({p_base['team']})",
                    "RawName": p_base['name'],
                    "Team": p_base['team'],
                    "Pos": p_base['pos'],
                    "Matchup": matchup_display,
                    "Logo": TEAM_LOGO_URL.format(p_base['team']),
                    "Projection": stats['Proj'],
                    "Heat Check": f"{trend_val:+.1f} {icon}",
                    "raw_trend": trend_val, # AQUI ESTÁ A CORREÇÃO: ADICIONEI ESTA LINHA
                    "Efficiency": stats['FPPM'],
                    "Mins (L5)": stats['MIN'],
                    "History": history,
                    "ApexScore": apex_score
                })
        
        if results:
            df = pd.DataFrame(results)
            df = df.sort_values(by="ApexScore", ascending=False)
            st.session_state['market_df'] = df
        else:
            st.session_state['market_df'] = pd.DataFrame()

# --- VISUALIZATION ---
if st.session_state['market_df'] is not None and not st.session_state['market_df'].empty:
    df = st.session_state['market_df']
    
    styled_df = df.style.map(color_matchup, subset=['Matchup']) \
                        .format({"Projection": "{:.1f}", "Efficiency": "{:.2f}", "Mins (L5)": "{:.1f}"})

    st.dataframe(
        styled_df,
        column_order=["Logo", "Player", "Pos", "Matchup", "Projection", "Heat Check", "Efficiency", "Mins (L5)"],
        column_config={
            "Logo": st.column_config.ImageColumn("Team", width="small"),
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Matchup": st.column_config.TextColumn("Matchup Analysis", width="large"),
            "Projection": st.column_config.ProgressColumn("Projection", format="%.1f", min_value=0, max_value=60),
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    st.divider()
    
    st.subheader("Performance Trend")
    selected_player_name = st.selectbox("Select Player:", df['Player'].head(25))
    if selected_player_name:
        p_data = df[df['Player'] == selected_player_name].iloc[0]
        c1, c2 = st.columns([1, 3])
        with c1:
            st.image(p_data['Logo'], width=100)
            st.markdown(f"### {p_data['RawName']}")
            st.metric("Projection", f"{p_data['Projection']:.1f}")
            st.caption(f"{p_data['Team']} | {p_data['Pos']}")
        with c2:
            if p_data['History']:
                chart_df = pd.DataFrame(p_data['History'])
                # AQUI USA O RAW_TREND QUE AGORA EXISTE
                color = '#00ff00' if p_data['raw_trend'] >= 0 else '#ff4b4b'
                st.line_chart(chart_df, x='Date', y='FPTS', color=color, height=300)

elif st.session_state['market_df'] is not None:
    st.warning("No players found. Try changing the date or filters.")