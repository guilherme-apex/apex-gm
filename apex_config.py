# ARQUIVO: apex_config.py
# LOCAL: D:\Dev\NBA_Fantasy\scripts\apex_config.py

# --- CREDENCIAIS DA LIGA (NBA GyG) ---
LEAGUE_ID = 300699640
YEAR = 2026

# Cookies (Copiados do seu histórico)
SWID = "{E2237048-BE8A-4D17-8E42-21BA3E598AD3}"
ESPN_S2 = "AECAc0HlD60N%2F%2FRe5jORzp7PQ5LJJ%2BehE7Z5WWzEtWdPFjopFMRix1mQFgRiYVhvhdSvG5O4Jj8Ob%2FUkUr%2FK3kp0CF5jaGo2hVwjDV4mEtGoiHRb7CkMxPRtHQYY%2BX55jFDUyEfSlrR7K3onCarGsyvPWEtXUpVuU7G1mKGl99LKnk1nvRqaq%2FcF8rDhbmiOm%2FCQSsxOPe8Mo6dlXhxAuIRAZ5elP6ah5tL7jVazvZj4gWvaJjCWLVQU8T2Z5A6lDcen8vbA6oWgd9LgCIojdHbg"

# --- REGRAS DE PONTUAÇÃO (MANUAL) ---
# Isso garante precisão matemática para o Trade Calculator
SCORING_RULES = {
    'PTS': 1,       # Points
    'REB': 1,       # Rebounds (Total)
    'AST': 2,       # Assists
    'STL': 4,       # Steals
    'BLK': 3,       # Blocks
    'TO': -2,       # Turnovers
    '3PM': 0.75,    # Three Pointers Made
    'FGMI': -0.5,   # Field Goals Missed
    'FTMI': -0.5,   # Free Throws Missed
    'OREB': 0.5,    # Offensive Rebounds (Bonus sobre o REB normal?)
    'EJ': -5,       # Ejections
    'QD': 100       # Quadruple Doubles
}