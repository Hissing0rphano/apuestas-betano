import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.data_loader import FootballDataLoader, LEAGUE_MAP
from src.poisson_model import DixonColesPoissonModel
from src.value_finder import ValueBetFinder
from src.betano_scraper import BetanoChileScraper, COMPETITIONS_MAP
from src.tracker import MultiUserBetTracker

# Configuración de la página (Responsive para Móvil y PC)
st.set_page_config(
    page_title="Apuestas Estadísticas - Betano Chile Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS de alto contraste
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.3rem;
    }
    .sub-header {
        font-size: 1.05rem;
        text-align: center;
        color: #888;
        margin-bottom: 1.5rem;
    }
    .value-card-green {
        background-color: #D4EDDA !important;
        border-left: 6px solid #28A745 !important;
        padding: 16px !important;
        border-radius: 8px !important;
        margin-bottom: 14px !important;
        color: #002200 !important;
    }
    .value-card-gold {
        background-color: #FFF3CD !important;
        border-left: 6px solid #FFC107 !important;
        padding: 16px !important;
        border-radius: 8px !important;
        margin-bottom: 14px !important;
        color: #4A3B00 !important;
    }
    .legend-bar {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 0.95rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 10px;
    }
    .card-title {
        font-size: 1.25rem !important;
        font-weight: 800 !important;
        margin-bottom: 6px !important;
    }
    .card-text {
        font-size: 1.0rem !important;
        font-weight: 600 !important;
        margin-bottom: 4px !important;
    }
    .card-ev {
        font-size: 1.4rem !important;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FUNCIONES CON CACHE PARA ALTO RENDIMIENTO
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_all_historical_models():
    loader = FootballDataLoader()
    models = {}
    for code in ['SP1', 'E0', 'D1', 'I1', 'F1']:
        df = loader.load_combined_seasons(code, start_years=[2023, 2024, 2025])
        if not df.empty:
            m = DixonColesPoissonModel(time_decay=0.001)
            m.fit(df)
            models[code] = m
    return models

# Inicializar Tracker y Buscador de Valor
tracker = MultiUserBetTracker()
finder = ValueBetFinder()
scraper = BetanoChileScraper()

# ---------------------------------------------------------
# BARRA LATERAL (LIMPIA: SOLO PERFILES DE USUARIO)
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/000000/soccer-ball.png", width=65)
st.sidebar.title("⚽ Betano Chile Pro")

# Selector de Usuario Activo
users_list = tracker.get_users()
active_user = st.sidebar.selectbox("👤 Apostador Activo", options=users_list, index=0)
tracker.set_active_user(active_user)

# Crear o Eliminar Amigos
with st.sidebar.expander("👥 Gestionar Amigos"):
    new_friend_name = st.text_input("Nombre del Nuevo Amigo")
    if st.button("➕ Agregar Amigo"):
        if tracker.add_user(new_friend_name):
            st.success(f"¡Amigo '{new_friend_name}' agregado!")
            st.rerun()

    if len(users_list) > 1:
        st.markdown("---")
        friend_to_remove = st.selectbox("Eliminar Amigo", options=[u for u in users_list if u != "Fernando"])
        if st.button("🗑️ Eliminar Amigo"):
            if tracker.remove_user(friend_to_remove):
                st.success(f"¡Amigo '{friend_to_remove}' eliminado!")
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Semáforo IA:**\n\n🟩 **≥ 70%** (Muy Segura)\n\n🟨 **55-69%** (Segura)\n\n🟥 **40-54%** (Ajustada)\n\n⚠️ **< 40%** (Alto Riesgo)")

# Cargar Modelos Estadísticos
with st.spinner("Inicializando modelos estadísticos..."):
    league_models = load_all_historical_models()
    base_model = league_models.get('SP1', DixonColesPoissonModel())

# ---------------------------------------------------------
# HEADER PRINCIPAL
# ---------------------------------------------------------
st.markdown("<div class='main-header'>⚽ Algoritmo de Apuestas - Betano Chile Automático</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-header'>Apostador Activo: <b>{active_user}</b> | Pronósticos Inteligentes 1X2 (betanosports.com)</div>", unsafe_allow_html=True)

# Pestañas Principales
tab_populares, tab_ligas, tab_tracker, tab_ratings = st.tabs([
    "🔥 Partidos Populares & Top Recomendaciones",
    "🏆 Explorar por Ligas & Campeonatos",
    "👥 Duelo de Amigos & Tracker",
    "📊 Ratings & Racha de Equipos"
])

def build_highlighted_table(matches_df, highlight_enabled=True):
    """Genera la tabla con semáforo por color según probabilidad: 🟩 ≥70%, 🟨 55-69%, 🟥 40-54%, ⚠️ <40%."""
    table_rows = []
    all_picks = []

    for _, match in matches_df.iterrows():
        home = match['home_team']
        away = match['away_team']
        o1 = float(match['odds_1']) if match.get('odds_1') else 1.0
        oX = float(match['odds_X']) if match.get('odds_X') else 1.0
        o2 = float(match['odds_2']) if match.get('odds_2') else 1.0
        horario = match.get('horario', 'Pronto')
        liga = match['liga']

        c1_str = str(o1)
        cX_str = str(oX)
        c2_str = str(o2)
        nivel_str = "—"

        try:
            pred = base_model.predict_match(home, away, odds_1=o1, odds_X=oX, odds_2=o2)
            ai_pick = finder.get_match_ai_prediction(pred, {'odds_1': o1, 'odds_X': oX, 'odds_2': o2})
            ai_pick['liga'] = liga
            all_picks.append(ai_pick)

            best = ai_pick['best_pick']
            prob = ai_pick['pick_prob_%']

            # Definición del Semáforo según rangos pedidos por el usuario:
            # ≥70% -> 🟩, 55-69% -> 🟨, 40-54% -> 🟥, <40% -> ⚠️
            if prob >= 70.0:
                emoji = "🟩"
                tag = "Muy Segura"
            elif prob >= 55.0:
                emoji = "🟨"
                tag = "Segura"
            elif prob >= 40.0:
                emoji = "🟥"
                tag = "Ajustada"
            else:
                emoji = "⚠️"
                tag = "Alto Riesgo"

            if highlight_enabled:
                nivel_str = f"{emoji} {prob}% - {tag}"
                if best == '1':
                    c1_str = f"{emoji} {o1} (IA)"
                elif best == 'X':
                    cX_str = f"{emoji} {oX} (IA)"
                elif best == '2':
                    c2_str = f"{emoji} {o2} (IA)"
        except Exception:
            pass

        row_dict = {
            'Horario ⏰ (Chile)': horario,
            'Liga 🏆': liga,
            'Local 🏠 (Equipo 1)': home,
            'Visitante ✈️ (Equipo 2)': away,
            'Cuota 1': c1_str,
            'Cuota X': cX_str,
            'Cuota 2': c2_str
        }
        if highlight_enabled:
            row_dict['Nivel IA 💡'] = nivel_str

        table_rows.append(row_dict)

    return pd.DataFrame(table_rows), all_picks

# =========================================================
# TAB 1: PARTIDOS POPULARES & TOP RECOMENDACIONES (PORTADA)
# =========================================================
with tab_populares:
    st.subheader("🔥 Partidos Populares del Día & Pronósticos Recomendados")
    st.write("La IA analiza en tiempo real las cuotas de **Betano Chile** y te entrega el pronóstico más certero para cada partido.")

    col_btn, col_blank = st.columns([1, 1])
    with col_btn:
        scan_pop_button = st.button("🔄 Escanear Partidos Populares en Vivo", type="primary", use_container_width=True)

    if scan_pop_button or 'pop_matches_df' in st.session_state:
        if scan_pop_button:
            with st.spinner("Escaneando partidos populares de Betano Chile y calculando pronósticos IA..."):
                st.session_state.pop_matches_df = scraper.get_matches_by_competition('POPULARES', max_matches=20)

        pop_df = st.session_state.get('pop_matches_df', pd.DataFrame())

        if not pop_df.empty:
            st.markdown("---")
            
            # INTERRUPTOR INTELIGENTE IA
            highlight_pop = st.toggle("🟢 Modo Inteligente IA: Resaltar Semáforo de Cuotas en la Tabla", value=True, key="toggle_pop")

            st.markdown("<div class='legend-bar'>🚦 <b>Semáforo de Probabilidades:</b> 🟩 ≥70% (Muy Segura) | 🟨 55-69% (Segura) | 🟥 40-54% (Ajustada) | ⚠️ &lt;40% (Alto Riesgo)</div>", unsafe_allow_html=True)

            table_pop_df, all_picks = build_highlighted_table(pop_df, highlight_enabled=highlight_pop)
            
            st.success(f"Se encontraron {len(table_pop_df)} partidos en Betano Chile (Horario oficial de Chile).")
            # Mostrar tabla sin índice numérico 0, 1, 2...
            st.dataframe(table_pop_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 🌟 Top 5 Mejores Pronósticos Seleccionados por la IA")

            if all_picks:
                sorted_picks = sorted(all_picks, key=lambda x: x['pick_prob_%'], reverse=True)

                for idx, pick in enumerate(sorted_picks[:5]):
                    st.markdown(f"""
                    <div class='{pick['badge_class']}'>
                        <div class='card-title'>{pick['confianza']}: {pick['partido']}</div>
                        <div class='card-text'>👉 <b>Elección Recomendada:</b> {pick['pick_label']} | <b>Cuota Betano:</b> {pick['pick_odds']} | <b>Cuota Justa IA:</b> {pick['fair_odd']}</div>
                        <div class='card-text'>📊 <b>Probabilidad Estimada por la IA:</b> {pick['pick_prob_%']}%</div>
                        <div class='card-ev'>🔥 Ventaja Matemática (EV): +{pick['pick_ev_%']}%</div>
                        <div class='card-text'>💡 <b>Justificación:</b> {pick['justificacion']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"⚡ Aceptar Pronóstico en 1-Clic para {active_user} (Pronóstico #{idx+1})", key=f"btn_pop_{idx}"):
                        tracker.register_bet(
                            username=active_user,
                            match_name=pick['partido'],
                            league=pick['liga'],
                            market=pick['pick_label'],
                            odds=pick['pick_odds'],
                            stake=10.0,
                            ev_pct=pick['pick_ev_%']
                        )
                        st.success(f"¡Pronóstico registrado exitosamente para {active_user}!")
            else:
                st.info("No se pudieron generar pronósticos para los partidos actuales.")
        else:
            st.warning("No se pudieron cargar partidos desde Betano. Presiona el botón para escanear.")

# =========================================================
# TAB 2: EXPLORAR POR LIGAS & CAMPEONATOS
# =========================================================
with tab_ligas:
    st.subheader("🏆 Explorar Cuotas en Vivo por Liga o Campeonato")
    st.write("Selecciona una competencia específica para consultar los partidos y pronósticos en tiempo real desde **Betano Chile**.")

    selected_comp_key = st.selectbox(
        "Seleccionar Liga o Campeonato",
        options=list(COMPETITIONS_MAP.keys()),
        format_func=lambda x: COMPETITIONS_MAP[x],
        index=1  # Default: Premier League
    )

    col_lbtn, col_lblank = st.columns([1, 1])
    with col_lbtn:
        scan_league_btn = st.button(f"🔄 Consultar {COMPETITIONS_MAP[selected_comp_key]} en Vivo", type="primary", use_container_width=True)

    if scan_league_btn or f"league_matches_{selected_comp_key}" in st.session_state:
        if scan_league_btn:
            with st.spinner(f"Consultando {COMPETITIONS_MAP[selected_comp_key]} en Betano Chile y calculando pronósticos..."):
                st.session_state[f"league_matches_{selected_comp_key}"] = scraper.get_matches_by_competition(selected_comp_key, max_matches=25)

        league_matches_df = st.session_state.get(f"league_matches_{selected_comp_key}", pd.DataFrame())

        if not league_matches_df.empty:
            st.markdown("---")
            
            # INTERRUPTOR INTELIGENTE IA
            highlight_league = st.toggle("🟢 Modo Inteligente IA: Resaltar Semáforo de Cuotas en la Tabla", value=True, key=f"toggle_lg_{selected_comp_key}")

            st.markdown("<div class='legend-bar'>🚦 <b>Semáforo de Probabilidades:</b> 🟩 ≥70% (Muy Segura) | 🟨 55-69% (Segura) | 🟥 40-54% (Ajustada) | ⚠️ &lt;40% (Alto Riesgo)</div>", unsafe_allow_html=True)

            table_league_df, league_picks = build_highlighted_table(league_matches_df, highlight_enabled=highlight_league)

            st.success(f"Se encontraron {len(table_league_df)} partidos en {COMPETITIONS_MAP[selected_comp_key]} (Horario oficial de Chile).")
            # Mostrar tabla sin índice numérico 0, 1, 2...
            st.dataframe(table_league_df, use_container_width=True, hide_index=True)

            st.markdown(f"### 🌟 Top Pronósticos en {COMPETITIONS_MAP[selected_comp_key]}")
            if league_picks:
                sorted_lg_picks = sorted(league_picks, key=lambda x: x['pick_prob_%'], reverse=True)
                for idx, pick in enumerate(sorted_lg_picks[:5]):
                    st.markdown(f"""
                    <div class='{pick['badge_class']}'>
                        <div class='card-title'>{pick['confianza']}: {pick['partido']}</div>
                        <div class='card-text'>👉 <b>Elección Recomendada:</b> {pick['pick_label']} | <b>Cuota Betano:</b> {pick['pick_odds']} | <b>Cuota Justa IA:</b> {pick['fair_odd']}</div>
                        <div class='card-text'>📊 <b>Probabilidad Estimada por la IA:</b> {pick['pick_prob_%']}%</div>
                        <div class='card-ev'>🔥 Ventaja Matemática (EV): +{pick['pick_ev_%']}%</div>
                        <div class='card-text'>💡 <b>Justificación:</b> {pick['justificacion']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"⚡ Aceptar Pronóstico de {selected_comp_key} para {active_user} (#{idx+1})", key=f"btn_lg_{selected_comp_key}_{idx}"):
                        tracker.register_bet(
                            username=active_user,
                            match_name=pick['partido'],
                            league=pick['liga'],
                            market=pick['pick_label'],
                            odds=pick['pick_odds'],
                            stake=10.0,
                            ev_pct=pick['pick_ev_%']
                        )
                        st.success(f"¡Pronóstico registrado para {active_user}!")
            else:
                st.info("No se pudieron generar pronósticos en esta liga.")
        else:
            st.info(f"ℹ️ No hay partidos programados para {COMPETITIONS_MAP[selected_comp_key]} en este momento en Betano Chile.")

# =========================================================
# TAB 3: DUELO DE AMIGOS & TRACKER MULTI-USUARIO
# =========================================================
with tab_tracker:
    st.subheader("👥 Tabla de Posiciones y Historial de Amigos")
    st.write("Compara el rendimiento, porcentaje de aciertos y estado de apuestas entre tú y tus amigos.")

    lead_df = tracker.get_leaderboard()
    if not lead_df.empty:
        st.dataframe(lead_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 📋 Historial de Apuestas Registradas")

    filter_user = st.selectbox("Filtrar Historial por Amigo", options=["Todos"] + users_list, index=0)
    target_user = None if filter_user == "Todos" else filter_user
    bets_df = tracker.get_bets_df(username=target_user)

    if not bets_df.empty:
        st.dataframe(bets_df[['id', 'usuario', 'fecha', 'partido', 'liga', 'mercado', 'cuota', 'ev_pct', 'estado']], use_container_width=True, hide_index=True)

        st.markdown("#### ⚙️ Actualizar Estado de Apuesta")
        c_id, c_st = st.columns(2)
        with c_id:
            bet_id_to_edit = st.selectbox("Seleccionar Apuesta ID", options=bets_df['id'].tolist())
        with c_st:
            new_status = st.selectbox("Nuevo Estado", options=["Pendiente ⏳", "Ganada ✅", "Perdida ❌", "Anulada ⚪"])

        if st.button("Actualizar Estado"):
            tracker.update_bet_status(bet_id_to_edit, new_status)
            st.success("¡Estado de apuesta actualizado!")
            st.rerun()
    else:
        st.info("No hay apuestas registradas en el historial aún. Usa el botón '⚡ Aceptar Pronóstico en 1-Clic' en la portada para registrar apuestas.")

# =========================================================
# TAB 4: RATINGS & RACHA DE EQUIPOS
# =========================================================
with tab_ratings:
    st.subheader("📊 Ratings Dixon-Coles y Fuerza de Equipos")
    st.write("Consulta el ranking de fuerza de ataque y defensa calculada por el modelo histórico.")

    if base_model and base_model.attack:
        att_df = pd.DataFrame(list(base_model.attack.items()), columns=['Equipo', 'Rating Ataque']).sort_values('Rating Ataque', ascending=False)
        def_df = pd.DataFrame(list(base_model.defense.items()), columns=['Equipo', 'Rating Defensa']).sort_values('Rating Defensa', ascending=True)

        col_att, col_def = st.columns(2)
        with col_att:
            st.markdown("#### ⚽ Top 10 Ataque")
            st.dataframe(att_df.head(10), use_container_width=True, hide_index=True)
        with col_def:
            st.markdown("#### 🛡️ Top 10 Defensa (Menor = Mejor)")
            st.dataframe(def_df.head(10), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("⚽ Sistema de Apuestas Estadísticas Inteligente Pro | Betano Chile (betanosports.com)")
