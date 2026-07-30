-- migrations/013_expedientes.sql
-- Crea tabla expedientes y vincula registro_central
-- Aplica: sqlite3 paraguasmj.db < 013_expedientes.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS expedientes (
    pk_expediente_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_expediente TEXT    NOT NULL UNIQUE,
    nombre            TEXT    NOT NULL,
    descripcion       TEXT,
    estado            TEXT    NOT NULL DEFAULT 'Activo'
                      CHECK(estado IN ('Activo', 'Cerrado', 'Archivado')),
    fase_archivo      TEXT    NOT NULL DEFAULT 'Gestion'
                      CHECK(fase_archivo IN ('Gestion', 'Central', 'Historico')),
    creado_por        TEXT,
    fecha_creacion    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

CREATE INDEX IF NOT EXISTS idx_expedientes_estado
    ON expedientes(estado);

-- Columna que vincula documentos a un expediente (nullable — documentos existentes no se ven afectados)
ALTER TABLE registro_central ADD COLUMN fk_expediente_id INTEGER
    REFERENCES expedientes(pk_expediente_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_reg_central_expediente
    ON registro_central(fk_expediente_id)
    WHERE fk_expediente_id IS NOT NULL;
