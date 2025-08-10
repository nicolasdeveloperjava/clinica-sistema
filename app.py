from flask import Flask, request, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from datetime import datetime


app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinica.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

class Paciente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prontuario = db.Column(db.String, unique=True)
    nome = db.Column(db.String)
    data_inicio = db.Column(db.Date)
    data_anamnese = db.Column(db.Date)

class Terapia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo_terapia = db.Column(db.String(50), nullable=False)
    frequencia = db.Column(db.Integer, nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    sessoes = db.relationship('Sessao', backref='terapia', cascade="all, delete-orphan")

class Sessao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10), nullable=False)
    documento = db.Column(db.String(200))
    terapia_id = db.Column(db.Integer, db.ForeignKey('terapia.id'), nullable=False)

with app.app_context():
    db.create_all()
    print("Banco de dados e tabelas criados com sucesso!")

@app.route('/')
def index():
    return 'Backend da Clínica funcionando!'

@app.route('/pacientes', methods=['POST'])
def criar_paciente():
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Dados JSON obrigatórios'}), 400

    prontuario = data.get('prontuario')
    nome = data.get('nome')
    data_inicio = data.get('data_inicio', None)
    data_anamnese = data.get('data_anamnese', None)

    if not prontuario or not nome:
        return jsonify({'success': False, 'error': 'Prontuário e nome são obrigatórios'}), 400

    if Paciente.query.filter_by(prontuario=prontuario).first():
        return jsonify({'success': False, 'error': 'Prontuário já existe'}), 400

    data_inicio_obj = None
    data_anamnese_obj = None

    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato inválido para data_inicio'}), 400

    if data_anamnese:
        try:
            data_anamnese_obj = datetime.strptime(data_anamnese, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato inválido para data_anamnese'}), 400

    paciente = Paciente(
        prontuario=prontuario,
        nome=nome,
        data_inicio=data_inicio_obj,
        data_anamnese=data_anamnese_obj
    )
    db.session.add(paciente)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/terapias')
def listar_terapias():
    prontuario = request.args.get('prontuario')
    if not prontuario:
        return jsonify({'error': 'prontuario é obrigatório'}), 400
    paciente = Paciente.query.filter_by(prontuario=prontuario).first()
    if not paciente:
        return jsonify([])
    terapias = [{'id': t.id, 'tipo_terapia': t.tipo_terapia, 'frequencia': t.frequencia} for t in paciente.terapias]
    return jsonify(terapias)

@app.route('/terapias', methods=['POST'])
def criar_terapia():
    prontuario = request.form.get('prontuario')
    tipo_terapia = request.form.get('tipo_terapia')
    frequencia = request.form.get('frequencia')
    if not (prontuario and tipo_terapia and frequencia):
        return jsonify({'success': False, 'error': 'Campos obrigatórios faltando'}), 400
    paciente = Paciente.query.filter_by(prontuario=prontuario).first()
    if not paciente:
        return jsonify({'success': False, 'error': 'Paciente não encontrado'}), 404
    try:
        frequencia = int(frequencia)
    except:
        return jsonify({'success': False, 'error': 'Frequência inválida'}), 400
    terapia = Terapia(tipo_terapia=tipo_terapia, frequencia=frequencia, paciente_id=paciente.id)
    db.session.add(terapia)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/terapias/<int:id>', methods=['DELETE'])
def apagar_terapia(id):
    terapia = Terapia.query.get(id)
    if not terapia:
        return jsonify({'success': False, 'error': 'Terapia não encontrada'}), 404
    for sessao in terapia.sessoes:
        if sessao.documento:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], sessao.documento))
            except Exception:
                pass
    db.session.delete(terapia)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/sessoes')
def listar_sessoes():
    terapia_id = request.args.get('terapia_id')
    if not terapia_id:
        return jsonify({'error': 'terapia_id obrigatório'}), 400
    sessoes = Sessao.query.filter_by(terapia_id=terapia_id).order_by(Sessao.data).all()
    resultado = [{'id': s.id, 'data': s.data, 'documento': s.documento} for s in sessoes]
    return jsonify(resultado)

@app.route('/sessoes', methods=['POST'])
def criar_sessao():
    terapia_id = request.form.get('terapia_id')
    data = request.form.get('data')
    if not (terapia_id and data):
        return jsonify({'success': False, 'error': 'Campos obrigatórios faltando'}), 400
    terapia = Terapia.query.get(terapia_id)
    if not terapia:
        return jsonify({'success': False, 'error': 'Terapia não encontrada'}), 404
    arquivo = request.files.get('file')
    nome_arquivo_salvo = None
    if arquivo:
        nome_arquivo = secure_filename(arquivo.filename)
        nome_arquivo_salvo = f"{terapia_id}_{data}_{nome_arquivo}"
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo_salvo)
        arquivo.save(caminho)
    sessao = Sessao(data=data, documento=nome_arquivo_salvo, terapia_id=terapia.id)
    db.session.add(sessao)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/sessoes/<int:id>', methods=['DELETE'])
def apagar_sessao(id):
    sessao = Sessao.query.get(id)
    if not sessao:
        return jsonify({'success': False, 'error': 'Sessão não encontrada'}), 404
    if sessao.documento:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], sessao.documento))
        except Exception:
            pass
    db.session.delete(sessao)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/download/<filename>')
def download_arquivo(filename):
    caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.isfile(caminho):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
    return abort(404)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


