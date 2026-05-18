from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import engine, get_db, Base, SessionLocal
from models import Tela, Rollo, Corte
from schemas import (
    TelaBase, TelaCreate,
    RolloCreate, RolloResponse,
    CorteCreate, CorteResponse,
    StockItem
)
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import os

app = FastAPI(title="Textil API")

# Cargar datos iniciales desde CSV
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        if db.query(Tela).count() == 0:
            telas_df = pd.read_csv("telas.csv")
            rollos_df = pd.read_csv("rollos.csv")

            for _, row in telas_df.iterrows():
                db.add(Tela(
                    codigo_tela=row["codigo_tela"],
                    tipo=row["tipo"],
                    color=row["color"],
                    precio_kg=row["precio_kg"],
                    minimo_kg=row["minimo_kg"]
                ))

            db.commit()

            for _, row in rollos_df.iterrows():
                db.add(Rollo(
                    id_rollo=row["id_rollo"],
                    fecha=pd.to_datetime(row["fecha"]),
                    codigo_tela=row["codigo_tela"],
                    tipo=row["tipo"],
                    color=row["color"],
                    kg_rollo=row["kg_rollo"],
                    observacion=row["observacion"]
                ))

            db.commit()

if db.query(Corte).count() == 0:
    cortes_df = pd.read_csv("cortes.csv")

    for _, row in cortes_df.iterrows():
        db.add(Corte(
            nro_corte=int(row["nro_corte"]),
            fecha=pd.to_datetime(row["fecha"]),
            codigo_tela=float(row["codigo_tela"]),
            tipo=row["tipo"],
            color=row["color"],
            kg_usados=float(row["kg_usados"]),
            rollos_usados=int(row["rollos_usados"]),
            observacion=row.get("observacion", "")
        ))

    db.commit()

    print("CSV cargados correctamente")

    except Exception as e:
        print("ERROR:", e)

    finally:
        db.close()

# Endpoints de consulta
@app.get("/telas")
def get_telas(db: Session = Depends(get_db)):
    return db.query(Tela).all()

@app.get("/stock", response_model=List[StockItem])
def get_stock(db: Session = Depends(get_db)):
    stock_data = []
    telas = db.query(Tela).all()
    for tela in telas:
        kg_ing = db.query(func.coalesce(func.sum(Rollo.kg_rollo), 0)).filter(
            Rollo.codigo_tela == tela.codigo_tela,
            Rollo.tipo == tela.tipo,
            Rollo.color == tela.color
        ).scalar()
        kg_us = db.query(func.coalesce(func.sum(Corte.kg_usados), 0)).filter(
            Corte.codigo_tela == tela.codigo_tela,
            Corte.tipo == tela.tipo,
            Corte.color == tela.color
        ).scalar()
        rollos_tot = db.query(func.count(Rollo.id_rollo)).filter(
            Rollo.codigo_tela == tela.codigo_tela,
            Rollo.tipo == tela.tipo,
            Rollo.color == tela.color
        ).scalar()
        rollos_us = db.query(func.coalesce(func.sum(Corte.rollos_usados), 0)).filter(
            Corte.codigo_tela == tela.codigo_tela,
            Corte.tipo == tela.tipo,
            Corte.color == tela.color
        ).scalar()

        stock_actual = kg_ing - kg_us
        rollos_disp = rollos_tot - rollos_us
        if stock_actual <= 0:
            estado = "SIN STOCK"
        elif stock_actual <= tela.minimo_kg:
            estado = "COMPRAR"
        else:
            estado = "OK"

        stock_data.append(StockItem(
            codigo_tela=tela.codigo_tela,
            tipo=tela.tipo,
            color=tela.color,
            kg_ingresados=kg_ing,
            kg_usados=kg_us,
            stock_actual_kg=stock_actual,
            rollos_disponibles=rollos_disp,
            estado=estado,
            precio_kg=tela.precio_kg,
            valor_stock=stock_actual * tela.precio_kg
        ))
    return stock_data

