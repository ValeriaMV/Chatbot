from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import http.client
import json
import os

app = Flask(__name__)

# Configuración de la base de datos SQLITE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///metapython.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de la tabla log
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_y_hora = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    texto = db.Column(db.Text)

# Crear la tabla si no existe
with app.app_context():
    db.create_all()

# Ordenar registros por fecha
def ordenar_por_fecha_y_hora(registros):
    return sorted(registros, key=lambda x: x.fecha_y_hora, reverse=True)

@app.route('/')
def index():
    registros = Log.query.all()
    registros_ordenados = ordenar_por_fecha_y_hora(registros)
    return render_template('index.html', registros=registros_ordenados)

# Guardar log en DB
def agregar_mensajes_log(texto):
    try:
        nuevo = Log(texto=texto)
        db.session.add(nuevo)
        db.session.commit()
    except Exception as e:
        print("Error guardando log:", e)

# Token de verificación
TOKEN_ANDERCODE = os.getenv("VERIFY_TOKEN", "ANDERCODE")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return verificar_token(request)
    else:
        return recibir_mensajes()

def verificar_token(req):
    token = req.args.get('hub.verify_token')
    challenge = req.args.get('hub.challenge')

    if challenge and token == TOKEN_ANDERCODE:
        return challenge
    return jsonify({'error': 'Token inválido'}), 401

def recibir_mensajes():
    try:
        req = request.get_json()

        entry = req.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})
        mensajes = value.get('messages', [])

        if not mensajes:
            return jsonify({'message': 'EVENT_RECEIVED'})

        message = mensajes[0]

        # Guardar log
        agregar_mensajes_log(json.dumps(message))

        numero = message.get("from")
        texto = ""

        if message.get("type") == "interactive":
            interactive = message.get("interactive", {})
            tipo = interactive.get("type")

            if tipo == "button_reply":
                texto = interactive.get("button_reply", {}).get("id", "")
            elif tipo == "list_reply":
                texto = interactive.get("list_reply", {}).get("id", "")

        elif "text" in message:
            texto = message.get("text", {}).get("body", "")

        if texto and numero:
            enviar_mensajes_whatsapp(texto, numero)

        return jsonify({'message': 'EVENT_RECEIVED'})

    except Exception as e:
        agregar_mensajes_log(str(e))
        return jsonify({'error': str(e)}), 500

def enviar_mensajes_whatsapp(texto, number):
    texto = texto.lower()

    if "hola" in texto:
        body = "🚀 Hola, ¿Cómo estás? Bienvenido."

    elif "1" in texto:
        body = "Información del curso disponible."

    elif "6" in texto:
        body = "🤝 En breve me pondré en contacto contigo."

    elif "7" in texto:
        body = "📅 Horario: Lunes a Viernes, 9:00 am a 5:00 pm"

    else:
        body = (
            "📌 Menú:\n"
            "1️⃣ Curso\n"
            "2️⃣ Ubicación\n"
            "3️⃣ PDF\n"
            "4️⃣ Audio\n"
            "5️⃣ Video\n"
            "6️⃣ Asesor\n"
            "7️⃣ Horario\n"
            "0️⃣ Menú"
        )

    data = {
        "messaging_product": "whatsapp",
        "to": number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": body
        }
    }

    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("PHONE_NUMBER_ID")

    if not token or not phone_id:
        print("Faltan variables de entorno")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    connection = http.client.HTTPSConnection("graph.facebook.com")

    try:
        connection.request(
            "POST",
            f"/v18.0/{phone_id}/messages",
            json.dumps(data),
            headers
        )
        response = connection.getresponse()
        print(response.status, response.reason)

    except Exception as e:
        agregar_mensajes_log(str(e))

    finally:
        connection.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)