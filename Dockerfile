FROM python:3.11-slim

WORKDIR /app

# Abhängigkeiten kopieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY streamlit_app.py .
COPY Übersicht.ipynb .

# Ports exposieren
EXPOSE 8501 8888

# Standard: Streamlit starten
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
