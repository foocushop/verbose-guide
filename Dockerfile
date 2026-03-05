# Utiliser Python 3.10 slim
FROM python:3.10-slim

# Configuration de l'environnement Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installation des certificats SSL pour curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway attribue dynamiquement un port via la variable d'environnement $PORT. 
# S'il n'y en a pas, on utilise 5000 par défaut.
ENV PORT=5000
EXPOSE $PORT

# RÈGLE D'OR : 1 seul worker, mais plusieurs threads. 
# Cela empêche "l'exit code 3" et permet de garder les scans en mémoire !
CMD sh -c "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 app:app"
