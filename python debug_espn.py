import requests
import json
from fake_useragent import UserAgent

# ==============================================================================
# SEUS DADOS (COLOQUE EXATAMENTE COMO COPIOU DO NAVEGADOR - COM OS %)
# ==============================================================================
LEAGUE_ID = 300699640
SEASON_ID = 2026
SWID_RAW = "{E2237048-BE8A-4D17-8E42-21BA3E598AD3}"
# Cole aqui a versão GIGANTE com os %2B, %2F, etc. (A original do navegador)
ESPN_S2_RAW = "AEBKIwpBdqEIHIdRdiJg8Y5vavMr9VlHgjoxSKq7K8nlWkio6dsT2oTpcglkwNaZk%2B9gjRAfFt1hQxMbxP0uMS7QxvoEMyghKku1VM94862ft29QVO%2B2bsaRRNPK4%2FjARnmjwAV0%2BMifMwfF0X%2FWQx5LLCLoX9nLj%2B6NGyudSpWFuE9mQ2S0UltohZLpqQSJxQQgFkjF61BawPNyrXazTEYPepWONACBuRxIztS8zX1jhuAZZfT%2Fkb6G%2BDNaY8koYjRU%2BngmH4y3bJHQOjhOyfpe"

print("--- 🕵️ INICIANDO DIAGNÓSTICO DE CONEXÃO ---")

# 1. TENTATIVA COM COOKIES NO HEADER (MÉTODO BRUTO - IGUAL NAVEGADOR)
url = f"https://fantasy.espn.com/apis/v3/games/fba/seasons/{SEASON_ID}/segments/0/leagues/{LEAGUE_ID}?view=kona_player_info"

# Monta a string de cookie manualmente para evitar que o Python mude a formatação
cookie_string = f"swid={SWID_RAW}; espn_s2={ESPN_S2_RAW}"

ua = UserAgent()
headers = {
    'User-Agent': ua.random,
    'Cookie': cookie_string, # Envia direto, sem processar
    'x-fantasy-filter': json.dumps({
        "players": {
            "filterStatus": {"value": ["FREEAGENT", "WAIVERS", "ONTEAM"]},
            "limit": 5, # Pede só 5 jogadores pra testar rápido
            "sortPercOwned": {"sortPriority": 1, "sortAsc": False}
        }
    })
}

try:
    print(f"📡 Conectando na Liga {LEAGUE_ID} ({SEASON_ID})...")
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCESSO! Acesso liberado.")
        data = response.json()
        print(f"Jogadores encontrados: {len(data.get('players', []))}")
        print("A chave ESPN_S2 RAW (com %) funcionou!")
    elif response.status_code == 401:
        print("❌ ERRO 401: NÃO AUTORIZADO.")
        print("Significado: O servidor recusou o cookie espn_s2 ou swid.")
        print("Dica: Verifique se copiou o código inteiro ou se a sessão do navegador expirou.")
    elif response.status_code == 404:
        print("❌ ERRO 404: NÃO ENCONTRADO.")
        print("Significado: O ID da Liga ou o Ano da Temporada não existem nessa URL.")
    else:
        print(f"⚠️ ERRO DESCONHECIDO ({response.status_code})")
        print("Resposta do servidor (Primeiros 500 caracteres):")
        print(response.text[:500])

except Exception as e:
    print(f"🔥 ERRO CRÍTICO NO SCRIPT: {e}")

print("---------------------------------------------")