import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from espn_api.basketball import League

# ==============================================================================
# CONFIG
# ==============================================================================
st.set_page_config(page_title="Apex Corsair Scanner", layout="wide", page_icon="🏴‍☠️")

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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ENGINE 1: O ESPIÃO (SCRAPER DO HASHTAG BASKETBALL)
# ==============================================================================
@st.cache_data(ttl=3600)
def scrape_hashtag_ownership():
    """
    Busca o % Rostered real no Hashtag Basketball.
    """
    url = "https://hashtagbasketball.com/fantasy-basketball-rankings"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, f"Erro Hashtag: {r.status_code}"
            
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find(id='ContentPlaceHolder1_GridView1')
        
        if not table:
            return None, "Tabela não encontrada."
            
        data = {}
        rows = table.find_all('tr')
        
        for row in rows[1:]:
            cols = row.find_all('td')
            if not cols: continue
            
            # Nome do Jogador
            player_tag = cols[1].find('a')
            if not player_tag: continue
            name = player_tag.text.strip().lower().replace('.', '') # Normaliza nome
            
            # Busca a % ESPN
            espn_owned = 0.0
            for col in cols:
                txt = col.text.strip()
                if '%' in txt and len(txt) < 6:
                    try:
                        val = float(txt.replace('%', ''))
                        espn_owned = val 
                    except: continue
            
            data[name] = espn_owned
            
        return data, None

    except Exception as e:
        return None, str(e)

# ==============================================================================
# ENGINE 2: A LIGA (SEUS JOGADORES)
# ==============================================================================
def get_league_free_agents(lid, yr, swid_val, s2_val):
    try:
        league = League(league_id=int(lid), year=int(yr), espn_s2=s2_val, swid=swid_val)
        # Pega 400 Free Agents para garantir profundidade
        free_agents = league.free_agents(size=400)
        return free_agents, None
    except Exception as e:
        return None, str(e)

# ==============================================================================
# UI
# ==============================================================================
st.sidebar.header("🔐 Configurações")
lid = st.sidebar.text_input("League ID", value="300699640")
yr = st.sidebar.number_input("Year", value=2026)
swid = st.sidebar.text_input("SWID", value="{E2237048-BE8A-4D17-8E42-21BA3E598AD3}")
s2 = st.sidebar.text_input("ESPN_S2", value="AEBKIwpBdqEIHIdRdiJg8Y5vavMr9VlHgjoxSKq7K8nlWkio6dsT2oTpcglkwNaZk%2B9gjRAfFt1hQxMbxP0uMS7QxvoEMyghKku1VM94862ft29QVO%2B2bsaRRNPK4%2FjARnmjwAV0%2BMifMwfF0X%2FWQx5LLCLoX9nLj%2B6NGyudSpWFuE9mQ2S0UltohZLpqQSJxQQgFkjF61BawPNyrXazTEYPepWONACBuRxIztS8zX1jhuAZZfT%2Fkb6G%2BDNaY8koYjRU%2BngmH4y3bJHQOjhOyfpe")

st.title("🏴‍☠️ Waiver Wire Corsair")
st.caption("Critérios Barutha: Deep (<10%) | Standard (<33%)")

c1, c2 = st.columns([2, 1])
with c1:
    target = st.selectbox(
        "Alvo do Scanner",
        [
            "💎 Deep League (< 10% Real Owned)", 
            "⚖️ Standard League (10% - 33% Real Owned)", 
            "🌟 Rostered / Stars (> 33% Real Owned)",
            "🔍 Show All Available"
        ]
    )
with c2:
    if st.button("🚀 Iniciar Operação", type="primary"):
        st.session_state['run'] = True

st.divider()

if st.session_state.get('run'):
    
    # 1. Scraping Externo
    with st.spinner("Buscando % Rostered no Hashtag Basketball..."):
        external_map, err_ext = scrape_hashtag_ownership()
        if err_ext:
            st.error(f"Falha Externa: {err_ext}")
            st.stop()
            
    # 2. Dados da Liga
    with st.spinner("Verificando disponibilidade na sua liga..."):
        local_players, err_loc = get_league_free_agents(lid, yr, swid, s2)
        if err_loc:
            st.error(f"Erro Local: {err_loc}")
            st.stop()
            
    # 3. Cruzamento e Filtro (Lógica Barutha)
    final_data = []
    
    # Definição das Faixas baseada no tweet do Barutha
    if "Deep" in target: 
        min_o, max_o = 0.0, 10.0
    elif "Standard" in target: 
        min_o, max_o = 10.0, 33.0
    elif "Stars" in target: 
        min_o, max_o = 33.0, 100.0
    else: 
        min_o, max_o = 0.0, 100.0
    
    for p in local_players:
        p_name_key = p.name.lower().replace('.', '').strip()
        
        # Tenta achar o ownership real
        real_owned = external_map.get(p_name_key, 0.0)
        
        # Fallback de busca parcial
        if real_owned == 0.0:
            for k, v in external_map.items():
                if k in p_name_key or p_name_key in k:
                    real_owned = v
                    break
        
        # Aplica Filtro
        if not (min_o <= real_owned <= max_o):
            continue
            
        # Pega Stats
        avg_pts = p.avg_points if hasattr(p, 'avg_points') else 0.0
        
        # Formatação Visual de Status
        status_icon = "🟢" if p.injuryStatus == 'ACTIVE' else "🔴" if p.injuryStatus == 'OUT' else "🟡"
        
        final_data.append({
            "Player": p.name,
            "Team": p.proTeam,
            "Status": f"{status_icon} {p.injuryStatus}",
            "Real Owned%": real_owned,
            "Avg FPTS": avg_pts
        })
        
    df = pd.DataFrame(final_data)
    
    if df.empty:
        st.warning(f"Nenhum jogador encontrado na faixa {min_o}% - {max_o}%.")
    else:
        # Ordena por pontos (já que estamos filtrando por ownership, queremos ver quem pontua mais nessa faixa)
        df = df.sort_values(by="Avg FPTS", ascending=False)
        
        st.success(f"{len(df)} Jogadores Encontrados (Critério Barutha).")
        
        st.dataframe(
            df,
            column_order=["Player", "Team", "Status", "Real Owned%", "Avg FPTS"],
            column_config={
                "Real Owned%": st.column_config.ProgressColumn(
                    format="%.1f%%", min_value=0, max_value=100
                ),
                "Avg FPTS": st.column_config.NumberColumn(format="%.1f"),
            },
            use_container_width=True,
            hide_index=True
        )