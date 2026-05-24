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
PORT = 3001

db_host = os.environ.get('DB_HOST')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_name = os.environ.get('DB_NAME')
db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"

app.config["SECRET_KEY"] = os.environ.get("JWT_SECRET", "llave_por_defecto_insegura")

def token_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({"error": "Falta el token de autenticación (JWT)"}), 401
        try:
            datos = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except Exception as e:
            return jsonify({"error": "Token inválido o expirado"}), 401
        return f(datos, *args, **kwargs)

    return decorado

def esperar_por_bd():
    print("API Hoteles: Esperando...")
    engine_temp = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/")
    intentos = 0
    while intentos < 100:
        try:
            engine_temp.connect()
            return True
        except OperationalError:
            time.sleep(1)
            intentos += 1
    return False

if esperar_por_bd():
    engine = create_engine(db_url)
else:
    exit("Falló la conexión con db_hoteles.")

def inicializar_bd():
    try:
        with engine.connect() as conn:
            # CAMBIO: Agregamos 'max_personas'
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hoteles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_agencia INT NOT NULL,
                    nombre_agencia VARCHAR(150) NOT NULL,
                    nombre_hotel VARCHAR(100) NOT NULL,
                    ciudad VARCHAR(100),
                    descripcion_habitacion VARCHAR(255),
                    precio_noche DECIMAL(10, 2) NOT NULL,
                    habitaciones_disponibles INT DEFAULT 10,
                    max_personas INT DEFAULT 2, 
                    imagen_url VARCHAR(512),
                    horario_checkin VARCHAR(100)
                );
            """))

            row = conn.execute(text("SELECT COUNT(*) FROM hoteles")).fetchone()
            if row and row[0] == 0:
                print("API Hoteles: Insertando datos...")
                conn.execute(text("""
                    INSERT INTO hoteles (id_agencia,nombre_agencia,nombre_hotel, ciudad, descripcion_habitacion, precio_noche, habitaciones_disponibles, max_personas, imagen_url, horario_checkin)
                    VALUES 
                    (10,'PonsAgencia','Hotel KIS', 'Cancun', 'Habitación estándar, vista al mar', 1800.00, 5, 4,
                    'https://images.pexels.com/photos/271624/pexels-photo-271624.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 
                    'Check-in: 3:00 PM');
                """))
                conn.commit()
    except Exception as e:
        print(f"Error init DB: {e}")

@app.route('/')
def home():
    return "¡API Hoteles Lista!"

# --- GET: Obtener Hoteles ---
@app.route('/api/v1/hoteles', methods=['GET'])
@token_requerido
def get_hoteles(datos_usuario):
    filtro_agencia = request.args.get('id_agencia')
    
    try:
        with engine.connect() as conn:
            if filtro_agencia:
                query = text("SELECT * FROM hoteles WHERE id_agencia = :aid ORDER BY id DESC")
                result = conn.execute(query, {"aid": filtro_agencia})
            else:
                query = text("SELECT * FROM hoteles WHERE habitaciones_disponibles > 0 ORDER BY id DESC")
                result = conn.execute(query)
            hoteles = []
            for row in result.fetchall():
                hoteles.append({
                    "id": row[0],
                    "id_agencia": row[1],    
                    "nombre_agencia": row[2],
                    "tipo": "🏨 Hotel",
                    "servicio": row[3],
                    "ciudad": row[4],
                    "descripcion": row[5],
                    "precio": float(row[6]),
                    "stock": row[7],
                    "max_personas": row[8], 
                    "imagen": row[9],
                    "horario": row[10]
                })
            return jsonify(hoteles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST: Crear Hotel (Admin) ---
@app.route('/api/v1/hoteles', methods=['POST'])
@token_requerido
def create_hotel(datos_usuario):
    data = request.get_json()
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO hoteles (id_agencia,nombre_agencia,nombre_hotel, ciudad, descripcion_habitacion, precio_noche, habitaciones_disponibles, max_personas, imagen_url, horario_checkin)
                VALUES (:aid,:aname,:nombre, :ciudad, :desc, :precio, :stock, :max_p, :imagen, :checkin)
            """), {
                "aid": data.get('id_agencia'),
                "aname": data.get('nombre_agencia'),
                "nombre": data.get('nombre'),
                "ciudad": data.get('ciudad'),
                "desc": data.get('descripcion'),
                "precio": data.get('precio'),
                "stock": data.get('stock'),
                "max_p": data.get('max_personas'), # Recibimos este dato del form del admin
                "imagen": data.get('imagen'),
                "checkin": data.get('horario')
            })
            conn.commit()
            return jsonify({"mensaje": "Hotel creado exitosamente"}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Error al crear hotel"}), 500

# --- ENDPOINT: RESTAR STOCK HOTEL ---
@app.route('/api/v1/hoteles/<int:id>/reservar', methods=['POST'])
@token_requerido
def reservar_stock(datos_usuario, id):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE hoteles 
                SET habitaciones_disponibles = habitaciones_disponibles - 1 
                WHERE id = :id AND habitaciones_disponibles > 0
            """), {"id": id})
            conn.commit()

            if result.rowcount == 0:
                return jsonify({"error": "No hay habitaciones disponibles"}), 409
            
            return jsonify({"mensaje": "Stock reservado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- BORRAR HOTEL ---
@app.route('/api/v1/hoteles/<int:id>', methods=['DELETE'])
@token_requerido
def delete_hotel(datos_usuario, id):
    data = request.get_json()
    id_agencia_solicitante = data.get('id_agencia')
    es_admin = data.get('es_admin', False)

    try:
        with engine.connect() as conn:
            if es_admin:
                query = text("DELETE FROM hoteles WHERE id = :id")
                params = {"id": id}
            else:
                query = text("DELETE FROM hoteles WHERE id = :id AND id_agencia = :aid")
                params = {"id": id, "aid": id_agencia_solicitante}

            result = conn.execute(query, params)
            conn.commit()

            if result.rowcount == 0:
                return jsonify({"error": "No encontrado o no tienes permiso"}), 404
            
            return jsonify({"mensaje": "Hotel eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    inicializar_bd()
    app.run(debug=True, host='0.0.0.0', port=PORT)
