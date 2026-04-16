from flask import Flask, render_template, request, redirect, session
from banco import conectar
import random, qrcode, os
app = Flask(__name__)
app.secret_key = "chave_secreta"


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        conexao = conectar()
        cursor = conexao.cursor()

        sql = "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"
        valores = (nome, email, senha)

        cursor.execute(sql, valores)
        conexao.commit()

        cursor.close()
        conexao.close()

        return redirect('/login')

    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE email=%s AND senha=%s",
            (email, senha)
        )

        user = cursor.fetchone()
        conexao.close()

        if user:
            return redirect('/produtos')
        else:
            return "Login inválido"

    return render_template('login.html')

@app.route('/produtos')
def produtos():
    conexao = conectar()
    cursor = conexao.cursor()

    categoria = request.args.get('categoria')

    if categoria:
        cursor.execute("SELECT * FROM produtos WHERE categoria = %s", (categoria,))
    else:
        cursor.execute("SELECT * FROM produtos")

    produtos = cursor.fetchall()
    conexao.close()

    return render_template('produtos.html', produtos=produtos, categoria=categoria)

@app.route('/add_carrinho/<int:id>')
def add_carrinho(id):
    if 'carrinho' not in session:
        session['carrinho'] = []

    session['carrinho'].append(id)
    session.modified = True

    return redirect('/produtos')

@app.route('/carrinho')
def carrinho():
    conexao = conectar()
    cursor = conexao.cursor()

    produtos_carrinho = []
    total = 0 
    
    if 'carrinho' in session:
        for id in session['carrinho']:
            cursor.execute("SELECT * FROM produtos WHERE id = %s", (id,))
            produto = cursor.fetchone()
            
            if produto:
                produtos_carrinho.append(produto)
                total += float(produto[2]) 
    conexao.close()

    return render_template('carrinho.html', produtos=produtos_carrinho, total=total)

@app.route('/remover_carrinho/<int:id>')
def remover_carrinho(id):
    if 'carrinho' in session:
        if id in session['carrinho']:
            session['carrinho'].remove(id)
            session.modified = True

    return redirect('/carrinho')

@app.route('/pagamento', methods=['GET', 'POST'])
def pagamento():
    etapa = "escolher"
    forma = None
    codigo_pix = None
    qr_code_path = None

    if request.method == 'POST':
        etapa = request.form.get('etapa')
        forma = request.form.get('forma')

        if etapa == "forma":
            return render_template('pagamento.html', etapa="dados", forma=forma)

        if etapa == "finalizar":
            conexao = conectar()
            cursor = conexao.cursor()

            total = 0
            produtos = []

            if 'carrinho' in session:
                for id in session['carrinho']:
                    cursor.execute("SELECT * FROM produtos WHERE id=%s", (id,))
                    produto = cursor.fetchone()
                    if produto:
                        total += float(produto[2])
                        produtos.append(produto)

            cursor.execute(
                "INSERT INTO pedidos (total, forma_pagamento) VALUES (%s, %s)",
                (total, forma)
            )
            conexao.commit()

            pedido_id = cursor.lastrowid

            for p in produtos:
                cursor.execute(
                    "INSERT INTO itens_pedido (pedido_id, produto_id) VALUES (%s, %s)",
                    (pedido_id, p[0])
                )

            conexao.commit()

            if forma == "pix":
                codigo_pix = ''.join([str(random.randint(0, 9)) for _ in range(10)])

                img = qrcode.make(codigo_pix)

                os.makedirs("static/qrcodes", exist_ok=True)
                caminho = f"static/qrcodes/pix_{pedido_id}.png"
                img.save(caminho)

                qr_code_path = caminho

            session['carrinho'] = []
            session.modified = True

            conexao.close()

            return render_template(
                'sucesso.html',
                forma=forma,
                codigo_pix=codigo_pix,
                qr_code=qr_code_path
            )

    return render_template('pagamento.html', etapa=etapa, forma=forma)

app.run(debug=True)