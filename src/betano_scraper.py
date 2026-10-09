import requests
import json
import re
import pandas as pd
from datetime import datetime, timezone, timedelta
import zoneinfo

COMPETITIONS_MAP = {
    'POPULARES': '🔥 Todos los Partidos Populares del Día',
    'INGLATERRA': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League (Inglaterra)',
    'ALEMANIA': '🇩🇪 Bundesliga (Alemania)',
    'ITALIA': '🇮🇹 Serie A (Italia)',
    'FRANCIA': '🇫🇷 Ligue 1 (Francia)',
    'ESPANA': '🇪🇸 La Liga (España)',
    'BRASIL': '🇧🇷 Brasileirão (Brasil)',
    'CHILE': '🇨🇱 Primera División de Chile',
    'ARGENTINA': '🇦🇷 Liga Profesional de Argentina',
    'CHAMPIONS': '🏆 UEFA Champions League',
    'EUROPA_LEAGUE': '🥈 UEFA Europa League',
    'LIBERTADORES': '🌎 Copa Libertadores',
    'SUDAMERICANA': '🌎 Copa Sudamericana',
    'SELECCIONES': '🌍 Partidos de Selecciones (Internacionales)'
}

COMPETITION_DIRECT_URLS = {
    'INGLATERRA': 'https://www.betanosports.com/api/sport/futbol/inglaterra/premier-league/1r/',
    'ALEMANIA': 'https://www.betanosports.com/api/sport/futbol/alemania/bundesliga/216r/',
    'ITALIA': 'https://www.betanosports.com/api/sport/futbol/italia/serie-a/1635r/',
    'FRANCIA': 'https://www.betanosports.com/api/sport/futbol/francia/ligue-1/215r/',
    'ESPANA': 'https://www.betanosports.com/api/sport/futbol/espana/laliga/10008r/',
    'BRASIL': 'https://www.betanosports.com/api/sport/futbol/brasil/brasileirao-serie-a/10016r/',
    'CHILE': 'https://www.betanosports.com/api/sport/futbol/chile/primera-division/10014r/',
    'ARGENTINA': 'https://www.betanosports.com/api/sport/futbol/argentina/liga-profesional/10011r/',
    'CHAMPIONS': 'https://www.betanosports.com/api/sport/futbol/internacional/uefa-champions-league/10005r/',
    'EUROPA_LEAGUE': 'https://www.betanosports.com/api/sport/futbol/internacional/uefa-europa-league/10006r/',
    'LIBERTADORES': 'https://www.betanosports.com/api/sport/futbol/sudamerica/copa-libertadores/10023r/',
    'SUDAMERICANA': 'https://www.betanosports.com/api/sport/futbol/sudamerica/copa-sudamericana/10024r/',
    'SELECCIONES': 'https://www.betanosports.com/api/sport/futbol/internacional/eliminatorias-conmebol/10050r/'
}

