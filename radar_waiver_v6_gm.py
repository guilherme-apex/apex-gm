import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from nba_api.stats.endpoints import playergamelogs, leaguegamelog, scoreboardv2 # <--- MUDANÇA AQUI (ScoreboardV2)
from nba_api.stats.static import teams
from datetime import datetime, timedelta
import time

# --- ⚙️ CONFIGURAÇÕES ---
CAMINHO_RELATORIO = Path(r"D:\Dev\NBA_Apostas\reports\WAIVER_GM_V6.xlsx")
TEMPORADA_NBA = '2025-26'
SISTEMA_ATUAL = 'ESPN_STD' 

# --- 🛡️ MATRIZ DE DEFESA (TIERS) ---
DEFENSE_TIERS = {
    'WAS': 1.15, 'DET': 1.12, 'CHA': 1.12, 'POR': 1.10, 'UTA': 1.10, 
    'ATL': 1.08, 'CHI': 1.05, 'BKN': 1.05, 'NOP': 1.05,
    'BOS': 0.85, 'ORL': 0.88, 'MIN': 0.88, 'OKC': 0.90, 'HOU': 0.90, 'CLE': 0.92,
    'DEFAULT': 1.0
}

# --- 🎮 SCORING ---
SCORING_SYSTEMS = {
    'ESPN_STD': {'PTS': 1, 'REB': 1.2, 'AST': 1.5, 'STL': 3, 'BLK': 3, 'TOV': -1, '3PM': 0},
    'YAHOO_STD': {'PTS': 1, 'REB': 1.2, 'AST': 1.5, 'STL': 3, 'BLK': 3, 'TOV': -1, '3PM': 0.5},
    'FANDUEL': {'PTS': 1, 'REB': 1.2, 'AST': 1.5, 'STL': 3, 'BLK': 3, 'TOV': -1, '3PM': 0}
}

# --- 🧬 HERDEIROS ---
HERDEIROS_USAGE = {
    'Jayson Tatum': 'Sam Hauser', 'Jaylen Brown': 'Payton Pritchard',
    'Giannis Antetokounmpo': 'Bobby Portis', 'Damian Lillard': 'AJ Green',
    'Joel Embiid': 'Andre Drummond', 'Tyrese Maxey': 'Kyle Lowry',
    'Donovan Mitchell': 'Caris LeVert', 'Darius Garland': 'Craig Porter Jr.',
    'Paolo Banchero': 'Franz Wagner', 'Franz Wagner': 'Goga Bitadze',
    'Tyrese Haliburton': 'T.J. McConnell', 'LaMelo Ball': 'Tre Mann',
    'Nikola Jokic': 'Russell Westbrook', 'Jamal Murray': 'Russell Westbrook',
    'Shai Gilgeous-Alexander': 'Cason Wallace', 'Chet Holmgren': 'Isaiah Hartenstein',
    'Luka Doncic': 'Spencer Dinwiddie', 'Kyrie Irving': 'Quentin Grimes',
    'LeBron James': 'Austin Reaves', 'Anthony Davis': 'Jaxson Hayes',
    'Stephen Curry': 'Buddy Hield', 'Ja Morant': 'Scotty Pippen Jr.',
    'Alperen Sengun': 'Steven Adams', 'Fred VanVleet': 'Amen Thompson'
}

def buscar_lesoes_cbs():
    print("🕷️ Buscando Notícias de Lesão...")
    url = "https://www.cbssports.com/nba/injuries/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        lesionados = []
        for row in soup.find_all('tr', class_='TableBase-bodyTr'):
            cols = row.find_all('td')
            if len(cols) >= 5:
                nome = cols[0].find('a').text.strip() if cols[0].find('a') else ""
                status = cols[4].text.strip().lower()
                if 'out' in status or 'questionable' in status or 'doubtful' in status:
                    lesionados.append(nome)
        return lesionados
    except:
        return []

def analisar_calendario_semanal():
    """
    Versão Dinâmica: Pega a data do sistema automaticamente.
    """
    # ---------------------------------------------------------
    # 📅 DATA AUTOMÁTICA (HOJE)
    # Se o seu Windows estiver em 07/01/2026, ele pegará 2026-01-07
    DATA_ALVO = datetime.now().strftime('%Y-%m-%d')
    # ---------------------------------------------------------
    
    print(f"📅 Analisando jogos para a data: {DATA_ALVO}")
    
    nba_teams = teams.get_teams()
    id_to_abbrev = {team['id']: team['abbreviation'] for team in nba_teams}
    
    try:
        # Usa ScoreboardV2 que respeita a data passada
        board = scoreboardv2.ScoreboardV2(game_date=DATA_ALVO)
        
        # Pegamos a lista de tabelas direto do objeto board.
        # O índice [0] é sempre o GameHeader (Cabeçalho dos Jogos)
        df_games = board.get_data_frames()[0]
        
        matchups_hoje = {}
        times_jogando_hoje = []
        
        for _, row in df_games.iterrows():
            h_id = row['HOME_TEAM_ID']
            a_id = row['VISITOR_TEAM_ID']
            
            h_sigla = id_to_abbrev.get(h_id)
            a_sigla = id_to_abbrev.get(a_id)
            
            if h_sigla and a_sigla:
                matchups_hoje[h_sigla] = a_sigla
                matchups_hoje[a_sigla] = h_sigla
                times_jogando_hoje.extend([h_sigla, a_sigla])
                
        print(f"✅ Jogos Encontrados: {len(times_jogando_hoje)//2}")
        return matchups_hoje, times_jogando_hoje

    except Exception as e:
        print(f"⚠️ Erro no calendario: {e}")
        return {}, []
