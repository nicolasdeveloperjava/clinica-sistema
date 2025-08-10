from app import db, app

with app.app_context():
    db.create_all()
    print("Banco de dados e tabelas criados com sucesso!")
