import streamlit as st
import pandas as pd
from espn_api.basketball import League
import apex_config as cfg 

st.title("🩻 Raio-X de Estatísticas (Debug)")

def run_debug():
    try:
        st.info(f"Conectando na liga {cfg.LEAGUE_ID}...")
        league = League(league_id=cfg.LEAGUE_ID, year=cfg.YEAR, espn_s2=cfg.ESPN_S2, swid=cfg.SWID)
        st.success(f"Conectado: {league.settings.name}")
        
        # Pega o primeiro time e o primeiro jogador
        team = league.teams[0]
        player = team.roster[0]
        
        st.subheader(f"🕵️ Investigando Jogador: {player.name}")
        
        # 1. ATRIBUTOS DIRETOS (Às vezes a média já vem pronta aqui)
        st.write("**Atributos Diretos:**")
        st.write(f"- avg_points: `{getattr(player, 'avg_points', 'Não existe')}`")
        st.write(f"- total_points: `{getattr(player, 'total_points', 'Não existe')}`")
        st.write(f"- projected_total_points: `{getattr(player, 'projected_total_points', 'Não existe')}`")
        
        # 2. CHAVES DO DICIONÁRIO .STATS (Aqui está o segredo)
        st.write("**Chaves disponíveis em player.stats:**")
        st.write(list(player.stats.keys()))
        
        # 3. CONTEÚDO BRUTO (Para vermos o formato)
        st.write("**Conteúdo Bruto de player.stats:**")
        st.json(player.stats)
        
    except Exception as e:
        st.error(f"Erro: {e}")

if __name__ == "__main__":
    run_debug()