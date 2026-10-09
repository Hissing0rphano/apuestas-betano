import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

class DixonColesPoissonModel:
    def __init__(self, time_decay=0.001):
        self.time_decay = time_decay
        self.teams = []
        self.team_indices = {}
        self.home_adv = 1.30
        self.rho = 0.001
        self.attack = {}
        self.defense = {}

    def fit(self, df):
        self.teams = sorted(list(set(df['HomeTeam']).union(set(df['AwayTeam']))))
        n_teams = len(self.teams)
        self.team_indices = {team: i for i, team in enumerate(self.teams)}

        if 'Date' in df.columns and not df['Date'].isna().all():
            max_date = df['Date'].max()
            days_diff = (max_date - df['Date']).dt.days.fillna(0).values
            weights = np.exp(-self.time_decay * days_diff)
        else:
            weights = np.ones(len(df))

        home_idx = df['HomeTeam'].map(self.team_indices).values
        away_idx = df['AwayTeam'].map(self.team_indices).values
        home_goals = df['FTHG'].values
        away_goals = df['FTAG'].values

        mask_00 = (home_goals == 0) & (away_goals == 0)
        mask_01 = (home_goals == 0) & (away_goals == 1)
        mask_10 = (home_goals == 1) & (away_goals == 0)
        mask_11 = (home_goals == 1) & (away_goals == 1)

        init_attack = np.zeros(n_teams)
        init_defense = np.zeros(n_teams)
        init_home_adv = 0.2
        init_rho = 0.0

        init_params = np.concatenate([init_attack, init_defense, [init_home_adv, init_rho]])

        def log_likelihood_vectorized(params):
            att = params[:n_teams]
            def_ = params[n_teams:2*n_teams]
            home_adv = params[2*n_teams]
            rho = params[2*n_teams + 1]

            att = att - np.mean(att)

            lambda_arr = np.exp(att[home_idx] + def_[away_idx] + home_adv)
            mu_arr = np.exp(att[away_idx] + def_[home_idx])

            tau_arr = np.ones(len(df))
            tau_arr[mask_00] = 1.0 - lambda_arr[mask_00] * mu_arr[mask_00] * rho
            tau_arr[mask_01] = 1.0 + lambda_arr[mask_01] * rho
            tau_arr[mask_10] = 1.0 + mu_arr[mask_10] * rho
            tau_arr[mask_11] = 1.0 - rho
            tau_arr = np.maximum(tau_arr, 1e-6)

            prob_hg = poisson.pmf(home_goals, lambda_arr)
            prob_ag = poisson.pmf(away_goals, mu_arr)

            match_probs = np.maximum(tau_arr * prob_hg * prob_ag, 1e-10)
            return -np.sum(weights * np.log(match_probs))

        res = minimize(log_likelihood_vectorized, init_params, method='L-BFGS-B')
        
        opt_params = res.x
        att = opt_params[:n_teams]
        att = att - np.mean(att)
        def_ = opt_params[n_teams:2*n_teams]

        self.attack = {team: float(np.exp(att[i])) for i, team in enumerate(self.teams)}
        self.defense = {team: float(np.exp(def_[i])) for i, team in enumerate(self.teams)}
        self.home_adv = float(np.exp(opt_params[2*n_teams]))
        self.rho = float(opt_params[2*n_teams + 1])

    def predict_match(self, home_team, away_team, odds_1=None, odds_X=None, odds_2=None):
        """
        Calcula probabilidades 1X2 usando Dixon-Coles si los equipos existen en el modelo,
        o mediante el modelo Bayesiano / Poisson Universal con cuotas de mercado limpias.
        """
        # Caso 1: Equipos encontrados directamente en la base histórica
        if home_team in self.attack and away_team in self.attack:
            lambda_ = self.attack[home_team] * self.defense[away_team] * self.home_adv
            mu = self.attack[away_team] * self.defense[home_team]

            grid = np.zeros((8, 8))
            for x in range(8):
                for y in range(8):
                    tau_val = 1.0
                    if x == 0 and y == 0: tau_val = 1.0 - (lambda_ * mu * self.rho)
                    elif x == 0 and y == 1: tau_val = 1.0 + (lambda_ * self.rho)
                    elif x == 1 and y == 0: tau_val = 1.0 + (mu * self.rho)
                    elif x == 1 and y == 1: tau_val = 1.0 - self.rho
                    grid[x, y] = max(tau_val, 1e-6) * poisson.pmf(x, lambda_) * poisson.pmf(y, mu)

            grid /= grid.sum()
            prob_home = float(np.tril(grid, -1).sum())
            prob_draw = float(np.diag(grid).sum())
            prob_away = float(np.triu(grid, 1).sum())

        # Caso 2: Equipo de otra liga / internacional (Modelo Universal Shin / Poisson Desmarcado)
        elif odds_1 and odds_X and odds_2:
            # Desmarcar cuotas de la casa de apuestas (quitar el margen del ~5% de Betano)
            inv_1 = 1.0 / odds_1
            inv_X = 1.0 / odds_X
            inv_2 = 1.0 / odds_2
            margin = inv_1 + inv_X + inv_2

            # Probabilidades desmarcadas / justas reales
            raw_p1 = inv_1 / margin
            raw_pX = inv_X / margin
            raw_p2 = inv_2 / margin

            # Ajuste de valor por ventaja de localía e ineficiencia de empate
            prob_home = float(min(max(raw_p1 * 1.025, 0.05), 0.90))
            prob_draw = float(min(max(raw_pX * 0.97, 0.05), 0.50))
            prob_away = float(1.0 - prob_home - prob_draw)
            if prob_away <= 0:
                prob_away = 0.05
                total = prob_home + prob_draw + prob_away
                prob_home /= total
                prob_draw /= total
                prob_away /= total

            lambda_ = round(prob_home * 2.2 + 0.5, 2)
            mu = round(prob_away * 1.8 + 0.4, 2)

        else:
            raise ValueError(f"No se pudieron estimar probabilidades para {home_team} vs {away_team}")

        return {
            'home_team': home_team,
            'away_team': away_team,
            'expected_home_goals': round(lambda_, 2),
            'expected_away_goals': round(mu, 2),
            'prob_1': round(prob_home, 4),
            'prob_X': round(prob_draw, 4),
            'prob_2': round(prob_away, 4),
            'fair_odds_1': round(1.0 / prob_home, 2) if prob_home > 0 else 999.0,
            'fair_odds_X': round(1.0 / prob_draw, 2) if prob_draw > 0 else 999.0,
            'fair_odds_2': round(1.0 / prob_away, 2) if prob_away > 0 else 999.0,
        }
