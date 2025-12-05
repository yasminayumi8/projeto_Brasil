from datetime import datetime
from functools import wraps
from pickle import GET

from flask import Flask, request, jsonify
# from flask_pydantic_spec import FlaskPydanticSpec
from flask_jwt_extended import get_jwt_identity, JWTManager, create_access_token, jwt_required
from flask_pydantic_spec import FlaskPydanticSpec
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.functions import user

from models import SessionLocal, Usuario, Produto, Blog, Movimentacao, Pedido, Cartao, Envio

from sqlalchemy import func, join, select

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "secret!"  # chave usada para assinar os tokens
jwt = JWTManager(app)


def admin_required(fn):
    """
    Middleware para verificar se o usuário autenticado possui privilégios de administrador.

    ## Descrição:
    Este decorator protege rotas que exigem o papel de **administrador**.
    Ele verifica o usuário autenticado via JWT, consulta o banco de dados e valida o campo `papel`.

    ## Como funciona:
    - Obtém o usuário atual com `get_jwt_identity()`
    - Busca o usuário no banco pelo email
    - Verifica se `papel == "admin"`
    - Se for admin → permite o acesso
    - Caso contrário → retorna erro **403 - Acesso Negado**

    ## Requisitos:
    - O usuário precisa estar autenticado via JWT.
    - O token JWT deve conter o email do usuário como identidade.
    - A tabela `Usuario` deve possuir o atributo `papel`.

    ## Retorno (JSON em caso de erro):
    ```json
    {
        "msg": "Acesso negado: Requer privilégios de administrador"
    }
    ```

    ## Código de resposta:
    - **403** → quando o usuário não possui papel de administrador
    - O código original da função decorada é executado apenas se o usuário for admin.

    ## Erros possíveis:
    - Token JWT inválido ou ausente
    - Usuário não encontrado no banco
    - Usuário com papel diferente de "admin"

    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        print(f'c_user:{current_user}')
        db = SessionLocal()
        try:
            sql = select(Usuario)
            user = db.execute(sql).scalars()
            print(f'teste admin: {user and user.papel == "admin"} {user.papel}')
            if user and user.papel == "admin":
                return fn(*args, **kwargs)
            return jsonify(msg="Acesso negado: Requer privilégios de administrador"), 403
        except Exception as e:
            print(e)
        finally:
            db.close()
    return wrapper

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
    """
    API para autenticação de usuários.

    ## Endpoint:
    **POST** `/login`

    ## Descrição:
    Esta rota autentica um usuário a partir de um email e senha.
    Caso as credenciais estejam corretas, retorna um *JWT access token* e o papel do usuário.

    ## Parâmetros (JSON Body):
    ```json
    {
        "email": "usuario@exemplo.com",
        "password_hash": "senha123"
    }
    ```

    - `email` (str): **Obrigatório.** Email cadastrado no sistema.
    - `password_hash` (str): **Obrigatório.** Senha enviada pelo usuário para validação.

    ## Resposta (200 – Sucesso):
    ```json
    {
        "access_token": "jwt_token_aqui",
        "papel": "admin"
    }
    ```

    ## Resposta (401 – Credenciais inválidas):
    ```json
    {
        "msg": "Credenciais inválidas"
    }
    ```

    ## Resposta (500 – Erro interno):
    ```json
    {
        "msg": "Descrição do erro"
    }
    ```

    ## Erros possíveis:
    - Email não encontrado no banco.
    - Senha incorreta.
    - Campos ausentes no JSON.
    - Erros internos no servidor.
    """
    db = SessionLocal()
    try:
        dados = request.get_json()
        print('pug8', dados)
        email = dados['email']
        password_hash = dados['senha']

        sql = select(Usuario).where(Usuario.email == email)
        user= db.execute(sql).scalar_one_or_none()
        print('hh9s', user)

        if user and user.check_password(password_hash):
            access_token = create_access_token(identity=str(user.email))
            return jsonify({
                "access_token": access_token,
                "papel": user.papel,
            }), 200
        return jsonify({"msg": "Credenciais inválidas"}), 401
    except Exception as e:
        print(str(e))
        return jsonify({"msg": str(e)}), 500
    finally:
        db.close()


@app.route('/cadastro/cartao', methods=['POST'])
def cadastro_cartao():
    """
    API para cadastrar um novo cartão de crédito/débito.

    ## Endpoint:
    **POST** `/cadastro/cartao`

    ## Descrição:
    Esta rota permite registrar um cartão vinculado a um usuário.
    Todos os campos obrigatórios devem ser enviados no corpo da requisição.

    ## Parâmetros (JSON Body):
    ```json
    {
        "usuario_id": 1,
        "nome_titular": "João da Silva",
        "numero_cartao": "1234123412341234",
        "data_validade": "12/2028",
        "CVV": "123"
    }
    ```

    - `usuario_id` (int): **Obrigatório.** ID do usuário proprietário do cartão.
    - `nome_titular` (str): **Obrigatório.** Nome impresso no cartão.
    - `numero_cartao` (str): **Obrigatório.** Número completo do cartão.
    - `data_validade` (str): **Obrigatório.** Data de validade do cartão (ex: "12/2028").
    - `CVV` (str): **Obrigatório.** Código de segurança do cartão.

    ## Resposta (201 – Criado com sucesso):
    ```json
    {
        "id_cartao": 10,
        "usuario_id": 1,
        "nome_titular": "João da Silva",
        "numero_cartao": "1234123412341234",
        "data_validade": "12/2028",
        "CVV": "123"
    }
    ```

    ## Resposta (400 – Dados inválidos ou campos ausentes):
    ```json
    {
        "erro": "Campos obrigatórios não podem ser vazios"
    }
    ```

    ## Resposta (400 – Erro interno):
    ```json
    {
        "msg": "Descrição do erro"
    }
    ```

    ## Erros possíveis:
    - Ausência de campos obrigatórios no JSON.
    - Dados do cartão inválidos ou mal formatados.
    - Falha ao salvar no banco de dados.
    - Exceções internas inesperadas.
    """
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
    """
    API para cadastrar um endereço de envio.

    ## Endpoint:
    **POST** `/cadastro/envio`

    ## Descrição:
    Esta rota registra um endereço de entrega vinculado a um usuário.
    Todos os campos obrigatórios devem ser enviados no corpo da requisição.

    ## Parâmetros (JSON Body):
    ```json
    {
        "usuario_id": 1,
        "nome_destinatario": "Maria Oliveira",
        "endereco": "Rua das Flores, 123",
        "cidade": "São Paulo",
        "estado": "SP",
        "CEP": "01010000",
        "telefone": "11999999999",
        "email": "maria@gmail.com"
    }
    ```

    - `usuario_id` (int): **Obrigatório.** ID do usuário dono do endereço.
    - `nome_destinatario` (str): **Obrigatório.** Nome da pessoa que receberá o produto.
    - `endereco` (str): **Obrigatório.** Rua, número e complemento.
    - `cidade` (str): **Obrigatório.**
    - `estado` (str): **Obrigatório.**
    - `CEP` (str): **Obrigatório.** Código postal (somente números).
    - `telefone` (str): **Obrigatório.** Telefone de contato.
    - `email` (str): **Obrigatório.** Email de contato relacionado ao envio.

    ## Resposta (201 – Criado com sucesso):
    ```json
    {
        "id_envio": 5,
        "usuario_id": 1,
        "nome_destinatario": "Maria Oliveira",
        "endereco": "Rua das Flores, 123",
        "cidade": "São Paulo",
        "estado": "SP",
        "CEP": "01010000",
        "telefone": "11999999999",
        "email": "maria@gmail.com"
    }
    ```

    ## Resposta (400 – Campos ausentes):
    ```json
    {
        "erro": "Campos obrigatórios não podem ser vazios"
    }
    ```

    ## Resposta (400 – Erro interno):
    ```json
    {
        "msg": "Descrição do erro"
    }
    ```

    ## Erros possíveis:
    - Campos obrigatórios ausentes.
    - Formato inválido de CEP, telefone ou email.
    - Falha ao salvar no banco de dados.
    - Exceções internas inesperadas.
    """
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
    """
    API para cadastro de novos usuários.

    ## Endpoint:
    **POST** `/cadastro/usuario`

    ## Descrição:
    Esta rota registra um novo usuário no sistema, incluindo nome, CPF, email, senha e papel.
    Todos os campos obrigatórios devem ser enviados no corpo da requisição.

    ## Parâmetros (JSON Body):
    ```json
    {
        "nome": "João Silva",
        "CPF": "12345678900",
        "email": "joao@gmail.com",
        "senha": "senha123",
        "papel": "cliente"
    }
    ```

    - `nome` (str): **Obrigatório.** Nome completo do usuário.
    - `CPF` (str): **Obrigatório.** Documento CPF (somente números).
    - `email` (str): **Obrigatório.** Email válido do usuário.
    - `senha` (str): **Obrigatório.** Senha que será criptografada antes de salvar.
    - `papel` (str): **Obrigatório.** Define o tipo de usuário, como `"cliente"` ou `"admin"`.

    ## Resposta (201 – Criado com sucesso):
    ```json
    {
        "id_usuario": 15,
        "nome": "João Silva",
        "CPF": "12345678900",
        "email": "joao@gmail.com",
        "papel": "cliente"
    }
    ```

    ## Resposta (400 – Campos ausentes):
    ```json
    {
        "erro": "Campos obrigatórios (nome, email) não podem ser vazios"
    }
    ```

    ## Resposta (400 – Erro interno):
    ```json
    {
        "erro": "Descrição do erro"
    }
    ```

    ## Erros possíveis:
    - Campos obrigatórios ausentes.
    - Email já cadastrado no sistema.
    - CPF inválido ou duplicado.
    - Falha ao criptografar a senha.
    - Exceções internas ao salvar no banco de dados.
    """
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
    """
        API para cadastro de medicamentos.

        ## Endpoint:
        **POST** `/cadastro/medicamento`

        ## Descrição:
        Esta rota realiza o cadastro de um medicamento, utilizando os campos gerais de um Produto
        (como nome, preço, fabricante etc.) e campos específicos relacionados ao uso medicinal.
        Todos os campos obrigatórios devem ser enviados no corpo da requisição.

        ## Parâmetros (JSON Body):
        ```json
        {
            "nome_produto": "Chá de Camomila",
            "preco_produto": 19.90,
            "descricao_produto": "Produto natural para relaxamento",
            "fabricante": "FloraVida",
            "categoria_produto": "Medicamento Natural",
            "dimensao_produto": "10x5x5cm",
            "peso_produto": "100g",
            "cor_produto": "Amarelo",
            "uso": "Calmante",
            "parte_utilizada": "Flores",
            "forma_uso": "Infusão",
            "imagem_url": "https://exemplo.com/camomila.jpg"
        }
        ```

        ### Campos obrigatórios:
        - `nome_produto` (str)
        - `preco_produto` (float)
        - `descricao_produto` (str)
        - `fabricante` (str)
        - `categoria_produto` (str)
        - `dimensao_produto` (str)
        - `peso_produto` (str)
        - `cor_produto` (str)
        - `uso` (str) — finalidade medicinal
        - `parte_utilizada` (str) — parte da planta usada
        - `forma_uso` (str) — modo correto de consumo
        - `imagem_url` (str)

        ## Resposta (201 – Criado com sucesso):
        ```json
        {
            "id_produto": 32,
            "nome_produto": "Chá de Camomila",
            "preco_produto": 19.90,
            "descricao_produto": "Produto natural para relaxamento",
            "fabricante": "FloraVida",
            "categoria_produto": "Medicamento Natural",
            "dimensao_produto": "10x5x5cm",
            "peso_produto": "100g",
            "cor_produto": "Amarelo",
            "uso": "Calmante",
            "parte_utilizada": "Flores",
            "forma_uso": "Infusão",
            "imagem_url": "https://exemplo.com/camomila.jpg"
        }
        ```

        ## Resposta (400 – Campos ausentes):
        ```json
        {
            "error": "Preencher todos os campos obrigatórios para Medicamento (incluindo uso, parte e forma)"
        }
        ```

        ## Resposta (400 – Erro interno):
        ```json
        {
            "error": "Erro no cadastro do medicamento: descrição_do_erro"
        }
        ```

        ## Erros possíveis:
        - Falta de campos obrigatórios.
        - Tipos inválidos (ex: preço não numérico).
        - URL de imagem inválida ou ausente.
        - Problemas ao salvar no banco de dados.
        - Exceções internas inesperadas.
        """
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
    """
        ROTA: /cadastro/produto
        MÉTODO: POST
        DESCRIÇÃO:
            Rota responsável por cadastrar um novo produto no sistema.
            Verifica se todos os campos obrigatórios foram enviados e,
            caso estejam corretos, salva o produto no banco de dados.

        CAMPOS OBRIGATÓRIOS (JSON):
            - nome_produto (str)
            - dimensao_produto (str)
            - preco_produto (float)
            - peso_produto (str)
            - cor_produto (str)
            - descricao_produto (str)
            - fabricante (str)
            - categoria_produto (str)
            - uso (str)
            - parte_utilizada (str)
            - imagem_url (str)

        CAMPOS OPCIONAIS:
            - forma_uso (str)

        EXEMPLO DE JSON ESPERADO:
            {
                "nome_produto": "Óleo de Copaíba",
                "dimensao_produto": "10cm x 4cm",
                "preco_produto": 29.90,
                "peso_produto": "50g",
                "cor_produto": "Âmbar",
                "descricao_produto": "Óleo natural da copaibeira",
                "fabricante": "Amazônia Viva",
                "categoria_produto": "Medicinal",
                "uso": "Anti-inflamatório",
                "parte_utilizada": "Resina",
                "forma_uso": "Aplicar na pele 2x ao dia",
                "imagem_url": "https://example.com/img.jpg"
            }

        RESPOSTAS POSSÍVEIS:
            SUCESSO (201):
                {
                    "id_produto": 10,
                    "nome_produto": "...",
                    ...
                }

            ERRO CAMPOS FALTANDO (400):
                {
                    "error": "preencher todos os campos"
                }

            ERRO INTERNO (400):
                {
                    "error": "descrição do erro"
                }
        """
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
    """
       ROTA: /cadastro/blog
       MÉTODO: POST
       DESCRIÇÃO:
           Rota responsável por cadastrar uma nova postagem de blog.
           Valida os campos obrigatórios e salva o conteúdo no banco.

       CAMPOS OBRIGATÓRIOS (JSON):
           - usuario_id (int)
           - comentario (str)
           - titulo (str)
           - data (str)  -> formato esperado: "YYYY-MM-DD"
           - link_video (str)

       EXEMPLO DE JSON ESPERADO:
           {
               "usuario_id": 3,
               "comentario": "A importância das ervas medicinais na cultura indígena.",
               "titulo": "Ervas da Amazônia",
               "data": "2025-02-14",
               "link_video": "https://youtube.com/abcd1234"
           }

       REGRAS DE VALIDAÇÃO:
           - usuario_id deve ser um número inteiro.
           - Nenhum campo pode estar vazio.

       RESPOSTAS POSSÍVEIS:
           SUCESSO (201):
               {
                   "id_blog": 10,
                   "usuario_id": 3,
                   "comentario": "...",
                   "titulo": "...",
                   "data": "2025-02-14",
                   "link_video": "..."
               }

           ERRO CAMPOS FALTANDO (400):
               {
                   "mensagem": "Erro de cadastro"
               }

           ERRO usuario_id inválido (400):
               {
                   "erro": "usuario_id deve ser um número inteiro"
               }

           ERRO INTERNO (400):
               {
                   "erro": "descrição do erro"
               }
       """
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
    """
        ROTA: /cadastro/movimentacao
        MÉTODO: POST
        DESCRIÇÃO:
            Rota responsável por cadastrar uma nova movimentação de estoque.
            Valida todos os campos obrigatórios e salva o registro no banco.

        CAMPOS OBRIGATÓRIOS (JSON):
            - quantidade (int)
            - produto_id (int)
            - data (str ou int)   *OBS: código atual usa int, verifique se deveria ser string 'YYYY-MM-DD'*
            - status (bool)
            - usuario_id (int)

        EXEMPLO DE JSON ESPERADO:
            {
                "quantidade": 15,
                "produto_id": 3,
                "data": "2025-02-10",
                "status": true,
                "usuario_id": 1
            }

        OBSERVAÇÃO IMPORTANTE:
            No código atual, o campo "data" está recebendo int(dados["produto_id"]),
            o que provavelmente é um erro. Caso deseje, posso corrigir.

        RESPOSTAS POSSÍVEIS:
            SUCESSO (201):
                {
                    "ID_movimentacao": 12,
                    "quantidade": 15,
                    "produto_id": 3,
                    "data": "2025-02-10",
                    "status": true,
                    "usuario_id": 1
                }

            ERRO CAMPOS FALTANDO (400):
                {
                    "mensagem": "Todos os campos são obrigatórios"
                }

            ERRO INTERNO (400):
                {
                    "error": "descrição do erro"
                }
        """
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
    """
        ROTA: /cadastro/pedido
        MÉTODO: POST
        DESCRIÇÃO:
            Rota responsável por cadastrar um novo pedido no sistema.
            Valida os campos obrigatórios, cria o objeto Pedido e salva no banco.

        CAMPOS OBRIGATÓRIOS (JSON):
            - produto_id (int)
            - vendedor_id (int)
            - quantidade (int)
            - valor_total (float)
            - endereco (str)
            - usuario_id (int)

        EXEMPLO DE JSON ESPERADO:
            {
                "produto_id": 5,
                "vendedor_id": 2,
                "quantidade": 3,
                "valor_total": 129.90,
                "endereco": "Rua das Árvores, 45 - Manaus/AM",
                "usuario_id": 7
            }

        RESPOSTAS POSSÍVEIS:
            SUCESSO (201):
                {
                    "mensagem": "Pedido cadastrado com sucesso",
                    "pedido": {
                        "id_pedido": 15,
                        "produto_id": 5,
                        "vendedor_id": 2,
                        "quantidade": 3,
                        "valor_total": 129.90,
                        "endereco": "Rua das Árvores, 45 - Manaus/AM",
                        "usuario_id": 7,
                        ...
                    }
                }

            ERRO CAMPOS FALTANDO (400):
                {
                    "mensagem": "Todos os campos são obrigatórios"
                }

            ERRO BANCO DE DADOS (500):
                {
                    "erro": "Erro no banco de dados",
                    "detalhes": "descrição do erro"
                }

            ERRO INESPERADO (400):
                {
                    "erro": "Erro inesperado",
                    "detalhes": "descrição do erro"
                }
        """
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
    """
        ROTA: /consulta/envio/<id>
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por consultar os dados de envio de um usuário
            com base no ID do envio. Retorna todos os dados relacionados
            ao endereço de entrega.

        PARÂMETRO NA URL:
            - id (int) → ID do envio a ser consultado

        EXEMPLO DE REQUISIÇÃO:
            GET /consulta/envio/10

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "envio": {
                        "id_envio": 10,
                        "nome_destinatario": "João Silva",
                        "endereco": "Rua A, 123",
                        "cidade": "Manaus",
                        "estado": "AM",
                        "CEP": "69000-000",
                        "telefone": "92999999999",
                        "email": "joao@email.com"
                    }
                }

            NÃO ENCONTRADO (404):
                {
                    "mensagem": "Dados de envio não encontrado"
                }

            ERRO NA CONSULTA (400):
                {
                    "mensagem": "Erro de consulta: descrição do erro"
                }
        """
    db = SessionLocal()
    try:
        var_envio = select(Envio).where(Envio.id_envio == id)
        var_envio = db.execute(var_envio).scalar()

        if not var_envio:
            return jsonify({'mensagem': 'Dados de envio não encontrado'}), 404

        envio_resultado = {
            "id_envio": var_envio.id_envio,
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
    """
        ROTA: /consulta/usuario/<id>
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por consultar os dados de um usuário
            com base no ID informado. Retorna as informações básicas
            do usuário cadastrado no sistema.

        PARÂMETRO NA URL:
            - id (int) → ID do usuário a ser consultado

        EXEMPLO DE REQUISIÇÃO:
            GET /consulta/usuario/5

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "usuario": {
                        "nome": "Maria Oliveira",
                        "CPF": "12345678900",
                        "email": "maria@email.com",
                        "papel": "cliente"
                    }
                }

            NÃO ENCONTRADO (404):
                {
                    "mensagem": "Dados do usuario não encontrado"
                }

            ERRO NA CONSULTA (400):
                {
                    "mensagem": "Erro de consulta: descrição do erro"
                }
    """
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
    """
        ROTA: /consulta/produto/<id>
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por consultar os dados de um produto
            com base no ID informado. Retorna todas as informações
            cadastradas sobre o produto.

        PARÂMETRO NA URL:
            - id (int) → ID do produto a ser consultado

        EXEMPLO DE REQUISIÇÃO:
            GET /consulta/produto/12

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "Produto": {
                        "id_produto": 12,
                        "nome_produto": "Cocar Tradicional",
                        "dimensao_produto": "30cm x 20cm",
                        "preco_produto": 150.00,
                        "peso_produto": "200g",
                        "cor_produto": "Colorido",
                        "descricao_produto": "Cocar feito à mão por artesãos indígenas."
                    }
                }

            NÃO ENCONTRADO (404):
                {
                    "mensagem": "Produto não encontrado"
                }

            ERRO NA CONSULTA (400):
                {
                    "mensagem": "Erro de consulta: descrição do erro"
                }
    """
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
    """
        ROTA: /consulta/blog/<id>
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por consultar as informações de um blog
            associado a um usuário específico, com base no ID do usuário.
            Retorna o título, comentário e data da publicação.

        PARÂMETRO NA URL:
            - id (int) → ID do usuário ao qual o blog pertence

        EXEMPLO DE REQUISIÇÃO:
            GET /consulta/blog/5

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "blog": {
                        "usuario_id": 5,
                        "comentario": "Texto do blog...",
                        "titulo": "Meu primeiro post",
                        "data": "2025-01-10"
                    }
                }

            NÃO ENCONTRADO (404):
                {
                    "mensagem": "Blog não encontrado"
                }

            ERRO NA CONSULTA (400):
                {
                    "mensagem": "Erro de consulta: descrição do erro"
                }
    """
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
    """
        ROTA: /consulta/pedido/<id>
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por consultar um pedido específico com base
            no ID do pedido. Retorna todas as informações do pedido,
            incluindo produto, vendedor, quantidade, valor total,
            endereço e usuário relacionado.

        PARÂMETRO NA URL:
            - id (int) → ID do pedido a ser consultado

        EXEMPLO DE REQUISIÇÃO:
            GET /consulta/pedido/12

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "pedido": {
                        "ID_pedido": 12,
                        "produto_id": 3,
                        "vendedor_id": 7,
                        "quantidade": 2,
                        "valor_total": 150.00,
                        "endereco": "Rua X, 456",
                        "usuario_id": 10,
                        "data_pedido": "2025-02-01"
                    }
                }

            NÃO ENCONTRADO (404):
                {
                    "mensagem": "Pedido não encontrado"
                }

            ERRO INTERNO (500):
                {
                    "mensagem": "Erro interno: descrição do erro"
                }
    """
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
    """
        ROTA: /consulta/movimentacao/<id>
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por consultar uma movimentação específica
            com base no seu ID. Retorna todas as informações relacionadas
            à movimentação, como quantidade, produto, status, usuário e data.

        PARÂMETRO NA URL:
            - id (int) → ID da movimentação a ser consultada

        EXEMPLO DE REQUISIÇÃO:
            GET /consulta/movimentacao/5

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "movimentacao": {
                        "ID_movimentacao": 5,
                        "quantidade": 10,
                        "produto_id": 3,
                        "status": true,
                        "data": "2025-01-20",
                        "usuario_id": 8
                    }
                }

            NÃO ENCONTRADO (404):
                {
                    "mensagem": "Movimentação não encontrada"
                }

            ERRO INTERNO (500):
                {
                    "mensagem": "Erro interno: descrição do erro"
                }
    """
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
    """
        ROTA: /lista/usuario
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por listar todos os usuários cadastrados no sistema.
            Retorna uma lista contendo ID, nome e email de cada usuário encontrado.

        EXEMPLO DE REQUISIÇÃO:
            GET /lista/usuario

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "usuarios": [
                        {
                            "id": 1,
                            "nome": "Sandra Maria",
                            "email": "sandra@email.com"
                        },
                        {
                            "id": 2,
                            "nome": "João Silva",
                            "email": "joao@email.com"
                        }
                    ]
                }

            ERRO NA CONSULTA (400):
                {
                    "erro": "descrição do erro"
                }
    """
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
    """
        ROTA: /lista/produto
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por listar todos os produtos cadastrados no sistema.
            Retorna uma lista com informações básicas de cada produto, como nome,
            preço, dimensões e descrição.

        EXEMPLO DE REQUISIÇÃO:
            GET /lista/produto

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "produtos": [
                        {
                            "id_produto": 1,
                            "nome_produto": "Artesanato Indígena",
                            "dimensao_produto": "15x20 cm",
                            "preco_produto": 120.00,
                            "peso_produto": "300g",
                            "cor_produto": "Natural",
                            "descricao_produto": "Produto feito à mão por artesãos indígenas."
                        }
                    ]
                }

            ERRO NA CONSULTA (400):
                {
                    "erro": "descrição do erro"
                }
    """
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


@app.route('/lista/blog/', methods=['GET'])
# @jwt_required()
def lista_blog():
    """
        ROTA: /lista/blog
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por listar todos os blogs cadastrados no sistema.
            Retorna uma lista contendo informações de cada publicação, incluindo
            título, data, comentário e o ID do usuário responsável.

        EXEMPLO DE REQUISIÇÃO:
            GET /lista/blog/

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "blog": [
                        {
                            "id_blog": 5,
                            "usuario_id": 3,
                            "titulo": "Cultura Indígena na Atualidade",
                            "data": "2024-11-10",
                            "comentario": "Texto explicando a importância da preservação cultural."
                        }
                    ]
                }

            ERRO NA CONSULTA (400):
                {
                    "erro": "descrição do erro"
                }
    """

    db = SessionLocal()  # Cria a sessão
    try:
        resultado = db.execute(select(Blog)).scalars()  # Pega todos os blogs
        blog = [
            {
                "id_blog": b.id_blog,
                "usuario_id": b.usuario_id,
                "titulo": b.titulo,
                "data": b.data,
                "comentario": b.comentario
            }
            for b in resultado
        ]
        return jsonify({'blog': blog}), 200
    except SQLAlchemyError as e:
        return jsonify({'erro': str(e)}), 400
    finally:
        db.close()  # Fecha a sessão


@app.route('/lista/pedido/', methods=['GET'])
# @jwt_required()
# @admin_required
def lista_pedido():
    """
        ROTA: /lista/pedido
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por listar todos os pedidos cadastrados no sistema.
            Retorna uma lista com informações completas de cada pedido, como
            produto, usuário, vendedor, quantidade e endereço de entrega.

        EXEMPLO DE REQUISIÇÃO:
            GET /lista/pedido/

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "pedidos": [
                        {
                            "ID_pedido": 12,
                            "produto_id": 3,
                            "usuario_id": 8,
                            "vendedor_id": 2,
                            "quantidade": 4,
                            "valor_total": 159.90,
                            "endereco": "Rua Exemplo, 456 - AM"
                        }
                    ]
                }

            ERRO NA CONSULTA (400):
                {
                    "erro": "descrição do erro"
                }
    """
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


@app.route('/lista/movimentacao', methods=['GET'])
# @jwt_required()
# @admin_required
def lista_movimentacao():
    """
        ROTA: /lista/movimentacao
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por listar todas as movimentações registradas no sistema.
            Cada movimentação contém informações como quantidade, produto associado,
            data da operação, status e o usuário responsável.

        EXEMPLO DE REQUISIÇÃO:
            GET /lista/movimentacao

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "movimentacoes": [
                        {
                            "ID_movimentacao": 5,
                            "quantidade": 20,
                            "produto_id": 3,
                            "data": "2025-01-10",
                            "status": true,
                            "usuario_id": 1
                        }
                    ]
                }

            ERRO NA CONSULTA (400):
                {
                    "erro": "descrição do erro"
                }
    """
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


@app.route('/lista/envio', methods=['GET'])
# @jwt_required()
# @admin_required
def lista_envio():
    """
        ROTA: /lista/envio
        MÉTODO: GET
        DESCRIÇÃO:
            Rota responsável por listar todos os envios cadastrados no sistema.
            Cada envio contém informações completas sobre o destinatário,
            endereço, contato e usuário associado.

        EXEMPLO DE REQUISIÇÃO:
            GET /lista/envio

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "envio": [
                        {
                            "id_envio": 12,
                            "usuario_id": 3,
                            "nome_destinatario": "Maria Oliveira",
                            "endereco": "Rua das Flores, 55",
                            "cidade": "Manaus",
                            "estado": "AM",
                            "CEP": "69000-000",
                            "telefone": "92988887777",
                            "email": "maria@example.com"
                        }
                    ]
                }

            ERRO NA CONSULTA (400):
                {
                    "erro": "descrição do erro"
                }
    """
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
    """
        ROTA: /atualizar/cartao/<id_cartao>
        MÉTODO: PUT
        DESCRIÇÃO:
            Rota responsável por atualizar os dados de um cartão já cadastrado.
            A atualização é feita com base no ID do cartão enviado na URL e todos
            os campos obrigatórios devem ser preenchidos na requisição.

        PARÂMETRO NA URL:
            - id_cartao (int) → ID do cartão a ser atualizado.

        CAMPOS OBRIGATÓRIOS NO BODY (JSON):
            - nome_titular (string)
            - numero_cartao (string)
            - data_validade (string)
            - CVV (string)

        EXEMPLO DE REQUISIÇÃO:
            PUT /atualizar/cartao/7
            {
                "nome_titular": "Maria Oliveira",
                "numero_cartao": "5555444433332222",
                "data_validade": "08/2031",
                "CVV": "987"
            }

        RESPOSTAS POSSÍVEIS:
            SUCESSO (200):
                {
                    "mensagem": "Dados do cartao atualizado com sucesso"
                }

            NÃO ENCONTRADO (404):
                {
                    "erro": "dados de cartao não encontrado"
                }

            ERRO DE VALIDAÇÃO (400):
                {
                    "erro": "Preencher todos os campos obrigatórios"
                }

            ERRO NO BANCO (400):
                {
                    "erro": "descrição do erro"
                }
    """
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
    """
    API para atualizar os dados de envio de um pedido.

    ## Endpoint:
    `PUT /atualizar/envio/<id_envio>`

    ## Parâmetros:
    - `id_envio` (int): **ID do envio a ser atualizado.**

    ## Corpo da Requisição (JSON):
    ```json
    {
        "nome_destinatario": "João Silva",
        "endereco": "Rua A, 123",
        "cidade": "São Paulo",
        "estado": "SP",
        "CEP": "01234567",
        "telefone": "11999999999",
        "email": "email@example.com"
    }
    ```

    ## Campos obrigatórios:
    - nome_destinatario
    - endereco
    - cidade
    - estado
    - CEP
    - telefone
    - email

    ## Resposta (JSON):
    ```json
    {
        "mensagem": "Dados de envio atualizado com sucesso"
    }
    ```

    ## Erros possíveis:
    - Se o `id_envio` não existir:
        ```json
        {
            "erro": "dados de envio não encontrado"
        }
        ```
    - Se faltar qualquer campo obrigatório:
        ```json
        {
            "erro": "Preencher todos os campos obrigatórios"
        }
        ```
    - Em caso de erro interno do banco:
        ```json
        {
            "erro": "mensagem de erro SQLAlchemy"
        }
        ```
    """
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
    """
    Atualizar Usuário
    -----------------
    Rota: PUT /atualizar/usuario/<id_usuario>

    Descrição:
        Atualiza os dados de um usuário existente no sistema, incluindo nome,
        CPF, e-mail, papel e, opcionalmente, a senha caso seja enviada.

    Parâmetros de URL:
        id_usuario (int): ID do usuário que será atualizado.

    Campos obrigatórios no JSON:
        - nome (string)
        - CPF (string)
        - email (string)
        - papel (string)

    Campo opcional:
        - password (string): Atualiza a senha somente se for fornecida.

    Exemplo de JSON enviado:
    {
        "nome": "Usuário Teste",
        "CPF": "00000000000",
        "email": "teste@example.com",
        "papel": "cliente",
        "password": "novaSenhaOpcional"
    }

    Respostas:
        200:
            {
                "mensagem": "Usuário atualizado com sucesso"
            }

        400:
            {
                "erro": "Preencher todos os campos obrigatórios"
            }
            ou erros de banco de dados.

        404:
            {
                "erro": "Usuário não encontrado"
            }

    Observações:
        - A senha só é atualizada se o campo 'password' for enviado.
        - Em caso de erro durante o commit, é executado rollback().
    """
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
    """
     API para atualizar as informações de um produto.

     ## Endpoint:
     `PUT /atualizar/produto/<id_produto>`

     ## Parâmetros:
     - `id_produto` (int): **ID do produto que será atualizado.**

     ## Corpo da Requisição (JSON):
     ```json
     {
         "nome_produto": "Camiseta Azul",
         "dimensao_produto": "40x30 cm",
         "preco_produto": 59.90,
         "peso_produto": "300g",
         "cor_produto": "Azul",
         "descricao_produto": "Camiseta de algodão tamanho M"
     }
     ```

     ## Campos obrigatórios:
     - nome_produto
     - dimensao_produto
     - preco_produto
     - peso_produto
     - descricao_produto
     - **cor_produto é opcional**

     ## Resposta (JSON):
     ```json
     {
         "mensagem": "Produto atualizado com sucesso"
     }
     ```

     ## Erros possíveis:
     - Se o `id_produto` não existir:
         ```json
         {
             "erro": "Produto não encontrado"
         }
         ```
     - Se faltar qualquer campo obrigatório:
         ```json
         {
             "erro": "Preencher todos os campos obrigatórios"
         }
         ```
     - Em caso de erro interno do banco:
         ```json
         {
             "erro": "mensagem de erro SQLAlchemy"
         }
         ```
     """
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
    """
      API para atualizar um post do blog.

      ## Endpoint:
      `PUT /atualizar/blog/<id_blog>`

      ## Parâmetros:
      - `id_blog` (int): **ID do blog que será atualizado.**

      ## Corpo da Requisição (JSON):
      ```json
      {
          "titulo": "Meu novo título",
          "data": "2025-03-15",
          "comentario": "Atualizando conteúdo do post",
          "usuario_id": 12
      }
      ```

      ## Campos obrigatórios:
      - titulo
      - data
      - comentario
      - **usuario_id é opcional** (se não enviado, mantém o valor atual)

      ## Resposta (JSON):
      ```json
      {
          "mensagem": "Blog atualizado com sucesso"
      }
      ```

      ## Erros possíveis:
      - Se o `id_blog` não existir:
          ```json
          {
              "erro": "Blog não encontrado"
          }
          ```
      - Se faltar qualquer campo obrigatório:
          ```json
          {
              "erro": "Preencher todos os campos obrigatórios"
          }
          ```
      - Em caso de erro interno do banco:
          ```json
          {
              "erro": "mensagem de erro SQLAlchemy"
          }
          ```
      """
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
    """
       API para atualizar os dados de um pedido.

       ## Endpoint:
       `PUT /atualizar/pedido/<id_pedido>`

       ## Parâmetros:
       - `id_pedido` (int): **ID do pedido que será atualizado.**

       ## Corpo da Requisição (JSON):
       ```json
       {
           "usuario_id": 5,
           "produto_id": 12,
           "quantidade": 3,
           "valor_total": 199.90,
           "endereco": "Rua Central, 1200",
           "vendedor_id": 7
       }
       ```

       ## Campos obrigatórios:
       - usuario_id
       - produto_id
       - quantidade
       - valor_total
       - endereco
       - vendedor_id

       ## Resposta (JSON):
       ```json
       {
           "mensagem": "Pedido atualizado com sucesso"
       }
       ```

       ## Erros possíveis:
       - Se o `id_pedido` não existir:
           ```json
           {
               "erro": "Pedido não encontrado"
           }
           ```
       - Se faltar qualquer campo obrigatório:
           ```json
           {
               "erro": "Preencher todos os campos obrigatórios"
           }
           ```
       - Erro interno do banco:
           ```json
           {
               "erro": "mensagem de erro SQLAlchemy"
           }
           ```
       """
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
    """
    API para atualizar uma movimentação de estoque.

    ## Endpoint:
    `PUT /atualizar/movimentacao/<id_movimentacao>`

    ## Parâmetros:
    - `id_movimentacao` (int): **ID da movimentação que será atualizada.**

    ## Corpo da Requisição (JSON):
    ```json
    {
        "quantidade": 10,
        "produto_id": 5,
        "data": "2025-02-10",
        "status": true,
        "usuario_id": 3
    }
    ```

    ## Campos obrigatórios:
    - quantidade
    - produto_id
    - data (formato **YYYY-MM-DD**)
    - status
    - usuario_id

    ## Resposta (JSON):
    ```json
    {
        "mensagem": "Movimentação atualizada com sucesso",
        "movimentacao": {
            "ID_movimentacao": 1,
            "quantidade": 10,
            "produto_id": 5,
            "data": "2025-02-10",
            "status": true,
            "usuario_id": 3
        }
    }
    ```

    ## Erros possíveis:
    - Se o ID não existir:
        ```json
        {
            "erro": "Movimentação não encontrada"
        }
        ```
    - Se faltar algum campo obrigatório:
        ```json
        {
            "erro": "Preencher todos os campos obrigatórios"
        }
        ```
    - Se a data estiver em formato inválido:
        ```json
        {
            "erro": "Formato de data inválido. Use YYYY-MM-DD"
        }
        ```
    - Erro interno do banco:
        ```json
        {
            "erro": "mensagem de erro SQLAlchemy"
        }
        ```
    """
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
    """
      API para atualizar um medicamento no sistema.

      ## Endpoint:
      `PUT /atualizar/medicamento/<id_produto>`

      ## Parâmetros:
      - `id_produto` (int): **ID do medicamento que será atualizado.**

      ## Corpo da Requisição (JSON):
      ```json
      {
          "nome_produto": "Paracetamol 750mg",
          "preco_produto": 12.50,
          "descricao_produto": "Medicamento para dor e febre",
          "fabricante": "MedPharma",
          "categoria_produto": "Analgesico",
          "dimensao_produto": "10x5 cm",
          "peso_produto": "50g",
          "cor_produto": "Branco",
          "uso": "Para dor e febre",
          "parte_utulizado": "Comprimido",
          "forma_uso": "Tomar 1 comprimido a cada 8h",
          "imagem_url": "https://exemplo.com/imagem.png"
      }
      ```

      ## Campos obrigatórios:
      - nome_produto
      - preco_produto
      - descricao_produto
      - fabricante
      - categoria_produto
      - dimensao_produto
      - peso_produto
      - cor_produto
      - uso
      - parte_utulizado
      - forma_uso
      - imagem_url

      ## Resposta (JSON):
      ```json
      {
          "mensagem": "medicamento atualizado com sucesso"
      }
      ```

      ## Erros possíveis:
      - Medicamento não encontrado:
          ```json
          {
              "erro": "medicamento não encontrada"
          }
          ```
      - Campos obrigatórios faltando:
          ```json
          {
              "erro": "Preencher todos os campos obrigatórios"
          }
          ```
      - Erro interno:
          ```json
          {
              "erro": "mensagem de erro SQLAlchemy"
          }
          ```
      """
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
    """
    ---
    **Endpoint:** /dashboard/produtos-mais-vendidos
    **Método:** GET
    **Descrição:**
        Retorna um ranking dos produtos mais vendidos, com total de quantidade vendida
        e valor total gerado por cada produto. Os dados são agrupados pelo nome
        do produto e ordenados do mais vendido para o menos vendido.

    **Retorno de Sucesso (200):**
    {
        "ranking_produtos": [
            {
                "nome_produto": "Dipirona 500mg",
                "quantidade_total": 185,
                "valor_total": 1420.50
            },
            {
                "nome_produto": "Vitamina C",
                "quantidade_total": 90,
                "valor_total": 450.00
            }
        ]
    }

    **Erros Possíveis:**
    - (400) Erro interno ao gerar relatório
        {
            "erro": "mensagem do erro"
        }
    ---
    """
    db = SessionLocal()
    try:
        resultado = (
            db.query(
            Produto.nome_produto,
            func.sum(Pedido.quantidade).label("quantidade_total"),
            func.sum(Pedido.valor_total).label("valor_total")
        )
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
    app.run(debug=True, host="0.0.0.0", port=5009)