import os
import requests
import pyotp
import qrcode
import io
import base64
import jwt
import datetime
import secrets
from functools import wraps
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from repository import AgenciaRepository  # Importamos nuestro repositorio

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("JWT_SECRET", "llave_por_defecto_insegura")
CORS(app)
PORT = 3003

# Instanciamos el repositorio
repo = AgenciaRepository()

# Inicializamos BBDD al arrancar
# (Nota: Movemos la creación del admin aquí o la dejamos en repo,
# para mantenerlo simple lo haré aquí usando el repo)
try:
    repo.inicializar_tablas()
    # Verificar si existe admin, si no, crearlo
    if not repo.obtener_usuario_por_email("admin@demo.com"):
        print("Creando admin...")
        repo.crear_usuario(
            "admin@demo.com",
            generate_password_hash("admin123"),
            "admin",
            "Administración Central",
        )
except Exception as e:
    print(f"Error inicio: {e}")


@app.route("/")
def home():
    return "¡API Agencia Lista!"


@app.route("/api/agencia/csrf-token", methods=["GET"])
def obtener_csrf():
    # Generamos un token aleatorio seguro
    token = secrets.token_hex(32)
    return jsonify({"csrf_token": token}), 200


def token_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        # 1. Verificar JWT en la cabecera 'Authorization'
        token = None
        if "Authorization" in request.headers:
            # El formato suele ser: "Bearer eyJhbGci..."
            partes = request.headers["Authorization"].split()
            if len(partes) == 2:
                token = partes[1]

        if not token:
            return jsonify({"error": "Falta el token de autenticación (JWT)"}), 401

        try:
            # Decodificamos y validamos la firma del JWT
            datos_usuario = jwt.decode(
                token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "El token ha expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401

        # 2. Verificar Token CSRF (Solo para peticiones que modifican datos como POST, PUT, DELETE)
        if request.method in ["POST", "PUT", "DELETE"]:
            csrf_token = request.headers.get("X-CSRFToken")
            if not csrf_token:
                return (
                    jsonify(
                        {"error": "Ataque CSRF detectado: Falta token de seguridad"}
                    ),
                    403,
                )
            # En un entorno real, validaríamos que este token coincida con el de la sesión.
            # Para esta práctica, exigimos su presencia como medida de mitigación.

        # Pasamos los datos del usuario a la ruta protegida
        return f(datos_usuario, *args, **kwargs)

    return decorador


@app.route("/api/agencia/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    codigo_2fa = data.get("codigo_2fa")

    if not email or not password:
        return jsonify({"error": "Faltan datos"}), 400

    user = repo.obtener_usuario_por_email(email)

    if user and check_password_hash(user[2], password):
        user_id = user[0]
        secret_db = user[5]

        tiene_2fa = True if secret_db else False

        if secret_db:
            if not codigo_2fa:

                return jsonify({"mensaje": "2FA Requerido", "requiere_2fa": True}), 200

            totp = pyotp.TOTP(secret_db)
            if not totp.verify(codigo_2fa):
                return jsonify({"error": "Código 2FA incorrecto"}), 401

        # 1. Generamos el JWT
        token = jwt.encode(
            {
                "id": user[0],
                "email": user[1],
                "tipo": user[3],
                "exp": datetime.datetime.utcnow()
                + datetime.timedelta(hours=2),  # Expira en 2 horas
            },
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

        return (
            jsonify(
                {
                    "mensaje": "Login exitoso",
                    "token": token,  # <-- ¡AQUÍ ENVIAMOS EL JWT!
                    "id": user[0],
                    "email": user[1],
                    "tipo_usuario": user[3],
                    "nombre_agencia": user[4],
                    "tiene_2fa": tiene_2fa,
                }
            ),
            200,
        )

    return jsonify({"error": "Credenciales inválidas"}), 401


@app.route("/api/agencia/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if data is None:
        return (
            jsonify(
                {
                    "error": "Flask no detectó un JSON válido. Verifica la caché de tu navegador."
                }
            ),
            400,
        )

    email = data.get("email")
    password = data.get("password")
    es_agencia = data.get("es_agencia", False)
    nombre_agencia = data.get("nombre_agencia", None)

    if not email or not password:
        return jsonify({"error": "Faltan datos obligatorios (email o password)"}), 400

    if repo.obtener_usuario_por_email(email):
        return jsonify({"error": "El usuario ya existe"}), 409

    try:
        tipo = "agencia" if es_agencia else "cliente"
        if tipo == "agencia" and not nombre_agencia:
            return jsonify({"error": "Las agencias requieren un nombre comercial"}), 400

        repo.crear_usuario(
            email, generate_password_hash(password), tipo, nombre_agencia
        )
        return jsonify({"mensaje": "Usuario creado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- RUTA UNIFICADA Y PROTEGIDA ---
@app.route("/api/agencia/reservas", methods=["POST"])
@token_requerido
def crear_reserva(datos_usuario):  # El decorador nos pasa los datos del JWT
    data = request.get_json()

    # MAGIA DE SEGURIDAD: Usamos el email del Token, no el del Frontend
    email = datos_usuario["email"]

    tipo = data.get("tipo_servicio")
    id_ext = data.get("id_servicio")
    detalles = data.get("detalles")

    # Extraer el JWT del usuario del header Authorization para reenviarlo a los microservicios
    token_usuario = None
    if "Authorization" in request.headers:
        partes = request.headers["Authorization"].split()
        if len(partes) == 2:
            token_usuario = partes[1]

    # Lógica de Negocio: Llamar a la API externa
    urls = {
        "vuelo": f"http://api_aviones:3000/api/v1/vuelos/{id_ext}/reservar",
        "hotel": f"http://api_hoteles:3001/api/v1/hoteles/{id_ext}/reservar",
        "bus": f"http://api_buses:3002/api/v1/buses/{id_ext}/reservar",
    }

    try:
        url_destino = urls.get(tipo)
        if not url_destino:
            return jsonify({"error": "Tipo inválido"}), 400

        # Enviar el JWT del usuario en el header Authorization
        headers = {}
        if token_usuario:
            headers["Authorization"] = f"Bearer {token_usuario}"

        resp = requests.post(url_destino, headers=headers)
        if resp.status_code != 200:
            return jsonify({"error": "Sin stock"}), 409
        # Usar Repositorio para guardar
        user = repo.obtener_usuario_por_email(email)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        repo.crear_reserva(user[0], tipo, id_ext, detalles)

        return (
            jsonify(
                {
                    "mensaje": "Reserva guardada con seguridad",
                    "usuario_verificado": email,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agencia/mis-reservas", methods=["GET"])
@token_requerido
def mis_reservas(datos_usuario):
    # Extraemos el ID directamente del payload seguro y firmado del JWT
    usuario_id = datos_usuario.get("id")

    if not usuario_id:
        return jsonify({"error": "El token no contiene un ID de usuario válido"}), 400

    # Ejecutamos tu método del repositorio pasando el ID extraído
    reservas_raw = repo.obtener_reservas_usuario(usuario_id)

    # Como fetchall() devuelve una lista de tuplas, las mapeamos a un diccionario
    # según tu Query: id, tipo_servicio, detalles_reserva, fecha_reserva
    lista_reservas = []
    for fila in reservas_raw:
        lista_reservas.append(
            {
                "id": fila[0],
                "tipo_servicio": fila[1],
                "detalles": fila[
                    2
                ],  # Lo renombramos a 'detalles' para mantener compatibilidad con tu JS
                "fecha_reserva": str(fila[3]),
            }
        )

    return jsonify(lista_reservas), 200


# --- GENERAR QR PARA 2FA ---
@app.route("/api/agencia/2fa/setup", methods=["POST"])
def setup_2fa():
    data = request.get_json()
    email = data.get("email")

    # Generar un secreto aleatorio
    secret = pyotp.random_base32()

    # Crear la URI para Google Authenticator
    # Esto le dice a la app: "Cuenta: email, Emisor: Agencia KIS, Secreto: X"
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name="Agencia KIS"
    )

    # Generar imagen QR
    img = qrcode.make(totp_uri)
    buffered = io.BytesIO()
    img.save(buffered, "PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Devolvemos el secreto (temporal) y la imagen para mostrarla
    return jsonify({"secret": secret, "qr_image": f"data:image/png;base64,{img_str}"})


# --- ACTIVAR 2FA (Confirmar código) ---
@app.route("/api/agencia/2fa/enable", methods=["POST"])
def enable_2fa():
    data = request.get_json()
    user_id = data.get("user_id")
    secret = data.get("secret")
    code = data.get("code")

    totp = pyotp.TOTP(secret)
    if totp.verify(code):
        repo.activar_2fa(user_id, secret)
        return jsonify({"mensaje": "2FA Activado correctamente"}), 200

    return jsonify({"error": "Código incorrecto, intenta de nuevo"}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=PORT)