def calcular_pontos_fantasy(row, sistema):
    try:
        regras = SCORING_SYSTEMS[sistema]
        pts = float(row['PTS']) * regras.get('PTS', 0)
        reb = float(row['REB']) * regras.get('REB', 0)
        ast = float(row['AST']) * regras.get('AST', 0)
        stl = float(row['STL']) * regras.get('STL', 0)
        blk = float(row['BLK']) * regras.get('BLK', 0)
        tov = float(row['TOV']) * regras.get('TOV', 0)
        fg3m = float(row['FG3M']) * regras.get('3PM', 0)
        return pts + reb + ast + stl + blk + tov + fg3m
    except:
        return 0

def radar_v6_gm():
    print(f"🚀 INICIANDO RADAR V6 (GM EDITION) | MODO: {SISTEMA_ATUAL}")
    
    lista_lesionados = buscar_lesoes_cbs()
    # Adicionando manuais se necessário
    lista_lesionados.extend(['Tyrese Haliburton', 'Joel Embiid', 'Franz Wagner']) 

    # 1. CALENDÁRIO & MATCHUPS (Agora com data fixa)
    matchups_hoje, times_jogando_hoje = analisar_calendario_semanal()

    # 2. BLOWOUTS
    print("Step 1/3: Filtrando Blowouts...")
    try:
        game_log = leaguegamelog.LeagueGameLog(season=TEMPORADA_NBA)
        df_games = game_log.get_data_frames()[0]
        blowout_ids = []
        for gid, group in df_games.groupby('GAME_ID'):
            if len(group) == 2:
                pts = group['PTS'].values
                if abs(pts[0] - pts[1]) > 20: blowout_ids.append(gid)
    except:
        blowout_ids = []

    # 3. STATS
    print("Step 2/3: Calculando Performance Recente...")
    try:
        log = playergamelogs.PlayerGameLogs(season_nullable=TEMPORADA_NBA)
        df_nba = log.get_data_frames()[0]
        df_nba['GAME_DATE'] = pd.to_datetime(df_nba['GAME_DATE'])
        
        # Últimos 14 dias
        data_limite = datetime.now() - timedelta(days=14)
        df_recent = df_nba[df_nba['GAME_DATE'] >= data_limite].copy()

        stats_list = []
        for _, row in df_recent.iterrows():
            fpts = calcular_pontos_fantasy(row, SISTEMA_ATUAL)
            peso = 0.75 if row['GAME_ID'] in blowout_ids else 1.0
            
            stats_list.append({
                'Player': row['PLAYER_NAME'],
                'Team': row['TEAM_ABBREVIATION'],
                'FPTS_Weighted': fpts * peso,
                'PTS': row['PTS'], 'AST': row['AST'], 'REB': row['REB'],
                'STL': row['STL'], 'BLK': row['BLK'],
                'Games': 1
            })
        
        df_stats = pd.DataFrame(stats_list)
        analise = df_stats.groupby(['Player', 'Team']).agg({
            'FPTS_Weighted': 'mean',
            'PTS': 'mean', 'AST': 'mean', 'REB': 'mean',
            'STL': 'mean', 'BLK': 'mean', 'Games': 'count'
        }).reset_index()

        # 4. INTELIGÊNCIA FINAL
        print("Step 3/3: Cruzando Lesão + Matchup + Calendário...")
        sugestoes = []
        
        quem_ganha_boost = []
        for titular, reserva in HERDEIROS_USAGE.items():
            for lesionado in lista_lesionados:
                if titular in lesionado or lesionado in titular:
                    quem_ganha_boost.append(reserva)
                    
        for _, row in analise.iterrows():
            nome = row['Player']
            time_jogador = row['Team']
            media = row['FPTS_Weighted']
            
            # Filtro de Waiver
            if 18 <= media <= 48 and row['Games'] >= 3:
                projecao = media
                obs_list = []
                
                # A. BOOST LESÃO
                if nome in quem_ganha_boost:
                    projecao = projecao * 1.25
                    obs_list.append("🔥 USAGE SPIKE")
                
                # B. BOOST MATCHUP (DVP) - Só se jogar hoje
                oponente = matchups_hoje.get(time_jogador)
                
                if oponente:
                    matchup_multiplier = DEFENSE_TIERS.get(oponente, 1.0)
                    if matchup_multiplier > 1.05:
                        obs_list.append(f"🟢 vs {oponente}")
                    elif matchup_multiplier < 0.95:
                        obs_list.append(f"🔴 vs {oponente}")
                    else:
                        obs_list.append(f"vs {oponente}")
                    
                    projecao = projecao * matchup_multiplier
                else:
                    # Se não joga hoje, penaliza levemente a projeção
                    projecao = projecao * 0.9 

                full_obs = " | ".join(obs_list) if obs_list else ""

                # Só mostra quem joga hoje OU quem é muito bom
                is_playing = time_jogador in times_jogando_hoje
                
                if is_playing or "USAGE" in full_obs:
                    sugestoes.append({
                        'PLAYER': nome,
                        'TEAM': time_jogador,
                        'STATUS': 'JOGA HOJE' if is_playing else 'OFF',
                        'PROJ_FPTS': round(projecao, 1),
                        'AVG_FPTS': round(media, 1),
                        'STK_BLK': round(row['STL'] + row['BLK'], 1),
                        'NOTE': full_obs
                    })

        df_final = pd.DataFrame(sugestoes).sort_values('PROJ_FPTS', ascending=False)
        
        print(f"\n✅ Relatório V6 Salvo! ({len(df_final)} sugestões)")
        # Cria a pasta se não existir
        CAMINHO_RELATORIO.parent.mkdir(parents=True, exist_ok=True)
        
        df_final.to_excel(CAMINHO_RELATORIO, index=False)

    except Exception as e:
        print(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    radar_v6_gm()