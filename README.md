# 🧬 Apex Fantasy Engine (Public Beta)

![Status](https://img.shields.io/badge/Status-Public_Beta-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Tech](https://img.shields.io/badge/Streamlit-SaaS-red)

**Apex Fantasy Engine** é uma ferramenta de *Data Science* e análise preditiva para NBA Fantasy & DFS. Diferente de ferramentas que dependem de "achismo", o Apex utiliza algoritmos de média ponderada e análise de matchups em tempo real para identificar **ineficiências de mercado** (Moneyball).

🔗 **Acesse a Ferramenta Online:** [apex-fantasy.streamlit.app](https://apex-fantasy.streamlit.app/)

---

## 🚀 O Motor (Features)

A ferramenta escaneia os 30 times da NBA instantaneamente através de APIs oficiais e processa os dados para gerar insights acionáveis:

### 🧠 Weighted Projections
O algoritmo ignora médias simples da temporada. Ele aplica um peso dinâmico (**70% Forma Recente / 30% Histórico**) para projetar o que o jogador fará *hoje*.

### 🛡️ Matchup Analysis (Live)
Cruza o calendário do dia com o **Ranking Defensivo** atualizado da NBA.
- 🟢 **Green Light:** Jogador enfrenta uma das 5 piores defesas (Rank 25-30).
- 🔴 **Red Flag:** Jogador enfrenta uma defesa de elite (Rank 1-10).

### 🔥 Heat Check & Trends
Identifica anomalias de performance.
- **Trend Positiva (+):** Jogadores esquentando e ganhando minutos.
- **Trend Negativa (❄️):** Estrelas em declínio ou perdendo espaço na rotação.

### 💎 Moneyball Detector
Filtra automaticamente as "Superestrelas" (>30 FPTS) para focar no que importa para quem joga Fantasy: **Waiver Wire Gems** e **Role Players** com alto potencial de retorno.

---

## 📸 Interface (Dark Mode UI)

*A interface foi desenhada para ser responsiva (Mobile/Desktop) e direta ao ponto.*

> *Nota: A ferramenta atualiza automaticamente estatísticas e lesões a cada acesso.*

---

## 🛠️ Tech Stack (Bastidores)

Este projeto utiliza Engenharia de Dados moderna para garantir velocidade e estabilidade:

* **Core:** Python 3.10+
* **Front-end:** Streamlit Cloud (SaaS)
* **Data Fetching:** `aiohttp` (Requisições Assíncronas para 30 endpoints simultâneos)
* **Data Processing:** `pandas` & `numpy`
* **Source:** ESPN Official Endpoints (Hidden APIs)

---

## 👨‍💻 Autor

Desenvolvido por **Guilherme Lopes de Souza**.
*Data Scientist turning stats into wins.*

---