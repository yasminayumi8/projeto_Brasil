from datetime import datetime
from functools import wraps
from pickle import GET

from flask import Flask, request
# from flask_pydantic_spec import FlaskPydanticSpec
from flask_jwt_extended import get_jwt_identity, JWTManager, create_access_token, jwt_required

from models import SessionLocal, Usuario, Produto, Blog, Movimentacao, Pedido, Cartao, Envio

from sqlalchemy import func, join


app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "secret!"  # chave usada para assinar os tokens


# app.config["JWT_TOKEN_LOCATION"] = ["headers"]  # JWT só vai ser lido dos headers
# jwt = JWTManager(app)


# def admin_required(fn):
#
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         user_email = get_jwt_identity()
#         db = SessionLocal()
#         try:
#             user = db.execute(select(Usuario).where(Usuario.email == user_email)).scalar()
#             if user and user.papel != "adm":
#                 return jsonify({"msg": "Acesso negado"}), 403
#             return fn(*args, **kwargs)
#         finally:
#             db.close()
#     return wrapper


@app.route('/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()

        email = dados['email']
        password_hash = dados['password_hash']

        db = SessionLocal()

        sql = select(Usuario).where(Usuario.email == email)
        user = db.execute(sql).scalar()

        if user and user.check_password(password_hash):
            access_token = create_access_token(identity=str(user.email))
            return jsonify({
                "access_token": access_token,
                "papel": user.papel,
            }), 200
        return jsonify({"msg": "Credenciais inválidas"}), 401
    except Exception as e:
        print(e)
        return jsonify({"msg": str(e)}), 500
    finally:
        db.close()


@app.route('/cadastro/cartao', methods=['POST'])
def cadastro_cartao():
    dados = request.get_json()
    db = SessionLocal()
    try:
        if not all(
                [dados.get('usuario_id'),dados.get('nome_titular'), dados.get('numero_cartao'), dados.get('data_validade'), dados.get('CVV')]):
            return jsonify({'erro': 'Campos obrigatórios não podem ser vazios'}), 400

        novo_cartao = Cartao(
            usuario_id=dados['usuario_id'],
            nome_titular=dados['nome_titular'],
            numero_cartao=dados['numero_cartao'],   # ← CORRIGIDO
            data_validade=dados['data_validade'],
            CVV=dados['CVV'],
        )

        novo_cartao.save(db)
        cartao_response = novo_cartao.serialize_cartao()
        cartao_response['id_cartao'] = novo_cartao.id_cartao
        return jsonify(cartao_response), 201

    except Exception as e:
        return jsonify({"msg": str(e)}), 400
    finally:
        db.close()

@app.route('/cadastro/envio', methods=['POST'])
def cadastro_envio():
    db = SessionLocal()
    dados = request.get_json()

    try:
        if not all([dados.get('usuario_id'), dados.get('nome_destinatario'), dados.get('endereco'),
                    dados.get('cidade'), dados.get('estado'), dados.get('CEP'), dados.get('telefone'), dados.get('email')]):
            return jsonify({'erro': 'Campos obrigatórios não podem ser vazios'}), 400

        novo_envio = Envio(
            usuario_id=dados['usuario_id'],
            nome_destinatario=dados['nome_destinatario'],
            endereco=dados['endereco'],
            cidade=dados['cidade'],
            estado=dados['estado'],
            CEP=dados['CEP'],        # ✅ corrigido
            telefone=dados['telefone'],
            email=dados['email'],
        )

        novo_envio.save(db)
        envio_response = novo_envio.serialize_envio()
        envio_response['id_envio'] = novo_envio.id_envio
        return jsonify(envio_response), 201

    except Exception as e:
        return jsonify({"msg": str(e)}), 400
    finally:
        db.close()



@app.route('/cadastro/usuario', methods=['POST'])
def cadastrar_usuario():
    dados = request.get_json()
    db = SessionLocal()
    try:
        if not all([dados.get('nome'), dados.get('CPF'), dados.get('email'), dados.get('senha'), dados.get('papel')]):
            return jsonify({'erro': "Campos obrigatórios (nome, email) não podem ser vazios"}), 400

        novo_usuario = Usuario(
            nome=dados['nome'],
            CPF=dados['CPF'],
            email=dados['email'],
            papel=dados['papel'],
        )
        novo_usuario.set_password(dados['senha'])
        novo_usuario.save(db)
        usuario_response = novo_usuario.serialize_usuario()
        return jsonify(usuario_response), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()


@app.route('/cadastro/medicamento', methods=['POST'])
# @jwt_required()
def cadastro_medicamento():
    dados = request.get_json()
    db = SessionLocal()
    try:
        # Validação da Rota de MEDICAMENTO (exige campos de Produto + campos específicos)
        campos_obrigatorios_med = ['nome_produto', 'preco_produto', 'descricao_produto', 'fabricante',
                                   'categoria_produto', 'dimensao_produto', 'peso_produto', 'cor_produto', 'uso',
                                   'parte_utilizada',
                                   'forma_uso', 'imagem_url']

        if not all(dados.get(campo) for campo in campos_obrigatorios_med):
            return jsonify({
                "error": "Preencher todos os campos obrigatórios para Medicamento (incluindo uso, parte e forma)"}), 400

        novo_medicamento = Produto(
            # Campos de Produto (herdado)
            nome_produto=dados['nome_produto'],
            preco_produto=dados['preco_produto'],
            descricao_produto=dados['descricao_produto'],
            fabricante=dados['fabricante'],
            categoria_produto=dados['categoria_produto'],
            # Campos opcionais de Produto
            dimensao_produto=dados.get('dimensao_produto'),
            peso_produto=dados.get('peso_produto'),
            cor_produto=dados.get('cor_produto'),

            # Campos ESPECÍFICOS do Medicamento
            uso=dados['uso'],
            parte_utilizada=dados['parte_utilizada'],
            forma_uso=dados['forma_uso'],
            imagem_url=dados.get('imagem_url')
        )
        novo_medicamento.save(db)
        produto_response = novo_medicamento.serialize_produto()
        produto_response["id_produto"] = novo_medicamento.id_produto
        return jsonify(produto_response), 201
    except Exception as e:
        return jsonify({"error": f"Erro no cadastro do medicamento: {str(e)}"}), 400
    finally:
        db.close()


# ... (o resto da sua API continua inalterado) ...

@app.route('/cadastro/produto', methods=['POST'])
def cadastro_produto():
    dados = request.get_json()
    db = SessionLocal()
    try:
        if (not dados['nome_produto'] or not dados['dimensao_produto'] or not dados['preco_produto'] or not
            dados['peso_produto'] or not dados['cor_produto'] or not dados['descricao_produto'] or not dados['fabricante']
            or not dados['categoria_produto'] or not dados['uso'] or not dados['parte_utilizada']or not dados['imagem_url']):
            return jsonify({"error": "preencher todos os campos"}), 400

        novo_produto = Produto(
            nome_produto=dados['nome_produto'],
            dimensao_produto=dados['dimensao_produto'],
            preco_produto=dados['preco_produto'],
            peso_produto=dados['peso_produto'],
            cor_produto=dados['cor_produto'],
            descricao_produto=dados['descricao_produto'],
            fabricante=dados['fabricante'],
            categoria_produto=dados['categoria_produto'],
            uso=dados['uso'],
            forma_uso=dados['forma_uso'],
            parte_utilizada=dados['parte_utilizada'],
            imagem_url=dados['imagem_url']
        )
        novo_produto.save(db)
        produto_response = novo_produto.serialize_produto()
        produto_response["id_produto"] = novo_produto.id_produto
        return jsonify(produto_response), 201
    except Exception as e:
        print(f"Erro no cadastro do produto: {e}")
        return jsonify({"error": f"{e}"}), 400
    finally:
        db.close()


@app.route('/cadastro/blog', methods=['POST'])
# @jwt_required()
def cadastro_blog():
    dados = request.get_json()
    db = SessionLocal()

    try:
        if not dados["usuario_id"] or not dados["comentario"] or not dados["titulo"] or not dados["data"] or not dados['link_video']:
            return jsonify({'mensagem': 'Erro de cadastro'}), 400

        # Garantir que usuario_id seja inteiro
        usuario_id = int(dados["usuario_id"])

        novo_blog = Blog(
            usuario_id=usuario_id,
            comentario=dados["comentario"],
            titulo=dados["titulo"],
            data=dados["data"],
            link_video=dados['link_video']
        )
        novo_blog.save(db)
        blog_response = novo_blog.serialize_blog()
        blog_response["id_blog"] = novo_blog.id_blog
        return jsonify(blog_response), 201
    except ValueError:
        return jsonify({'erro': 'usuario_id deve ser um número inteiro'}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()



@app.route('/cadastro/movimentacao', methods=['POST'])
# @jwt_required()
# @admin_required
def cadastro_movimentacao():
    dados = request.get_json()
    db = SessionLocal()

    try:
        if (not dados['quantidade'] or not dados['produto_id'] or not dados['data'] or not
            dados['status'] or not dados['usuario_id']):
            return jsonify({'mensagem': 'Todos os campos são obrigatórios'}), 400

        novo_movimentacao = Movimentacao(
            quantidade=int(dados["quantidade"]),
            produto_id=int(dados["produto_id"]),
            data=int(dados["produto_id"]),
            status=bool(dados["status"]),
            usuario_id=int(dados["usuario_id"]),
        )
        novo_movimentacao.save(db)

        resposta = novo_movimentacao.serialize_movimentacao()
        resposta["ID_movimentacao"] = novo_movimentacao.ID_movimentacao
        return jsonify(resposta), 201
    except Exception as e:
        print(f"Erro no cadastro da movimentacao: {e}")
        return jsonify({"error": f"{e}"}), 400
    finally:
        db.close()


@app.route('/cadastro/pedido', methods=['POST'])
# @jwt_required()
def cadastro_pedido():
    db = SessionLocal()
    try:
        dados = request.get_json()

        # Validação de campos obrigatórios
        campos_obrigatorios = ['produto_id', 'vendedor_id', 'quantidade', 'valor_total', 'endereco', 'usuario_id']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({'mensagem': 'Todos os campos são obrigatórios'}), 400

        # Criação do objeto Pedido
        pedido = Pedido(
            produto_id=dados["produto_id"],
            vendedor_id=dados["vendedor_id"],
            quantidade=dados["quantidade"],
            valor_total=dados["valor_total"],
            endereco=dados["endereco"],
            usuario_id=dados["usuario_id"]
        )

        # Salvando no banco
        pedido.save(db)

        # Retornando resposta com os dados do pedido criado
        return jsonify({
            'mensagem': 'Pedido cadastrado com sucesso',
            'pedido': pedido.serialize_pedido()
        }), 201


    except SQLAlchemyError as e:

        db.rollback()

        return jsonify({'erro': 'Erro no banco de dados', 'detalhes': str(e)}), 500

    except Exception as e:

        db.rollback()

        return jsonify({'erro': 'Erro inesperado', 'detalhes': str(e)}), 400

    finally:
        db.close()


@app.route('/consulta/envio/<int:id>', methods=['GET'])
# @jwt_required()
def consulta_envio(id):
    db = SessionLocal()
    try:
        var_envio = select(Envio).where(Envio.id_envio == id)
        var_envio = db.execute(var_envio).scalar()

        if not var_envio:
            return jsonify({'mensagem': 'Dados de envio não encontrado'}), 404

        envio_resultado = {
            "nome_destinatario": var_envio.nome_destinatario,
            "endereco": var_envio.endereco,
            "cidade": var_envio.cidade,
            "estado": var_envio.estado,
            "CEP": var_envio.CEP,
            "telefone": var_envio.telefone,
            "email": var_envio.email,
        }
        return jsonify({'envio': envio_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro de consulta: {str(e)}'}), 400
    finally:
        db.close()


@app.route('/consulta/usuario/<int:id>', methods=['GET'])
# @jwt_required()
def consulta_usuario(id):
    db = SessionLocal()
    try:
        var_usuario = select(Usuario).where(Usuario.id == id)
        var_usuario = db.execute(var_usuario).scalar()

        if not var_usuario:
            return jsonify({'mensagem': 'Dados do usuario não encontrado'}), 404

        usuario_resultado = {
            "nome": var_usuario.nome,
            "CPF": var_usuario.CPF,
            "email": var_usuario.email,
            "papel": var_usuario.papel,
        }
        return jsonify({'usuario': usuario_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro de consulta: {str(e)}'}), 400
    finally:
        db.close()


@app.route('/consulta/produto/<int:id>', methods=['GET'])
# @jwt_required()
def consulta_produto(id):
    db = SessionLocal()
    try:
        # busca o produto pelo id_produto
        var_produto = db.execute(
            select(Produto).where(Produto.id_produto == id)
        ).scalars().first()

        # se não encontrar, retorna 404
        if not var_produto:
            return jsonify({'mensagem': 'Produto não encontrado'}), 404

        # monta o dicionário com os dados
        produto_resultado = {
            "id_produto": var_produto.id_produto,
            "nome_produto": var_produto.nome_produto,
            "dimensao_produto": var_produto.dimensao_produto,
            "preco_produto": var_produto.preco_produto,
            "peso_produto": var_produto.peso_produto,
            "cor_produto": var_produto.cor_produto,
            "descricao_produto": var_produto.descricao_produto,
        }

        return jsonify({'Produto': produto_resultado}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro de consulta: {str(e)}'}), 400

    finally:
        db.close()


@app.route('/consulta/blog/<int:id>', methods=['GET'])
# @jwt_required()
def consulta_blog_id(id):
    db = SessionLocal()
    try:
        var_blog = select(Blog).where(Blog.usuario_id == id)
        var_blog = db.execute(var_blog).scalar()

        if not var_blog:
            return jsonify({'mensagem': 'Blog não encontrado'}), 404

        blog_resultado = {
            "usuario_id": var_blog.usuario_id,
            "comentario": var_blog.comentario,
            "titulo": var_blog.titulo,
            "data": var_blog.data,
        }
        return jsonify({'blog': blog_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro de consulta: {str(e)}'}), 400
    finally:
        db.close()


@app.route('/consulta/pedido/<int:id>', methods=['GET'])
# @jwt_required()
# @admin_required
def consulta_pedido_id(id):
    db = SessionLocal()
    try:
        var_pedido = select(Pedido).where(Pedido.ID_pedido == id)
        var_pedido = db.execute(var_pedido).scalars().first()

        if not var_pedido:
            return jsonify({'mensagem': 'Pedido não encontrado'}), 404

        pedido_resultado = var_pedido.serialize_pedido()

        return jsonify({'pedido': pedido_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro interno: {str(e)}'}), 500
    finally:
        db.close()


@app.route('/consulta/movimentacao/<int:id>', methods=['GET'])
# @jwt_required()
# @admin_required
def consulta_movimentacao_id(id):
    db = SessionLocal()
    try:
        var_movimentacao = select(Movimentacao).where(Movimentacao.ID_movimentacao == id)
        var_movimentacao = db.execute(var_movimentacao).scalars().first()

        if not var_movimentacao:
            return jsonify({'mensagem': 'Movimentação não encontrada'}), 404

        movimentacao_resultado = var_movimentacao.serialize_movimentacao()

        return jsonify({'movimentacao': movimentacao_resultado}), 200
    except Exception as e:
        return jsonify({'mensagem': f'Erro interno: {str(e)}'}), 500
    finally:
        db.close()


@app.route('/lista/usuario', methods=['GET'])
# @jwt_required()
def lista_usuario():
    db = SessionLocal()
    try:
        resultado = db.execute(select(Usuario)).scalars()
        usuarios = [
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email
            }
            for u in resultado
        ]
        return jsonify({'usuarios': usuarios}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()


@app.route('/lista/produto', methods=['GET'])
# @jwt_required()
def lista_produto():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Produto)).scalars()  # Pega todos os produtos
        produtos = [
            {
                "id_produto": p.id_produto,
                "nome_produto": p.nome_produto,
                "dimensao_produto": p.dimensao_produto,
                "preco_produto": p.preco_produto,
                "peso_produto": p.peso_produto,
                "cor_produto": p.cor_produto,
                "descricao_produto": p.descricao_produto
            }
            for p in resultado
        ]
        return jsonify({'produtos': produtos}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


from flask import Flask, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


@app.route('/lista/blog/', methods=['GET'])
# @jwt_required()
def lista_blog():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Blog)).scalars()  # Pega todos os blogs
        blogs = [
            {
                "id_blog": b.id_blog,
                "usuario_id": b.usuario_id,
                "titulo": b.titulo,
                "data": b.data,
                "comentario": b.comentario
            }
            for b in resultado
        ]
        return jsonify({'blogs': blogs}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/lista/pedido/', methods=['GET'])
# @jwt_required()
# @admin_required
def lista_pedido():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Pedido)).scalars()  # Pega todos os pedidos
        pedidos = [
            {
                "ID_pedido": p.ID_pedido,
                "produto_id": p.produto_id,
                "usuario_id": p.usuario_id,
                "vendedor_id": p.vendedor_id,
                "quantidade": p.quantidade,
                "valor_total": p.valor_total,
                "endereco": p.endereco
            }
            for p in resultado
        ]
        return jsonify({'pedidos': pedidos}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/lista/movimentacao/', methods=['GET'])
# @jwt_required()
# @admin_required
def lista_movimentacao():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Movimentacao)).scalars()  # Pega todas as movimentações
        movimentacoes = [
            {
                "ID_movimentacao": m.ID_movimentacao,
                "quantidade": m.quantidade,
                "produto_id": m.produto_id,
                "data": m.data,
                "status": m.status,
                "usuario_id": m.usuario_id
            }
            for m in resultado
        ]
        return jsonify({'movimentacoes': movimentacoes}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/lista/produto/', methods=['GET'])
# @jwt_required()
# @admin_required
def lista_envio():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Envio)).scalars()
        envio = [
            {
                "id_envio": m.id_envio,
                "usuario_id": m.usuario_id,
                "nome_destinatario": m.nome_destinatario,
                "endereco": m.endereco,
                "cidade": m.cidade,
                "estado": m.estado,
                "CEP": m.CEP,
                "telefone": m.telefone,
                "email": m.email,
            }
            for m in resultado
        ]
        return jsonify({'envio': envio}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/lista/cartao/', methods=['GET'])
# @jwt_required()
# @admin_required
def lista_cartao():
    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Envio)).scalars()
        cartao = [
            {
                "id_cartao": m.id_cartao,
                "usuario_id": m.usuario_id,
                "nome_titular": m.nome_titular,
                "numero_cartao": m.numero_cartao,
                "data_validade": m.data_validade,
                "CVV": m.CVV
            }
            for m in resultado
        ]
        return jsonify({'cartao': cartao}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão



@app.route('/atualizar/cartao/<int:id_cartao>', methods=['PUT'])
# @jwt_required()
def atualizar_cartao(id_cartao):
    db = SessionLocal()  # Cria a sessão
    try:
        cartao = db.execute(
            select(Cartao).where(Cartao.id == id_cartao)
        ).scalar()

        if not cartao:
            return jsonify({'erro': 'dados de cartao não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['nome_titular', 'numero_cartao', 'data_validade', 'CVV']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        cartao.nome_titular = dados['nome_titular']
        cartao.numero_cartao = dados['numero_cartao']
        cartao.data_validade = dados['data_validade']
        cartao.CVV = dados['CVV']

        db.commit()
        return jsonify({"mensagem": "Dados do cartao atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Garante que a sessão seja fechada


@app.route('/atualizar/envio/<int:id_envio>', methods=['PUT'])
# @jwt_required()
def atualizar_envio(id_envio):
    db = SessionLocal()  # Cria a sessão
    try:
        envio = db.execute(
            select(Envio).where(Envio.id == id_envio)
        ).scalar()

        if not envio:
            return jsonify({'erro': 'dados de envio não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['nome_destinatario', 'endereco', 'cidade', 'estado', 'CEP', 'telefone', 'email']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        envio.nome_destinatario = dados['nome_destinatario']
        envio.endereco = dados['endereco']
        envio.cidade = dados['cidade']
        envio.estado = dados['estado']
        envio.CEP = dados['telefone']
        envio.telefone = dados['telefone']
        envio.email = dados['email']

        db.commit()
        return jsonify({"mensagem": "Dados de envio atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Garante que a sessão seja fechada


@app.route('/atualizar/usuario/<int:id_usuario>', methods=['PUT'])
# @jwt_required()
def atualizar_usuario(id_usuario):
    db = SessionLocal()  # Cria a sessão
    try:
        usuario = db.execute(
            select(Usuario).where(Usuario.id == id_usuario)
        ).scalar()

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['nome', 'CPF', 'email', 'papel']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        usuario.nome = dados['nome']
        usuario.CPF = dados['CPF']
        usuario.email = dados['email']
        usuario.papel = dados['papel']

        # Atualiza a senha se fornecida
        if 'password' in dados and dados['password']:
            usuario.set_password(dados['password'])

        db.commit()
        return jsonify({"mensagem": "Usuário atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Garante que a sessão seja fechada


@app.route('/atualizar/produto/<int:id_produto>', methods=['PUT'])
# @jwt_required()
def atualizar_produto(id_produto):
    db = SessionLocal()  # Cria a sessão
    try:
        produto = db.execute(
            select(Produto).where(Produto.id_produto == id_produto)
        ).scalar()

        if not produto:
            return jsonify({'erro': 'Produto não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['nome_produto', 'dimensao_produto', 'preco_produto', 'peso_produto', 'descricao_produto']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        produto.nome_produto = dados['nome_produto']
        produto.dimensao_produto = dados['dimensao_produto']
        produto.preco_produto = dados['preco_produto']
        produto.peso_produto = dados['peso_produto']
        produto.cor_produto = dados.get('cor_produto')  # opcional
        produto.descricao_produto = dados['descricao_produto']

        db.commit()
        return jsonify({"mensagem": "Produto atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/atualizar/blog/<int:id_blog>', methods=['PUT'])
# @jwt_required()
def atualizar_blog(id_blog):
    db = SessionLocal()  # Cria a sessão
    try:
        blog = db.execute(
            select(Blog).where(Blog.id_blog == id_blog)
        ).scalar()

        if not blog:
            return jsonify({'erro': 'Blog não encontrado'}), 404

        dados = request.get_json()

        # Verifica se todos os campos obrigatórios estão presentes
        campos_obrigatorios = ['titulo', 'data', 'comentario']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        blog.titulo = dados['titulo']
        blog.data = dados['data']
        blog.comentario = dados['comentario']
        blog.usuario_id = dados.get('usuario_id', blog.usuario_id)  # mantém valor antigo se não fornecido

        db.commit()
        return jsonify({"mensagem": "Blog atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/atualizar/pedido/<int:id_pedido>', methods=['PUT'])
# @jwt_required()
def atualizar_pedido(id_pedido):
    db = SessionLocal()  # Cria a sessão
    try:
        pedido = db.execute(
            select(Pedido).where(Pedido.ID_pedido == id_pedido)
        ).scalar()

        if not pedido:
            return jsonify({'erro': 'Pedido não encontrado'}), 404

        dados = request.get_json()

        # Campos obrigatórios
        campos_obrigatorios = ['usuario_id', 'produto_id', 'quantidade', 'valor_total', 'endereco', 'vendedor_id']
        if not all(dados.get(campo) for campo in campos_obrigatorios):
            return jsonify({"erro": "Preencher todos os campos obrigatórios"}), 400

        # Atualiza os campos
        pedido.usuario_id = dados['usuario_id']
        pedido.produto_id = dados['produto_id']
        pedido.quantidade = dados['quantidade']
        pedido.valor_total = dados['valor_total']
        pedido.endereco = dados['endereco']
        pedido.vendedor_id = dados['vendedor_id']

        db.commit()
        return jsonify({"mensagem": "Pedido atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/atualizar/movimentacao/<int:id_movimentacao>', methods=['PUT'])
# @jwt_required()
# @admin_required  # se só admin pode atualizar movimentações
def atualizar_movimentacao(id_movimentacao):
    db = SessionLocal()
    try:
        movimentacao = db.execute(
            select(Movimentacao).where(Movimentacao.ID_movimentacao == id_movimentacao)
        ).scalar()

        if not movimentacao:
            return jsonify({'erro': 'Movimentação não encontrada'}), 404

        dados = request.get_json()
        campos_obrigatorios = ['quantidade', 'produto_id', 'data', 'status', 'usuario_id']
        if not all(dados.get(campo) is not None for campo in campos_obrigatorios):
            return jsonify({'erro': 'Preencher todos os campos obrigatórios'}), 400

        # Atualiza os campos
        movimentacao.quantidade = int(dados['quantidade'])
        movimentacao.produto_id = int(dados['produto_id'])

        # converte string para date
        try:
            movimentacao.data = datetime.strptime(dados['data'], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({'erro': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

        movimentacao.status = bool(dados['status'])
        movimentacao.usuario_id = int(dados['usuario_id'])

        db.commit()
        return jsonify({'mensagem': 'Movimentação atualizada com sucesso',
                        'movimentacao': movimentacao.serialize_movimentacao()}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()


@app.route('/atualizar/medicamento/<int:id_produto>', methods=['PUT'])
# @jwt_required()
# @admin_required  # se só admin pode atualizar movimentações
def atualizar_medicamento(id_produto):
    db = SessionLocal()
    try:
        produto = db.execute(
            select(Produto).where(Produto.ID_produto == id_produto)
        ).scalar()

        if not produto:
            return jsonify({'erro': 'medicamento não encontrada'}), 404

        dados = request.get_json()
        campos_obrigatorios = ['nome_produto', 'preco_produto', 'descricao_produto', 'fabricante', 'categoria_produto',
                               'dimensao_produto', 'peso_produto',
                               'cor_produto', 'uso', 'parte_utulizada', 'forma_uso', 'imagem_url']
        if not all(dados.get(campo) is not None for campo in campos_obrigatorios):
            return jsonify({'erro': 'Preencher todos os campos obrigatórios'}), 400

        # Atualiza os campos
        nome_produto = dados['nome_produto']
        preco_produto = dados['preco_produto']
        descricao_produto = dados['descricao_produto']
        fabricante = dados['fabricante']
        categoria_produto = dados['categoria_produto']
        dimensao_produto = dados['dimensao_produto']
        peso_produto = dados['peso_produto']
        cor_produto = dados['cor_produto']
        uso = dados['uso']
        parte_utulizado = dados['parte_utulizado']
        forma_uso = dados['forma_uso']
        imagem_url = dados['imagem_url']

        db.commit()
        return jsonify({"mensagem": "medicamento atualizado com sucesso"}), 200

    except SQLAlchemyError as e:
        db.rollback()
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/dashboard/produtos-mais-vendidos', methods=['GET'])
def produtos_mais_vendidos():
    db = SessionLocal()
    try:
        resultado = (
            db.query(
            Produto.nome_produto,
            func.sum(Pedido.quantidade).label("quantidade_total"),
            func.sum(Pedido.valor_total).label("valor_total")
        ) \
        .join(Produto, Produto.id_produto == Pedido.produto_id) \
        .group_by(Produto.nome_produto) \
        .order_by(func.sum(Pedido.quantidade).desc()) \
        .all())

        resposta = [
            {
                "nome_produto": r.nome_produto,
                "quantidade_total": int(r.quantidade_total),
                "valor_total": float(r.valor_total)
            }
            for r in resultado
        ]

        return jsonify({"ranking_produtos": resposta}), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        db.close()


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5003)
