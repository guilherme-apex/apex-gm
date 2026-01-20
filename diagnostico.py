import streamlit as st
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
import time

# ==============================================================================
# CONFIGURAÇÃO DA UI
# ==============================================================================
st.set_page_config(page_title="Apex Diagnostic Tool", layout="wide", page_icon="🔧")

st.markdown("""
<style>
    .console {
        background-color: #000000;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        padding: 15px;
        border-radius: 5px;
        height: 500px;
        overflow-y: scroll;
        white-space: pre-wrap;
        font-size: 12px;
    }
    .fail { color: #ff3333; }
    .success { color: #33ff33; }
    .info { color: #33ccff; }
    .data { color: #ffff33; }
</style>
""", unsafe_allow_html=True)

if 'logs' not in st.session_state: st.session_state['logs'] = []

def log(msg, type="info"):
    icon = "ℹ️"
    if type == "fail": icon = "❌"
    if type == "success": icon = "✅"
    if type == "data": icon = "🔍"
    
    st.session_state['logs'].append(f"<span class='{type}'>{icon} {msg}</span>")

# ==============================================================================
# TESTE 1: HASHTAG BASKETBALL (SCRAPING)
# ==============================================================================
def test_hashtag():
    log("--- INICIANDO TESTE 1: SCRAPING HASHTAG BASKETBALL ---", "info")
    url = "https://hashtagbasketball.com/fantasy-basketball-rankings"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        log(f"Status Code: {r.status_code}", "info" if r.status_code == 200 else "fail")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Tenta achar TODAS as tabelas
            tables = soup.find_all('table')
            log(f"Tabelas encontradas na página: {len(tables)}", "info")
            
            for i, table in enumerate(tables):
                # Pega os cabeçalhos da tabela para ver os nomes das colunas
                headers = [th.text.strip() for th in table.find_all('th')]
                log(f"Tabela #{i} - Cabeçalhos encontrados: {headers}", "data")
                
                # Tenta pegar a primeira linha de dados
                rows = table.find_all('tr')
                if len(rows) > 1:
                    first_row_cols = [td.text.strip() for td in rows[1].find_all('td')]
                    log(f"Tabela #{i} - Linha 1 (Amostra): {first_row_cols}", "data")
                    
                    # Verifica se tem dados de ownership
                    found_pct = False
                    for col in first_row_cols:
                        if "%" in col:
                            log(f"--> DETECTADO FORMATO DE PORCENTAGEM: '{col}'", "success")
                            found_pct = True
                    if not found_pct:
                        log("--> NENHUMA PORCENTAGEM VISÍVEL NESTA LINHA.", "fail")
                else:
                    log(f"Tabela #{i} está vazia.", "fail")
                log("------------------------------------------------", "info")

    except Exception as e:
        log(f"Erro Crítico Hashtag: {str(e)}", "fail")

# ==============================================================================
# TESTE 2: ESPN GLOBAL API (2025)
# ==============================================================================
def test_espn_global(cookies=None):
    log("--- INICIANDO TESTE 2: ESPN API GLOBAL (2025) ---", "info")
    url = "https://fantasy.espn.com/apis/v3/games/fba/seasons/2025/segments/0/leagues/0?view=kona_player_info"
    
    headers = {
        'x-fantasy-filter': json.dumps({
            "players": {
                "filterStatus": {"value": ["FREEAGENT", "WAIVERS", "ONTEAM"]},
                "limit": 3, 
                "sortPercOwned": {"sortPriority": 1, "sortAsc": False}
            }
        })
    }
    
    try:
        r = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        log(f"Status Code: {r.status_code}", "info" if r.status_code == 200 else "fail")
        
        if r.status_code == 200:
            data = r.json()
            if 'players' in data and len(data['players']) > 0:
                p = data['players'][0]
                name = p.get('fullName', 'Unknown')
                owned = p.get('ownership', {}).get('percentOwned', 'N/A')
                log(f"Jogador Top 1: {name}", "success")
                log(f"Campo 'percentOwned': {owned}", "data")
                
                # Mostra chaves do objeto ownership para ver se mudou o nome
                keys = list(p.get('ownership', {}).keys())
                log(f"Estrutura do objeto 'ownership': {keys}", "data")
            else:
                log("JSON retornado mas lista 'players' está vazia.", "fail")
                log(f"Chaves do JSON: {list(data.keys())}", "data")
        elif r.status_code == 401:
            log("Erro 401: Falha de Permissão (Cookies necessários para dados globais?)", "fail")

    except Exception as e:
        log(f"Erro Crítico ESPN: {str(e)}", "fail")

# ==============================================================================
# UI
# ==============================================================================
st.sidebar.title("🛠️ Console DevTools")
st.sidebar.markdown('<div class="console">' + "".join(st.session_state['logs']) + '</div>', unsafe_allow_html=True)
if st.sidebar.button("LIMPAR CONSOLE"):
    st.session_state['logs'] = []
    st.rerun()

st.title("Diagnóstico de Fonte de Dados")
st.markdown("Este script vai varrer as fontes possíveis e mostrar a estrutura bruta dos dados.")

c1, c2 = st.columns(2)
with c1:
    swid_in = st.text_input("SWID (Opcional)", value="{E2237048-BE8A-4D17-8E42-21BA3E598AD3}")
with c2:
    s2_in = st.text_input("ESPN_S2 (Opcional)", value="AEBKIwpBdqEIHIdRdiJg8Y5vavMr9VlHgjoxSKq7K8nlWkio6dsT2oTpcglkwNaZk%2B9gjRAfFt1hQxMbxP0uMS7QxvoEMyghKku1VM94862ft29QVO%2B2bsaRRNPK4%2FjARnmjwAV0%2BMifMwfF0X%2FWQx5LLCLoX9nLj%2B6NGyudSpWFuE9mQ2S0UltohZLpqQSJxQQgFkjF61BawPNyrXazTEYPepWONACBuRxIztS8zX1jhuAZZfT%2Fkb6G%2BDNaY8koYjRU%2BngmH4y3bJHQOjhOyfpe")

if st.button("RODAR DIAGNÓSTICO COMPLETO", type="primary"):
    st.session_state['logs'] = []
    
    # Executa Teste 1
    test_hashtag()
    
    # Executa Teste 2 (Sem Cookies)
    log("--- TESTANDO ESPN SEM COOKIES ---", "info")
    test_espn_global(cookies=None)
    
    # Executa Teste 2 (Com Cookies)
    log("--- TESTANDO ESPN COM COOKIES ---", "info")
    cookies = {"swid": swid_in, "espn_s2": s2_in}
    test_espn_global(cookies=cookies)
    
    st.rerun()