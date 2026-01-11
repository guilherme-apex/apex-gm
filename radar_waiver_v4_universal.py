import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from nba_api.stats.endpoints import playergamelogs, leaguegamelog
from nba_api.live.nba.endpoints import scoreboard # <--- NOVA IMPORTAÇÃO ESSENCIAL
from datetime import datetime, timedelta

# --- ⚙️ CONFIGURAÇÕES ---
CAMINHO_RELATORIO = Path(r"D:\Dev\NBA_Apostas\reports\WAIVER_DVP_V5.xlsx")
TEMPORADA_NBA = '2025-26'
SISTEMA_ATUAL = 'ESPN_STD' 

# --- 🛡️ MATRIZ DE DEFESA (TIER LIST 2026) ---
# Aqui você define quem são as "Peneiras" e as "Muralhas".
# Ajuste conforme a temporada for rolando.
DEFENSE_TIERS = {
    # 🟢 ALVOS FÁCEIS (Times que cedem muitos pontos de Fantasy) - MULTIPLICADOR > 1.0
    'WAS': 1.15, 'DET': 1.12, 'CHA': 1.12, 'POR': 1.10, 'UTA': 1.10, 
    'ATL': 1.08, 'CHI': 1.05, 'BKN': 1.05, 'NOP': 1.05,
    
    # 🔴 EVITAR (Defesas de Elite) - MULTIPLICADOR < 1.0
    'BOS': 0.85, 'ORL': 0.88, 'MIN': 0.88, 'OKC': 0.90, 'HOU': 0.90, 'CLE': 0.92,
    
    # ⚪ NEUTROS (Padrão)
    'DEFAULT': 1.0
}

# --- 🎮 SCORING SYSTEMS ---
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

def obter_mapa_jogos_hoje():
    """
    Retorna um dicionário: { 'TIME_DO_JOGADOR': 'OPONENTE' }
    Ex: { 'LAL': 'BOS', 'BOS': 'LAL' }
    """
    print("📅 Mapeando jogos de HOJE (Scoreboard)...")
    try:
        games = scoreboard.ScoreBoard().games.get_dict()
        mapa_confrontos = {}
        
        for game in games:
            home_team = game['homeTeam']['teamTricode']
            away_team = game['awayTeam']['teamTricode']
            
            # Mapeia quem joga contra quem
            mapa_confrontos[home_team] = away_team
            mapa_confrontos[away_team] = home_team
            
        print(f"✅ {len(games)} jogos encontrados para hoje/amanhã.")
        return mapa_confrontos
    except Exception as e:
        print(f"⚠️ Não há jogos agora ou erro na API: {e}")
        return {}

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

def radar_v5_dvp():
    print(f"🚀 INICIANDO RADAR V5 (DvP EDITION) | MODO: {SISTEMA_ATUAL}")
    
    lista_lesionados = buscar_lesoes_cbs()
    # Backup manual caso o site esteja vazio
    lista_lesionados.extend(['Tyrese Haliburton', 'Joel Embiid', 'Franz Wagner']) 

    # 1. MAPEAR OPONENTES DE HOJE
    mapa_jogos = obter_mapa_jogos_hoje()

    # 2. BLOWOUTS
    print("Step 1/3: Analisando Blowouts passados...")
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
    print("Step 2/3: Processando Stats...")
    try:
        log = playergamelogs.PlayerGameLogs(season_nullable=TEMPORADA_NBA)
        df_nba = log.get_data_frames()[0]
        df_nba['GAME_DATE'] = pd.to_datetime(df_nba['GAME_DATE'])
        
        # Filtro: Últimos 14 dias (Amostra maior)
        data_limite = datetime.now() - timedelta(days=14)
        df_recent = df_nba[df_nba['GAME_DATE'] >= data_limite].copy()

        stats_list = []
        for _, row in df_recent.iterrows():
            fpts = calcular_pontos_fantasy(row, SISTEMA_ATUAL)
            peso = 0.75 if row['GAME_ID'] in blowout_ids else 1.0
            
            stats_list.append({
                'Player': row['PLAYER_NAME'],
                'Team': row['TEAM_ABBREVIATION'], # Importante para o Matchup
                'FPTS_Weighted': fpts * peso,
                'PTS': row['PTS'], 'AST': row['AST'], 'REB': row['REB'],
                'STL': row['STL'], 'BLK': row['BLK'],
                'Games': 1
            })
        
        df_stats = pd.DataFrame(stats_list)
        
        # Média
        analise = df_stats.groupby(['Player', 'Team']).agg({
            'FPTS_Weighted': 'mean',
            'PTS': 'mean', 'AST': 'mean', 'REB': 'mean',
            'STL': 'mean', 'BLK': 'mean', 'Games': 'count'
        }).reset_index()

        # 4. INTELIGÊNCIA FINAL (DvP + NEWS)
        print("Step 3/3: Cruzando com Defesa Adversária (DvP)...")
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
            
            if 18 <= media <= 48 and row['Games'] >= 3:
                projecao = media
                obs_list = []
                
                # A. BOOST DE LESÃO
                if nome in quem_ganha_boost:
                    projecao = projecao * 1.25
                    obs_list.append("🔥 USAGE SPIKE")
                
                # B. BOOST DE MATCHUP (DVP)
                # Verifica se o time do jogador joga hoje
                oponente = mapa_jogos.get(time_jogador) 
                
                matchup_multiplier = 1.0
                matchup_txt = ""
                
                if oponente:
                    # Busca o multiplicador na lista de defesa (se não achar, usa 1.0)
                    matchup_multiplier = DEFENSE_TIERS.get(oponente, 1.0)
                    
                    if matchup_multiplier > 1.05:
                        matchup_txt = f"vs {oponente} (EASY)"
                        obs_list.append("🟢 MATCHUP")
                    elif matchup_multiplier < 0.95:
                        matchup_txt = f"vs {oponente} (HARD)"
                        obs_list.append("🔴 HARD MATCHUP")
                    else:
                        matchup_txt = f"vs {oponente}"
                    
                    # Aplica o multiplicador na projeção final
                    projecao = projecao * matchup_multiplier
                else:
                    matchup_txt = "No Game Today"

                # Formatação da observação
                full_obs = " | ".join(obs_list) if obs_list else ""

                # Só adiciona se jogar hoje ou tiver boost de lesão
                if oponente or "USAGE" in full_obs:
                    sugestoes.append({
                        'PLAYER': nome,
                        'TEAM': time_jogador,
                        'OPPONENT': matchup_txt,
                        'PROJ_FPTS': round(projecao, 1),
                        'AVG_FPTS': round(media, 1),
                        'PTS': round(row['PTS'], 1),
                        'STK_BLK': round(row['STL'] + row['BLK'], 1),
                        'NOTE': full_obs
                    })

        df_final = pd.DataFrame(sugestoes).sort_values('PROJ_FPTS', ascending=False)
        
        print(f"\n✅ Relatório V5 Gerado! Melhores opções para HOJE:")
        print(df_final.head(15))
        df_final.to_excel(CAMINHO_RELATORIO, index=False)

    except Exception as e:
        print(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    radar_v5_dvp()