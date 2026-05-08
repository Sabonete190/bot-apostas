import streamlit as st

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Bot de Apostas",
    layout="centered"
)

# TÍTULO
st.title("📊 Bot de Apostas Profissional")

st.write("Preencha os dados da partida.")

# =========================
# ODDS 1X2
# =========================

st.subheader("Mercado 1X2")

odd_casa = st.number_input(
    "Odd Casa",
    min_value=1.0,
    step=0.01
)

odd_empate = st.number_input(
    "Odd Empate",
    min_value=1.0,
    step=0.01
)

odd_fora = st.number_input(
    "Odd Fora",
    min_value=1.0,
    step=0.01
)

# =========================
# OVER / UNDER
# =========================

st.subheader("Over / Under")

odd_over15 = st.number_input(
    "Odd Over 1.5",
    min_value=1.0,
    step=0.01
)

odd_over25 = st.number_input(
    "Odd Over 2.5",
    min_value=1.0,
    step=0.01
)

odd_over35 = st.number_input(
    "Odd Over 3.5",
    min_value=1.0,
    step=0.01
)

# =========================
# BTTS
# =========================

st.subheader("BTTS")

odd_btts_sim = st.number_input(
    "Odd BTTS SIM",
    min_value=1.0,
    step=0.01
)

odd_btts_nao = st.number_input(
    "Odd BTTS NÃO",
    min_value=1.0,
    step=0.01
)

# =========================
# DADOS DOS TIMES
# =========================

st.subheader("Dados dos Times")

xg_casa = st.number_input(
    "xG Casa",
    min_value=0.0,
    step=0.1
)

xg_fora = st.number_input(
    "xG Fora",
    min_value=0.0,
    step=0.1
)

xga_casa = st.number_input(
    "xGA Casa",
    min_value=0.0,
    step=0.1
)

xga_fora = st.number_input(
    "xGA Fora",
    min_value=0.0,
    step=0.1
)

sofridos_casa = st.number_input(
    "Gols Sofridos Casa",
    min_value=0.0,
    step=0.1
)

sofridos_fora = st.number_input(
    "Gols Sofridos Fora",
    min_value=0.0,
    step=0.1
)

chutes_casa = st.number_input(
    "Chutes no Gol Casa",
    min_value=0.0,
    step=0.1
)

chutes_fora = st.number_input(
    "Chutes no Gol Fora",
    min_value=0.0,
    step=0.1
)

eficiencia_casa = st.number_input(
    "Eficiência Casa",
    min_value=0.0,
    step=0.1
)

eficiencia_fora = st.number_input(
    "Eficiência Fora",
    min_value=0.0,
    step=0.1
)
# =========================
# BOTÃO
# =========================

if st.button("Analisar Jogo"):

    # =========================
    # FORÇA OFENSIVA
    # =========================

    ataque_casa = (
        xg_casa * 0.5 +
        chutes_casa * 0.3 +
        eficiencia_casa * 0.2
    )

    ataque_fora = (
        xg_fora * 0.5 +
        chutes_fora * 0.3 +
        eficiencia_fora * 0.2
    )

    # =========================
    # FORÇA DEFENSIVA
    # =========================

    defesa_casa = (
        xga_casa * 0.6 +
        sofridos_casa * 0.4
    )

    defesa_fora = (
        xga_fora * 0.6 +
        sofridos_fora * 0.4
    )

    # =========================
    # FORÇA DE GOL
    # =========================

    forca_gol = (
        (ataque_casa / (defesa_fora + 0.5)) +
        (ataque_fora / (defesa_casa + 0.5))
    ) / 2

    st.subheader("Análise Estatística")

    st.write(f"Ataque Casa: {round(ataque_casa, 2)}")
    st.write(f"Ataque Fora: {round(ataque_fora, 2)}")

    st.write(f"Defesa Casa: {round(defesa_casa, 2)}")
    st.write(f"Defesa Fora: {round(defesa_fora, 2)}")

    st.write(f"Força de Gol: {round(forca_gol, 2)}")
    # =========================
    # PROBABILIDADES IMPLÍCITAS
    # =========================

    prob_casa = 1 / odd_casa
    prob_empate = 1 / odd_empate
    prob_fora = 1 / odd_fora

    # =========================
    # NORMALIZAÇÃO
    # =========================

    soma = prob_casa + prob_empate + prob_fora

    prob_casa /= soma
    prob_empate /= soma
    prob_fora /= soma

    # =========================
    # RESULTADO
    # =========================

    st.success("Análise concluída")

    st.subheader("Probabilidades")

    st.write(f"Casa: {round(prob_casa * 100, 2)}%")
    st.write(f"Empate: {round(prob_empate * 100, 2)}%")
    st.write(f"Fora: {round(prob_fora * 100, 2)}%")

# =========================
    # EV
    # =========================

    ev_casa = (prob_casa * odd_casa) - 1
    ev_empate = (prob_empate * odd_empate) - 1
    ev_fora = (prob_fora * odd_fora) - 1

    st.subheader("EV")

    st.write(f"EV Casa: {round(ev_casa, 2)}")
    st.write(f"EV Empate: {round(ev_empate, 2)}")
    st.write(f"EV Fora: {round(ev_fora, 2)}")

    # =========================
    # DECISÃO
    # =========================

    st.subheader("Decisão")

    if ev_casa > 0.05:
        st.success("ENTRAR CASA")
    else:
        st.error("NÃO ENTRAR CASA")

    if ev_empate > 0.05:
        st.success("ENTRAR EMPATE")
    else:
        st.error("NÃO ENTRAR EMPATE")

    if ev_fora > 0.05:
        st.success("ENTRAR FORA")
    else:
        st.error("NÃO ENTRAR FORA")
