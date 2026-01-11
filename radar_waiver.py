import pandas as pd
from pathlib import Path
from nba_api.stats.endpoints import playergamelogs
from espn_api.basketball import League
from datetime import datetime, timedelta

# --- SUAS CONFIGURAÇÕES ---
LEAGUE_ID = 300699640  # <--- COLOQUE SEU ID AQUI
YEAR = 2026
SWID = '{E2237048-BE8A-4D17-8E42-21BA3E598AD3}' 
ESPN_S2 = 'AECVP7bALLkpO2Z4AocQYb3JfYHs5SQxEnm6IcAxCJ8zw%2Fetqd7kz0xk6wqQDTZfrhEcnO7J84EZqUZX0nXGtsBf202Iah7eh2EAzgb5q3Rj%2FL8wQs9QI5jEZ7ca5xuKSFa17VT362Z3E17YPpgXXrgntwRPaLMeEjTs2o9IQpwMGwhYBswWqVyRh%2BBRsLvbyXVxV65ryClZAPaWHx%2BiMu9m%2BqqhRvLyo72VCmSfPoABN69NndistLnKwQyrY12cd092ehkdWhIHnRUoN7CgDbSZ'

# --- CONFIGURAÇÃO DE CAMINHOS ABSOLUTOS (BLINDADOS) ---
# Aqui definimos exatamente onde ler e onde salvar, sem depender de onde o script está
CAMINHO_DB = Path(r"D:\Dev\NBA_Apostas\data\nba_betting.db")
CAMINHO_RELATORIO = Path(r"D:\Dev\NBA_Apostas\reports\WAIVER_REAL_TIME.xlsx")
TEMPORADA_NBA = '2025-26'

def radar_inteligente():
    print("🚀 INICIANDO RADAR DE WAIVER V2 (CAMINHOS ABSOLUTOS)...")

    # 1. DEFINIR O PERÍODO VÁLIDO (Últimos 5 dias)
    hoje = datetime.now()
    data_limite = hoje - timedelta(days=5)
    print(f"📅 Analisando performance apenas a partir de: {data_limite.strftime('%Y-%m-%d')}")

    # 2. BAIXAR DADOS DA NBA
    print("Step 1/3: Baixando dados da liga...")
    try:
        log = playergamelogs.PlayerGameLogs(season_nullable=TEMPORADA_NBA)
        df_nba = log.get_data_frames()[0]
        
        df_nba['GAME_DATE'] = pd.to_datetime(df_nba['GAME_DATE'])
        
        # Filtro de Data
        df_recent = df_nba[df_nba['GAME_DATE'] >= data_limite].copy()
        
        if df_recent.empty:
            print("❌ Nenhum jogo recente encontrado.")
            return

        print(f"✅ Filtrado! {len(df_recent)} atuações recentes encontradas.")

        # Cálculo de Pontos Fantasy
        stats_list = []
        for _, row in df_recent.iterrows():
            min_val = row['MIN']
            if isinstance(min_val, str) and ':' in min_val:
                m, s = map(int, min_val.split(':'))
                min_val = m + s/60
            else:
                min_val = float(min_val)
            
            fgmi = row['FGA'] - row['FGM']
            ftmi = row['FTA'] - row['FTM']
            
            fpts = (
                (row['PTS'] * 1) + 
                (row['REB'] * 1) + 
                (row['AST'] * 2) + 
                (row['STL'] * 4) + 
                (row['BLK'] * 3) + 
                (row['TOV'] * -2) + 
                (row['FG3M'] * 0.75) + 
                (row['OREB'] * 0.5) + 
                (fgmi * -0.5) + 
                (ftmi * -0.5)
            )
            
            stats_list.append({
                'Player': row['PLAYER_NAME'],
                'Date': row['GAME_DATE'],
                'Fantasy_Pts': fpts,
                'Team': row['TEAM_ABBREVIATION']
            })
            
        df_stats = pd.DataFrame(stats_list)
        
    except Exception as e:
        print(f"❌ Erro na API da NBA: {e}")
        return

    # 3. ANÁLISE ESTATÍSTICA
    print("Step 2/3: Calculando quem está quente AGORA...")
    
    analise = df_stats.groupby('Player').agg({
        'Fantasy_Pts': 'mean',
        'Date': ['count', 'max'] 
    }).reset_index()
    
    analise.columns = ['Player', 'Avg_Last14Days', 'Games_Played', 'Last_Game_Date']
    
    # Filtros
    criterio_pontos = analise['Avg_Last14Days'] > 20
    criterio_jogos = analise['Games_Played'] >= 2
    
    candidatos = analise[criterio_pontos & criterio_jogos].sort_values('Avg_Last14Days', ascending=False)
    
    print(f"📊 {len(candidatos)} jogadores passaram no filtro de qualidade.")

    # 4. CRUZAMENTO COM A ESPN
    print("Step 3/3: Verificando disponibilidade e saúde na ESPN...")
    try:
        league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)
        free_agents = league.free_agents(size=400)
        fa_map = {fa.name: fa.injuryStatus for fa in free_agents}
        
        sugestoes = []
        for _, row in candidatos.iterrows():
            nome = row['Player']
            if nome in fa_map:
                status_lesao = fa_map[nome] 
                
                sugestoes.append({
                    'Jogador': nome,
                    'Media_14Dias': round(row['Avg_Last14Days'], 1),
                    'Jogos_Recentes': row['Games_Played'],
                    'Ultimo_Jogo': row['Last_Game_Date'].strftime('%d/%m'),
                    'Status_ESPN': status_lesao
                })
        
        df_final = pd.DataFrame(sugestoes)
        
        print(f"\n💎 ENCONTREI {len(df_final)} OPÇÕES REAIS!")
        print(df_final.head(10))
        
        # --- AQUI ESTAVA O ERRO (CORRIGIDO) ---
        # Agora salvamos no caminho absoluto que definimos lá em cima
        df_final.to_excel(CAMINHO_RELATORIO, index=False)
        print(f"\n✅ Relatório salvo com sucesso em:\n{CAMINHO_RELATORIO}")
        
    except Exception as e:
        print(f"❌ Erro na ESPN: {e}")

if __name__ == "__main__":
    radar_inteligente()