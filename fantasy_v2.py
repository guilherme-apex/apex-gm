import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
# IMPORTANDO A BIBLIOTECA OFICIAL
from espn_api.basketball import League

# ==============================================================================
# 1. CONFIG & STYLES (V135 - ESPN API LIBRARY EDITION)
# ==============================================================================
st.set_page_config(page_title="Apex Scanner", layout="wide", page_icon="🔭")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    div.stButton > button:first-child {
        margin-top: 27px;
        height: 50px;
        font-weight: bold;
        border: 1px solid #30363d;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        border-color: #58a6ff;
        color: #58a6ff;
    }
    div[data-testid="stDataFrame"] { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SIDEBAR - CREDENCIAIS
# ==============================================================================
st.sidebar.header("🔐 Acesso da Liga")
st.sidebar.markdown("Necessário instalar: `pip install espn_api`")

# Valores padrão (seus dados)
default_league_id = "300699640"
default_year = "2026"
# SWID e S2 padrão (os últimos que você mandou)
default_swid = "{E2237048-BE8A-4D17-8E42-21BA3E598AD3}"
default_s2 = "AEBKIwpBdqEIHIdRdiJg8Y5vavMr9VlHgjoxSKq7K8nlWkio6dsT2oTpcglkwNaZk%2B9gjRAfFt1hQxMbxP0uMS7QxvoEMyghKku1VM94862ft29QVO%2B2bsaRRNPK4%2FjARnmjwAV0%2BMifMwfF0X%2FWQx5LLCLoX9nLj%2B6NGyudSpWFuE9mQ2S0UltohZLpqQSJxQQgFkjF61BawPNyrXazTEYPepWONACBuRxIztS8zX1jhuAZZfT%2Fkb6G%2BDNaY8koYjRU%2BngmH4y3bJHQOjhOyfpe"

league_id = st.sidebar.text_input("League ID", value=default_league_id)
year = st.sidebar.number_input("Year", value=int(default_year))
swid = st.sidebar.text_input("SWID", value=default_swid)
espn_s2 = st.sidebar.text_input("ESPN_S2", value=default_s2)

st.sidebar.info("👉 Se der erro de autenticação, pegue novos cookies no navegador (eles expiram rápido!).")

# ==============================================================================
# 3. CORE LOGIC
# ==============================================================================
def get_espn_data(lid, yr, swid_val, s2_val, limit_fa=50):
    """
    Usa a biblioteca espn_api para buscar dados.
    """
    try:
        # Inicializa a Liga usando a biblioteca
        # Ela trata a autenticação e URL internamente
        league = League(league_id=int(lid), year=int(yr), espn_s2=s2_val, swid=swid_val)
        
        # Busca Free Agents (Jogadores livres)
        # size=limit_fa define quantos pegar. Pegamos mais para filtrar depois.
        free_agents = league.free_agents(size=limit_fa)
        
        if not free_agents:
            return None, "Nenhum Free Agent encontrado (ou falha silenciosa)."
            
        data = []
        for p in free_agents:
            # A biblioteca retorna objetos 'Player'. Vamos extrair o que precisamos.
            # Nota: Stats podem vir vazios se a season não começou ou é muito no futuro.
            
            # Tenta pegar média de pontos (varies by scoring type, usually 'total' or 'avg')
            avg_pts = p.avg_points if hasattr(p, 'avg_points') else 0.0
            
            # % Rostered (percent_owned)
            owned = p.percent_owned if hasattr(p, 'percent_owned') else 0.0
            
            # Stats Reais (Projected vs Actual)
            # A biblioteca estrutura stats complexos, vamos simplificar para FPTS padrão
            stats = p.stats
            # Tenta pegar a projeção ou média real da temporada atual
            
            data.append({
                "id": p.playerId,
                "Player": p.name,
                "Team": p.proTeam, # Ex: "LAL"
                "Position": p.position,
                "Owned%": owned,
                "Avg FPTS": avg_pts,
                "Status": p.injuryStatus
            })
            
        return pd.DataFrame(data), None
        
    except Exception as e:
        return None, str(e)

# ==============================================================================
# 4. MAIN UI
# ==============================================================================
st.title("Waiver Wire Scanner (Powered by espn-api)")

col1, col2 = st.columns([2, 1])
with col1:
    st.write("Conexão direta via biblioteca oficial. Mais estável e seguro.")
with col2:
    if st.button("🚀 Connect & Scan", type="primary"):
        st.session_state['trigger'] = True

if st.session_state.get('trigger'):
    with st.spinner("Connecting to ESPN API..."):
        df, error = get_espn_data(league_id, year, swid, espn_s2, limit_fa=100)
        
        if error:
            st.error(f"Erro de Conexão: {error}")
            st.error("Dica: Verifique se o SWID tem as chaves {} e se o ESPN_S2 está correto.")
        else:
            st.success(f"Sucesso! {len(df)} Free Agents encontrados.")
            
            # Filtros Visuais
            st.dataframe(
                df,
                column_config={
                    "Owned%": st.column_config.NumberColumn(format="%.1f%%"),
                    "Avg FPTS": st.column_config.NumberColumn(format="%.1f")
                },
                use_container_width=True,
                hide_index=True
            )