import requests
import json
import re
import pandas as pd
from datetime import datetime, timezone, timedelta
import zoneinfo
from concurrent.futures import ThreadPoolExecutor, as_completed

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

COMPETITION_DIRECT_PATHS = {
    'INGLATERRA': '/api/sport/futbol/inglaterra/premier-league/1r/',
    'ALEMANIA': '/api/sport/futbol/alemania/bundesliga/216r/',
    'ITALIA': '/api/sport/futbol/italia/serie-a/1635r/',
    'FRANCIA': '/api/sport/futbol/francia/ligue-1/215r/',
    'ESPANA': '/api/sport/futbol/espana/laliga/10008r/',
    'BRASIL': '/api/sport/futbol/brasil/brasileirao-serie-a/10016r/',
    'CHILE': '/api/sport/futbol/chile/primera-division/10014r/',
    'ARGENTINA': '/api/sport/futbol/argentina/liga-profesional/10011r/',
    'CHAMPIONS': '/api/sport/futbol/internacional/uefa-champions-league/10005r/',
    'EUROPA_LEAGUE': '/api/sport/futbol/internacional/uefa-europa-league/10006r/',
    'LIBERTADORES': '/api/sport/futbol/sudamerica/copa-libertadores/10023r/',
    'SUDAMERICANA': '/api/sport/futbol/sudamerica/copa-sudamericana/10024r/',
    'SELECCIONES': '/api/sport/futbol/internacional/eliminatorias-conmebol/10050r/'
}

MIRROR_DOMAINS = [
    "https://www.betanosports.com",
    "https://www.betano.com",
    "https://br.betano.com"
]

class BetanoChileScraper:
    def __init__(self):
        self.base_url = "https://www.betanosports.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })

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

    def _safe_get(self, path):
        for domain in MIRROR_DOMAINS:
            url = f"{domain}{path}"
            try:
                res = self.session.get(url, timeout=4)
                if res.status_code == 200:
                    return res.json()
            except Exception:
                continue
        return None

    def fetch_top_events(self):
        data = self._safe_get("/api/home/top-events-v2/")
        if data:
            return data.get('data', {}).get('topEventsV2', {}).get('events', {})
        return {}

    def fetch_event_detail(self, event_url, event_id):
        clean_url = event_url.strip('/')
        data = self._safe_get(f"/api/{clean_url}/")
        if data:
            return data.get('data', {}).get('event', {})
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
                    s_name = str(s.get('name', '')).strip().upper()
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

        # Caso A: Partidos Populares del Día (Top Events en Paralelo Ultra Rápido)
        if comp_key == 'POPULARES':
            events = self.fetch_top_events()
            ev_list = [(ev_id, ev_info) for ev_id, ev_info in list(events.items())[:max_matches] if ev_info.get('url')]

            # Usar ThreadPoolExecutor para descargar en paralelo en 1 segundo
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_ev = {executor.submit(self.fetch_event_detail, ev_info['url'], ev_id): ev_id for ev_id, ev_info in ev_list}
                for future in as_completed(future_to_ev):
                    try:
                        detail = future.result()
                        parsed = self.parse_match_1x2(detail)
                        if parsed:
                            results.append(parsed)
                    except Exception:
                        pass

            if results:
                return pd.DataFrame(results)

        # Caso B: Liga / Campeonato Específico
        direct_path = COMPETITION_DIRECT_PATHS.get(comp_key)
        if direct_path:
            try:
                data = self._safe_get(direct_path)
                if data:
                    blocks = data.get('data', {}).get('blocks', [])
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

            ev_list = []
            for ev_id, ev_info in events.items():
                ev_str = f"{ev_info.get('url', '')} {ev_info.get('regionName', '')} {ev_info.get('leagueDescription', '')}".lower()
                if any(kw in ev_str for kw in target_kws) and ev_info.get('url'):
                    ev_list.append((ev_id, ev_info))

            if ev_list:
                with ThreadPoolExecutor(max_workers=8) as executor:
                    future_to_ev = {executor.submit(self.fetch_event_detail, ev_info['url'], ev_id): ev_id for ev_id, ev_info in ev_list[:max_matches]}
                    for future in as_completed(future_to_ev):
                        try:
                            detail = future.result()
                            parsed = self.parse_match_1x2(detail)
                            if parsed:
                                results.append(parsed)
                        except Exception:
                            pass

        if results:
            return pd.DataFrame(results)

        # Fallback de Respaldo: Leer live_betano_cache.json si el servidor de la nube (Streamlit Cloud) es bloqueado por Betano
        try:
            import os
            cache_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'live_betano_cache.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    matches = cache_data.get(comp_key, [])
                    if not matches and comp_key == 'POPULARES':
                        matches = []
                        for k, v in cache_data.items():
                            matches.extend(v[:4])
                    if matches:
                        return pd.DataFrame(matches[:max_matches])
        except Exception:
            pass

        return pd.DataFrame(results)

