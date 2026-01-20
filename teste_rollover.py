import streamlit as st
import pandas as pd
import requests
import io
import sqlite3
from datetime import datetime, timedelta
from fake_useragent import UserAgent
from espn_api.basketball import League
import apex_config as cfg 

# ==============================================================================
# 1. CONFIGURAÇÃO (SCANNER FOCUS)
# ==============================================================================
st.set_page_config(page_title="Apex Waiver Scanner", layout="wide", page_icon="🔭")

# Estilo focado em Tabela e Leitura Rápida
st.markdown("""
<style>
    .block-container { padding-top: 2rem !important; }
    
    /* KPI CARDS */
    .kpi-card {
        background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; text-align: center;
    }
    .kpi-val { font-size: 24px; font-weight: bold; color: white; }
    .kpi-lbl { font-size: 12px; color: #8b949e; text-transform: uppercase; }
    
    /* TABLE STYLES */
    .dataframe { font-size: 14px !important; }
    
    /* UTILS */
    .trend-up { color: #3fb950; font-weight: bold; }
    .trend-down { color: #f85149; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# URLs & DB
ESPN_ROSTER = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/roster"
ESPN_GAMELOG = "https://www.espn.com/nba/player/gamelog/_/id/{}/type/nba/year/2026"
ESPN_TEAMS = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
ESPN_SCOREBOARD = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"
DB_NAME = "nba_apex_scanner.db"
ua = UserAgent()

# ==============================================================================
# 2. CACHE & DADOS
# ==============================================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('CREATE TABLE IF NOT EXISTS gamelogs (pid INTEGER PRIMARY KEY, data TEXT, updated TIMESTAMP)')
    conn.commit(); conn.close()

def get_header(): return {'User-Agent': ua.random}

@st.cache_data(ttl=3600)
def get_nba_teams():
    try:
        data = requests.get(ESPN_TEAMS, headers=get_header(), timeout=5).json()
        teams = []
        for t in data['sports'][0]['leagues'][0]['teams']:
            teams.append({'name': t['team']['displayName'], 'id': t['team']['id'], 'abbr': t['team']['abbreviation']})
        return teams
    except: return []

def fetch_gamelog(pid):
    # Cache simples em memória do Streamlit para velocidade durante a sessão
    # (Poderíamos usar o SQLite aqui, mas para manter o código limpo hoje, vamos de st.cache_data)
    return _fetch_gamelog_cached(pid)

@st.cache_data(ttl=43200) # Cache de 12 horas
def _fetch_gamelog_cached(pid):
    try:
        url = ESPN_GAMELOG.format(pid)
        r = requests.get(url, headers=get_header(), timeout=5)
        if r.status_code != 200: return None
        dfs = pd.read_html(io.StringIO(r.text), header=0)
        df = next((d for d in dfs if 'Date' in d.columns and 'PTS' in d.columns), pd.DataFrame())
        if df.empty: return None
        df = df[df['Date'] != 'Date']
        df = df[~df['MIN'].isin(['DNP', '--'])]
        cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM'] # Adicionei 3PM
        for c in cols: 
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # Fantasy Points (Padrão ESPN Points)
        df['FPTS'] = df['PTS'] + 1.2*df['REB'] + 1.5*df['AST'] + 3*df['STL'] + 3*df['BLK'] - df['TO']
        return df
    except: return None

# ==============================================================================
# 3. LÓGICA DE CALENDÁRIO (ROLLOVER INCLUSO)
# ==============================================================================
def get_schedule_density(start_date, end_date):
    """
    Retorna quantos jogos cada time tem no período.
    Aplica a lógica de -4h para jogos da madrugada caírem no dia certo.
    """
    # Range de busca (Safety margin)
    delta_days = (end_date - start_date).days + 1
    search_end = end_date + timedelta(days=1) # Busca um dia a mais para o rollover
    date_range_str = f"{start_date.strftime('%Y%m%d')}-{search_end.strftime('%Y%m%d')}"
    
    schedule = {t['abbr']: 0 for t in get_nba_teams()}
    
    try:
        url = ESPN_SCOREBOARD.format(date_range_str)
        data = requests.get(url, headers=get_header(), timeout=5).json()
        
        target_start_str = start_date.strftime('%Y%m%d')
        target_end_str = end_date.strftime('%Y%m%d')
        
        for e in data['events']:
            raw_date = e['date']
            try:
                # Parse e Ajuste -4h
                game_dt = datetime.strptime(raw_date, "%Y-%m-%dT%H:%MZ") - timedelta(hours=4)
                game_day_str = game_dt.strftime('%Y%m%d')
                
                # Se o jogo ajustado cair dentro do período selecionado pelo usuário
                if target_start_str <= game_day_str <= target_end_str:
                    for comp in e['competitions']:
                        h = comp['competitors'][0]['team']['abbreviation']
                        a = comp['competitors'][1]['team']['abbreviation']
                        if h in schedule: schedule[h] += 1
                        if a in schedule: schedule[a] += 1
            except: continue
            
        return schedule
    except: return {}

# ==============================================================================
# 4. UI DO SCANNER (FOCO TOTAL)
# ==============================================================================
st.title("🔭 Waiver Wire Scanner")

# --- FILTROS SUPERIORES ---
c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
with c1: 
    start_d = st.date_input("Início", datetime.today())
with c2: 
    end_d = st.date_input("Fim", datetime.today() + timedelta(days=6))
with c3:
    # Filtro de profundidade (Simulando tamanho da liga)
    depth = st.selectbox("Profundidade", ["Standard (12T)", "Shallow (10T)", "Deep (16T)"])
with c4:
    # Botão de Ação
    run_scan = st.button("🔍 Escanear Mercado", type="primary", use_container_width=True)

st.divider()

if run_scan:
    # 1. Analisa Calendário
    with st.status("Analisando Calendário...", expanded=True) as status:
        st.write("Baixando tabela de jogos...")
        sched = get_schedule_density(start_d, end_d)
        
        # Filtra times com bons jogos (3 ou 4 jogos na semana)
        good_schedule_teams = [t for t, count in sched.items() if count >= 3]
        st.write(f"Times com calendário cheio (3+ jogos): {len(good_schedule_teams)}")
        
        # 2. Busca Jogadores (Simulação de Waiver)
        # Na versão real, aqui conectaríamos na League() do pacote espn_api
        # Como estamos focando na ferramenta, vou buscar nos elencos dos times com bom calendário
        
        st.write("Escaneando elencos...")
        all_teams = get_nba_teams()
        candidates = []
        
        progress_bar = st.progress(0)
        total_teams = len(good_schedule_teams)
        
        for idx, t_abbr in enumerate(good_schedule_teams):
            # Acha o ID do time
            tid = next((x['id'] for x in all_teams if x['abbr'] == t_abbr), None)
            if not tid: continue
            
            # Pega o Roster
            try:
                roster_data = requests.get(ESPN_ROSTER.format(tid), headers=get_header()).json()
                # Pega apenas os jogadores "fundo de banco" (simulando waiver)
                # Lógica: Pega do 6º ao 12º jogador da rotação (Geralmente os disponíveis)
                rotation = roster_data['athletes']
                
                # Ajuste de profundidade
                if depth == "Standard (12T)": target_players = rotation[5:10] # 6º ao 10º homem
                elif depth == "Deep (16T)": target_players = rotation[7:13] # 8º ao 13º homem
                else: target_players = rotation[4:9]
                
                for p in target_players:
                    pid = p['id']
                    name = p['fullName']
                    status = p.get('status', {}).get('type', 'active')
                    
                    if status != 'active': continue
                    
                    # Pega Stats
                    df = fetch_gamelog(pid)
                    if df is not None and len(df) >= 5:
                        l5_avg = df.head(5)['FPTS'].mean()
                        season_avg = df['FPTS'].mean()
                        last_game = df.iloc[0]['FPTS']
                        min_l5 = df.head(5)['MIN'].mean()
                        
                        # Filtro de Qualidade Mínima
                        if min_l5 > 18: # Só mostra quem joga pelo menos 18 min
                            trend = l5_avg - season_avg
                            
                            candidates.append({
                                "Jogador": name,
                                "Time": t_abbr,
                                "Jogos": sched[t_abbr],
                                "Min (L5)": f"{min_l5:.1f}",
                                "FPTS (L5)": f"{l5_avg:.1f}",
                                "Trend": trend,
                                "Último": last_game
                            })
            except: pass
            
            progress_bar.progress((idx + 1) / total_teams)
            
        status.update(label="Scan Completo!", state="complete", expanded=False)

    # 3. Exibição dos Resultados
    if candidates:
        df_res = pd.DataFrame(candidates)
        
        # Ordenação Inteligente: Primeiro por Jogos (Volume), depois por Trend (Momento)
        df_res = df_res.sort_values(by=["Jogos", "Trend"], ascending=[False, False])
        
        st.subheader(f"💎 Encontramos {len(df_res)} Oportunidades")
        
        # Formatação Condicional da Tabela
        st.dataframe(
            df_res,
            column_config={
                "Trend": st.column_config.NumberColumn(
                    "Tendência",
                    help="Diferença entre média L5 e Temporada",
                    format="%.1f"
                ),
                "Jogos": st.column_config.ProgressColumn(
                    "Jogos na Semana",
                    format="%f",
                    min_value=0,
                    max_value=5,
                ),
                "Jogador": st.column_config.TextColumn("Nome", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("Nenhum jogador relevante encontrado com os filtros atuais.")