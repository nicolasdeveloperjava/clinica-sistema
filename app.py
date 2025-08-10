import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime, timedelta

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'png'}

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Usuário e senha únicos
USERNAME = "admin"
PASSWORD = "clinica123"

# Criar pasta de uploads
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Função para conectar no banco
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criar tabelas se não existirem
def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            prontuario TEXT PRIMARY KEY,
            nome TEXT,
            data_inicio TEXT,
            data_anamnese TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS terapias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prontuario TEXT,
            tipo_terapia TEXT,
            frequencia INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            terapia_id INTEGER,
            data TEXT,
            documento TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prontuario TEXT,
            tipo TEXT,
            data TEXT,
            arquivo TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Autenticação simples
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if data["username"] == USERNAME and data["password"] == PASSWORD:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

# Listar pacientes
@app.route("/pacientes", methods=["GET"])
def listar_pacientes():
    conn = get_db_connection()
    pacientes = conn.execute("SELECT * FROM pacientes").fetchall()
    conn.close()
    return jsonify([dict(p) for p in pacientes])

# Adicionar paciente
@app.route("/pacientes", methods=["POST"])
def adicionar_paciente():
    data = request.form
    prontuario = data["prontuario"]
    nome = data["nome"]
    data_inicio = data.get("data_inicio", "")
    data_anamnese = data.get("data_anamnese", "")

    conn = get_db_connection()
    conn.execute("INSERT INTO pacientes (prontuario, nome, data_inicio, data_anamnese) VALUES (?, ?, ?, ?)",
                 (prontuario, nome, data_inicio, data_anamnese))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# Upload de documento
@app.route("/upload", methods=["POST"])
def upload_file():
    prontuario = request.form["prontuario"]
    tipo = request.form["tipo"]  # evolução, pei, pti, anamnese
    file = request.files["file"]

    if file and file.filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS:
        filename = secure_filename(file.filename)
        pasta_paciente = os.path.join(app.config['UPLOAD_FOLDER'], prontuario)
        os.makedirs(pasta_paciente, exist_ok=True)
        caminho = os.path.join(pasta_paciente, filename)
        file.save(caminho)

        conn = get_db_connection()
        conn.execute("INSERT INTO documentos (prontuario, tipo, data, arquivo) VALUES (?, ?, ?, ?)",
                     (prontuario, tipo, datetime.today().strftime("%Y-%m-%d"), filename))
        conn.commit()
        conn.close()

        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Formato inválido"}), 400

# Baixar documento
@app.route("/download/<prontuario>/<filename>", methods=["GET"])
def download_file(prontuario, filename):
    pasta_paciente = os.path.join(app.config['UPLOAD_FOLDER'], prontuario)
    return send_from_directory(pasta_paciente, filename)

if __name__ == "__main__":
    app.run(debug=True)
