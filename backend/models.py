from sqlalchemy import Column, Integer, Float, String, DateTime
from database import Base
import datetime

class Tela(Base):
    __tablename__ = "telas"
    codigo_tela = Column(Float, primary_key=True)
    tipo = Column(String, primary_key=True)
    color = Column(String, primary_key=True)
    precio_kg = Column(Float)
    minimo_kg = Column(Float)

class Rollo(Base):
    __tablename__ = "rollos"
    id_rollo = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    codigo_tela = Column(Float)
    tipo = Column(String)
    color = Column(String)
    kg_rollo = Column(Float)
    observacion = Column(String, nullable=True)

class Corte(Base):
    __tablename__ = "cortes"
    nro_corte = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    codigo_tela = Column(Float)
    tipo = Column(String)
    color = Column(String)
    kg_usados = Column(Float)
    rollos_usados = Column(Integer)
    metros_usados = Column(Float, nullable=True)
    observacion = Column(String, nullable=True)