import os

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, DateTime, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, scoped_session


# a pasta de trabalho é a "dados" na mesmo diretório onde esta este arquivo
path = os.path.dirname(os.path.realpath(__file__)) + "/dados"

# cria pasta 'dados' se ela ainda não existe
if not os.path.isdir(path):
    os.mkdir(path)

Base = declarative_base()


class Log(Base):
    __tablename__ = 'log'

    id = Column(Integer, primary_key=True)
    horario = Column(DateTime, default=datetime.now)
    nivel = Column(String(10), default='info')      # nivel de importancia: info, alerta, erro...
    origem = Column(String(20), nullable=False)     # aerador, tratador, conexao
    evento = Column(String(20), nullable=False)     # evento ocorrido na origem
    mensagem = Column(String(300))  # mensagem adcional que acompanha o evento ex: nova agenda


# agenda atual do aerador
class Aerador(Base):
    __tablename__ = 'agenda_aerador'

    id = Column(Integer, primary_key=True)
    inicio = Column(Time, nullable=False)
    fim = Column(Time, nullable=False)


# agenda atual do tratador
class Tratador(Base):
    __tablename__ = 'agenda_tratador'
    id = Column(Integer, primary_key=True)
    inicio = Column(Time, nullable=False)
    quantidade = Column(Float, nullable=False)

class DHT22(Base):
    __tablename__ = 'sensor_dht22'
    id = Column(Integer, primary_key=True)
    tempo = Column(DateTime, default=datetime.now)
    temperature = Column(Float)
    humidity = Column(Float)

# funções para gravação no banco de dados

# salva log no banco de dados alem de imprimir
def log(origem, evento, nivel='info', msg=None):
    entrada = Log(nivel=nivel, origem=origem, evento=evento, mensagem=msg)
    session = Session()
    session.add(entrada)
    session.commit()
    session.flush()
    session.close()

    texto = "{}, {}, {}".format(nivel, origem, evento)
    if msg:
        texto += ', {}'.format(msg)
    print(texto)


# salva a agenda dos atuadores
def salva_agenda(agenda):
    # formato da agenda {'tratador':[...], 'aerador':[...]}
    # percorre os atuadores da agenda
    session = Session()
    for atuador in agenda:
        # limpa dados antigos
        if atuador == 'tratador':
            session.query(Tratador).delete()
        elif atuador == 'aerador':
            session.query(Aerador).delete()
        else:
            session.flush()
            session.close()
            raise ValueError("atuador {} não está configurado no banco de dados".format(atuador))

        for alarme in agenda[atuador]:
            if atuador == 'tratador':
                entrada = Tratador(inicio=alarme[0], quantidade=alarme[1])
            elif atuador == 'aerador':
                entrada = Aerador(inicio=alarme[0], fim=alarme[1])

            session.add(entrada)

    session.commit()
    session.flush()
    session.close()


# recupera a agenda como um dicionário
def recupera_agenda():
    session = Session()
    agenda = {}

    tratador = agenda['tratador'] = []
    rows = session.query(Tratador).all()
    for item in rows:
        tratador.append([item.inicio, item.quantidade])

    aerador = agenda['aerador'] = []
    rows = session.query(Aerador).all()
    for item in rows:
        aerador.append([item.inicio, item.fim])

    session.flush()
    session.close()

    return agenda


def salva_dht(temperature, humidity):
    entrada = DHT22(temperature=temperature, humidity=humidity)
    session = Session()
    session.add(entrada)
    session.commit()
    session.flush()
    session.close()


def ultimo_dht():
    session = Session()

    row = session.query(DHT22).order_by(DHT22.id.desc()).\
        filter(DHT22.temperature is not None, DHT22.humidity is not None).first()

    payload = { 'hora': row.tempo, 'ar_temperatura': row.temperature,
                'ar_umidade': row.humidity}

    session.flush()
    session.close()

    return payload


url = 'sqlite:///{}/arquivo.db'.format(path)

engine = create_engine(url, poolclass=NullPool)

Base.metadata.create_all(engine)

# configuração da banco de dados
Base.metadata.bind = engine

# cria uma sessão
# scoped_session foi adcionado pq estava recebendo um erro do sqlite:
# SQLite objects created in a thread can only be used in that same thread
Session = scoped_session(sessionmaker(bind=engine))
# db_session = DBSession()
