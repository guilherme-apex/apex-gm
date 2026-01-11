import streamlit as st
import pandas as pd
import numpy as np
import requests
import sqlite3
import io
import plotly.express as px
from datetime import datetime, timedelta
from fake_useragent import UserAgent
from espn_api.basketball import League
import apex_config as cfg 

# ==============================================================================
# 1. CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Apex V81 GM", layout="wide", page_icon="🏛️")

# URLs Globais
ESPN_ROSTER_API = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/roster"
ESPN_GAMELOG_URL = "https://www.espn.com/nba/player/gamelog/_/id/{}/type/nba/year/2026"
ESPN_TEAMS_API = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
ESPN_SCOREBOARD = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"
ESPN_STANDINGS = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/standings"
CBS_INJURY_URL = "https://www.cbssports.com/nba/injuries/"

DB_NAME = "nba_apex_v81.db"
ua = UserAgent()

st.markdown("""
<style>
    .block-container { padding-top: 3rem !important; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; color: #e0e0e0; }
    
    /* UNIVERSAL BADGES */
    .st-active { color: #00ff41; font-weight: 900; font-size: 13px; }
    .st-dtd { color: #ffcc00; font-weight: 900; font-size: 13px; }
    .st-out { color: #ff4b4b; font-weight: 900; font-size: 13px; }
    
    .tier-badge { font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 4px; display: inline-block; width: 35px; text-align: center; margin-right: 5px;}
    .tier-s { background-color: #00ff41; color: black; border: 1px solid white; }
    .tier-a { background-color: #ffcc00; color: black; }
    .tier-b { background-color: #00aaff; color: white; }
    
    /* BUZZ & CARDS */
    .buzz-card { background-color: #222; border: 1px solid #444; border-radius: 10px; padding: 20px; margin-bottom: 20px; text-align: center; }
    .buzz-title { color: #ffcc00; font-size: 20px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; }
    .buzz-value { font-size: 32px; font-weight: 900; color: white; }
    .buzz-sub { color: #888; font-size: 14px; }
    
    .finder-card { background-color: #262626; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #00ff41; display: flex; justify-content: space-between; align-items: center; }
    .finder-left { display: flex; flex-direction: column; }
    .finder-val { font-size: 20px; font-weight: 900; color: #00ff41; text-align: right; min-width: 100px; }
    
    .radar-card { background-color: #1a1a2e; border: 1px solid #16213e; border-left: 5px solid #ff4b4b; padding: 15px; margin-bottom: 10px; border-radius: 8px; }
    .radar-discount { background-color: #ff4b4b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    
    .trade-card { background-color: #1e1e1e; padding: 20px; border-radius: 12px; border: 1px solid #333; text-align: center; margin-top: 20px; }
    .trade-detail-box { background-color: #2b2b2b; padding: 12px; border-radius: 8px; margin-bottom: 8px; text-align: left; font-size: 14px; border-left: 4px solid #555; }
    .detail-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .detail-label { color: #aaa; }
    .detail-val { font-weight: bold; color: #fff; }
    
    .trade-verdict { font-size: 28px; font-weight: 900; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }
    .trade-win { color: #00ff41; } .trade-loss { color: #ff4b4b; } .trade-fair { color: #ffcc00; }
    .penalty-tag { color: #ff4b4b; font-size: 11px; font-weight: bold; text-transform: uppercase; }
    .momentum-tag { color: #00ff41; font-size: 11px; font-weight: bold; text-transform: uppercase; }
    
    /* MATCHUP H2H TABLE */
    .h2h-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; align-items: center; }
    .h2h-player { flex: 1; font-size: 15px; }
    .h2h-score { width: 60px; text-align: center; font-weight: bold; font-size: 16px; }
    .h2h-vs { width: 40px; text-align: center; color: #666; font-size: 12px; }
    .weak-spot { color: #ff4b4b; font-weight: bold; }
    .mod-spot { color: #ffcc00; }
    .strong-spot { color: #00ff41; }
    
    .coach-card { background-color: #1a1a2e; border: 1px solid #333; border-left: 5px solid #ffcc00; padding: 15px; margin-top: 15px; border-radius: 8px; }
    .coach-title { font-size: 18px; font-weight: bold; color: white; margin-bottom: 10px; display: flex; align-items: center; gap: 10px;}
    .coach-action { background-color: #222; padding: 8px; border-radius: 4px; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .drop-text { color: #ff4b4b; font-weight: bold; }
    .add-text { color: #00ff41; font-weight: bold; }
    .finder-title { font-size: 18px; font-weight: bold; color: white; }
    .finder-sub { font-size: 14px; color: #bbb; margin-top: 4px;}
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
    return pd.read_json(io.StringIO(row[0])) if row else None

init_db()

# ==============================================================================
# 3. FUNÇÕES GLOBAIS
# ==============================================================================
def get_header(): return {'User-Agent': ua.random, 'Connection': 'keep-alive'}

@st.cache_data(ttl=3600)
def fetch_cbs_injuries():
    try:
        tables = pd.read_html(CBS_INJURY_URL, storage_options={'User-Agent': ua.random})
        injured_players = []
        for df in tables:
            if 'Player' in df.columns:
                injured_players.extend(df['Player'].tolist())
        return [str(n).strip() for n in injured_players]
    except: return []

@st.cache_data(ttl=86400) 
def get_nba_teams():
    try:
        data = requests.get(ESPN_TEAMS_API, headers=get_header(), timeout=10).json()
        teams = []
        for t in data['sports'][0]['leagues'][0]['teams']:
            teams.append({'name': t['team']['displayName'], 'id': t['team']['id'], 'abbr': t['team']['abbreviation']})
        return teams
    except: return []

@st.cache_data(ttl=86400)
def fetch_all_players_global():
    teams = get_nba_teams()
    all_players = []
    for t in teams:
        try:
            url = ESPN_ROSTER_API.format(t['id'])
            data = requests.get(url, headers=get_header(), timeout=5).json()
            for item in data['athletes']:
                p_name = item['fullName']
                label = f"{p_name} ({t['abbr']})"
                all_players.append({'label': label, 'id': item['id']})
        except: pass
    return sorted(all_players, key=lambda x: x['label'])

@st.cache_data(ttl=86400)
def fetch_dynamic_weak_defenses():
    try:
        data = requests.get(ESPN_STANDINGS, headers=get_header(), timeout=10).json()
        teams_stats = []
        for conference in data['children']:
            for team_entry in conference['standings']['entries']:
                stats = team_entry.get('stats', [])
                win_pct = 0.0
                for s in stats:
                    if s.get('name') == 'winPercent': win_pct = float(s.get('value', 0)); break
                teams_stats.append({'name': team_entry['team']['displayName'], 'win_pct': win_pct})
        sorted_teams = sorted(teams_stats, key=lambda x: x['win_pct'])
        return [t['name'] for t in sorted_teams[:8]]
    except: return ['Wizards', 'Pistons', 'Hornets', 'Trail Blazers', 'Jazz', 'Bulls', 'Nets', 'Raptors']

@st.cache_data(ttl=3600)
def fetch_espn_roster(team_espn_id):
    try:
        url = ESPN_ROSTER_API.format(team_espn_id)
        data = requests.get(url, headers=get_header(), timeout=10).json()
        players = []
        for item in data['athletes']:
            status = item.get('status', {}).get('type', 'active') 
            players.append({'name': item['fullName'], 'id': item['id'], 'status': status})
        return players
    except: return []

def fetch_espn_gamelog(espn_player_id):
    cached = get_cache('player_log_cache', espn_player_id)
    if cached is not None: return cached
    try:
        url = ESPN_GAMELOG_URL.format(espn_player_id)
        response = requests.get(url, headers={'User-Agent': ua.random}, timeout=10)
        if response.status_code != 200: return None
        dfs = pd.read_html(io.StringIO(response.text), header=0)
        df_log = pd.DataFrame()
        for df in dfs:
            if 'Date' in df.columns and 'PTS' in df.columns: df_log = df; break
        if df_log.empty: return None
        df_log = df_log[df_log['Date'] != 'Date']
        df_log = df_log[~df_log['MIN'].isin(['DNP', '--'])]
        cols_to_num = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'MIN']
        for c in cols_to_num: df_log[c] = pd.to_numeric(df_log[c], errors='coerce').fillna(0)
        df_log['FPTS'] = df_log['PTS'] + 1.2*df_log['REB'] + 1.5*df_log['AST'] + 3*df_log['STL'] + 3*df_log['BLK'] - df_log['TO']
        save_cache('player_log_cache', espn_player_id, df_log)
        return df_log
    except: return None

# ==============================================================================
# 4. INTELIGÊNCIA MATEMÁTICA V81
# ==============================================================================
@st.cache_resource(ttl=3600)
def get_league_connection():
    try:
        league = League(league_id=cfg.LEAGUE_ID, year=cfg.YEAR, espn_s2=cfg.ESPN_S2, swid=cfg.SWID)
        return league
    except Exception as e: return None

def get_current_week_safe(league_obj):
    try:
        if hasattr(league_obj, 'currentMatchupPeriod'): return league_obj.currentMatchupPeriod
        if hasattr(league_obj, 'current_matchup_period'): return league_obj.current_matchup_period
        if hasattr(league_obj, 'settings') and hasattr(league_obj.settings, 'reg_season_count'): return league_obj.scoringPeriodId
    except: pass
    return 1

def get_stats_from_map(stats_map, key_type='avg'):
    keys = [f"{cfg.YEAR}_total", "2026_total", "total", f"{cfg.YEAR}_projected", "2026_projected"]
    for k in keys:
        if k in stats_map:
            if key_type in stats_map[k]: return stats_map[k][key_type]
            return stats_map[k]
    return None

def get_last_15_stats(stats_map):
    keys = [f"{cfg.YEAR}_last_15", "2026_last_15", "last_15"]
    for k in keys:
        if k in stats_map:
            if 'avg' in stats_map[k]: return stats_map[k]['avg']
            return stats_map[k]
    return None

def calculate_player_value_v70(player_obj, mode='trade'):
    """V70 Engine"""
    try:
        stats_map = player_obj.stats
        real_stats = get_stats_from_map(stats_map)
        l15_stats = get_last_15_stats(stats_map)
        proj_dict_raw = stats_map.get(f"{cfg.YEAR}_projected") or stats_map.get("2026_projected")
        proj_stats = proj_dict_raw.get('avg') if proj_dict_raw and 'avg' in proj_dict_raw else proj_dict_raw

        def compute_score(s_dict):
            if not s_dict: return 0.0
            score = 0.0
            for k, v in cfg.SCORING_RULES.items():
                score += s_dict.get(k, 0) * v
            return score

        s_real = compute_score(real_stats)
        s_l15 = compute_score(l15_stats)
        s_proj = compute_score(proj_stats)
        
        if s_l15 == 0: s_l15 = s_real
        if s_proj == 0: s_proj = s_real
        if s_real == 0: s_real = s_proj

        if mode == 'waiver': return s_real, 0.0
        elif mode == 'trade':
            raw_value = (s_real * 0.4) + (s_l15 * 0.4) + (s_proj * 0.2)
            penalty = 0.0
            status = player_obj.injuryStatus
            if status == 'OUT': penalty = 0.50
            elif status == 'DAY_TO_DAY': penalty = 0.10
            final_value = raw_value * (1 - penalty)
            meta = {"real": s_real, "l15": s_l15, "proj": s_proj, "penalty": penalty}
            return final_value, meta
    except: return 0.0, {}

def get_ownership_safe(player_obj):
    try:
        if hasattr(player_obj, 'percent_owned'): return player_obj.percent_owned
        if hasattr(player_obj, 'percentOwned'): return player_obj.percentOwned
        if hasattr(player_obj, 'ownership'): return player_obj.ownership.get('percentOwned', 0.0)
        return 0.0
    except: return 0.0

# ==============================================================================
# 5. LOGICA GLOBAL
# ==============================================================================
@st.cache_data(ttl=3600)
def analyze_schedule_advanced(start_date, end_date):
    weak_defs = fetch_dynamic_weak_defenses()
    team_data = {}
    all_teams = get_nba_teams()
    for t in all_teams: team_data[t['name']] = {'games': 0, 'b2b': 0, 'dates': [], 'opponents': [], 'easy_matchups': 0}
    
    delta = (end_date - start_date).days + 1
    current = start_date
    for _ in range(delta):
        d_str = current.strftime('%Y%m%d')
        try:
            url = ESPN_SCOREBOARD.format(d_str)
            data = requests.get(url, headers=get_header(), timeout=5).json()
            for e in data['events']:
                h = e['competitions'][0]['competitors'][0]['team']['displayName']
                a = e['competitions'][0]['competitors'][1]['team']['displayName']
                if h in team_data:
                    team_data[h]['games'] += 1; team_data[h]['dates'].append(current); team_data[h]['opponents'].append(a)
                    if any(w in a for w in weak_defs): team_data[h]['easy_matchups'] += 1
                if a in team_data:
                    team_data[a]['games'] += 1; team_data[a]['dates'].append(current); team_data[a]['opponents'].append(h)
                    if any(w in h for w in weak_defs): team_data[a]['easy_matchups'] += 1
        except: pass
        current += timedelta(days=1)
    
    for team, stats in team_data.items():
        dates = sorted(stats['dates'])
        b2b = 0
        for i in range(len(dates) - 1):
            if (dates[i+1] - dates[i]).days == 1: b2b += 1
        stats['b2b'] = b2b
    return team_data, weak_defs

def calculate_tier_global(games, trend, b2b, avg_fpts, easy_matchups):
    score = 0
    if games >= 4: score += 50
    elif games == 3: score += 30
    elif games == 2: score -= 10
    score += (easy_matchups * 5)
    if trend > 5: score += 15
    elif trend > 0: score += 5
    if avg_fpts > 30: score += 10
    score -= (b2b * 8)
    if score >= 60: return "S"
    elif score >= 35: return "A"
    else: return "B"

def calculate_trade_value_global(player_df):
    if player_df is None or player_df.empty: return 0
    return (player_df['FPTS'].mean() * 0.5) + (player_df.head(10)['FPTS'].mean() * 0.3) + (player_df.head(5)['FPTS'].mean() * 0.2)

# ==============================================================================
# 6. UI PRINCIPAL
# ==============================================================================
st.sidebar.title("🏛️ Apex V81 Commish")
app_mode = st.sidebar.selectbox("Select Mode:", ["🌍 General Analysis (X/Twitter)", "🏆 My League Manager (Nba GyG)"])

if 'scan_results' not in st.session_state: st.session_state.scan_results = None
if 'all_players_global' not in st.session_state: st.session_state.all_players_global = []

# MODO GERAL
if app_mode == "🌍 General Analysis (X/Twitter)":
    tool = st.sidebar.radio("Global Tools:", ["🚀 Smart Scanner", "⚖️ Trade Calculator", "📉 Buy/Sell", "🗓️ Schedule"])
    if tool == "🚀 Smart Scanner":
        st.header("🚀 Global Waiver Scanner")
        c1, c2, c3 = st.columns([1,1,1])
        d1 = c1.date_input("Start", datetime.today())
        d2 = c2.date_input("End", datetime.today() + timedelta(days=6))
        if c3.button("⚡ SCAN MARKET", type="primary"):
            st.session_state.scan_results = None
            status = st.empty(); bar = st.progress(0)
            status.text("🚑 Fetching CBS Injuries..."); cbs_inj = fetch_cbs_injuries()
            status.text("📊 Analyzing Schedule..."); sched, weak = analyze_schedule_advanced(d1, d2)
            target_teams = [t for t, s in sched.items() if s['games'] >= 3]
            all_teams = get_nba_teams()
            results = []
            if target_teams:
                for i, tname in enumerate(target_teams):
                    status.text(f"Scanning {tname}..."); bar.progress((i+1)/len(target_teams))
                    tid = next((x['id'] for x in all_teams if x['name'] == tname), None)
                    t_sched = sched[tname]
                    if tid:
                        roster = fetch_espn_roster(tid)
                        for p in roster[:13]:
                            if any(inj_name in p['name'] for inj_name in cbs_inj): continue 
                            if p.get('status') != 'active': continue
                            df = fetch_espn_gamelog(p['id'])
                            if df is not None and not df.empty:
                                avg = df['FPTS'].mean()
                                if 12 <= avg <= 55:
                                    l5 = df.head(5); avg_l5 = l5['FPTS'].mean(); trend = avg_l5 - avg
                                    if l5['MIN'].mean() > 10:
                                        tier = calculate_tier_global(t_sched['games'], trend, t_sched['b2b'], avg, t_sched['easy_matchups'])
                                        weak_opps = [o for o in t_sched['opponents'] if any(w in o for w in weak)]
                                        matchup = ", ".join(weak_opps[:2])
                                        results.append({"Tier": tier, "Player": p['name'], "Team": tname, "Games": t_sched['games'], 
                                                        "Context": f"{t_sched['b2b']} B2Bs", "Matchups": matchup if matchup else "Avg/Hard", "Trend": trend, "FPTS": avg_l5})
            status.empty(); bar.empty()
            if results:
                df = pd.DataFrame(results)
                tier_map = {"S": 0, "A": 1, "B": 2}
                df['Rank'] = df['Tier'].map(tier_map)
                st.session_state.scan_results = df.sort_values(by=['Rank', 'Trend'], ascending=[True, False])
            else: st.warning("No players found.")
        if st.session_state.scan_results is not None:
            df = st.session_state.scan_results
            st.success(f"Found {len(df)} players.")
            for _, r in df.iterrows():
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([0.5, 2.5, 1, 1, 1.5])
                    col1.markdown(f"<span class='tier-badge tier-{r['Tier'].lower()}'>{r['Tier']}</span>", unsafe_allow_html=True)
                    col2.markdown(f"**{r['Player']}** ({r['Team']})")
                    col3.markdown(f"🗓️ **{r['Games']} G**")
                    col4.markdown(f"📈 **{r['FPTS']:.1f}** ({r['Trend']:+.1f})")
                    matchup_html = f"<span class='tag-matchup'>vs {r['Matchups']}</span>" if r['Matchups'] != "Avg/Hard" else ""
                    b2b_html = "risk-b2b" if "0 B2Bs" not in r['Context'] else ""
                    col5.markdown(f"{matchup_html} <span class='{b2b_html}'>{r['Context']}</span>", unsafe_allow_html=True)
                    st.divider()
    elif tool == "⚖️ Trade Calculator":
        st.header("⚖️ Global Trade Calculator")
        if not st.session_state.all_players_global:
            with st.spinner("Loading Database..."): st.session_state.all_players_global = fetch_all_players_global()
        all_p = [x['label'] for x in st.session_state.all_players_global]
        c1, c2 = st.columns(2)
        give = c1.multiselect("They Receive", all_p)
        get = c2.multiselect("I Receive", all_p)
        if st.button("Analyze"): pass
    elif tool == "🗓️ Schedule":
        d1 = st.date_input("Start", datetime.today()); d2 = st.date_input("End", datetime.today()+timedelta(days=6))
        if st.button("Analyze"):
            data, _ = analyze_schedule_advanced(d1, d2)
            srt = sorted(data.items(), key=lambda x: x[1]['games'], reverse=True)
            c1, c2, c3 = st.columns(3)
            with c1: 
                st.success("🔥 HIGH VOLUME")
                for t, s in srt: 
                    if s['games']>=4: st.write(f"**{t}**: {s['games']} G")
            with c2: st.info("⚖️ STANDARD"); [st.write(f"{t}: {s['games']} G") for t,s in srt if s['games']==3]
            with c3: st.error("❄️ LOW VOLUME"); [st.write(f"{t}: {s['games']} G") for t,s in srt if s['games']<=2]

# ------------------------------------------------------------------------------
# MODO LIGA (V81 STABLE)
# ------------------------------------------------------------------------------
elif app_mode == "🏆 My League Manager (Nba GyG)":
    tool = st.sidebar.radio("League Tools:", ["📢 League Buzz HQ (New)", "🔍 Smart Trade Hunter", "⚔️ Matchup Faceoff", "💎 Waiver Sniper", "⚖️ League Trade Machine", "📊 Power Rankings"])
    league = get_league_connection()
    if not league: st.error("Connection Failed."); st.stop()

    # --- LEAGUE BUZZ HQ (V81 FIXED RADIO) ---
    if tool == "📢 League Buzz HQ (New)":
        st.header("📢 League Buzz HQ")
        # V81: USO DE RADIO BUTTON PARA NAVEGAÇÃO ESTÁVEL
        buzz_mode = st.radio("Choose Buzz Type:", ["🏆 Weekly Wrap-Up", "⚖️ Trade Judgement Day", "📰 Waiver News"], horizontal=True)
        st.divider()
        
        # 1. WEEKLY AWARDS
        if buzz_mode == "🏆 Weekly Wrap-Up":
            st.subheader("Weekly Awards & Recap")
            try:
                current_week = get_current_week_safe(league)
                target_week = current_week - 1 if current_week > 1 else 1
                matchups = None
                try: matchups = league.box_scores(matchup_period=target_week)
                except: pass
                if not matchups:
                    try: matchups = league.box_scores(matchup_period=current_week)
                    except: pass
                
                if matchups:
                    scores = []
                    for m in matchups:
                        scores.append({"team": m.home_team.team_name, "pts": m.home_score})
                        scores.append({"team": m.away_team.team_name, "pts": m.away_score})
                    scores.sort(key=lambda x: x['pts'], reverse=True)
                    high_score = scores[0]; low_score = scores[-1]
                    
                    buzz_text = f"🏀 **LEAGUE RECAP: WEEK {target_week}** 🏀\n\n🔥 **THE JUGGERNAUT (Highest Score):**\n{high_score['team']} with {high_score['pts']:.1f} FPTS!\n\n🧱 **THE BRICKLAYER (Lowest Score):**\n{low_score['team']} with {low_score['pts']:.1f} FPTS...\n\n📊 **POWER RANKINGS UPDATE:**\n(Check Apex GM)\n\n#LeagueBuzz"
                    c1, c2 = st.columns(2)
                    c1.markdown(f"<div class='buzz-card'><div class='buzz-title'>🔥 HIGH SCORE</div><div class='buzz-value'>{high_score['pts']:.1f}</div><div class='buzz-sub'>{high_score['team']}</div></div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='buzz-card'><div class='buzz-title'>🧱 LOW SCORE</div><div class='buzz-value'>{low_score['pts']:.1f}</div><div class='buzz-sub'>{low_score['team']}</div></div>", unsafe_allow_html=True)
                    st.text_area("📋 Copy to Group Chat:", value=buzz_text, height=200)
                else: st.warning("No matchups found.")
            except Exception as e: st.error(f"Error: {e}")

        # 2. TRADE JUDGE
        elif buzz_mode == "⚖️ Trade Judgement Day":
            st.subheader("⚖️ Trade Judgement Day")
            teams = sorted(league.teams, key=lambda x: x.team_name); tnames = [t.team_name for t in teams]
            c1, c2 = st.columns(2); t1n = c1.selectbox("Team A", tnames, key="jb1"); t2n = c2.selectbox("Team B", tnames, key="jb2")
            t1 = next(t for t in teams if t.team_name == t1n); t2 = next(t for t in teams if t.team_name == t2n)
            p1s = c1.multiselect(f"{t1n} sends:", [p.name for p in t1.roster], key="jps1"); p2s = c2.multiselect(f"{t2n} sends:", [p.name for p in t2.roster], key="jps2")
            if st.button("🔨 JUDGE THIS TRADE"):
                val1 = sum([calculate_player_value_v70(next(x for x in t1.roster if x.name==n), 'trade')[0] for n in p1s])
                val2 = sum([calculate_player_value_v70(next(x for x in t2.roster if x.name==n), 'trade')[0] for n in p2s])
                diff = val2 - val1; pct = (diff/val1*100) if val1>0 else 0
                verdict = "🤝 FAIR TRADE"; 
                if pct > 5: verdict = f"✅ WIN: {t1n.upper()}"
                elif pct < -5: verdict = f"✅ WIN: {t2n.upper()}"
                report = f"⚖️ **OFFICIAL TRADE REVIEW** ⚖️\n\n**{t1n}** sends: {', '.join(p1s)} ({val1:.1f} Val)\n**{t2n}** sends: {', '.join(p2s)} ({val2:.1f} Val)\n\n📊 **VERDICT:** {verdict}\n(Net Value Swing: {diff:+.1f})\n\n#ApexGM"
                st.markdown(f"<div class='buzz-card'><div class='buzz-title'>VERDICT</div><div class='buzz-value' style='color:#00ff41'>{verdict}</div></div>", unsafe_allow_html=True); st.text_area("📋 Copy Verdict:", value=report, height=200)

        # 3. WAIVER NEWS (V81 UPGRADE: POSITION FILTER)
        elif buzz_mode == "📰 Waiver News":
            st.subheader("📰 Waiver Wire Alert")
            # V81: FILTRO DE POSIÇÃO
            pos_filter = st.multiselect("Filter by Position (Optional):", ["PG", "SG", "SF", "PF", "C"])
            
            if st.button("GENERATE WAIVER REPORT"):
                fas = league.free_agents(size=100); top_gems = []
                for p in fas:
                    if p.injuryStatus=='OUT' or p.proTeam=='FA': continue
                    if pos_filter and p.position not in pos_filter: continue # Filtro
                    v, _ = calculate_player_value_v70(p, 'waiver'); 
                    if v > 20: top_gems.append((p.name, v, p.position))
                top_gems.sort(key=lambda x: x[1], reverse=True); top3 = top_gems[:5]
                
                pos_txt = f" ({', '.join(pos_filter)})" if pos_filter else ""
                news = f"💎 **WAIVER WIRE ALERT{pos_txt}** 💎\n\nTop Available Agents:\n"
                for p, v, pos in top3: news += f"🔹 {p} ({pos}) - Avg: {v:.1f}\n"
                news += "\nGrab them before they're gone! 🏃💨"; st.text_area("📋 Copy News:", value=news, height=200)

    # --- DEMAIS FERRAMENTAS MANTIDAS (V76) ---
    elif tool == "⚔️ Matchup Faceoff":
        st.header("⚔️ Matchup Faceoff & Coach's Intel"); teams = sorted(league.teams, key=lambda x: x.team_name); tnames = [t.team_name for t in teams]; c1, c2, c3 = st.columns([2, 0.5, 2]); 
        with c1: t1n = st.selectbox("My Team", tnames, key="m_t1")
        with c3: t2n = st.selectbox("Opponent", [n for n in tnames if n!=t1n], key="m_t2")
        if st.button("🔥 SIMULATE MATCHUP"):
            t1 = next(t for t in teams if t.team_name == t1n); t2 = next(t for t in teams if t.team_name == t2n)
            def get_sorted_roster(team):
                data = []
                for p in team.roster:
                    if p.injuryStatus == 'OUT': continue
                    if p.lineupSlot == 'IR': continue
                    v, _ = calculate_player_value_v70(p, mode='waiver'); data.append({"p": p, "val": v})
                data.sort(key=lambda x: x['val'], reverse=True); return data
            r1 = get_sorted_roster(t1); r2 = get_sorted_roster(t2); s1 = sum([x['val'] for x in r1[:12]]); s2 = sum([x['val'] for x in r2[:12]]); delta = s1 - s2
            c_a, c_b, c_c = st.columns([1,1,1]); c_a.markdown(f"<div style='text-align:center'><div style='font-size:32px; font-weight:bold'>{s1:.1f}</div><div style='color:#aaa'>{t1n}</div></div>", unsafe_allow_html=True); c_b.markdown(f"<div style='text-align:center; font-size:24px; font-weight:900; color:#ffcc00; margin-top:10px'>VS</div>", unsafe_allow_html=True); c_c.markdown(f"<div style='text-align:center'><div style='font-size:32px; font-weight:bold'>{s2:.1f}</div><div style='color:#aaa'>{t2n}</div></div>", unsafe_allow_html=True)
            if delta > 0: st.success(f"✅ {t1n} is favored by {delta:.1f} points")
            else: st.error(f"⚠️ {t1n} is losing by {abs(delta):.1f} points")
            st.divider(); st.subheader("Head-to-Head Roster Comparison (Active Rotation)"); max_len = min(13, max(len(r1), len(r2))); c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3]); c1.markdown("**My Roster**"); c2.markdown("**Avg**"); c3.markdown("**Diff**"); c4.markdown("**Avg**"); c5.markdown("**Opponent**")
            for i in range(max_len):
                p1 = r1[i] if i < len(r1) else None; p2 = r2[i] if i < len(r2) else None; v1 = p1['val'] if p1 else 0; v2 = p2['val'] if p2 else 0; diff = v1 - v2; hl_class = ""
                if diff < -5: hl_class = "weak-spot"
                elif diff < 0: hl_class = "mod-spot"
                elif diff > 5: hl_class = "strong-spot"
                with st.container(): col_a, col_b, col_c, col_d, col_e = st.columns([3, 1, 1, 1, 3]); 
                if p1: col_a.markdown(f"{p1['p'].name}"); col_b.markdown(f"**{v1:.1f}**")
                col_c.markdown(f"<span class='{hl_class}'>{diff:+.1f}</span>", unsafe_allow_html=True)
                if p2: col_d.markdown(f"**{v2:.1f}**"); col_e.markdown(f"{p2['p'].name}")
            st.divider(); st.subheader("👨‍🏫 Coach's Intel (Smart Add/Drops)"); weak_links = r1[-3:] if len(r1) >= 3 else r1; free_agents = league.free_agents(size=20); best_fa = []
            for fa in free_agents:
                if fa.injuryStatus == 'OUT' or fa.proTeam == 'FA': continue
                val, _ = calculate_player_value_v70(fa, mode='waiver'); best_fa.append({"p": fa, "val": val})
            best_fa.sort(key=lambda x: x['val'], reverse=True); top_fa = best_fa[:3]; suggestion_found = False
            for weak in weak_links:
                if top_fa:
                    fa_target = top_fa[0]
                    if fa_target['val'] > (weak['val'] + 2.0):
                        diff = fa_target['val'] - weak['val']; st.markdown(f"<div class='coach-card'><div class='coach-title'>💡 Upgrade Opportunity for <b>{weak['p'].name}</b></div><div class='coach-action'><span class='drop-text'>DROP: {weak['p'].name} ({weak['val']:.1f})</span><span>➡️</span><span class='add-text'>ADD: {fa_target['p'].name} ({fa_target['val']:.1f})</span></div><div style='text-align:right; font-size:12px; color:#aaa'>Net: <span style='color:#00ff41'>+{diff:.1f}</span></div></div>", unsafe_allow_html=True); suggestion_found = True; top_fa.pop(0)
            if not suggestion_found: st.info("✅ No obvious waiver upgrades.")

    elif tool == "🔍 Smart Trade Hunter":
        # (Mantido Igual)
        st.header("🔍 Smart Trade Hunter"); teams = sorted(league.teams, key=lambda x: x.team_name); tnames = [t.team_name for t in teams]; my_team_name = st.selectbox("My Team", tnames, key="find_t"); my_team = next(t for t in teams if t.team_name == my_team_name); tab1, tab2, tab3 = st.tabs(["📦 Package Finder", "🤖 Sell High", "🦅 Opportunity Radar"])
        with tab1:
            trade_assets = [p.name for p in my_team.roster]; players_to_sell_names = st.multiselect("Select players to package (Max 3):", trade_assets, max_selections=3)
            if st.button("🔎 FIND TARGETS", key="btn_manual"):
                if not players_to_sell_names: st.error("Select player.")
                else:
                    total_out = 0
                    for name in players_to_sell_names: p=next(x for x in my_team.roster if x.name==name); v,_=calculate_player_value_v70(p, mode='trade'); total_out+=v
                    st.info(f"Package Value: **{total_out:.1f}**"); found=[]
                    for opp in teams:
                        if opp.team_name==my_team_name: continue
                        for tgt in opp.roster:
                            if tgt.injuryStatus=='OUT': continue
                            vin, min_ = calculate_player_value_v70(tgt, mode='trade'); ratio = vin/total_out if total_out>0 else 0
                            if 0.95<=ratio<=1.15 and vin>18: pct=((vin-total_out)/total_out)*100; found.append({"p":tgt.name,"t":opp.team_name,"avg":min_['real'],"pct":pct})
                    if found:
                        found.sort(key=lambda x: x['pct'], reverse=True)
                        for ft in found: st.markdown(f"<div class='finder-card'><div class='finder-left'><div class='finder-title'>{ft['p']} <span style='color:#888; font-size:14px'>({ft['t']})</span></div><div class='finder-sub'>Avg: {ft['avg']:.1f}</div></div><div class='finder-val'>+{ft['pct']:.1f}% WIN</div></div>", unsafe_allow_html=True)
                    else: st.warning("No targets.")
        with tab2:
            st.markdown("### 📈 Sell High Candidates"); sell_highs = []
            for p in my_team.roster:
                if p.injuryStatus=='OUT': continue
                _, m = calculate_player_value_v70(p, mode='trade')
                if m['l15']>(m['real']*1.15) and m['real']>15: diff=m['l15']-m['real']; sell_highs.append((p, diff, m))
            if not sell_highs: st.success("No sell high candidates.")
            else:
                for p, diff, m in sell_highs:
                    if st.button(f"Find Trades for {p.name} (Trending +{diff:.1f})"):
                        st.divider(); v_out, _ = calculate_player_value_v70(p, mode='trade'); found=[]
                        for opp in teams:
                            if opp.team_name==my_team_name: continue
                            for tgt in opp.roster:
                                if tgt.injuryStatus=='OUT': continue
                                vin, min_ = calculate_player_value_v70(tgt, mode='trade'); stable = min_['l15']<=(min_['real']*1.05); ratio=vin/v_out
                                if 0.95<=ratio<=1.15 and stable: pct=((vin-v_out)/v_out)*100; found.append({"p":tgt.name,"t":opp.team_name,"v":min_['real'],"pct":pct})
                        found.sort(key=lambda x: x['pct'], reverse=True)
                        for ft in found: st.markdown(f"<div class='finder-card' style='border-left: 5px solid #00aaff'><div class='finder-left'><div class='finder-title'>{ft['p']} <span style='color:#00aaff; font-size:12px'>STABLE TARGET</span></div><div class='finder-sub'>Avg: {ft['v']:.1f}</div></div><div class='finder-val' style='color:#00aaff'>+{ft['pct']:.1f}%</div></div>", unsafe_allow_html=True)
        with tab3:
            st.markdown("### 🦅 Global Opportunity Radar"); 
            if st.button("📡 SCAN LEAGUE"):
                with st.spinner("Scanning..."):
                    opps = []
                    for opp in teams:
                        if opp.team_name==my_team_name: continue
                        for p in opp.roster:
                            if p.injuryStatus=='OUT': continue
                            _, m = calculate_player_value_v70(p, mode='trade')
                            if m['proj']>25 and m['l15']<(m['real']*0.85) and m['l15']>0:
                                drop=m['real']-m['l15']; pd= (drop/m['real'])*100; opps.append({"p":p.name,"t":opp.team_name,"r":m['real'],"l":m['l15'],"d":drop,"pd":pd})
                    if opps:
                        opps.sort(key=lambda x: x['d'], reverse=True)
                        for i, o in enumerate(opps): st.markdown(f"<div class='radar-card'><div class='radar-header'><div style='font-size:18px; font-weight:bold; color:white'>{i+1}. {o['p']} <span style='color:#888'>({o['t']})</span></div><span class='radar-discount'>📉 TRADING AT -{int(o['pd'])}% DISCOUNT</span></div><div style='display:flex; justify-content:space-between; margin-top:5px'><span style='color:#aaa'>Season Avg: <b style='color:white'>{o['r']:.1f}</b></span><span style='color:#ff4b4b'>Last 15: <b>{o['l']:.1f}</b> (Slumping)</span></div></div>", unsafe_allow_html=True)
                    else: st.success("No distressed assets.")

    elif tool == "💎 Waiver Sniper":
        # (Mantido Igual)
        st.header(f"💎 Waiver Wire: {league.settings.name}")
        if st.button("🚀 SCAN AVAILABLE"):
            with st.spinner("Analyzing..."):
                fas = league.free_agents(size=100); gems = []
                for p in fas:
                    if p.injuryStatus=='OUT' or p.proTeam=='FA': continue
                    fpts, _ = calculate_player_value_v70(p, mode='waiver'); own=get_ownership_safe(p)
                    if fpts>10:
                        tier="B"; 
                        if fpts>28: tier="S"
                        elif fpts>20: tier="A"
                        gems.append({"Tier":tier,"Player":p.name,"Team":p.proTeam,"Status":p.injuryStatus,"FPTS":fpts,"Own":own})
                if gems:
                    df=pd.DataFrame(gems).sort_values(by="FPTS", ascending=False); st.success(f"{len(df)} gems found.")
                    h1,h2,h3,h4=st.columns([1,3,2,2]); h1.markdown("**Tier**"); h2.markdown("**Player**"); h3.markdown("**Avg FPTS**"); h4.markdown("**Status**"); st.divider()
                    for _,r in df.iterrows():
                        cls_t=f"tier-{r['Tier'].lower()}"; cls_s="st-active"
                        if r['Status']=='DAY_TO_DAY': cls_s="st-dtd"
                        with st.container(): c1,c2,c3,c4=st.columns([1,3,2,2]); c1.markdown(f"<span class='tier-badge {cls_t}'>{r['Tier']}</span>", unsafe_allow_html=True); c2.markdown(f"**{r['Player']}** <span style='color:#888'>({r['Team']})</span>", unsafe_allow_html=True); c3.markdown(f"**{r['FPTS']:.1f}**"); c4.markdown(f"<span class='{cls_s}'>{r['Status']}</span>", unsafe_allow_html=True); st.markdown("---")
                else: st.warning("No gems.")

    elif tool == "⚖️ League Trade Machine":
        # (Mantido Igual)
        st.header("⚖️ League Trade Machine"); teams = sorted(league.teams, key=lambda x: x.team_name); tnames = [t.team_name for t in teams]; c1, c2 = st.columns(2)
        with c1: t1n = st.selectbox("Team A", tnames, key="lt1"); t1 = next(t for t in teams if t.team_name == t1n); p1s = st.multiselect("Give (Sends)", [p.name for p in t1.roster])
        with c2: t2n = st.selectbox("Team B", [n for n in tnames if n!=t1n], key="lt2"); t2 = next(t for t in teams if t.team_name == t2n); p2s = st.multiselect("Get (Receives)", [p.name for p in t2.roster])
        if st.button("Analyze League Trade"):
            if not p1s or not p2s: st.error("Select players.")
            else:
                def get_val(names, team):
                    tot=0; st.markdown(f"**{team.team_name} Sends:**")
                    for n in names:
                        p=next(x for x in team.roster if x.name==n); v,m=calculate_player_value_v70(p, mode='trade'); tot+=v
                        pen=f"<span class='penalty-tag'>INJURY (-{int(m['penalty']*100)}%)</span>" if m['penalty']>0 else ""; mom="<span class='momentum-tag'>HOT STREAK</span>" if m['l15']>m['real']*1.2 else ""
                        st.markdown(f"<div class='trade-detail-box'><div class='detail-row'><span class='detail-val'>{n} {pen} {mom}</span> <span class='detail-val' style='font-size:16px'>{v:.1f}</span></div><div class='detail-row'><span class='detail-label'>Season:</span> <span class='detail-val'>{m['real']:.1f}</span></div><div class='detail-row'><span class='detail-label'>Last 15:</span> <span class='detail-val'>{m['l15']:.1f}</span></div><div class='detail-row'><span class='detail-label'>Projected:</span> <span class='detail-val'>{m['proj']:.1f}</span></div></div>", unsafe_allow_html=True)
                    return tot
                cres1, cres2 = st.columns(2)
                with cres1: v1=get_val(p1s, t1)
                with cres2: v2=get_val(p2s, t2)
                diff=v2-v1; pct=(diff/v1*100) if v1>0 else 0
                st.markdown("<div class='trade-card'>", unsafe_allow_html=True)
                if abs(pct)<5: st.markdown("<div class='trade-verdict trade-fair'>🤝 FAIR TRADE</div>", unsafe_allow_html=True)
                elif pct>=5: st.markdown(f"<div class='trade-verdict trade-win'>✅ WIN FOR {t1n.upper()}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='trade-verdict trade-loss'>🚫 LOSS FOR {t1n.upper()}</div>", unsafe_allow_html=True)
                mc1, mc2, mc3 = st.columns(3); mc1.metric("Giving", f"{v1:.1f}"); mc2.metric("Receiving", f"{v2:.1f}"); mc3.metric("Net", f"{diff:+.1f}", f"{pct:.1f}%"); st.markdown("</div>", unsafe_allow_html=True)

    elif tool == "📊 Power Rankings":
        # (Mantido Igual)
        today_str = datetime.today().strftime('%Y-%m-%d'); st.header(f"📊 Power Ranking: {league.settings.name}"); st.caption(f"until: {today_str}")
        if st.button("Generate Rankings"):
            data = []; 
            with st.spinner("Analyzing..."):
                for t in league.teams:
                    h=[]
                    for p in t.roster:
                        if p.injuryStatus=='OUT': continue
                        v,_=calculate_player_value_v70(p, mode='waiver'); h.append(v)
                    h.sort(reverse=True); s=sum(h[:12]); data.append({"Team":f"{t.team_name} ({t.wins}-{t.losses})", "Strength":s})
            df = pd.DataFrame(data).sort_values("Strength", ascending=True)
            fig = px.bar(df, x="Strength", y="Team", orientation='h', title="", text="Strength", color="Strength", color_continuous_scale=['#ff4b4b', '#ffcc00', '#00ff41'], height=600)
            fig.update_traces(texttemplate='%{text:.1f}', textposition='inside'); fig.update_layout(yaxis={'categoryorder':'total ascending'}); st.plotly_chart(fig, use_container_width=True)