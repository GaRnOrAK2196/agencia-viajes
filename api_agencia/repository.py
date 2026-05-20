#En este archivo se encuentran las sentencias SQL (INSERT, SELECT, UPDATE).
#la clase AgenciaRepository sera la encargada de ejecutar estas sentencias(Hablar con la BBD).

from sqlalchemy import text
from database import Database

class AgenciaRepository:
    def __init__(self):
        self.engine = Database.get_engine()

    def inicializar_tablas(self):
        try:
            with self.engine.connect() as conn:
                # Tabla Usuarios
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        password_hash VARCHAR(256) NOT NULL,
                        tipo ENUM('cliente', 'admin', 'agencia') NOT NULL DEFAULT 'cliente',
                        nombre_agencia VARCHAR(150),
                        totp_secret VARCHAR(32)
                    );
                """))
                # Tabla Reservas
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS reservas (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        usuario_id INT NOT NULL,
                        tipo_servicio VARCHAR(50) NOT NULL,
                        id_servicio_externo INT NOT NULL,
                        detalles_reserva TEXT,
                        fecha_reserva DATETIME,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                    );
                """))
                
                # Admin por defecto (Simplificado para el ejemplo)
                # Nota: La lógica de hash se mantiene en el controller o se pasa ya hasheada
                print("Tablas verificadas.")
        except Exception as e:
            print(f"Error inicializando tablas: {e}")

    def crear_usuario(self, email, pass_hash, tipo='cliente', nombre_agencia=None):
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO usuarios (email, password_hash, tipo, nombre_agencia)
                VALUES (:email, :pass_hash, :tipo, :nombre)
            """), {"email": email, "pass_hash": pass_hash, "tipo": tipo, "nombre": nombre_agencia})
            conn.commit()

    def obtener_usuario_por_email(self, email):
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, email, password_hash, tipo, nombre_agencia, totp_secret 
                FROM usuarios 
                WHERE email = :email
            """), {"email": email})
            return result.fetchone()

    def crear_reserva(self, usuario_id, tipo_servicio, id_servicio, detalles):
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO reservas (usuario_id, tipo_servicio, id_servicio_externo, detalles_reserva, fecha_reserva)
                VALUES (:uid, :tipo, :sid, :detalles, NOW())
            """), {"uid": usuario_id, "tipo": tipo_servicio, "sid": id_servicio, "detalles": detalles})
            conn.commit()

    def obtener_reservas_usuario(self, usuario_id):
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, tipo_servicio, detalles_reserva, fecha_reserva 
                FROM reservas WHERE usuario_id = :uid 
                ORDER BY fecha_reserva DESC
            """), {"uid": usuario_id})
            return result.fetchall()

    def activar_2fa(self, user_id, secret):
        with self.engine.connect() as conn:
            conn.execute(text("UPDATE usuarios SET totp_secret = :secret WHERE id = :id"),
                         {"secret": secret, "id": user_id})
            conn.commit()

    def obtener_secreto_2fa(self, user_id):
        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT totp_secret FROM usuarios WHERE id = :id"), {"id": user_id}).fetchone()
            return res[0] if res else None