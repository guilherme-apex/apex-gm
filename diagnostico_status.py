import requests
import json
from fake_useragent import UserAgent

# Configuração
ua = UserAgent()
headers = {'User-Agent': ua.random}

# ID do Utah Jazz na ESPN é 26
URL_ROSTER = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/26/roster"

print("--- INICIANDO DIAGNÓSTICO DE STATUS (UTAH JAZZ) ---")

try:
    response = requests.get(URL_ROSTER, headers=headers)
    data = response.json()
    
    found = False
    print(f"{'JOGADOR':<25} | {'STATUS NAME':<20} | {'TYPE':<10} | {'ABBREV'}")
    print("-" * 70)
    
    for athlete in data['athletes']:
        name = athlete['fullName']
        
        # Aqui está o segredo: Vamos ler o objeto 'status' cru
        status = athlete.get('status', {})
        s_name = status.get('name', 'N/A')
        s_type = status.get('type', 'N/A')
        s_abbr = status.get('abbreviation', 'N/A')
        
        # Filtra apenas o Kessler para facilitar, ou mostra todos os lesionados
        if 'Kessler' in name:
            found = True
            print(f"🕵️ ALVO ENCONTRADO:")
            print(f"Nome: {name}")
            print(f"Status RAW: {status}")
            print("-" * 30)
        
        # Imprime na tabela geral também
        print(f"{name:<25} | {s_name:<20} | {s_type:<10} | {s_abbr}")

    if not found:
        print("❌ Walker Kessler não foi encontrado no elenco do Jazz.")

except Exception as e:
    print(f"Erro na conexão: {e}")

print("\n--- FIM DO DIAGNÓSTICO ---")