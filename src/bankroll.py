class BankrollManager:
    def __init__(self, bankroll=1000.0, kelly_fraction=0.25, max_stake_pct=0.05):
        """
        Gestor de Banca (Bankroll).
        :param bankroll: Saldo inicial disponible en la cuenta (ej. 1000 USD/CLP/EUR).
        :param kelly_fraction: Fracción de Kelly a aplicar (ej. 0.25 = Quarter Kelly para bajo riesgo).
        :param max_stake_pct: Porcentaje máximo de banca a arriesgar en una sola apuesta (ej. 0.05 = 5%).
        """
        self.bankroll = bankroll
        self.kelly_fraction = kelly_fraction
        self.max_stake_pct = max_stake_pct

    def calculate_kelly_stake(self, model_prob, decimal_odds):
        """
        Calcula el stake óptimo usando el Criterio de Kelly Fraccionado.
        """
        if decimal_odds <= 1.0 or model_prob <= 0:
            return 0.0, 0.0

        b = decimal_odds - 1.0
        p = model_prob
        q = 1.0 - p

        # Kelly puro (f*)
        f_star = (p * b - q) / b

        if f_star <= 0:
            return 0.0, 0.0  # No hay valor esperado positivo (EV <= 0)

        # Aplicar fracción de Kelly (Quarter Kelly)
        f_fractional = f_star * self.kelly_fraction

        # Limitar al stake máximo permitido por gestión de riesgo
        f_clamped = min(f_fractional, self.max_stake_pct)

        stake_amount = round(self.bankroll * f_clamped, 2)
        stake_pct = round(f_clamped * 100, 2)

        return stake_amount, stake_pct

    def calculate_ev(self, model_prob, decimal_odds):
        """
        Calcula el Valor Esperado (Expected Value - EV%) de una apuesta.
        EV = (Probabilidad_Modelo * Cuota) - 1
        """
        ev = (model_prob * decimal_odds) - 1.0
        return round(ev * 100, 2)
