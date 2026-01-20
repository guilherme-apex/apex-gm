import streamlit as st
import pandas as pd
import requests
import json
from espn_api.basketball import League

# ==============================================================================
# CONFIG
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ENGINE 1: DADOS GLOBAIS (LEAGUE 0 - 2025)
# Aqui pegamos a % Rostered REAL do mundo todo.
# ==============================================================================
@st.cache_data(ttl=3600)
def get_global_ownership_map():
    # Usamos 2025 porque é onde a massa de dados está populada
    url = "https://fantasy.espn.com/apis/v3/games/fba/seasons/2025/segments/0/leagues/0?view=kona_player_info"
    
    headers = {
        'x-fantasy-filter': json.dumps({
            "players": {
                "filterStatus": {"value": ["FREEAGENT", "WAIVERS", "ONTEAM"]},
                "limit": 6000, 
                "sortPercOwned": {"sortPriority": 1, "sortAsc": False}
            }
        })
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            ownership_map = {}
            for p in data.get('players', []):
                pid = str(p['id'])
                owned = p.get('ownership', {}).get('percentOwned', 0.0)
                ownership_map[pid] = owned
            return ownership_map
        return {}
    except:
        return {}

# ==============================================================================
# ENGINE 2: SUA LIGA (APENAS PARA VER QUEM ESTÁ LIVRE)
# ==============================================================================
def run_scan(lid, yr, swid_val, s2_val, target_profile):
    status_msg = st.empty()
    
    try:
        # 1. Buscar % Global
        status_msg.info("🌍 Carregando dados globais de ownership...")
        global_map = get_global_ownership_map()
        
        # 2. Conectar na Liga Privada
        status_msg.info(f"🔒 Verificando Free Agents na liga {lid}...")
        league = League(league_id=int(lid), year=int(yr), espn_s2=s2_val, swid=swid_val)
        
        # Pega Free Agents (Trazemos bastante para filtrar depois)
        free_agents = league.free_agents(size=400)
        
        if not free_agents:
            status_msg.empty()
            return None, "Nenhum Free Agent encontrado."

        data = []
        
        # 3. Definição dos Perfis (CRITÉRIO SOLICITADO)
        if target_profile == "Deep League Gems":
            # Jogadores ignorados pela maioria (< 30%), mas disponíveis
            min_own = 0.0
            max_own = 30.0
        elif target_profile == "Standard League Adds":
            # Jogadores de rotação sólida (30% a 70%)
            min_own = 30.0
            max_own = 75.0
        elif target_profile == "Must Roster / Stars":
            # Jogadores que não deveriam estar livres (> 75%)
            min_own = 75.0
            max_own = 100.0
        else:
            # Mostra tudo
            min_own = 0.0
            max_own = 100.0

        status_msg.info("⚡ Aplicando filtros de Ownership Global...")
        
        for p in free_agents:
            pid = str(p.playerId)
            
            # Pega o % Rostered GLOBAL (A verdade)
            # Se não achar (ex: rookie novo de 2026), assume 0.0
            real_owned = global_map.get(pid, 0.0)
            
            # --- O FILTRO DE OURO ---
            # Só passa se o ownership global estiver dentro do critério escolhido
            if not (min_own <= real_owned <= max_own):
                continue
            
            # Stats (Média)
            avg_pts = p.avg_points if hasattr(p, 'avg_points') else 0.0

            # Status
            status_raw = p.injuryStatus
            icon = "🟢" if status_raw == 'ACTIVE' else "🔴" if status_raw == 'OUT' else "🟡"
            
            data.append({
                "Player": p.name,
                "Team": p.proTeam,
                "Pos": p.position,
                "Status": f"{icon} {status_raw}",
                "Global %": real_owned, # AQUI ESTÁ O DADO QUE VOCÊ QUERIA
                "Avg FPTS": avg_pts
            })
            
        df = pd.DataFrame(data)
        if not df.empty:
            # Ordena pelo Ownership Global (do maior para o menor dentro da categoria)
            df = df.sort_values(by="Global %", ascending=False)
            
        status_msg.empty()
        return df, None

    except Exception as e:
        status_msg.empty()
        return None, f"Erro: {str(e)}"

# ==============================================================================
# UI
# ==============================================================================
# Sidebar Credentials
st.sidebar.header("🔐 Configurações")
lid = st.sidebar.text_input("League ID", value="300699640")
yr = st.sidebar.number_input("Year", value=2026)
swid = st.sidebar.text_input("SWID", value="{E2237048-BE8A-4D17-8E42-21BA3E598AD3}")
s2 = st.sidebar.text_input("ESPN_S2", value="AEBKIwpBdqEIHIdRdiJg8Y5vavMr9VlHgjoxSKq7K8nlWkio6dsT2oTpcglkwNaZk%2B9gjRAfFt1hQxMbxP0uMS7QxvoEMyghKku1VM94862ft29QVO%2B2bsaRRNPK4%2FjARnmjwAV0%2BMifMwfF0X%2FWQx5LLCLoX9nLj%2B6NGyudSpWFuE9mQ2S0UltohZLpqQSJxQQgFkjF61BawPNyrXazTEYPepWONACBuRxIztS8zX1jhuAZZfT%2Fkb6G%2BDNaY8koYjRU%2BngmH4y3bJHQOjhOyfpe")

st.title("Waiver Wire Scanner")
st.caption("Filtro Baseado em Ownership Global Real (2025 Data)")

c1, c2 = st.columns([2, 1])
with c1:
    profile = st.selectbox(
        "O que você procura?", 
        ["Deep League Gems (0-30% Rostered)", 
         "Standard League Adds (30-75% Rostered)", 
         "Must Roster / Stars (>75% Rostered)",
         "Show All Available"]
    )
with c2:
    if st.button("🚀 Scan Market", type="primary"):
        st.session_state['trigger'] = True

st.divider()

if st.session_state.get('trigger'):
    df, error = run_scan(lid, yr, swid, s2, profile)
    
    if error:
        st.error(error)
        st.warning("Verifique se os cookies SWID/S2 estão atualizados (F12 no navegador).")
    elif df is None or df.empty:
        st.info(f"Nenhum jogador encontrado na faixa '{profile}'. Tente outra categoria.")
    else:
        st.success(f"Encontrados {len(df)} jogadores disponíveis nessa faixa.")
        
        st.dataframe(
            df,
            column_order=["Player", "Team", "Pos", "Status", "Global %", "Avg FPTS"],
            column_config={
                "Global %": st.column_config.ProgressColumn(
                    "Global % Owned", 
                    format="%.1f%%", 
                    min_value=0, 
                    max_value=100
                ),
                "Avg FPTS": st.column_config.NumberColumn(format="%.1f"),
            },
            use_container_width=True,
            hide_index=True
        )