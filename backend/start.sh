#!/bin/bash

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar FastAPI
uvicorn main:app --host 0.0.0.0 --port $PORT
