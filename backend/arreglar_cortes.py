from database import SessionLocal
from models import Corte
from sqlalchemy import func

db = SessionLocal()
grupos = db.query(Corte.observacion, func.min(Corte.nro_corte)).group_by(Corte.observacion).all()
for obs, min_nro in grupos:
    if obs and "CORTE" in obs.upper():
        db.query(Corte).filter(Corte.observacion == obs).update({Corte.nro_corte: min_nro})
db.commit()
print("Listo")
