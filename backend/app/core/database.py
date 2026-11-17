from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
except ArgumentError as exc:
    raise RuntimeError(
        "DATABASE_URL tiene un formato inválido. Debe verse así: "
        "postgresql://USUARIO:CONTRASEÑA@HOST:5432/postgres (sin espacios, sin comillas y sin corchetes). "
        "Revisa el valor en Render > Environment."
    ) from None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """Crea las tablas y agrega columnas que falten en bases creadas con versiones anteriores.

    `create_all` no modifica tablas existentes; sin esto, una base SQLite antigua falla con
    "no such column". Solo se agregan columnas nulables (no se borra ni se altera nada).
    """
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing or not column.nullable:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}'))
