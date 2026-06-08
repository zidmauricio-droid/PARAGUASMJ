-- 014_baseline_metadata.sql
-- Agrega columna baseline_metadata a registro_central para trazabilidad arquitectonica.
-- Almacena JSON {baseline_id, core_version, extensions_enabled} en cada documento.
-- Garantia: verificable en 5/10/20 anios sin sistema activo.

ALTER TABLE registro_central
    ADD COLUMN baseline_metadata TEXT DEFAULT '{"baseline_id":"PARAGUASMJ-RC5.5-20260607","core_version":"RC5.5","extensions_enabled":[]}';