# CRUD Telas
@app.post("/telas", response_model=TelaBase)
def crear_tela(tela: TelaCreate, db: Session = Depends(get_db)):
    existente = db.query(Tela).filter_by(
        codigo_tela=tela.codigo_tela,
        tipo=tela.tipo,
        color=tela.color
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Esa combinación ya existe")
    nueva = Tela(**tela.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@app.delete("/telas/{codigo_tela}/{tipo}/{color}")
def eliminar_tela(codigo_tela: float, tipo: str, color: str, db: Session = Depends(get_db)):
    tela = db.query(Tela).filter_by(
        codigo_tela=codigo_tela,
        tipo=tipo,
        color=color
    ).first()
    if not tela:
        raise HTTPException(status_code=404, detail="Tela no encontrada")
    db.delete(tela)
    db.commit()
    return {"mensaje": "Tela eliminada"}

@app.delete("/cortes/{nro_corte}")
def eliminar_corte(nro_corte: int, db: Session = Depends(get_db)):
    corte = db.query(Corte).filter(Corte.nro_corte == nro_corte).first()
    if not corte:
        raise HTTPException(status_code=404, detail="Corte no encontrado")
    db.delete(corte)
    db.commit()
    return {"mensaje": f"Corte {nro_corte} eliminado"}

# Rollos
@app.post("/rollos", response_model=RolloResponse)
def crear_rollo(rollo: RolloCreate, db: Session = Depends(get_db)):
    tela = db.query(Tela).filter_by(
        codigo_tela=rollo.codigo_tela, tipo=rollo.tipo, color=rollo.color
    ).first()
    if not tela:
        raise HTTPException(status_code=400, detail="La tela no existe en el catálogo")
    nuevo = Rollo(**rollo.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.get("/rollos", response_model=List[RolloResponse])
def get_rollos(db: Session = Depends(get_db)):
    return db.query(Rollo).all()

class RolloLote(BaseModel):
    codigo_tela: float
    tipo: str
    color: str
    pesos: List[float]
    observacion: Optional[str] = None

# -------------------- NUEVO: Corte con detalle por rollo --------------------

class CorteDetalleItem(BaseModel):
    codigo_tela: float
    tipo: str
    color: str
    kg_usados: float
    rollos_usados: int

class CorteLote(BaseModel):
    detalles: List[CorteDetalleItem]
    observacion: Optional[str] = None


@app.post("/cortes/lote")
def crear_corte_lote(
    corte_lote: CorteLote,
    db: Session = Depends(get_db)
):

    ultimo = db.query(func.max(Corte.nro_corte)).scalar()
    siguiente_nro = (ultimo or 0) + 1

    for det in corte_lote.detalles:

        tela = db.query(Tela).filter_by(
            codigo_tela=det.codigo_tela,
            tipo=det.tipo,
            color=det.color
        ).first()

        if not tela:
            raise HTTPException(
                status_code=400,
                detail=f"Tela no existe: {det.tipo} {det.color}"
            )

        stock_items = [
            s for s in get_stock(db)
            if s.codigo_tela == det.codigo_tela
            and s.tipo == det.tipo
            and s.color == det.color
        ]

        if not stock_items:
            raise HTTPException(
                status_code=400,
                detail="Sin stock"
            )

        stock = stock_items[0]

        if det.kg_usados > stock.stock_actual_kg:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente: {stock.stock_actual_kg}"
            )

        nuevo_corte = Corte(
            nro_corte=siguiente_nro,
            fecha=datetime.utcnow(),
            codigo_tela=det.codigo_tela,
            tipo=det.tipo,
            color=det.color,
            kg_usados=det.kg_usados,
            rollos_usados=det.rollos_usados,
            observacion=corte_lote.observacion
        )

        db.add(nuevo_corte)

    db.commit()

    return {
        "mensaje": "Corte registrado",
        "numero": siguiente_nro
    }

# -------------------- FIN NUEVO --------------------

# Cortes (endpoint individual original se mantiene)
@app.post("/cortes", response_model=CorteResponse)
def crear_corte(corte: CorteCreate, db: Session = Depends(get_db)):
    tela = db.query(Tela).filter_by(
        codigo_tela=corte.codigo_tela, tipo=corte.tipo, color=corte.color
    ).first()
    if not tela:
        raise HTTPException(status_code=400, detail="Tela no existe")
    stock_items = [s for s in get_stock(db) if s.codigo_tela == corte.codigo_tela
                   and s.tipo == corte.tipo and s.color == corte.color]
    if not stock_items:
        raise HTTPException(status_code=400, detail="Sin datos de stock")
    stock = stock_items[0]
    if corte.kg_usados > stock.stock_actual_kg:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente (disponible: {stock.stock_actual_kg} kg)")
    if corte.rollos_usados > stock.rollos_disponibles:
        raise HTTPException(status_code=400, detail=f"Rollos insuficientes (disponibles: {stock.rollos_disponibles})")
    nuevo = Corte(**corte.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.get("/cortes", response_model=List[CorteResponse])
def get_cortes(db: Session = Depends(get_db)):
    return db.query(Corte).all()

# --- Nuevo endpoint para corte con detalle ---
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

@app.get("/recargar-cortes-csv")
def recargar_cortes_csv(db: Session = Depends(get_db)):
    try:

        db.query(Corte).delete()
        db.commit()

        cortes_df = pd.read_csv("cortes.csv")

        cantidad = 0

        for _, row in cortes_df.iterrows():

    obs = "" if pd.isna(row.get("observacion", "")) else str(row.get("observacion", ""))

    nro_real = int(row["nro_corte"])

    if "CORTE" in obs.upper():
        import re
        encontrado = re.search(r"N\.?\s*(\d+)", obs.upper())
        if encontrado:
            nro_real = int(encontrado.group(1))

    db.add(Corte(
        nro_corte=nro_real,
        fecha=pd.to_datetime(row["fecha"]),
        codigo_tela=float(row["codigo_tela"]),
        tipo=str(row["tipo"]),
        color=str(row["color"]),
        kg_usados=float(row["kg_usados"]),
        rollos_usados=int(row["rollos_usados"]),
        observacion=obs
    ))

    cantidad += 1

        db.commit()

        return {
            "mensaje": "Cortes recargados correctamente",
            "cantidad": cantidad
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
