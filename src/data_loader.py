import os
import requests
import pandas as pd
from datetime import datetime

LEAGUE_MAP = {
    'SP1': 'La Liga (España)',
    'E0': 'Premier League (Inglaterra)',
    'I1': 'Serie A (Italia)',
    'D1': 'Bundesliga (Alemania)',
    'F1': 'Ligue 1 (Francia)',
    'SP2': 'La Liga 2 (España)',
    'E1': 'Championship (Inglaterra)'
}

BASE_URL = "https://www.football-data.co.uk/mmz4281"

class FootballDataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(os.path.join(self.data_dir, "historical"), exist_ok=True)

    def get_season_code(self, start_year):
        """Devuelve el código de temporada usado por football-data.co.uk (ej. 2024 -> '2425')"""
        y1 = str(start_year)[-2:]
        y2 = str(start_year + 1)[-2:]
        return f"{y1}{y2}"

    def download_league_season(self, league_code, start_year):
        """
        Descarga el CSV de una liga y temporada específica.
        Si ya existe localmente y es reciente, lo lee de caché.
        """
        season_code = self.get_season_code(start_year)
        file_name = f"{league_code}_{season_code}.csv"
        file_path = os.path.join(self.data_dir, "historical", file_name)

        # Si el archivo existe localmente, lo cargamos
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
                if not df.empty:
                    return df
            except Exception:
                pass

        # Si no existe o falló, lo descargamos
        url = f"{BASE_URL}/{season_code}/{league_code}.csv"
        print(f"[DataLoader] Descargando datos de {LEAGUE_MAP.get(league_code, league_code)} ({season_code})...")
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(res.content)
                df = pd.read_csv(file_path, encoding='latin1', on_bad_lines='skip')
                return df
            else:
                print(f"[DataLoader] Error HTTP {res.status_code} al descargar de {url}")
                return None
        except Exception as e:
            print(f"[DataLoader] Excepción al descargar datos: {e}")
            return None

    def load_combined_seasons(self, league_code, start_years=[2023, 2024, 2025]):
        """
        Carga y combina varias temporadas para una liga dada.
        Retorna un DataFrame limpio listo para modelar.
        """
        dfs = []
        for year in start_years:
            df = self.download_league_season(league_code, year)
            if df is not None and not df.empty:
                dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        full_df = pd.concat(dfs, ignore_index=True)
        return self._clean_data(full_df)

    def _clean_data(self, df):
        """Limpia y estandariza los datos de partidos."""
        required_cols = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
        for col in required_cols:
            if col not in df.columns:
                return pd.DataFrame()

        # Filtrar filas donde falten datos clave de goles
        df = df.dropna(subset=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']).copy()
        df['FTHG'] = df['FTHG'].astype(int)
        df['FTAG'] = df['FTAG'].astype(int)

        # Tratar fechas
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df = df.sort_values('Date').reset_index(drop=True)

        return df
