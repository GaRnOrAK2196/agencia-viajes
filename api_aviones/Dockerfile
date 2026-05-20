# 1. Usamos una imagen base oficial de Python (ligera)
FROM python:3.9-alpine

# 2. Creamos el directorio de trabajo
WORKDIR /usr/src/app

# 3. Copiamos el archivo de requerimientos
COPY requirements.txt ./

# 4. Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el resto del código (nuestro app.py)
COPY . .

# 6. Exponemos el puerto 3000
EXPOSE 3000

# 7. El comando para arrancar el servidor
CMD [ "python", "app.py" ]