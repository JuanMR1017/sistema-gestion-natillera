"""Seed inicial: cuenta administradora y parámetros por defecto del fondo."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.deps import SessionLocal, hash_password
from app.models import (  # noqa: F401
    Base,
    ahorrador,
    aporte,
    cuota,
    parametro,
    prestamo,
    reparto,
    usuario,
)
from app.models.parametro import seed_defaults


def main() -> None:
    from app.deps import _engine

    Base.metadata.create_all(bind=_engine)
    db = SessionLocal()
    try:
        if db.query(usuario.Usuario).filter_by(username="admin").first() is None:
            db.add(
                usuario.Usuario(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    rol=usuario.ROL_ADMINISTRADOR,
                )
            )
            db.commit()
            print("admin creado (admin/admin123 — cambiar en producción)")
        seed_defaults(db, datetime.now(UTC).date(), autor="seed")
        print("parámetros por defecto listos")
    finally:
        db.close()


if __name__ == "__main__":
    main()
