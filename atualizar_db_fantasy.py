import sqlite3
import pandas as pd
from pathlib import Path
from nba_api.stats.endpoints import playergamelogs

# --- CONFIGURAÇÃO ---
TEMPORADA = '2025-26'
RAIZ = Path(__file__).resolve().parent.parent
DB_PATH = RAIZ / 'data' / 'nba_betting.db' # Vamos usar o mesmo banco, apenas melhorando ele

def atualizar_para_fantasy():
    print(f"🏀 Baixando dados avançados para Fantasy (Temporada {TEMPORADA})...")
    
    try:
        # Baixa tudo
        log = playergamelogs.PlayerGameLogs(season_nullable=TEMPORADA)
        df = log.get_data_frames()[0]
        print(f"✅ Download concluído! {len(df)} linhas baixadas.")
    except Exception as e:
        print(f"❌ Erro na API: {e}")
        return

    print("⚙️ Calculando estatísticas personalizadas...")
    
    dados_fantasy = []
    
    for _, row in df.iterrows():
        try:
            # Tratamento de Minutos
            min_raw = row['MIN']
            minutos = 0.0
            if isinstance(min_raw, float): minutos = min_raw
            elif isinstance(min_raw, str) and ':' in min_raw:
                parts = min_raw.split(':')
                minutos = int(parts[0]) + int(parts[1])/60
            
            # --- CÁLCULO DA PONTUAÇÃO ESPN (SUA LIGA) ---
            # FGMI = Field Goals Missed (Tentados - Convertidos)
            fgmi = row['FGA'] - row['FGM']
            # FTMI = Free Throws Missed
            ftmi = row['FTA'] - row['FTM']
            
            # Fórmula baseada na sua imagem:
            # PTS=1, REB=1, AST=2, STL=4, BLK=3, TOV=-2, 3PM=0.75, OREB=0.5, Missed=-0.5
            fpts = (row['PTS'] * 1) + \
                   (row['REB'] * 1) + \
                   (row['AST'] * 2) + \
                   (row['STL'] * 4) + \
                   (row['BLK'] * 3) + \
                   (row['TOV'] * -2) + \
                   (row['FG3M'] * 0.75) + \
                   (row['OREB'] * 0.5) + \
                   (fgmi * -0.5) + \
                   (ftmi * -0.5)
            
            dados_fantasy.append({
                'game_id': row['GAME_ID'],
                'player_id': row['PLAYER_ID'],
                'player_name': row['PLAYER_NAME'],
                'team': row['TEAM_ABBREVIATION'],
                'game_date': row['GAME_DATE'][:10],
                'minutes': round(minutos, 2),
                'fantasy_points': round(fpts, 2), # A pontuação JÁ CALCULADA
                'pts': row['PTS'],
                'reb': row['REB'],
                'ast': row['AST'],
                'stl': row['STL'],
                'blk': row['BLK'],
                'oreb': row['OREB'] # Importante para análise
            })
            
        except Exception:
            continue

    df_final = pd.DataFrame(dados_fantasy)

    # Salvar no Banco (Recriando a tabela com a coluna nova 'fantasy_points')
    print("💾 Atualizando banco de dados com a coluna 'fantasy_points'...")
    con = sqlite3.connect(DB_PATH)
    
    # Vamos criar uma tabela específica para fantasy para não misturar
    con.execute("DROP TABLE IF EXISTS fantasy_stats")
    
    # Salva direto (o pandas cria a tabela sozinho com as colunas certas)
    df_final.to_sql('fantasy_stats', con, if_exists='replace', index=False)
    con.close()
    
    print("-" * 40)
    print("🎉 BANCO ATUALIZADO PARA FANTASY!")
    print(f"Agora temos {len(df_final)} atuações com a pontuação EXATA da sua liga.")
    print("-" * 40)

if __name__ == "__main__":
    atualizar_para_fantasy()