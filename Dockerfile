# Utiliser une image Python légère
FROM python:3.10-slim

# Éviter la mise en cache des logs
ENV PYTHONUNBUFFERED=1

# Répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires pour tls-client (si besoin)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Exposer le port par défaut de Railway
EXPOSE 5000

# Lancer l'application avec Gunicorn (plus stable que le serveur de dev Flask)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