class BetanoChileScraper:
    def __init__(self):
        self.base_url = "https://www.betanosports.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
            'Referer': 'https://www.betanosports.com/'
        }

    def _format_chile_time(self, start_time_ms):
        """Convierte timestamp de milisegundos a Fecha y Hora oficial de Chile."""
        if not start_time_ms:
            return "Pronto"
        try:
            dt_utc = datetime.fromtimestamp(start_time_ms / 1000, tz=timezone.utc)
            try:
                chile_tz = zoneinfo.ZoneInfo('America/Santiago')
                dt_chile = dt_utc.astimezone(chile_tz)
            except Exception:
                dt_chile = dt_utc - timedelta(hours=3)
            return dt_chile.strftime("%d/%m %H:%M hrs")
        except Exception:
            return "Pronto"

    def fetch_top_events(self):
        url = f"{self.base_url}/api/home/top-events-v2/"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return data.get('data', {}).get('topEventsV2', {}).get('events', {})
            return {}
        except Exception:
            return {}

    def fetch_event_detail(self, event_url, event_id):
        clean_url = event_url.strip('/')
        api_url = f"{self.base_url}/api/{clean_url}/"
        try:
            res = requests.get(api_url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                return res.json().get('data', {}).get('event', {})
            return {}
        except Exception:
            return {}

    def parse_match_1x2(self, event_data):
        if not event_data:
            return None

        participants = event_data.get('participants', [])
        if len(participants) < 2:
            name = event_data.get('name', '')
            if '-' in name:
                parts = name.split('-')
                home_name = parts[0].strip()
                away_name = parts[1].strip()
            else:
                return None
        else:
            home_name = participants[0].get('name') or participants[0].get('shortName')
            away_name = participants[1].get('name') or participants[1].get('shortName')

        league_name = event_data.get('leagueName') or event_data.get('leagueDescription', 'Fútbol')
        region_name = event_data.get('regionName', '')
        start_time_ms = event_data.get('startTime')
        horario_chile = self._format_chile_time(start_time_ms)

        markets = event_data.get('markets', [])
        odds_1, odds_X, odds_2 = None, None, None

        for m in markets:
            m_name = m.get('name', '').lower()
            selections = m.get('selections', [])

            if 'resultado del partido' in m_name or m_name == 'resultado final' or m_name == '1x2' or m_name == 'resultado':
                for s in selections:
                    s_name = s.get('name', '').upper()
                    price = s.get('price')
                    if price:
                        if s_name == '1' and not odds_1: odds_1 = float(price)
                        elif s_name == 'X' and not odds_X: odds_X = float(price)
                        elif s_name == '2' and not odds_2: odds_2 = float(price)

        if odds_1 and odds_X and odds_2:
            return {
                'event_id': event_data.get('id'),
                'horario': horario_chile,
                'liga': league_name,
                'region': region_name,
                'home_team': home_name,
                'away_team': away_name,
                'odds_1': odds_1,
                'odds_X': odds_X,
                'odds_2': odds_2,
                'url': f"{self.base_url}{event_data.get('url', '')}"
            }
        return None

    def get_matches_by_competition(self, comp_key='POPULARES', max_matches=25):
        results = []

        # Caso A: Partidos Populares del Día (Top Events)
        if comp_key == 'POPULARES':
            events = self.fetch_top_events()
            for ev_id, ev_info in list(events.items())[:max_matches]:
                url = ev_info.get('url')
                if url:
                    detail = self.fetch_event_detail(url, ev_id)
                    parsed = self.parse_match_1x2(detail)
                    if parsed:
                        results.append(parsed)
            return pd.DataFrame(results)

        # Caso B: Liga / Campeonato Específico
        direct_url = COMPETITION_DIRECT_URLS.get(comp_key)
        if direct_url:
            try:
                res = requests.get(direct_url, headers=self.headers, timeout=8)
                if res.status_code == 200:
                    data = res.json().get('data', {})
                    blocks = data.get('blocks', [])
                    events = blocks[0].get('events', []) if blocks else []
                    league_title = COMPETITIONS_MAP.get(comp_key, 'Liga')

                    for ev in events[:max_matches]:
                        parsed = self.parse_match_1x2(ev)
                        if parsed:
                            parsed['liga'] = league_title
                            results.append(parsed)
            except Exception:
                pass

        if not results:
            keywords = {
                'CHILE': ['chile'],
                'INGLATERRA': ['premier league', 'inglaterra', 'championship'],
                'ESPANA': ['laliga', 'españa', 'la liga'],
                'ALEMANIA': ['bundesliga', 'alemania'],
                'ITALIA': ['serie a', 'italia'],
                'FRANCIA': ['ligue 1', 'francia'],
                'ARGENTINA': ['argentina', 'liga profesional', 'boca', 'river'],
                'BRASIL': ['brasil', 'brasileirao', 'brasileirão'],
                'CHAMPIONS': ['champions league', 'uefa champions'],
                'EUROPA_LEAGUE': ['europa league'],
                'LIBERTADORES': ['libertadores'],
                'SUDAMERICANA': ['sudamericana'],
                'SELECCIONES': ['internacional', 'eliminatorias', 'nations league']
            }
            target_kws = keywords.get(comp_key, [])
            events = self.fetch_top_events()

            for ev_id, ev_info in events.items():
                ev_str = f"{ev_info.get('url', '')} {ev_info.get('regionName', '')} {ev_info.get('leagueDescription', '')}".lower()
                if any(kw in ev_str for kw in target_kws):
                    url = ev_info.get('url')
                    if url:
                        detail = self.fetch_event_detail(url, ev_id)
                        parsed = self.parse_match_1x2(detail)
                        if parsed:
                            results.append(parsed)

        return pd.DataFrame(results)
