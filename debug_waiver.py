import streamlit as st
from espn_api.basketball import League
import apex_config as cfg 

st.title("🕵️ Waiver Detective")

try:
    league = League(league_id=cfg.LEAGUE_ID, year=cfg.YEAR, espn_s2=cfg.ESPN_S2, swid=cfg.SWID)
    st.success(f"Conectado: {league.settings.name}")
    
    # Pega 1 jogador da Waiver
    fa = league.free_agents(size=1)[0]
    
    st.subheader(f"Analisando: {fa.name}")
    
    # 1. INSPEÇÃO DE OWNERSHIP
    st.write("**Atributos de Ownership:**")
    st.write(f"- percent_owned: {getattr(fa, 'percent_owned', 'N/A')}")
    st.write(f"- percentOwned: {getattr(fa, 'percentOwned', 'N/A')}")
    
    # 2. INSPEÇÃO DE STATS (Para corrigir o erro de zeros)
    st.write("**Estrutura de Stats:**")
    st.json(fa.stats)
    
    # 3. DIR COMPLETO (O Mapa da Mina)
    st.write("**Todos os atributos disponíveis:**")
    st.write(dir(fa))

except Exception as e:
    st.error(f"Erro: {e}")