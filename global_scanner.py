import streamlit as st
import pandas as pd
import requests
import json

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Global Market Radar", layout="wide", page_icon="🌎")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    /* Estilo para as métricas */
    div[data-testid="metric-container"] {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 10px;
        border-radius: 5px;
    }
    div.stButton > button:first-child {
        background-color: #0099ff;
        color: white;
        font-weight: bold;
        height: 50px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ENGINE: ACESSO À LIGA 0 (GLOBAL DATA)
# ==============================================================================
@st.cache_data(ttl=1800) # Cache de 30 min para não ficar batendo na API toda hora
def fetch_global_market(season_id=2026):
    """
    Busca os dados globais da ESPN (League 0).
    Não requer autenticação (SWID/S2) pois é endpoint público.
    """
    url = f"https://fantasy.espn.com/apis/v3/games/fba/seasons/{season_id}/segments/0/leagues/0?view=kona_player_info"
    
    # Filtro: Pegar Top 5000 jogadores ordenados por % Rostered
    # Isso garante que temos desde o Jokic (100%) até o bagre (0.1%)
    filters = {
        "players": {
            "filterStatus": {"value": ["FREEAGENT", "WAIVERS", "ONTEAM"]},
            "limit": 5000, 
            "sortPercOwned": {"sortPriority": 1, "sortAsc": False}
        }
    }
    
    headers = {'x-fantasy-filter': json.dumps(filters)}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except:
        return None

def process_market_data(raw_data):
    if not raw_data: return pd.DataFrame()
    
    players = []
    
    for p in raw_data.get('players', []):
        # 1. Dados Básicos
        pid = p.get('id')
        name = p.get('fullName', 'Unknown')
        team = p.get('proTeam', 'FA') # Ex: "LAL"
        pos = p.get('defaultPositionId', 0) # Simplificado
        
        # 2. Ownership Global (A Chave do Sucesso)
        owned = p.get('ownership', {}).get('percentOwned', 0.0)
        change = p.get('ownership', {}).get('percentChange', 0.0)
        
        # 3. Estatísticas (Season Avg)
        # A ESPN retorna stats em estruturas complexas ('stats' -> lista de anos/tipos)
        # Vamos tentar pegar a projeção ou média atual.
        stats_list = p.get('player', {}).get('stats', [])
        
        avg_pts = 0.0
        avg_min = 0.0
        
        # Tenta achar stats da temporada 2026 (id=002026) e tipo=0 (Total) ou 1 (Proj) ou 2 (Avg)
        # Geralmente stats reais estão onde 'statSourceId' é 0 (Real) e 'scoringPeriodId' é 0 (Season)
        current_stats = None
        for s in stats_list:
            if s.get('seasonId') == 2026 and s.get('statSourceId') == 0 and s.get('statSplitTypeId') == 0:
                current_stats = s.get('appliedAverage', 0.0) # Pontos Fantasy (Avg)
                avg_min = s.get('stats', {}).get('0', 0.0) # Minutos costuma ser chave '0' ou similar dependendo da liga
                break
        
        # Se não achou na estrutura complexa, tenta na raiz (alguns endpoints trazem)
        if not current_stats and hasattr(p, 'avg_points'):
             current_stats = p.avg_points
        
        # Se ainda for 0, pega o 'appliedTotal' e divide por jogos, ou usa o valor bruto se for média
        if not current_stats:
             # Fallback simples: Tenta pegar qualquer valor de pontos disponível
             current_stats = p.get('draftRanksByRankType', {}).get('STANDARD', {}).get('rank', 0)
             # Nota: Sem autenticação na liga específica, o cálculo exato de FPTS varia.
             # Vamos usar o 'percentOwned' como proxy principal e tentar achar stats onde der.
             
             # CORREÇÃO: Vamos usar o ownership para filtrar, e se não tiver stats, mostramos N/A
             # mas a ferramenta foca em DESCOBRIR nomes.
             pass

        # Para facilitar, vamos assumir que queremos filtrar por OWNERSHIP.
        # O Stats exato depende das settings da liga, mas o Global % é universal.
        
        players.append({
            "id": pid,
            "Player": name,
            "Team": team,
            "Global %": owned,
            "Change (+/-)": change,
            "Status": p.get('injuryStatus', 'ACTIVE')
        })
        
    return pd.DataFrame(players)

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("🌎 Global Market Radar")
st.caption("Monitoramento de Tendências Globais (ESPN League 0)")

# Filtros
c1, c2 = st.columns([2, 1])
with c1:
    market_segment = st.selectbox(
        "Selecione o Segmento de Mercado",
        [
            "💎 Deep Gems (0% - 30% Rostered)",
            "⚖️ Standard Rotation (30% - 80% Rostered)",
            "🌟 Stars & Studs (80% - 100% Rostered)",
            "🚀 Trending Up (Maiores Altas)"
        ]
    )
with c2:
    if st.button("Rastrear Mercado Global"):
        st.session_state['run_global'] = True

st.divider()

if st.session_state.get('run_global'):
    with st.spinner("Conectando satélite na ESPN Global..."):
        raw = fetch_global_market(2026)
        
        if not raw:
            # Fallback para 2025 se 2026 estiver vazio (início de temporada)
            raw = fetch_global_market(2025)
            st.toast("Usando dados de referência 2025 (2026 indisponível)", icon="ℹ️")
            
        df = process_market_data(raw)
        
        if df.empty:
            st.error("Falha ao receber dados da ESPN.")
        else:
            # APLICAÇÃO DOS FILTROS
            if "Deep" in market_segment:
                filtered_df = df[df['Global %'] <= 30.0].sort_values(by="Global %", ascending=False)
                st.success(f"🔍 Encontrados {len(filtered_df)} jogadores no espectro Deep.")
            elif "Standard" in market_segment:
                filtered_df = df[(df['Global %'] > 30.0) & (df['Global %'] <= 80.0)].sort_values(by="Global %", ascending=False)
                st.success(f"🔍 Encontrados {len(filtered_df)} jogadores de Rotação Standard.")
            elif "Stars" in market_segment:
                filtered_df = df[df['Global %'] > 80.0].sort_values(by="Global %", ascending=False)
            elif "Trending" in market_segment:
                filtered_df = df.sort_values(by="Change (+/-)", ascending=False).head(100)
            
            # Exibição
            st.dataframe(
                filtered_df,
                column_order=["Player", "Team", "Status", "Global %", "Change (+/-)"],
                column_config={
                    "Global %": st.column_config.ProgressColumn(
                        "Global Rostered",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100
                    ),
                    "Change (+/-)": st.column_config.NumberColumn(
                        "Trend (7 Days)",
                        format="%+.1f%%"
                    )
                },
                use_container_width=True,
                hide_index=True
            )
            
            st.info("💡 Dica: Estes são os dados globais. Verifique manualmente na sua liga se eles estão livres.")