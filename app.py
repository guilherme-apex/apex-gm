import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import io
import requests
import json
from datetime import datetime, timedelta
from fake_useragent import UserAgent

# ==============================================================================
# 1. CONFIG & STYLES (CLEANEST UI)
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
    
    /* Main Button */
    div.stButton > button:first-child {
        background-color: #00b4d8;
        color: white;
        font-weight: bold;
        height: 50px;
        width: 100%;
        border-radius: 8px;
        font-size: 16px;
        margin-top: 10px;
        border: none;
    }
    div.stButton > button:first-child:hover {
        background-color: #0096c7;
    }
    
    /* Table Header Alignment */
    th { text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# ENDPOINTS
ESPN_GAMELOG = "https://www.espn.com/nba/player/gamelog/_/id/{}/type/nba/year/2026"
ESPN_TEAMS = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
ESPN_ROSTER = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/roster"
ESPN_SCOREBOARD = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"
ESPN_STANDINGS = "http://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
TEAM_LOGO_URL = "https://a.espncdn.com/i/teamlogos/nba/500/{}.png"

ua = UserAgent()
def get_header(): return {'User-Agent': ua.random}

# ==============================================================================
# 2. DATA ENGINE
# ==============================================================================
@st.cache_data(ttl=86400)
def get_all_nba_teams():
    try:
        data = requests.get(ESPN_TEAMS, headers=get_header(), timeout=5).json()
        teams = []
        for t in data['sports'][0]['leagues'][0]['teams']:
            teams.append({
                'id': t['team']['id'],
                'name': t['team']['displayName'],
                'abbr': t['team']['abbreviation'].lower()
            })
        return teams
    except: return []

@st.cache_data(ttl=3600)
def get_defense_rankings():
    try:
        data = requests.get(ESPN_STANDINGS, headers=get_header(), timeout=5).json()
        defense_stats = []
        for conf in data.get('children', []):
            for div in conf.get('children', []):
                for team_entry in div.get('standings', {}).get('entries', []):
                    team_abbr = team_entry['team']['abbreviation'].lower()
                    stats = team_entry.get('stats', [])
                    pts_against = 0.0
                    for s in stats:
                        if s['name'] == 'avgPointsAgainst':
                            pts_against = float(s['value'])
                            break
                    if pts_against > 0:
                        defense_stats.append({'abbr': team_abbr, 'pa': pts_against})
        
        df_def = pd.DataFrame(defense_stats).sort_values(by='pa', ascending=True).reset_index(drop=True)
        df_def['rank'] = df_def.index + 1
        return dict(zip(df_def['abbr'], df_def['rank']))
    except: return {}

def get_matchups_for_date(target_date):
    """3 AM Logic Applied"""
    try:
        date_str = target_date.strftime("%Y%m%d")
        next_day = (target_date + timedelta(days=1)).strftime("%Y%m%d")
        
        url = ESPN_SCOREBOARD.format(f"{date_str}-{next_day}")
        data = requests.get(url, headers=get_header(), timeout=5).json()
        
        def_ranks = get_defense_rankings()
        matchups = {}
        
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        for ev in data.get('events', []):
            raw_date = ev['date']
            game_dt_utc = datetime.strptime(raw_date, "%Y-%m-%dT%H:%MZ")
            game_fantasy_dt = game_dt_utc - timedelta(hours=4)
            game_fantasy_date = game_fantasy_dt.strftime("%Y-%m-%d")
            
            if game_fantasy_date == target_date_str:
                comp = ev['competitions'][0]
                team1 = comp['competitors'][0]['team']['abbreviation'].lower()
                team2 = comp['competitors'][1]['team']['abbreviation'].lower()
                
                rank1 = def_ranks.get(team1, 15)
                rank2 = def_ranks.get(team2, 15)
                
                matchups[team1] = {'opp': team2, 'loc': 'vs', 'opp_rank': rank2}
                matchups[team2] = {'opp': team1, 'loc': '@', 'opp_rank': rank1}
            
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

# ==============================================================================
# 3. ANALYTICS CORE
# ==============================================================================
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
        
        avg_l5 = last_5['FPTS'].mean()
        avg_min_l5 = last_5['MIN'].mean()
        
        projection = (avg_l5 * 0.70) + (avg_season * 0.30)
        trend = avg_l5 - avg_season
        
        stats = {
            "Proj": projection,
            "Trend": trend,
            "FPPM": last_5['FPPM'].mean(),
            "MIN": avg_min_l5
        }
        
        history = last_5[['Date', 'FPTS']].iloc[::-1].to_dict('records')
        return stats, history
    except: return None, None

# ==============================================================================
# 4. INTERFACE
# ==============================================================================
st.title("Apex Content Engine")

# --- FILTERS ---
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
    with st.spinner("Calculating Apex Scores & Matchups..."):
        
        daily_matchups = get_matchups_for_date(analysis_date)
        
        if "All Teams" in selected_teams or not selected_teams:
            target_ids = [t['id'] for t in teams_data]
        else:
            target_ids = [t['id'] for t in teams_data if t['name'] in selected_teams]
            
        rosters_json = asyncio.run(fetch_rosters_global(target_ids))
        
        players_to_check = []
        for r in rosters_json:
            if not r: continue
            team_abbr = r.get('team', {}).get('abbreviation', '').lower()
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
                opp_rank = 0
                apex_score = stats['Proj']
                
                if m_info:
                    opp_rank = m_info['opp_rank']
                    opp_abbr = m_info['opp'].upper()
                    
                    if opp_rank >= 25: 
                        matchup_str = f"{m_info['loc']} {opp_abbr} (Rank {opp_rank}) 🟢"
                        apex_score += 3.0
                    elif opp_rank <= 10: 
                        matchup_str = f"{m_info['loc']} {opp_abbr} (Rank {opp_rank}) 🔴"
                        apex_score -= 1.5
                    else:
                        matchup_str = f"{m_info['loc']} {opp_abbr} ({opp_rank}th)"
                else:
                    matchup_str = "OFF"
                    apex_score = -500
                
                trend_val = stats['Trend']
                if trend_val >= 5.0: 
                    icon = "🔥"
                    apex_score += 4.0
                elif trend_val >= 0.0: 
                    icon = "➖"
                else: 
                    icon = "❄️"
                    apex_score -= 1.0
                
                player_display = f"{p_base['name']} ({p_base['team'].upper()})"

                results.append({
                    "Player": player_display,
                    "RawName": p_base['name'],
                    "Team": p_base['team'].upper(),
                    "Pos": p_base['pos'],
                    "Today Matchup": matchup_str,
                    "Logo": TEAM_LOGO_URL.format(p_base['team']),
                    "Projection": stats['Proj'],
                    "Heat Check": f"{trend_val:+.1f} {icon}",
                    "raw_trend": trend_val,
                    "Efficiency": stats['FPPM'],
                    "Mins (L5)": stats['MIN'],
                    "History": history,
                    "OppRank": opp_rank,
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
    
    st.dataframe(
        df,
        column_order=["Logo", "Player", "Pos", "Today Matchup", "Projection", "Heat Check", "Efficiency", "Mins (L5)"],
        column_config={
            "Logo": st.column_config.ImageColumn("Team", width="small"),
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Today Matchup": st.column_config.TextColumn("Today Matchup", width="medium"),
            "Projection": st.column_config.ProgressColumn("Projection", format="%.1f", min_value=0, max_value=60),
            "Efficiency": st.column_config.NumberColumn("Efficiency", format="%.2f"),
            "Mins (L5)": st.column_config.NumberColumn("Minutes (last 5)", format="%.1f"),
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    st.divider()
    
    # --- PERFORMANCE TREND ---
    st.subheader("Performance Trend")
    selected_player_name = st.selectbox("Select Player:", df['Player'].head(25))
    
    if selected_player_name:
        p_data = df[df['Player'] == selected_player_name].iloc[0]
        
        c_perf1, c_perf2 = st.columns([1, 3])
        
        with c_perf1:
            st.image(p_data['Logo'], width=100)
            st.markdown(f"### {p_data['RawName']}")
            st.metric("Projection", f"{p_data['Projection']:.1f}")
            st.caption(f"{p_data['Team']} | {p_data['Pos']}")
            
        with c_perf2:
            if p_data['History']:
                chart_df = pd.DataFrame(p_data['History'])
                color = '#00ff00' if p_data['raw_trend'] >= 0 else '#ff4b4b'
                st.line_chart(chart_df, x='Date', y='FPTS', color=color, height=300)

elif st.session_state['market_df'] is not None:
    st.warning("No players found. Try changing the date or filters.")