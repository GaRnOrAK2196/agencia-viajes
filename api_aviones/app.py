import os
import jwt
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import time

app = Flask(__name__)
CORS(app)
PORT = 3000  # <--- PUERTO 3000 PARA AVIONES

# Configuración de BD
db_host = os.environ.get("DB_HOST")
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_name = os.environ.get("DB_NAME")
db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"

app.config["SECRET_KEY"] = os.environ.get("JWT_SECRET", "llave_por_defecto_insegura")

def esperar_por_bd():
    print("API Aviones: Esperando a db_aviones...")
    engine_temp = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/")
    intentos = 0
    while intentos < 100:
        try:
            engine_temp.connect()
            print("API Aviones: ¡db_aviones lista!")
            return True
        except OperationalError:
            time.sleep(1)
            intentos += 1
    return False


if esperar_por_bd():
    engine = create_engine(db_url)
else:
    exit("Falló la conexión con db_aviones.")


def inicializar_bd():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vuelos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_agencia INT NOT NULL,
                    nombre_agencia VARCHAR(150),
                    aerolinea VARCHAR(100) NOT NULL,
                    origen VARCHAR(100),
                    destino VARCHAR(100),
                    fecha_salida DATETIME, 
                    precio DECIMAL(10, 2) NOT NULL,
                    asientos_disponibles INT DEFAULT 20,
                    imagen_url VARCHAR(512),
                    descripcion VARCHAR(255),
                    horario_texto VARCHAR(100)
                );
            """))
            # Insertar datos solo si está vacía
            row = conn.execute(text("SELECT COUNT(*) FROM vuelos")).fetchone()
            if row and row[0] == 0:
                conn.execute(text("""
                    INSERT INTO vuelos (id_agencia, nombre_agencia, aerolinea, origen, destino, fecha_salida, precio, asientos_disponibles, imagen_url, descripcion, horario_texto)
                    VALUES 
                    (1, 'Agencia Demo', 'AeroSimple', 'Guadalajara', 'Cancun', '2025-12-01 08:00:00', 2500.00, 50, 'https://images.pexels.com/photos/358319/pexels-photo-358319.jpeg', 'Vuelo directo', '08:00 AM');
                """))
                conn.commit()
    except Exception as e:
        print(f"Error init DB: {e}")


@app.route("/")
def home():
    return "¡API Aviones Lista!"


def token_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({"error": "Falta el token de autenticación (JWT)"}), 401
        try:
            datos_usuario = jwt.decode(
                token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
        except Exception as e:
            return jsonify({"error": "Token inválido o expirado"}), 401

        return f(datos_usuario, *args, **kwargs)

    return decorado

# --- GET: BUSCAR VUELOS ---
@app.route("/api/v1/vuelos", methods=["GET"])
@token_requerido
def get_vuelos(datos_usuario):
    filtro_agencia = request.args.get("id_agencia")
    try:
        with engine.connect() as conn:
            if filtro_agencia:
                query = text(
                    "SELECT * FROM vuelos WHERE id_agencia = :aid ORDER BY id DESC"
                )
                result = conn.execute(query, {"aid": filtro_agencia})
            else:
                query = text(
                    "SELECT * FROM vuelos WHERE asientos_disponibles > 0 ORDER BY id DESC"
                )
                result = conn.execute(query)

            vuelos = []
            for row in result.fetchall():
                vuelos.append(
                    {
                        "id": row[0],
                        "id_agencia": row[1],
                        "nombre_agencia": row[2],
                        "tipo": "✈️ Vuelo",
                        "servicio": row[3],
                        "origen": row[4],
                        "destino": row[5],
                        "fecha": str(row[6]),
                        "precio": float(row[7]),
                        "stock": row[8],
                        "imagen": row[9],
                        "descripcion": row[10],
                        "horario": row[11],
                    }
                )
            return jsonify(vuelos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- POST: CREAR VUELO ---
@app.route("/api/v1/vuelos", methods=["POST"])
@token_requerido
def create_vuelo(datos_usuario):
    data = request.get_json()
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                INSERT INTO vuelos (id_agencia, nombre_agencia, aerolinea, origen, destino, fecha_salida, precio, asientos_disponibles, imagen_url, descripcion, horario_texto)
                VALUES (:aid, :aname, :aerolinea, :origen, :destino, :fecha, :precio, :stock, :imagen, :desc, :hora)
            """),
                {
                    "aid": data.get("id_agencia"),
                    "aname": data.get("nombre_agencia"),
                    "aerolinea": data.get("nombre"),
                    "origen": data.get("origen"),
                    "destino": data.get("destino"),
                    "fecha": data.get("fecha"),
                    "precio": data.get("precio"),
                    "stock": data.get("stock"),
                    "imagen": data.get("imagen"),
                    "desc": data.get("descripcion"),
                    "hora": data.get("horario"),
                },
            )
            conn.commit()
            return jsonify({"mensaje": "Vuelo creado"}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Error al crear vuelo"}), 500


# --- POST: RESERVAR ---
@app.route("/api/v1/vuelos/<int:id>/reservar", methods=["POST"])
@token_requerido
def reservar_stock(datos_usuario, id):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "UPDATE vuelos SET asientos_disponibles = asientos_disponibles - 1 WHERE id = :id AND asientos_disponibles > 0"
                ),
                {"id": id},
            )
            conn.commit()
            if result.rowcount == 0:
                return jsonify({"error": "Sin stock"}), 409
            return jsonify({"mensaje": "Reservado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- BORRAR VUELO ---
@app.route("/api/v1/vuelos/<int:id>", methods=["DELETE"])
@token_requerido
def delete_vuelo(datos_usuario, id):
    # Recibimos el ID de la agencia para verificar que sea el dueño
    data = request.get_json()
    id_agencia_solicitante = data.get("id_agencia")
    es_admin = data.get("es_admin", False)

    try:
        with engine.connect() as conn:
            # Si es admin borra lo que sea, si es agencia solo lo suyo
            if es_admin:
                query = text("DELETE FROM vuelos WHERE id = :id")
                params = {"id": id}
            else:
                query = text("DELETE FROM vuelos WHERE id = :id AND id_agencia = :aid")
                params = {"id": id, "aid": id_agencia_solicitante}

            result = conn.execute(query, params)
            conn.commit()

            if result.rowcount == 0:
                return jsonify({"error": "No encontrado o no tienes permiso"}), 404

            return jsonify({"mensaje": "Vuelo eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    inicializar_bd()
    app.run(debug=True, host="0.0.0.0", port=PORT)
