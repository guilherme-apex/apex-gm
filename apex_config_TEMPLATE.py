# ------------------------------------------------------------------------------
# CONFIGURAÇÃO DA LIGA (MODELO)
# Renomeie este arquivo para 'apex_config.py' e insira seus dados.
# ------------------------------------------------------------------------------

# Credenciais da Liga ESPN
LEAGUE_ID = 12345678  # Substitua pelo ID da sua liga
YEAR = 2026           # Ano da temporada
SWID = "{SEU_SWID_AQUI}"
ESPN_S2 = "SEU_ESPN_S2_AQUI"

# Regras de Pontuação (Ajuste conforme sua liga)
SCORING_RULES = {
    'PTS': 1.0,
    'REB': 1.2,
    'AST': 1.5,
    'STL': 3.0,
    'BLK': 3.0,
    'TO': -1.0,
    'FGM': 0.0,
    'FGA': 0.0,
    'FTM': 0.0,
    'FTA': 0.0,
    '3PM': 0.0,
}