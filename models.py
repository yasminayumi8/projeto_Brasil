
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, Date
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from werkzeug.security import check_password_hash, generate_password_hash

engine = create_engine('sqlite:///projeto.sqlite3')
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class Produto(Base):
    __tablename__ = 'produtos'
    id_produto = Column(Integer, primary_key=True)
    nome_produto = Column(String, nullable=False, index=True )
    dimensao_produto = Column(String, nullable=False, index=True)
    preco_produto = Column(String(11), nullable=False, index=True)
    peso_produto = Column(String(11), nullable=False, index=True)
    cor_produto = Column(String,nullable=False, index=True)
    descricao_produto = Column(String,nullable=False, index=True)

    # NOVOS CAMPOS ADICIONADOS PARA A LOJA:
    uso = Column(String, nullable=False, index=True)  # Ex: "Nisũ, para nó ou bolhas nas juntas"
    parte_utilizada = Column(String, nullable=False, index=True)  # Ex: "folha"
    forma_uso = Column(String, nullable=False, index=True )  # Ex: "cozimento e banho"
    imagem_url = Column(String, nullable=False, index=True)  # URL para a imagem (ou caminho estático)

    def __repr__(self):
        return '<Produto {} {} {} {} {} {} {} {} {} {} {} >'.format(self.id_produto, self.nome_produto, self.dimensao_produto,
                                                                    self.preco_produto, self.peso_produto, self.cor_produto,
                                                                    self.descricao_produto, self.uso, self.parte_utilizada, self.forma_uso, self.imagem_url)

    def save(self, db_session):
        try:
            db_session.add(self)
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            raise

    def delete(self, db_session):
        db_session.delete(self)
        db_session.commit()

    def serialize_produto(self):
        return {
            'id_produto': self.id_produto,
            'nome_produto': self.nome_produto,
            'dimensao_produto': self.dimensao_produto,
            'preco_produto': self.preco_produto,
            'peso_produto': self.peso_produto,
            'cor_produto': self.cor_produto,
            'descricao_produto': self.descricao_produto,
            'uso': self.uso,
            'parte_utilizada': self.parte_utilizada,
            'forma_uso': self.forma_uso,
            'imagem_url': self.imagem_url,
        }
        return dados_produto


class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, index=True)
    CPF = Column(String(11), nullable=False, unique=True, index=True)
    email = Column(String(30), nullable=False, index=True)
    password_hash = Column(String(128), nullable=False, index=True)  # aumentado o tamanho
    papel = Column(String, default="usuario", nullable=False, index=True)

    def __repr__(self):
        return '<usuario {} {} {} {} {} {}>'.format(self.id, self.nome, self.CPF, self.email, self.password_hash, self.papel)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def save(self, db_session):
        try:
            db_session.add(self)
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            raise

    def delete(self, db_session):
        db_session.delete(self)
        db_session.commit()

    def serialize_usuario(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'CPF': self.CPF,
            'email': self.email,
            'password_hash': self.password_hash,
            'papel': self.papel,
        }
        return dados_usuario

class Movimentacao(Base):
    __tablename__ = 'movimentacao'
    ID_movimentacao = Column(Integer, primary_key=True)
    quantidade = Column(Integer, nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey('produtos.id_produto'), nullable=False, index=True)
    data = Column(Date, nullable=False, index=True)  # agora tipo Date
    status = Column(Boolean, nullable=False, index=True, default=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))

    usuario = relationship('Usuario')
    produto = relationship('Produto')

    def __repr__(self):
        return f'<movimentacao: {self.ID_movimentacao} {self.quantidade} {self.produto_id} {self.data} {self.status} {self.usuario_id}>'

    def save(self, db_session):
        try:
            db_session.add(self)
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            raise

    def delete(self, db_session):
        db_session.delete(self)
        db_session.commit()

    def serialize_movimentacao(self):
        return {
            'ID_movimentacao': self.ID_movimentacao,
            'quantidade': self.quantidade,
            'produto_id': self.produto_id,
            'data': self.data.isoformat(),
            'status': self.status,
            'usuario_id': self.usuario_id,
        }
        return dados_movimentacao


class Pedido(Base):
    __tablename__ = 'pedido'

    ID_pedido = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id_produto'))
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    vendedor_id = Column(Integer, ForeignKey('usuarios.id'))
    quantidade = Column(Integer, nullable=False, index=True)
    valor_total = Column(Integer, nullable=False, index=True)
    endereco = Column(String(40), nullable=False, index=True)

    produto = relationship('Produto')
    usuario = relationship('Usuario', foreign_keys=[usuario_id])
    vendedor = relationship('Usuario', foreign_keys=[vendedor_id])

    def __repr__(self):
        return '<pedido: {} {} {} {} {} {}>'.format(
            self.ID_pedido,
            self.produto_id,
            self.quantidade,
            self.valor_total,
            self.endereco,
            self.vendedor_id
        )

    def save(self, db_session):
        try:
            db_session.add(self)
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            raise

    def delete(self, db_session):
        db_session.delete(self)
        db_session.commit()

    def serialize_pedido(self):
        return {
            'ID_pedido': self.ID_pedido,
            'produto_id': self.produto_id,
            'usuario_id': self.usuario_id,
            'vendedor_id': self.vendedor_id,
            'quantidade': self.quantidade,
            'valor_total': self.valor_total,
            'endereco': self.endereco
        }
        return dados_pedido


class Blog(Base):
    __tablename__ = 'blog'
    id_blog = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    comentario = Column(String(255), nullable=False, index=True)
    titulo = Column(String(255), nullable=False, index=True)
    data = Column(String(255), nullable=False, index=True)

    def __repr__(self):
        return '<blog: {} {} {} {} {}>'.format(self.id_blog, self.usuario_id, self.titulo, self.data, self.comentario)

    def save(self, db_session):
        try:
            db_session.add(self)
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            raise

    def delete(self, db_session):
        db_session.delete(self)
        db_session.commit()

    def serialize_blog(self):
        return {
            'id_blog': self.id_blog,
            'usuario_id': self.usuario_id,
            'titulo': self.titulo,
            'data': self.data,
            'comentario': self.comentario,
        }
        return dados_blog

def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == '__main__':
    init_db()




