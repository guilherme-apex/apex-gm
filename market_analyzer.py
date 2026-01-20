import streamlit as st
import pandas as pd
import re

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Apex Market Miner V156", layout="wide", page_icon="⛏️")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    textarea { font-family: monospace; font-size: 11px; }
    .stat-box { 
        background-color: #1e1e1e; 
        border: 1px solid #333; 
        padding: 10px; 
        border-radius: 5px; 
        text-align: center; 
    }
    .stat-val { font-size: 20px; font-weight: bold; color: #0099ff; }
    .stat-lbl { font-size: 11px; color: #888; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ENGINE: MINERADOR HÍBRIDO (VERTICAL/HORIZONTAL)
# ==============================================================================
def mine_data_v156(raw_text):
    # Limpeza básica
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    # --- 1. EXTRAÇÃO DE NOMES ---
    # Lógica: O nome do jogador sempre aparece ANTES da sigla do time.
    # Siglas comuns da ESPN
    nba_teams = {
        "Atl", "Bkn", "Bos", "Cha", "Chi", "Cle", "Dal", "Den", "Det", "GS", "Hou", "Ind", 
        "LAC", "LAL", "Mem", "Mia", "Mil", "Min", "NO", "NY", "OKC", "Orl", "Phi", "Phx", 
        "Por", "SA", "Sac", "Tor", "Utah", "Wsh", "FA"
    }
    
    extracted_names = []
    
    for i in range(1, len(lines)):
        current_line = lines[i]
        prev_line = lines[i-1]
        
        # Se a linha atual é um Time e a anterior não é lixo conhecido
        if current_line in nba_teams:
            # Limpa o nome (remove status de lesão O/DTD/etc)
            clean_name = re.sub(r'^(O|DTD|SSM|IR|OUT)\s+', '', prev_line).strip()
            
            # Filtro anti-ruído (evita pegar cabeçalhos)
            if clean_name not in ["Player", "Team", "Type", "Action", "STATUS"]:
                # Às vezes a ESPN cola o nome duplicado "NomeNome". 
                # Se for muito longo e repetir, cortamos no meio.
                if len(clean_name) > 10 and clean_name[:len(clean_name)//2] == clean_name[len(clean_name)//2:]:
                    clean_name = clean_name[:len(clean_name)//2]
                
                extracted_names.append(clean_name)

    # --- 2. EXTRAÇÃO DE PORCENTAGENS (% ROSTERED) ---
    # Lógica Híbrida:
    # Caso A (Horizontal): "31.6 100.0 0" -> Pega 100.0
    # Caso B (Vertical): Linha X="100.0", Linha X+1="0" (Inteiro, o +/-)
    
    extracted_percents = []
    
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        
        # Tenta achar padrão Horizontal primeiro (vários números na mesma linha)
        # Procura decimal entre 0-100 seguido de inteiro no final da linha
        horiz_match = re.search(r'(\d{1,3}\.\d)\s+([+\-]?\d+)$', line)
        if horiz_match:
            try:
                val = float(horiz_match.group(1))
                if 0.0 <= val <= 100.0:
                    extracted_percents.append(val)
                    i += 1
                    continue
            except: pass
            
        # Tenta achar padrão Vertical
        # Linha atual é float (0-100), Linha seguinte é int (+/-)
        try:
            # Verifica se linha atual é número
            if re.match(r'^\d{1,3}\.\d$', line):
                val = float(line)
                
                # Verifica se a PRÓXIMA linha é um inteiro (+/-)
                next_line = lines[i+1]
                if re.match(r'^[+\-]?\d+$', next_line):
                    # BINGO! Achamos um par (% e +/-)
                    if 0.0 <= val <= 100.0:
                        extracted_percents.append(val)
                        i += 2 # Pula os dois
                        continue
        except: pass
        
        i += 1

    # --- 3. ALINHAMENTO ---
    # O número de nomes e stats deve bater. Se não bater, cortamos o excesso.
    limit = min(len(extracted_names), len(extracted_percents))
    
    data = []
    for k in range(limit):
        p_name = extracted_names[k]
        p_rost = extracted_percents[k]
        
        # Classificação Barutha
        if p_rost < 10.0: cat = "💎 Deep (<10%)"
        elif p_rost < 33.0: cat = "⚖️ Standard (<33%)"
        else: cat = "🌟 Rostered"
        
        data.append({
            "Player": p_name,
            "Rostered %": p_rost,
            "Category": cat
        })
        
    return pd.DataFrame(data), len(extracted_names), len(extracted_percents)

# ==============================================================================
# UI
# ==============================================================================
st.title("⛏️ Apex Market Miner V156 (Vertical Fix)")
st.caption("Cole o texto completo das 22 páginas. O sistema detecta dados verticais e horizontais.")

c1, c2 = st.columns([3, 1])

with c1:
    raw_input = st.text_area(
        "Cole os dados brutos aqui:", 
        height=300, 
        placeholder="Cole as 22 páginas aqui..."
    )
    
    if st.button("🚀 Processar Dados", type="primary"):
        if not raw_input:
            st.error("Cole o texto primeiro!")
        else:
            df, n_names, n_stats = mine_data_v156(raw_input)
            
            if df.empty:
                st.error(f"Erro: Encontrei {n_names} nomes e {n_stats} porcentagens. O formato está ilegível.")
            else:
                # Remove duplicatas
                df = df.drop_duplicates(subset=['Player'])
                st.session_state['data_v156'] = df
                st.success(f"Sucesso Absoluto! {len(df)} jogadores processados.")

# VISUALIZAÇÃO
if 'data_v156' in st.session_state:
    df = st.session_state['data_v156']
    
    # Contadores
    deep_count = len(df[df['Category'] == "💎 Deep (<10%)"])
    std_count = len(df[df['Category'] == "⚖️ Standard (<33%)"])
    
    with c2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-val">{len(df)}</div>
            <div class="stat-lbl">Total</div>
        </div>
        <div style="margin-top: 5px"></div>
        <div class="stat-box" style="border-color: #00ff00">
            <div class="stat-val" style="color: #00ff00">{deep_count}</div>
            <div class="stat-lbl">Deep Gems</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # Filtros
    filter_val = st.radio("Visualizar:", ["💎 Deep Gems (<10%)", "⚖️ Standard (<33%)", "🌟 Tudo"], horizontal=True)
    
    if "Deep" in filter_val:
        final_df = df[df['Category'] == "💎 Deep (<10%)"].sort_values(by="Rostered %", ascending=True)
    elif "Standard" in filter_val:
        final_df = df[df['Category'] == "⚖️ Standard (<33%)"].sort_values(by="Rostered %", ascending=True)
    else:
        final_df = df.sort_values(by="Rostered %", ascending=False)
        
    st.dataframe(
        final_df,
        column_order=["Player", "Rostered %", "Category"],
        column_config={
            "Rostered %": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0, max_value=100
            )
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )