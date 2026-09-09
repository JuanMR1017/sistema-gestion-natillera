"""Ayudas compartidas de pruebas (usuarios y login)."""

from __future__ import annotations


def crear_usuario(db, username: str, password: str = "clave123", rol: str = "Ahorrador"):
    from app import deps
    from app.models.usuario import Usuario

    u = Usuario(username=username, password_hash=deps.hash_password(password), rol=rol)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def login(client, username: str, password: str = "clave123"):
    return client.post("/login", data={"username": username, "password": password})
