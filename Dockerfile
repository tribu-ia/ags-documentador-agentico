# Usa una imagen base de Python
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos del proyecto
WORKDIR /app
ADD . /app

# Actualizar pip y setuptools
RUN pip install --upgrade pip setuptools wheel

# Instalar dependencias del proyecto
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -c /app/constraints.txt -e /app

# Exponer el puerto de la aplicación
EXPOSE 8000

# Comando para iniciar el servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8098"]