import streamlit as st
import pandas as pd
from espn_api.basketball import League

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Apex Performance Scanner", layout="wide", page_icon="📈")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    div.stButton > button:first-child {
        background-color: #00b4d8;
        color: white;
        font-weight: bold;
        height: 50px;
        margin-top: 25px;
    }
    .big-stat { font-size: 18px; font-weight: bold; color: #00ff00; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ENGINE: CONEXÃO VIA API (CONFIÁVEL)
# ==============================================================================
def get_top_free_agents(lid, yr, swid_val, s2_val, limit=100):
    try:
        league = League(league_id=int(lid), year=int(yr), espn_s2=s2_val, swid=swid_val)
        
        # Busca os Top Free Agents disponíveis na sua liga
        # A API já retorna ordenado pelos melhores disponíveis geralmente
        free_agents = league.free_agents(size=limit)
        
        if not free_agents:
            return None, "Nenhum Free Agent encontrado ou erro de conexão."
            
        data = []
        for p in free_agents:
            # Tenta pegar a média de pontos da temporada
            avg_pts = p.avg_points if hasattr(p, 'avg_points') else 0.0
            
            # Se a média for 0 (as vezes acontece no inicio), tenta calcular pelo total
            if avg_pts == 0 and hasattr(p, 'total_points') and hasattr(p, 'games_played'):
                 if p.games_played > 0:
                     avg_pts = p.total_points / p.games_played

            # Status de Lesão
            status_icon = "🟢"
            if p.injuryStatus == 'OUT': status_icon = "🔴"
            elif p.injuryStatus == 'DAY_TO_DAY': status_icon = "🟡"
            
            data.append({
                "Player": p.name,
                "Team": p.proTeam,
                "Pos": p.position,
                "Status": f"{status_icon} {p.injuryStatus}",
                "Avg FPTS": avg_pts,
                "Total FPTS": p.total_points if hasattr(p, 'total_points') else 0
            })
            
        return pd.DataFrame(data), None

    except Exception as e:
        return None, f"Erro de API: {str(e)}"

# ==============================================================================
# UI
# ==============================================================================
st.sidebar.header("🔐 Suas Credenciais")
lid = st.sidebar.text_input("League ID", value="300699640")
yr = st.sidebar.number_input("Year", value=2026)
swid = st.sidebar.text_input("SWID", value="{E2237048-BE8A-4D17-8E42-21BA3E598AD3}")
s2 = st.sidebar.text_input("ESPN_S2", value="AEBKIwpBdqEIHIdRdiJg8Y5vavMr9VlHgjoxSKq7K8nlWkio6dsT2oTpcglkwNaZk%2B9gjRAfFt1hQxMbxP0uMS7QxvoEMyghKku1VM94862ft29QVO%2B2bsaRRNPK4%2FjARnmjwAV0%2BMifMwfF0X%2FWQx5LLCLoX9nLj%2B6NGyudSpWFuE9mQ2S0UltohZLpqQSJxQQgFkjF61BawPNyrXazTEYPepWONACBuRxIztS8zX1jhuAZZfT%2Fkb6G%2BDNaY8koYjRU%2BngmH4y3bJHQOjhOyfpe")

st.title("📈 Apex Performance Scanner")
st.caption("Substituto do %Rostered: Encontre valor real baseado em PONTUAÇÃO, não em fama.")

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    min_fpts = st.slider("Mínimo de Média (FPTS)", 0.0, 60.0, 20.0, step=0.5)
with c2:
    status_filter = st.selectbox("Status", ["Todos", "Apenas Ativos (🟢)", "Ativos + DTD (🟢+🟡)"])
with c3:
    if st.button("🚀 Escanear Waiver Wire"):
        st.session_state['scan_trigger'] = True

st.divider()

if st.session_state.get('scan_trigger'):
    with st.spinner("Analisando mercado via API..."):
        df, error = get_top_free_agents(lid, yr, swid, s2, limit=200)
        
        if error:
            st.error(error)
        elif df is None or df.empty:
            st.warning("Nenhum jogador encontrado.")
        else:
            # 1. Filtro de Pontuação Mínima
            df_filtered = df[df['Avg FPTS'] >= min_fpts].copy()
            
            # 2. Filtro de Status
            if status_filter == "Apenas Ativos (🟢)":
                df_filtered = df_filtered[df_filtered['Status'].str.contains("🟢")]
            elif status_filter == "Ativos + DTD (🟢+🟡)":
                df_filtered = df_filtered[~df_filtered['Status'].str.contains("🔴")]
            
            # 3. Ordenação (Do maior FPTS para o menor)
            df_filtered = df_filtered.sort_values(by="Avg FPTS", ascending=False)
            
            # Métricas
            top_player = df_filtered.iloc[0]['Player'] if not df_filtered.empty else "N/A"
            count = len(df_filtered)
            
            m1, m2 = st.columns(2)
            m1.metric("Jogadores Encontrados", count)
            m2.metric("Melhor Disponível", top_player)
            
            st.subheader(f"💎 Melhores Opções Disponíveis (>{min_fpts} FPTS)")
            
            st.dataframe(
                df_filtered,
                column_order=["Player", "Team", "Pos", "Status", "Avg FPTS", "Total FPTS"],
                column_config={
                    "Avg FPTS": st.column_config.ProgressColumn(
                        format="%.1f", 
                        min_value=0, 
                        max_value=60, # Ajuste conforme a pontuação máxima da sua liga
                        help="Média de pontos por jogo na temporada."
                    ),
                    "Total FPTS": st.column_config.NumberColumn(format="%d")
                },
                use_container_width=True,
                hide_index=True,
                height=600
            )
            
            if df_filtered.empty:
                st.info("Nenhum jogador atingiu o critério de pontos selecionado. Tente baixar a régua.")