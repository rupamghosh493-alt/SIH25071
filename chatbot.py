import os
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to your .env file."
    )

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-2.5-flash"


@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        message = data.get("message", "").strip()

        if not message:
            return jsonify({
                "reply": "Please enter a message."
            }), 400

        response = client.models.generate_content(
            model=MODEL,
            contents=message
        )

        return jsonify({
            "reply": response.text
        })

    except Exception as e:
        print("Gemini error:", e)

        return jsonify({
            "reply": "Sorry, I couldn't process your request right now."
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )