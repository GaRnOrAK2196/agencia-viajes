import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import time

app = Flask(__name__)
CORS(app)
PORT = 3002  # <--- PUERTO 3002 PARA BUSES

db_host = os.environ.get('DB_HOST')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_name = os.environ.get('DB_NAME')
db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"

def esperar_por_bd():
    print("API Buses: Esperando...")
    engine_temp = create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}/")
    intentos = 0
    while intentos < 100:
        try:
            engine_temp.connect()
            print("API Buses: Lista!")
            return True
        except OperationalError:
            time.sleep(1)
            intentos += 1
    return False

if esperar_por_bd():
    engine = create_engine(db_url)
else:
    exit("Falló conexión db_buses")

def inicializar_bd():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS viajes_bus (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_agencia INT NOT NULL,
                    nombre_agencia VARCHAR(150),
                    compania VARCHAR(100) NOT NULL,
                    origen VARCHAR(100),
                    destino VARCHAR(100),
                    fecha_salida DATETIME,
                    precio DECIMAL(10, 2) NOT NULL,
                    asientos_disponibles INT DEFAULT 40,
                    imagen_url VARCHAR(512),
                    descripcion VARCHAR(255),
                    horario_texto VARCHAR(100)
                );
            """))
            if conn.execute(text("SELECT COUNT(*) FROM viajes_bus")).fetchone()[0] == 0:
                conn.execute(text("""
                    INSERT INTO viajes_bus (id_agencia, nombre_agencia, compania, origen, destino, fecha_salida, precio, asientos_disponibles, imagen_url, descripcion, horario_texto)
                    VALUES 
                    (1, 'Agencia Demo', 'BusConnect', 'Guadalajara', 'Vallarta', '2025-12-01 09:00:00', 750.00, 20, 'https://images.pexels.com/photos/5010996/pexels-photo-5010996.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'Ejecutivo', '09:00 AM');
                """))
                conn.commit()
    except Exception as e:
        print(f"Error init DB: {e}")

@app.route('/')
def home():
    return "¡API Buses Lista!"

# --- GET BUSES ---
@app.route('/api/v1/buses', methods=['GET'])
def get_buses():
    filtro_agencia = request.args.get('id_agencia')
    try:
        with engine.connect() as conn:
            if filtro_agencia:
                query = text("SELECT * FROM viajes_bus WHERE id_agencia = :aid ORDER BY id DESC")
                result = conn.execute(query, {"aid": filtro_agencia})
            else:
                query = text("SELECT * FROM viajes_bus WHERE asientos_disponibles > 0 ORDER BY id DESC")
                result = conn.execute(query)

            buses = []
            for row in result.fetchall():
                buses.append({
                    "id": row[0],
                    "id_agencia": row[1],
                    "nombre_agencia": row[2],
                    "tipo": "🚌 Autobús",
                    "servicio": row[3],
                    "origen": row[4],
                    "destino": row[5],
                    "fecha": str(row[6]),
                    "precio": float(row[7]),
                    "stock": row[8],
                    "imagen": row[9],
                    "descripcion": row[10],
                    "horario": row[11]
                })
            return jsonify(buses)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- POST BUSES ---
@app.route('/api/v1/buses', methods=['POST'])
def create_bus():
    data = request.get_json()
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO viajes_bus (id_agencia, nombre_agencia, compania, origen, destino, fecha_salida, precio, asientos_disponibles, imagen_url, descripcion, horario_texto)
                VALUES (:aid, :aname, :compania, :origen, :destino, :fecha, :precio, :stock, :imagen, :desc, :hora)
            """), {
                "aid": data.get('id_agencia'),
                "aname": data.get('nombre_agencia'),
                "compania": data.get('nombre'),
                "origen": data.get('origen'),
                "destino": data.get('destino'),
                "fecha": data.get('fecha'),
                "precio": data.get('precio'),
                "stock": data.get('stock'),
                "imagen": data.get('imagen'),
                "desc": data.get('descripcion'),
                "hora": data.get('horario')
            })
            conn.commit()
            return jsonify({"mensaje": "Bus creado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- RESERVAR BUS ---
@app.route('/api/v1/buses/<int:id>/reservar', methods=['POST'])
def reservar_stock(id):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("UPDATE viajes_bus SET asientos_disponibles = asientos_disponibles - 1 WHERE id = :id AND asientos_disponibles > 0"), {"id": id})
            conn.commit()
            if result.rowcount == 0:
                return jsonify({"error": "Sin stock"}), 409
            return jsonify({"mensaje": "Reservado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- BORRAR BUS ---
@app.route('/api/v1/buses/<int:id>', methods=['DELETE'])
def delete_bus(id):
    data = request.get_json()
    id_agencia_solicitante = data.get('id_agencia')
    es_admin = data.get('es_admin', False)

    try:
        with engine.connect() as conn:
            if es_admin:
                query = text("DELETE FROM viajes_bus WHERE id = :id")
                params = {"id": id}
            else:
                query = text("DELETE FROM viajes_bus WHERE id = :id AND id_agencia = :aid")
                params = {"id": id, "aid": id_agencia_solicitante}

            result = conn.execute(query, params)
            conn.commit()

            if result.rowcount == 0:
                return jsonify({"error": "No encontrado o no tienes permiso"}), 404
            
            return jsonify({"mensaje": "Bus eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    inicializar_bd()
    app.run(debug=True, host='0.0.0.0', port=PORT)