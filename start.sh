<<<<<<< HEAD
#!/bin/bash

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar FastAPI
uvicorn main:app --host 0.0.0.0 --port $PORT
=======
#!/bin/bash

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar FastAPI
uvicorn main:app --host 0.0.0.0 --port $PORT
>>>>>>> 835ba31b483cfb9608de964e8d6a1d032d634d9a
