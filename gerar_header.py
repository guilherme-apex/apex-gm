import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import requests
import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# ==============================================================================
# 1. CONFIGURAÇÕES DE DESIGN (A IDENTIDADE VISUAL APEX)
# ==============================================================================
# Cores
BG_COLOR = "#0e1117"   # Fundo Dark do Streamlit
NEON_GREEN = "#00ff41" # Verde Apex
RED_LINE = "#ff4b4b"   # Vermelho Vegas
TEXT_WHITE = "#e0e0e0" # Texto padrão
TEXT_GREY = "#a0a0a0"  # Texto secundário

# Dimensões do Header Twitter
HEADER_W, HEADER_H = 1500, 500

# Dados Fictícios "Vencedores"
VEGAS_LINE = 26.5
PLAYER_NAME = "Kevin Durant (PHX)"
ESPN_ID = "3202" # ID do KD para a foto
SLOGAN = "Data. Not Luck."

# ==============================================================================
# 2. GERAR DADOS FICTÍCIOS (TUDO GREEN ✅)
# ==============================================================================
def generate_winning_data():
    # Gera 10 datas recentes
    dates = [datetime.today() - timedelta(days=x*2) for x in range(10)]
    dates.reverse() # Ordem cronológica
    
    # Gera pontos SEMPRE acima da linha (entre 28 e 38)
    np.random.seed(42) # Para o resultado ser sempre igual e bonito
    points = np.random.randint(int(VEGAS_LINE) + 2, int(VEGAS_LINE) + 12, size=10)
    
    df = pd.DataFrame({'Date': dates, 'PTS': points})
    df['Date_Str'] = df['Date'].dt.strftime('%d/%b')
    return df

# ==============================================================================
# 3. FUNÇÕES DE APOIO (FOTO E FONTES)
# ==============================================================================
def get_player_photo(espn_id):
    url = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nba/players/full/{espn_id}.png&w=350&h=254"
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(io.BytesIO(response.content))
        # Redimensiona para caber no header
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        return img
    except:
        return Image.new('RGB', (150, 150), color='gray')

def get_fonts():
    # Tenta usar Arial (comum no Windows), senão usa padrão
    try:
        font_xl = ImageFont.truetype("arialbd.ttf", 70) # Métricas
        font_lg = ImageFont.truetype("arialbd.ttf", 40) # Nome Jogador
        font_md = ImageFont.truetype("arial.ttf", 24)   # Labels
        font_sm = ImageFont.truetype("arialbd.ttf", 20) # Banner/Slogan
    except IOError:
        font_xl = font_lg = font_md = font_sm = ImageFont.load_default()
    return font_xl, font_lg, font_md, font_sm

# ==============================================================================
# 4. GERAR O GRÁFICO (MATPLOTLIB)
# ==============================================================================
def create_chart_image(df):
    # Configura o estilo dark do matplotlib para bater com o app
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 4.5)) # Formato mais largo
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    
    # Linha Neon e Marcadores
    ax.plot(df['Date_Str'], df['PTS'], color=NEON_GREEN, marker='o', linewidth=4, markersize=10, markerfacecolor=BG_COLOR, markeredgewidth=3)
    
    # Linha de Vegas (Tracejada Vermelha)
    ax.axhline(y=VEGAS_LINE, color=RED_LINE, linestyle='--', linewidth=2.5, zorder=0)
    ax.text(df['Date_Str'].iloc[0], VEGAS_LINE - 1.5, f"Line: {VEGAS_LINE}", color=RED_LINE, fontsize=12)

    # Limpeza do Gráfico
    ax.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(TEXT_GREY)
    ax.spines['bottom'].set_color(TEXT_GREY)
    ax.tick_params(axis='x', colors=TEXT_GREY, labelsize=12)
    ax.tick_params(axis='y', colors=TEXT_GREY, labelsize=12)
    plt.xticks(rotation=0)
    
    # Salva o gráfico em memória
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', pad_inches=0.2)
    buf.seek(0)
    plt.close(fig)
    return Image.open(buf)

# ==============================================================================
# 5. MONTAGEM FINAL (PILLOW)
# ==============================================================================
def assemble_header():
    print("🎨 Iniciando criação do header...")
    # 1. Cria a tela preta de 1500x500
    canvas = Image.new('RGB', (HEADER_W, HEADER_H), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    f_xl, f_lg, f_md, f_sm = get_fonts()
    
    # 2. Busca e cola a foto
    photo = get_player_photo(ESPN_ID)
    canvas.paste(photo, (50, 120)) # Posição X, Y
    
    # 3. Textos da Esquerda (Simulando o App)
    # Nome Jogador
    draw.text((230, 130), PLAYER_NAME, font=f_lg, fill=TEXT_WHITE)
    draw.text((230, 180), "PTS Trend Analysis", font=f_md, fill=TEXT_GREY)

    # Métricas Grandes (L10 Avg / Consistency)
    df = generate_winning_data()
    avg_val = df['PTS'].mean()
    cv = (df['PTS'].std() / avg_val * 100)
    diff = avg_val - VEGAS_LINE
    
    draw.text((230, 250), f"{avg_val:.1f}", font=f_xl, fill=NEON_GREEN)
    draw.text((230, 320), "L10 Avg", font=f_md, fill=TEXT_GREY)
    
    draw.text((430, 250), f"{cv:.0f}% CV", font=f_xl, fill=NEON_GREEN)
    draw.text((430, 320), "Consistency", font=f_md, fill=TEXT_GREY)

    # Banner Verde "OVER EDGE"
    banner_x, banner_y = 230, 370
    banner_w, banner_h = 350, 40
    draw.rectangle([(banner_x, banner_y), (banner_x + banner_w, banner_y + banner_h)], fill="#1e3a2a", outline=NEON_GREEN, width=2)
    draw.text((banner_x + 20, banner_y + 8), f"🔥 OVER EDGE (+{diff:.1f})", font=f_sm, fill=NEON_GREEN)

    # 4. Gera e cola o Gráfico na direita
    print("📈 Gerando gráfico vencedor...")
    chart_img = create_chart_image(df)
    # Redimensiona o gráfico para caber no lado direito do header
    chart_w_target = 850
    ratio = chart_w_target / chart_img.width
    chart_h_target = int(chart_img.height * ratio)
    chart_resized = chart_img.resize((chart_w_target, chart_h_target), Image.Resampling.LANCZOS)
    
    # Cola o gráfico (Posição X=600 para ficar na direita)
    canvas.paste(chart_resized, (600, 50))

    # 5. Slogan no espaço vazio (Canto Superior Direito)
    slogan_text = SLOGAN.upper()
    # Calcula largura do texto para alinhar à direita
    bbox = draw.textbbox((0, 0), slogan_text, font=f_md)
    text_w = bbox[2] - bbox[0]
    draw.text((HEADER_W - text_w - 50, 50), slogan_text, font=f_md, fill=TEXT_WHITE, spacing=4)
    draw.line([(HEADER_W - text_w - 50, 80), (HEADER_W - 50, 80)], fill=NEON_GREEN, width=3) # Linha abaixo do slogan

    # 6. Salva o resultado
    # 6. Salva o resultado
    import os  # Importando aqui dentro para garantir que funcione
    
    # Caminho para o Desktop (Área de Trabalho)
    desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
    output_filename = os.path.join(desktop, "header_apex_kd_winner.png")
    
    canvas.save(output_filename)
    print(f"✅ Header criado com sucesso em: {output_filename}")
    print("Abra a imagem na sua Área de Trabalho e use no Twitter!")

# Só isso fica fora da função, na ultima linha:
if __name__ == "__main__":
    assemble_header()