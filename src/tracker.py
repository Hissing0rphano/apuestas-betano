import os
import json
import pandas as pd
from datetime import datetime

DATA_FILE = os.path.join("data", "multiuser_bets.json")

class MultiUserBetTracker:
    def __init__(self, data_file=DATA_FILE):
        self.data_file = data_file
        os.makedirs("data", exist_ok=True)
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "users": ["Fernando"],
            "active_user": "Fernando",
            "bets": []
        }

    def _save_data(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_users(self):
        return self.data.get("users", ["Fernando"])

    def add_user(self, username):
        username = username.strip()
        if username and username not in self.data["users"]:
            self.data["users"].append(username)
            self._save_data()
            return True
        return False

    def remove_user(self, username):
        username = username.strip()
        if username in self.data["users"] and len(self.data["users"]) > 1:
            self.data["users"].remove(username)
            if self.data["active_user"] == username:
                self.data["active_user"] = self.data["users"][0]
            self._save_data()
            return True
        elif username in self.data["users"] and len(self.data["users"]) == 1:
            # Si solo queda 1 usuario, no lo elimina para mantener al menos 1
            return False
        return False

    def set_active_user(self, username):
        if username in self.data["users"]:
            self.data["active_user"] = username
            self._save_data()

    def get_active_user(self):
        return self.data.get("active_user", "Fernando")

    def register_bet(self, username, match_name, league, market, odds, stake, ev_pct):
        """Registra una nueva apuesta para un usuario específico."""
        new_bet = {
            "id": len(self.data["bets"]) + 1,
            "usuario": username,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "partido": match_name,
            "liga": league,
            "mercado": market,
            "cuota": float(odds),
            "stake": float(stake),
            "ev_pct": float(ev_pct),
            "estado": "Pendiente ⏳",  # 'Pendiente ⏳', 'Ganada ✅', 'Perdida ❌', 'Anulada ⚪'
            "ganancia_neta": 0.0
        }
        self.data["bets"].append(new_bet)
        self._save_data()
        return new_bet

    def update_bet_status(self, bet_id, status):
        for bet in self.data["bets"]:
            if bet["id"] == bet_id:
                bet["estado"] = status
                if status == "Ganada ✅":
                    bet["ganancia_neta"] = round(bet["stake"] * (bet["cuota"] - 1.0), 2)
                elif status == "Perdida ❌":
                    bet["ganancia_neta"] = -round(bet["stake"], 2)
                else:
                    bet["ganancia_neta"] = 0.0
                break
        self._save_data()

    def get_bets_df(self, username=None):
        bets = self.data.get("bets", [])
        if not bets:
            return pd.DataFrame()
        df = pd.DataFrame(bets)
        if username:
            df = df[df["usuario"] == username]
        return df

    def get_leaderboard(self):
        """Genera la Tabla de Posiciones / Ranking entre Amigos."""
        bets = self.data.get("bets", [])
        users = self.data.get("users", [])
        
        leaderboard = []
        for user in users:
            user_bets = [b for b in bets if b["usuario"] == user]
            total_bets = len(user_bets)
            settled_bets = [b for b in user_bets if b["estado"] in ["Ganada ✅", "Perdida ❌"]]
            won_bets = [b for b in user_bets if b["estado"] == "Ganada ✅"]
            
            total_staked = sum(b["stake"] for b in settled_bets)
            net_profit = sum(b["ganancia_neta"] for b in settled_bets)
            win_rate = round((len(won_bets) / len(settled_bets) * 100), 1) if settled_bets else 0.0
            roi = round((net_profit / total_staked * 100), 1) if total_staked > 0 else 0.0

            leaderboard.append({
                "Apostador 👤": user,
                "Apuestas Totales": total_bets,
                "Resueltas": len(settled_bets),
                "% Acierto": f"{win_rate}%",
                "Total Apostado ($)": f"${total_staked:.2f}",
                "Ganancia / Pérdida ($)": round(net_profit, 2),
                "Yield / ROI (%)": roi
            })

        df_lead = pd.DataFrame(leaderboard)
        if not df_lead.empty:
            df_lead = df_lead.sort_values(by="Ganancia / Pérdida ($)", ascending=False).reset_index(drop=True)
            # Agregar medallas
            medals = ["🥇 1º", "🥈 2º", "🥉 3º"] + [f"{i+4}º" for i in range(len(df_lead))]
            df_lead.insert(0, "Posición", medals[:len(df_lead)])
        return df_lead
