import streamlit as st

st.set_page_config(page_title="Apex Visuals", layout="wide")

# CSS FORÇADO (Sem margem para erro)
st.markdown("""
<style>
    .content-card { background: linear-gradient(145deg, #161b22, #0d1117); border: 1px solid #30363d; border-radius: 16px; padding: 20px; margin-bottom: 20px; font-family: sans-serif; box-shadow: 0 10px 20px rgba(0,0,0,0.4); }
    .card-header { display: flex; align-items: center; margin-bottom: 15px; }
    .player-img { width: 70px; height: 70px; border-radius: 50%; border: 3px solid #58a6ff; object-fit: cover; background: #21262d; }
    .matchup-badge { background-color: rgba(63, 185, 80, 0.2); color: #3fb950; border: 1px solid #3fb950; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    .stat-bar-container { display: flex; align-items: flex-end; height: 60px; gap: 8px; margin-top: 15px; }
    .stat-col { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; }
    .stat-bar { width: 100%; background-color: #58a6ff; border-radius: 4px 4px 0 0; opacity: 0.9; }
    .stat-label { text-align: center; font-size: 12px; color: #8b949e; margin-top: 4px; font-weight: bold; }
    .tier-tag { float: right; background: #3fb950; color: white; padding: 4px 12px; border-bottom-left-radius: 12px; font-size: 14px; font-weight: 900; }
    .p-name { font-size: 20px; font-weight: 800; color: white; line-height: 1.2; margin: 0; }
    .p-team { font-size: 14px; color: #8b949e; font-weight: 600; text-transform: uppercase; margin: 0; }
</style>
""", unsafe_allow_html=True)

def render_card(name, team, opp, history):
    ids = {"Tyler Kolek": "4433136", "Jordan Clarkson": "2528426"}
    pid = ids.get(name, "4433136")
    img = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nba/players/full/{pid}.png&w=350&h=254"
    
    # CONSTRUÇÃO DAS BARRAS EM UMA LINHA SÓ (Para evitar bug visual)
    bars = ""
    max_v = max(history) + 5
    avg = sum(history)/3
    
    for v in history:
        h = (v / max_v) * 100
        # HTML compactado sem quebras de linha
        bars += f'<div class="stat-col"><div class="stat-bar" style="height:{h}%;"></div><div class="stat-label">{v}</div></div>'

    html = f"""
    <div class="content-card">
        <div style="overflow:hidden;"><div class="tier-tag">TIER S</div></div>
        <div class="card-header">
            <img src="{img}" class="player-img">
            <div style="margin-left:15px;">
                <div class="p-name">{name}</div>
                <div class="p-team">{team}</div>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="matchup-badge">🎯 vs {opp}</span>
            <span style="font-size:18px; font-weight:bold; color:white">{avg:.1f} <span style="font-size:12px; color:#8b949e">FPTS</span></span>
        </div>
        <div class="stat-bar-container">{bars}</div>
    </div>
    """
    return html

st.title("📸 Apex Content Factory")
c1, c2 = st.columns(2)
with c1: st.markdown(render_card("Tyler Kolek", "NY KNICKS", "GSW", [25, 30, 35]), unsafe_allow_html=True)
with c2: st.markdown(render_card("Jordan Clarkson", "NY KNICKS", "GSW", [35, 28, 42]), unsafe_allow_html=True)