FROM python:3.10-slim

# Éviter la mise en cache des logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installation des certificats SSL pour curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie des fichiers
COPY . .

# Lancement avec Gunicorn (1 worker pour garder la mémoire, threads pour la performance)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 app:app
