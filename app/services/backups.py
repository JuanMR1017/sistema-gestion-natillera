"""Respaldos automáticos y periódicos (RNF-08).

SQLite/dev: copia versionada del archivo. PostgreSQL/prod: pg_dump diario.
Retención: últimas 30 copias.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "./backups"))
RETENCION = int(os.environ.get("BACKUP_RETENTION", "30"))


def _podar(patron: str) -> None:
    copias = sorted(BACKUP_DIR.glob(patron), reverse=True)
    for vieja in copias[RETENCION:]:
        vieja.unlink(missing_ok=True)


def _respaldar_sqlite(db_path: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    sello = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    destino = BACKUP_DIR / f"natillera-{sello}.db"
    shutil.copy2(db_path, destino)
    _podar("natillera-*.db")
    return destino


def _respaldar_postgres(database_url: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    sello = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    destino = BACKUP_DIR / f"natillera-{sello}.dump"
    with open(destino, "wb") as fh:
        subprocess.run(
            ["pg_dump", database_url], stdout=fh, check=True, timeout=600,
        )
    _podar("natillera-*.dump")
    return destino


def run_backup(database_url: str | None = None) -> Path:
    url = database_url or os.environ.get("DATABASE_URL", "sqlite:///./natillera.db")
    if url.startswith("sqlite") and url != "sqlite:///:memory:":
        return _respaldar_sqlite(url.split("sqlite:///", 1)[1] or "natillera.db")
    return _respaldar_postgres(url)
