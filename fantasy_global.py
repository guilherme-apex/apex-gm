import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Global Market Radar", layout="wide", page_icon="🌎")

st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; }
    div.stButton > button:first-child {
        background-color: #0099ff;
        color: white;
        height: 50px;
        font-weight: bold;
    }
    .deep-tag { color: #ff4b4b; font-weight: bold; }
    .std-tag { color: #00cc66; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ENGINE: SCRAPING HASHTAG BASKETBALL (DADOS GLOBAIS)
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_global_rankings():
    """
    Busca o ranking global e a % de Ownership (ESPN) direto do Hashtag Basketball.
    """
    url = "https://hashtagbasketball.com/fantasy-basketball-rankings"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, f"Erro HTTP: {r.status_code}"
            
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find(id='ContentPlaceHolder1_GridView1')
        
        if not table:
            return None, "Tabela de dados não encontrada."
            
        players = []
        rows = table.find_all('tr')
        
        # Itera sobre as linhas (ignorando header)
        for row in rows[1:]:
            cols = row.find_all('td')
            if not cols: continue
            
            # Extração de Dados
            try:
                # Nome e Time
                player_link = cols[1].find('a')
                if not player_link: continue
                
                full_name = player_link.text.strip()
                
                # Extrai Posição e Time (geralmente estão em spans ou texto solto)
                # O Hashtag formata como: "Player Name (TEAM, POS)"
                # Mas aqui vamos simplificar pegando o texto da célula
                meta_text = cols[1].text.strip()
                
                # Busca Ownership (Geralmente as ultimas colunas)
                # Vamos varrer procurando o símbolo '%'
                espn_owned = 100.0 # Valor padrão alto para não passar no filtro se falhar
                
                # Procura a coluna que tem % (Yahoo ou ESPN)
                # No Hashtag, a ESPN costuma ser a penúltima
                for col in reversed(cols):
                    txt = col.text.strip()
                    if '%' in txt:
                        try:
                            val = float(txt.replace('%', ''))
                            espn_owned = val
                            # Se achou um valor, assume que é esse e para (pega o último que geralmente é ESPN)
                            break 
                        except: continue
                
                # Busca Stats Principais (Pontos, Reb, Ast, Stl, Blk)
                # Índices aproximados: PTS=9, REB=10, AST=11, STL=12, BLK=13 (Isso pode variar)
                # Vamos pegar pelo texto para garantir
                
                # Cria objeto do jogador
                players.append({
                    "Player": full_name,
                    "Rostered %": espn_owned,
                    # Pegamos alguns stats chave para ajudar na decisão
                    "PTS": cols[9].text.strip(),
                    "REB": cols[10].text.strip(),
                    "AST": cols[11].text.strip(),
                    "STL": cols[12].text.strip(),
                    "BLK": cols[13].text.strip()
                })
                
            except Exception:
                continue
                
        return pd.DataFrame(players), None

    except Exception as e:
        return None, str(e)

# ==============================================================================
# UI PRINCIPAL
# ==============================================================================
st.title("🌎 Global Market Radar")
st.caption("Filtra jogadores baseado APENAS na % Rostered Global (Critério Barutha).")

# Seleção de Filtro (Barutha)
filter_option = st.selectbox(
    "Selecione o Perfil do Jogador:",
    [
        "💎 Deep Leagues (< 10% Rostered)",
        "⚖️ Standard Leagues (< 33% Rostered)",
        "🌟 All Players (Sem Filtro)"
    ]
)

if st.button("🚀 Rastrear Mercado Global"):
    with st.spinner("Analisando mercado global (Hashtag Basketball)..."):
        df, error = fetch_global_rankings()
        
        if error:
            st.error(f"Falha ao buscar dados: {error}")
        elif df is None or df.empty:
            st.warning("Nenhum dado encontrado.")
        else:
            # APLICAÇÃO DOS FILTROS
            original_len = len(df)
            
            if "Deep" in filter_option:
                filtered_df = df[df['Rostered %'] < 10.0]
                msg = "Jogadores com menos de 10% de ownership."
            elif "Standard" in filter_option:
                filtered_df = df[df['Rostered %'] < 33.0]
                msg = "Jogadores com menos de 33% de ownership."
            else:
                filtered_df = df
                msg = "Todos os jogadores."
            
            # Ordena: Menos Rostered primeiro (Gemas) ou Melhores Stats?
            # Melhor ordenar por % Rostered Crescente (Mais livres)
            filtered_df = filtered_df.sort_values(by="Rostered %", ascending=True)
            
            st.success(f"Encontrados {len(filtered_df)} jogadores (de {original_len} totais). {msg}")
            
            # Exibição da Tabela
            st.dataframe(
                filtered_df,
                column_order=["Player", "Rostered %", "PTS", "REB", "AST", "STL", "BLK"],
                column_config={
                    "Rostered %": st.column_config.ProgressColumn(
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        help="Porcentagem de times que possuem este jogador (Global)"
                    ),
                    "PTS": st.column_config.NumberColumn(format="%.1f"),
                    "REB": st.column_config.NumberColumn(format="%.1f"),
                    "AST": st.column_config.NumberColumn(format="%.1f"),
                },
                use_container_width=True,
                hide_index=True
            )