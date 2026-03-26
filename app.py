from flask import Flask, request, jsonify
import os, requests

from openai import OpenAI

app = Flask(__name__)

# ---------------- IA ----------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------- WHATSAPP ----------------
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "CHATCOURSE")


# ---------------- IA ----------------
def responder(texto):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "user", "content": texto}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Error IA:", e)
        return "Error en IA"


# ---------------- ENVIAR WHATSAPP ----------------
def enviar(numero, mensaje):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Faltan credenciales")
        return

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }

    requests.post(url, headers=headers, json=payload)


# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # Verificación Meta
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if token == VERIFY_TOKEN:
            return challenge
        return "Error", 403

    # Mensajes
    data = request.get_json()

    try:
        entry = data.get("entry", [])

        for e in entry:
            for change in e.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    numero = msg.get("from")

                    if msg.get("type") == "text":
                        texto = msg["text"]["body"]

                        respuesta = responder(texto)
                        enviar(numero, respuesta)

    except Exception as e:
        print("Error webhook:", e)

    return jsonify({"ok": True}), 200


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))