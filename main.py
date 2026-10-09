import sys
import pandas as pd
from src.data_loader import FootballDataLoader, LEAGUE_MAP
from src.poisson_model import DixonColesPoissonModel
from src.bankroll import BankrollManager
from src.value_finder import ValueBetFinder

def run_pipeline(league_code='SP1', start_years=[2023, 2024, 2025], min_ev=3.0, bankroll=1000.0):
    print("=" * 70)
    league_name = LEAGUE_MAP.get(league_code, league_code)
    print(f" ALGORITMO DE APUESTAS ESTADÍSTICAS - DIXON-COLES & POISSON")
    print(f" Liga: {league_name} ({league_code}) | Banca Inicial: ${bankroll}")
    print("=" * 70)

    # 1. Cargar Datos
    loader = FootballDataLoader()
    df = loader.load_combined_seasons(league_code, start_years=start_years)

    if df.empty:
        print(f"No se pudieron obtener datos para la liga {league_code}.")
        return

    print(f"\n[1] Datos cargados con éxito: {len(df)} partidos analizados.")
    print(f"    Rango de fechas: {df['Date'].min().strftime('%Y-%m-%d')} a {df['Date'].max().strftime('%Y-%m-%d')}")

    # 2. Entrenar Modelo Dixon-Coles
    print("\n[2] Entrenando modelo estadístico de Dixon-Coles (Poisson Bivariado)...")
    model = DixonColesPoissonModel(time_decay=0.001)
    model.fit(df)

    # Mostrar Top 5 Equipos con mejor ataque y mejor defensa
    att_sorted = sorted(model.attack.items(), key=lambda x: x[1], reverse=True)
    def_sorted = sorted(model.defense.items(), key=lambda x: x[1])  # menor defensa = menos goles recibidos

    print("\n--- RATINGS DEL MODELO ---")
    print(f"  Ventaja de Localía Factor: {model.home_adv:.2f}x")
    print(f"  Top 3 Ataque:  " + ", ".join([f"{k} ({v:.2f})" for k, v in att_sorted[:3]]))
    print(f"  Top 3 Defensa: " + ", ".join([f"{k} ({v:.2f})" for k, v in def_sorted[:3]]))

    # 3. Configurar Buscador de Valor y Gestión de Banca
    bm = BankrollManager(bankroll=bankroll, kelly_fraction=0.25, max_stake_pct=0.05)
    finder = ValueBetFinder(min_ev_pct=min_ev, bankroll_manager=bm)

    # 4. Probar el modelo sobre el último tramo de partidos (simulación / backtest rápido)
    print("\n[3] Escaneando partidos recientes/cuotas en busca de VALUE BETS (+EV)...")
    
    # Tomamos los últimos 30 partidos para evaluar cuotas del mercado
    recent_matches = df.tail(30).copy()
    all_value_bets = []

    for idx, match in recent_matches.iterrows():
        home = match['HomeTeam']
        away = match['AwayTeam']

        try:
            prediction = model.predict_match(home, away)
        except Exception as e:
            continue

        # Extraer cuotas disponibles en el dataset (Bet365 / Pinnacle / Avg Market)
        # Si no están presentes, usar columnas genéricas
        bookie_odds = {}
        
        # Intentar obtener cuotas de Pinnacle o Bet365 o Promedio
        odds_1 = match.get('PSH') or match.get('B365H') or match.get('AvgH')
        odds_X = match.get('PSD') or match.get('B365D') or match.get('AvgD')
        odds_2 = match.get('PSA') or match.get('B365A') or match.get('AvgA')
        odds_over25 = match.get('P>2.5') or match.get('B365>2.5') or match.get('Avg>2.5')
        odds_under25 = match.get('P<2.5') or match.get('B365<2.5') or match.get('Avg<2.5')

        if pd.notna(odds_1): bookie_odds['odds_1'] = float(odds_1)
        if pd.notna(odds_X): bookie_odds['odds_X'] = float(odds_X)
        if pd.notna(odds_2): bookie_odds['odds_2'] = float(odds_2)
        if pd.notna(odds_over25): bookie_odds['odds_over25'] = float(odds_over25)
        if pd.notna(odds_under25): bookie_odds['odds_under25'] = float(odds_under25)

        val_bets = finder.analyze_match_odds(prediction, bookie_odds)
        for vb in val_bets:
            vb['fecha'] = match['Date'].strftime('%Y-%m-%d') if pd.notna(match['Date']) else 'N/A'
            vb['resultado_real'] = f"{match['FTHG']}-{match['FTAG']} ({match.get('FTR', 'N/A')})"
            all_value_bets.append(vb)

    if all_value_bets:
        vb_df = pd.DataFrame(all_value_bets)
        print(f"\n Se encontraron {len(vb_df)} APUESTAS CON VALOR (+EV >= {min_ev}%):")
        cols_to_show = ['fecha', 'partido', 'mercado', 'cuota_casa', 'prob_modelo_%', 'prob_implícita_%', 'EV_%', 'stake_sugerido_$', 'resultado_real']
        print(vb_df[cols_to_show].to_string(index=False))
    else:
        print(f"\n No se encontraron apuestas con valor superior a +{min_ev}% EV en la muestra reciente.")

    print("\n" + "=" * 70)
    print(" Pipeline ejecutado con éxito.")
    print("=" * 70)

if __name__ == "__main__":
    league = sys.argv[1] if len(sys.argv) > 1 else 'SP1'
    run_pipeline(league_code=league)
