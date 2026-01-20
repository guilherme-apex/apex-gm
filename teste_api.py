import requests
import time
from datetime import datetime

# URL da ESPN para o Scoreboard
DATE = "20260116" # Testando a data de amanhã (Jogo Knicks vs GSW)
URL = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={DATE}"

print(f"--- INICIANDO DIAGNÓSTICO DE CONEXÃO ---")
print(f"Alvo: {URL}")

start_time = time.time()

try:
    # Tenta conectar
    print("1. Tentando conectar na ESPN...")
    response = requests.get(URL, timeout=10)
    
    # Mede o tempo
    elapsed = time.time() - start_time
    print(f"   Status Code: {response.status_code}")
    print(f"   Tempo de Resposta: {elapsed:.2f} segundos")
    
    if response.status_code == 200:
        data = response.json()
        games = data.get('events', [])
        print(f"2. Sucesso! Encontrei {len(games)} jogos para a data {DATE}.")
        
        print("\n--- LISTA DE JOGOS ENCONTRADOS ---")
        for event in games:
            comp = event['competitions'][0]
            home = comp['competitors'][0]['team']['displayName']
            away = comp['competitors'][1]['team']['displayName']
            print(f"   🏀 {away} @ {home}")
            
    else:
        print("❌ Erro: A API respondeu, mas com erro.")

except Exception as e:
    print(f"❌ ERRO CRÍTICO DE CONEXÃO: {e}")

print("\n--- DIAGNÓSTICO FINALIZADO ---")