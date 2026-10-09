class ValueBetFinder:
    def __init__(self, min_ev_pct=0.0):
        self.min_ev_pct = min_ev_pct

    def get_match_ai_prediction(self, match_prediction, bookie_odds):
        """
        Determina la mejor elección de apuesta de la IA para un partido (1, X o 2),
        calculando probabilidades reales, cuota justa y valor esperado.
        """
        home = match_prediction['home_team']
        away = match_prediction['away_team']
        p1 = match_prediction['prob_1']
        pX = match_prediction['prob_X']
        p2 = match_prediction['prob_2']

        o1 = bookie_odds.get('odds_1', 1.0)
        oX = bookie_odds.get('odds_X', 1.0)
        o2 = bookie_odds.get('odds_2', 1.0)

        # Calcular EV para cada opción
        ev1 = round(((p1 * o1) - 1.0) * 100, 1) if o1 > 1.0 else 0.0
        evX = round(((pX * oX) - 1.0) * 100, 1) if oX > 1.0 else 0.0
        ev2 = round(((p2 * o2) - 1.0) * 100, 1) if o2 > 1.0 else 0.0

        # Determinar la mejor elección (Por mayor probabilidad de éxito o mayor EV)
        if p1 >= p2 and p1 >= pX:
            best_pick = '1'
            pick_label = f"Gana {home} (1)"
            pick_odds = o1
            pick_prob = round(p1 * 100, 1)
            pick_ev = ev1
            fair_odd = round(1.0 / p1, 2)
        elif p2 >= p1 and p2 >= pX:
            best_pick = '2'
            pick_label = f"Gana {away} (2)"
            pick_odds = o2
            pick_prob = round(p2 * 100, 1)
            pick_ev = ev2
            fair_odd = round(1.0 / p2, 2)
        else:
            best_pick = 'X'
            pick_label = "Empate (X)"
            pick_odds = oX
            pick_prob = round(pX * 100, 1)
            pick_ev = evX
            fair_odd = round(1.0 / pX, 2)

        # Nivel de confianza
        if pick_prob >= 65.0 or pick_ev >= 5.0:
            confianza = "🌟 Alta Confianza"
            badge_class = "value-card-gold"
        elif pick_prob >= 48.0 or pick_ev >= 2.0:
            confianza = "🟢 Recomendación Sólida"
            badge_class = "value-card-green"
        else:
            confianza = "🛡️ Oportunidad Moderada"
            badge_class = "value-card-green"

        justificacion = f"La IA estima un {pick_prob}% de probabilidad para {pick_label} (Cuota justa {fair_odd} vs {pick_odds} en Betano)."

        return {
            'best_pick': best_pick,
            'pick_label': pick_label,
            'pick_odds': pick_odds,
            'pick_prob_%': pick_prob,
            'pick_ev_%': pick_ev,
            'fair_odd': fair_odd,
            'confianza': confianza,
            'badge_class': badge_class,
            'justificacion': justificacion,
            'home_team': home,
            'away_team': away,
            'partido': f"{home} vs {away}"
        }
