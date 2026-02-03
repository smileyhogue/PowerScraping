import requests
import logging
import json
import re
from bs4 import BeautifulSoup
from functools import lru_cache
from src.config import settings

logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        })

    def get_rate(self) -> float:
        try:
            logger.info(f"Fetching rates from {settings.HOLSTON_RATES_URL}")
            response = self.session.get(settings.HOLSTON_RATES_URL)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            targets = soup.find_all(string=re.compile("Energy Charge"))
            for target in targets:
                prices = []
                curr = target
                attempts = 0
                while len(prices) < 3 and attempts < 20:
                    curr = curr.find_next(string=True)
                    if not curr:
                        break
                    
                    text = curr.strip()
                    match = re.search(r'\$?\s*(0\.\d+)', text)
                    if match:
                        prices.append(float(match.group(1)))
                    attempts += 1
                
                if len(prices) >= 3:
                     rate = prices[2]
                     logger.info(f"Found rate: {rate} (Base: {prices[0]}, FCA: {prices[1]})")
                     return rate

            logger.warning("Precise 'Energy Charge' -> 3rd value logic failed. Trying broad search.")
            raise ValueError("Could not locate a valid rate using Energy Charge logic")

        except Exception as e:
            logger.error(f"Error scraping rate: {e}")
            raise

    def login(self):
        if settings.SMARTHUB_TOKEN:
            logger.info("Using configured SMARTHUB_TOKEN, skipping manual login.")
            token = settings.SMARTHUB_TOKEN
            if not token.lower().startswith("bearer"):
                token = f"Bearer {token}"
            self.session.headers.update({"Authorization": token})
            return

        try:
            logger.info("Attempting to login to SmartHub...")
            
            self.session.get(settings.SMARTHUB_LOGIN_URL)

            twofa_check_url = f"https://holston.smarthub.coop/services/two-factor?userId={settings.SMARTHUB_EMAIL}&isLogin=true"
            self.session.get(twofa_check_url)

            auth_url = "https://holston.smarthub.coop/services/oauth/auth/v2"
            auth_payload = {
                "userId": settings.SMARTHUB_EMAIL,
                "password": settings.SMARTHUB_PASSWORD
            }
            auth_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://holston.smarthub.coop",
                "Referer": "https://holston.smarthub.coop/ui/"
            }
            
            resp = self.session.post(auth_url, data=auth_payload, headers=auth_headers)
            
            if resp.status_code == 200:
                data = resp.json()
                logger.debug(f"Login response: {data}")
                status = data.get("status", "")
                
                if status == "SUCCESS":
                    token = (
                        data.get("authorizationToken") or
                        data.get("token") or 
                        data.get("access_token") or 
                        data.get("authorization") or
                        data.get("accessToken") or
                        data.get("jwt")
                    )
                    
                    if not token:
                        token = resp.headers.get("Authorization")
                    
                    if token:
                        logger.info("Login successful, token obtained from response.")
                        if not token.startswith("Bearer"):
                            token = f"Bearer {token}"
                        self.session.headers.update({
                            "Authorization": token,
                            "x-nisc-smarthub-username": settings.SMARTHUB_EMAIL
                        })
                        return
                    else:
                        logger.warning(f"Login SUCCESS but no token found. Response keys: {list(data.keys())}")
                        logger.warning(f"Full response: {data}")
                        self.session.headers.update({
                            "x-nisc-smarthub-username": settings.SMARTHUB_EMAIL
                        })
                        logger.info("Proceeding with cookie-based session (no Bearer token).")
                        return
                elif status == "FAILURE":
                    raise Exception(f"Login failed: Invalid credentials or account issue. Response: {data}")
                else:
                    logger.warning(f"Unexpected login status: {status}. Response: {data}")
            else:
                logger.warning(f"Login request failed with status {resp.status_code}. Response: {resp.text}")
            
            if "JSESSIONID" in self.session.cookies or any("session" in c.lower() for c in self.session.cookies.keys()):
                logger.info("Session cookie found, proceeding with cookie-based auth.")
                return

            raise Exception("Could not retrieve authentication token or session")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise

    def get_usage(self):
        try:
            logger.info("Polling for usage data...")
            
            import time
            now_ms = int(time.time() * 1000)
            thirty_days_ago_ms = now_ms - (30 * 24 * 60 * 60 * 1000)
            
            payload = {
                "timeFrame": "DAILY",
                "userId": settings.SMARTHUB_EMAIL,
                "screen": "USAGE_EXPLORER",
                "includeDemand": False,
                "serviceLocationNumber": settings.SMARTHUB_SERVICE_LOCATION,
                "accountNumber": settings.SMARTHUB_ACCOUNT_NUMBER,
                "industries": ["ELECTRIC"],
                "startDateTime": thirty_days_ago_ms,
                "endDateTime": now_ms
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*"
            }
            
            logger.debug(f"Poll payload: {payload}")
            
            max_retries = 10
            retry_delay = 5
            
            for attempt in range(max_retries):
                response = self.session.post(settings.SMARTHUB_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                status = data.get("status", "")
                
                if status == "PENDING":
                    logger.debug(f"Poll attempt {attempt + 1}/{max_retries}: PENDING, waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                elif status == "COMPLETE" or "data" in data:
                    logger.info(f"Poll complete after {attempt + 1} attempts")
                    break
                else:
                    logger.warning(f"Unexpected poll status: {status}")
                    break
            else:
                raise ValueError(f"Poll timed out after {max_retries} attempts")
            
            electric_data = data.get("data", {}).get("ELECTRIC", [])
            if not electric_data:
                logger.debug(f"Full response keys: {data.keys()}")
                raise ValueError("No ELECTRIC data found in response")
            
            meter_data = electric_data[0]
            logger.debug(f"Meter data keys: {meter_data.keys()}")
            
            def is_usage_series(lst):
                if not isinstance(lst, list) or not lst: return False
                first = lst[0]
                return isinstance(first, dict) and 'x' in first and 'y' in first
            
            def find_usage_series(obj, path=""):
                if isinstance(obj, list) and is_usage_series(obj):
                    logger.debug(f"Found usage series at path: {path} with {len(obj)} points")
                    return obj
                if isinstance(obj, dict):
                    for key, val in obj.items():
                        result = find_usage_series(val, f"{path}.{key}")
                        if result:
                            return result
                if isinstance(obj, list):
                    for i, item in enumerate(obj):
                        result = find_usage_series(item, f"{path}[{i}]")
                        if result:
                            return result
                return None
            
            usage_points = find_usage_series(meter_data)
                        
            if not usage_points:
                logger.warning(f"Could not find usage series. Available keys in meter_data: {list(meter_data.keys())[:20]}")
                raise ValueError("Could not find valid usage series in data")

            usage_points.sort(key=lambda p: p['x'])
            
            yesterday_point = usage_points[-1]
            timestamp = yesterday_point['x']
            usage = yesterday_point['y']
            
            logger.info(f"Retrieved usage from API: {usage} kWh at timestamp {timestamp}")
            return timestamp, usage

        except Exception as e:
            logger.error(f"Error getting usage: {e}")
            logger.debug(f"Response content: {response.text[:500]}..." if 'response' in locals() else "No response")
            raise
