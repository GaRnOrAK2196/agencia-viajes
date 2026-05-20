#Este archivo se encarga de crear el  motor de la conexion

import os
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

class Database:
    _engine = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            # Leer variables de entorno
            db_host = os.environ.get('DB_HOST')
            db_user = os.environ.get('DB_USER')
            db_password = os.environ.get('DB_PASSWORD')
            db_name = os.environ.get('DB_NAME')
            
            db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
            root_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/"

            # Lógica de reintentos (Wait for DB)
            print("Esperando a la base de datos...")
            engine_temp = create_engine(root_url)
            intentos = 0
            while intentos < 100:
                try:
                    engine_temp.connect()
                    print("¡Conexión exitosa!")
                    break
                except OperationalError:
                    time.sleep(1)
                    intentos += 1
            
            # Crear el engine definitivo
            cls._engine = create_engine(db_url)
        
        return cls._engine