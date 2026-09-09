"""Infraestructura de pruebas: BD SQLite de archivo + cliente con sesión override."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///./test_natillera.db"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB = "./test_natillera.db"


@pytest.fixture(scope="session", autouse=True)
def _db_archivo():
    _borrar_db()
    yield
    _borrar_db()


def _borrar_db():
    try:
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
    except PermissionError:
        pass  # Windows: el motor aún libera el archivo; se reintenta en la próxima corrida


@pytest.fixture()
def db():
    from app.models import Base, parametro, usuario
    from app.models import ahorrador as _m_ahorrador
    from app.models import aporte as _m_aporte
    from app.models import cuota as _m_cuota
    from app.models import prestamo as _m_prestamo
    from app.models import reparto as _m_reparto

    # Referencia explícita: registra las tablas en el metadata (no borrar;
    # cada bloque agrega aquí sus modelos).
    assert usuario.Usuario.__tablename__ == "usuarios"
    assert parametro.Parametro.__tablename__ == "parametros"
    assert _m_ahorrador.Ahorrador.__tablename__ == "ahorradores"
    assert _m_aporte.Aporte.__tablename__ == "aportes"
    assert _m_prestamo.Prestamo.__tablename__ == "prestamos"
    assert _m_cuota.Cuota.__tablename__ == "cuotas"
    assert _m_reparto.Reparto.__tablename__ == "repartos"

    motor = create_engine(
        f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=motor)
    sesion = sessionmaker(bind=motor, autoflush=False, autocommit=False)()
    try:
        yield sesion
    finally:
        sesion.close()
        Base.metadata.drop_all(bind=motor)
        motor.dispose()


@pytest.fixture()
def client(db):
    from app import deps
    from app.main import app

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[deps.get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# Re-exportadas para pasos BDD: from tests.helpers import ...
from tests.helpers import crear_usuario, login  # noqa: F401
