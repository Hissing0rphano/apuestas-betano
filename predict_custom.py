import sys
import pandas as pd
from src.data_loader import FootballDataLoader
from src.poisson_model import DixonColesPoissonModel
from src.bankroll import BankrollManager
from src.value_finder import ValueBetFinder

def predict_single_match(home_team, away_team, odds_dict, league_code='SP1', bankroll=1000.0):
    """
    Predice un partido personalizado introduciendo cuotas de Betano.
    :param home_team: Nombre del equipo local (ej: 'Real Madrid')
    :param away_team: Nombre del equipo visitante (ej: 'Barcelona')
    :param odds_dict: Diccionario con cuotas de Betano (ej: {'odds_1': 2.10, 'odds_X': 3.50, 'odds_2': 3.20, 'odds_over25': 1.80, 'odds_under25': 2.00})
    """
    print("=" * 70)
    print(f" PREDICCIÓN DE PARTIDO Y VALUE BETS (BETANO)")
    print(f" Partido: {home_team} vs {away_team}")
    print("=" * 70)

    # Cargar y entrenar modelo
    loader = FootballDataLoader()
    df = loader.load_combined_seasons(league_code)
    
    if df.empty:
        print("Error al cargar datos históricos.")
        return

    model = DixonColesPoissonModel()
    model.fit(df)

    try:
        pred = model.predict_match(home_team, away_team)
    except ValueError as e:
        print(f"\n[Error] {e}")
        print(f"Equipos disponibles en la liga ({league_code}): {', '.join(model.teams)}")
        return

    print("\n--- PREDICCIÓN DEL MODELO ---")
    print(f"  Goles Esperados Local ({home_team}):  {pred['expected_home_goals']}")
    print(f"  Goles Esperados Visitante ({away_team}): {pred['expected_away_goals']}")
    print("-" * 50)
    print(f"  Probabilidad 1 (Local):     {pred['prob_1']*100:.1f}%  | Cuota Justa Modelo: {pred['fair_odds_1']}")
    print(f"  Probabilidad X (Empate):    {pred['prob_X']*100:.1f}%  | Cuota Justa Modelo: {pred['fair_odds_X']}")
    print(f"  Probabilidad 2 (Visitante): {pred['prob_2']*100:.1f}%  | Cuota Justa Modelo: {pred['fair_odds_2']}")
    print(f"  Probabilidad Over 2.5:      {pred['prob_over25']*100:.1f}%  | Cuota Justa Modelo: {pred['fair_odds_over25']}")
    print(f"  Probabilidad Under 2.5:     {pred['prob_under25']*100:.1f}%  | Cuota Justa Modelo: {pred['fair_odds_under25']}")
    print(f"  Probabilidad BTTS (Ambos Anotan Sí): {pred['prob_btts_yes']*100:.1f}%")

    # Analizar Cuotas de Betano
    bm = BankrollManager(bankroll=bankroll, kelly_fraction=0.25, max_stake_pct=0.05)
    finder = ValueBetFinder(min_ev_pct=0.0, bankroll_manager=bm) # Mostrar todo EV

    opportunities = finder.analyze_match_odds(pred, odds_dict)

    print("\n--- ANÁLISIS DE VALOR EN BETANO ---")
    if opportunities:
        val_df = pd.DataFrame(opportunities)
        cols = ['mercado', 'cuota_casa', 'prob_modelo_%', 'prob_implícita_%', 'EV_%', 'stake_sugerido_$']
        print(val_df[cols].to_string(index=False))
    else:
        print("No se especificaron cuotas válidas para analizar.")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    # Ejemplo de prueba rápida: Real Madrid vs Barcelona con cuotas hipotéticas de Betano
    test_odds = {
        'odds_1': 2.15,
        'odds_X': 3.60,
        'odds_2': 3.10,
        'odds_over25': 1.65,
        'odds_under25': 2.25,
        'odds_btts_yes': 1.55,
        'odds_btts_no': 2.40
    }
    
    home = sys.argv[1] if len(sys.argv) > 1 else 'Real Madrid'
    away = sys.argv[2] if len(sys.argv) > 2 else 'Barcelona'
    league = sys.argv[3] if len(sys.argv) > 3 else 'SP1'
    
    predict_single_match(home, away, test_odds, league_code=league)
