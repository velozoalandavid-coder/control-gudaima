from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TelaBase(BaseModel):
    codigo_tela: float
    tipo: str
    color: str
    precio_kg: float
    minimo_kg: float

class TelaCreate(BaseModel):
    codigo_tela: float
    tipo: str
    color: str
    precio_kg: float
    minimo_kg: float

class RolloCreate(BaseModel):
    codigo_tela: float
    tipo: str
    color: str
    kg_rollo: float
    observacion: Optional[str] = None

class RolloResponse(RolloCreate):
    id_rollo: int
    fecha: datetime
    class Config:
        orm_mode = True

class CorteCreate(BaseModel):
    codigo_tela: float
    tipo: str
    color: str
    kg_usados: float
    rollos_usados: int
    observacion: Optional[str] = None

class CorteResponse(CorteCreate):
    nro_corte: int
    fecha: datetime
    class Config:
        orm_mode = True

class StockItem(BaseModel):
    codigo_tela: float
    tipo: str
    color: str
    kg_ingresados: float
    kg_usados: float
    stock_actual_kg: float
    rollos_disponibles: int
    estado: str
    precio_kg: float
    valor_stock: float