-- migrations/012_multi_hash_documents.sql
-- Multi-hash para documentos (Baseline RC5.5)
-- Aplica: sqlite3 paraguasmj.db < 012_multi_hash_documents.sql

PRAGMA foreign_keys = ON;

-- Hashes multi-algoritmo por documento
CREATE TABLE IF NOT EXISTS documento_multi_hash (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id  INTEGER NOT NULL
                  REFERENCES documentos(id) ON DELETE CASCADE ON UPDATE CASCADE,
    sha256        TEXT    NOT NULL,
    sha3_256      TEXT,
    blake2b       TEXT,
    contenido_kb  REAL,
    generado_en   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    generado_por  TEXT
);

CREATE INDEX IF NOT EXISTS idx_doc_multi_hash_doc
    ON documento_multi_hash(documento_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_doc_multi_hash_sha256
    ON documento_multi_hash(sha256);

-- Control de versiones del baseline
CREATE TABLE IF NOT EXISTS baseline_control (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    version       TEXT    NOT NULL,
    profile       TEXT    NOT NULL,
    hash_modulo   TEXT,
    activado_en   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    activado_por  TEXT,
    notas         TEXT
);

-- Perfiles operativos activados en producción (histórico)
CREATE TABLE IF NOT EXISTS perfiles_operativos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    perfil        TEXT    NOT NULL,
    activado_en   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    desactivado_en TEXT,
    activado_por  TEXT
);

-- Módulos futuros pendientes de habilitación
CREATE TABLE IF NOT EXISTS future_modules (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL UNIQUE,
    descripcion   TEXT,
    habilitado    INTEGER NOT NULL DEFAULT 0,
    habilitado_en TEXT,
    habilitado_por TEXT
);

INSERT OR IGNORE INTO future_modules (nombre, descripcion) VALUES
    ('firma_digital_pkcs11', 'Firma digital con token PKCS#11'),
    ('ocr_documentos',       'OCR para documentos escaneados'),
    ('integracion_govco',    'Integración con servicios Gov.co'),
    ('notificaciones_push',  'Notificaciones push via WebSocket'),
    ('multi_tenant',         'Soporte multi-organización');
