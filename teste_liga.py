import streamlit as st
import pandas as pd
from espn_api.basketball import League
import apex_config as cfg # Importa suas credenciais

# Configuração
st.set_page_config(page_title="Apex Liga Test", page_icon="🧬")
st.title("🧬 Apex League Diagnostics")

def run_test():
    # 1. TENTA LER AS VARIÁVEIS DO CONFIG
    try:
        lid = cfg.LEAGUE_ID
        st.success(f"Arquivo de configuração carregado. ID: {lid}")
    except AttributeError:
        st.error("ERRO CRÍTICO: Não salvei o arquivo apex_config.py corretamente.")
        st.stop()

    # 2. CONEXÃO COM A LIGA
    try:
        st.info("Conectando à ESPN API...")
        league = League(league_id=cfg.LEAGUE_ID, year=cfg.YEAR, espn_s2=cfg.ESPN_S2, swid=cfg.SWID)
        st.success(f"✅ Conectado: **{league.settings.name}** ({len(league.teams)} times)")
        
        # 3. MAPEAMENTO DE PONTUAÇÃO (A PARTE IMPORTANTE)
        st.subheader("📊 Mapeamento de Pontuação (IDs da ESPN)")
        st.write("Abaixo estão os códigos que a ESPN usa para a sua liga. Vamos usar isso para calibrar o robô.")
        
        # Tenta pegar o scoring_settings cru
        if hasattr(league.settings, 'scoring_settings'):
            raw_scoring = league.settings.scoring_settings
            
            # Cria tabela para visualizar
            score_data = []
            for stat_id, points in raw_scoring.items():
                score_data.append({"ESPN ID": stat_id, "Pontos": points})
            
            st.table(pd.DataFrame(score_data))
            st.caption("Tire um print dessa tabela ou me diga quais IDs tem valores negativos (ex: -0.5).")
            
        else:
            st.warning("A API não retornou 'scoring_settings' diretamente. Usaremos o modo manual.")

        # 4. TESTE DE TIME (Verifica se calculamos certo)
        st.subheader("🧪 Teste de Cálculo")
        my_team = league.teams[0] # Pega o primeiro time
        st.write(f"Time: {my_team.team_name} | Vitórias: {my_team.wins}")
        
    except Exception as e:
        st.error(f"Erro na Conexão: {e}")

if __name__ == "__main__":
    run_test()