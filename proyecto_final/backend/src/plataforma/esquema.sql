-- Esquema de la plataforma. Lo aplica `bd.crear_esquema()`.

PRAGMA foreign_keys = ON;

-- Una busqueda = un query del usuario, con su ciclo de vida.
CREATE TABLE IF NOT EXISTS busqueda (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    query        TEXT    NOT NULL,
    estado       TEXT    NOT NULL DEFAULT 'en_curso',
    creada_en    TEXT    NOT NULL,
    terminada_en TEXT
);

-- Un comentario/post extraido. Espeja el contrato de P6 (`contrato.Registro`).
CREATE TABLE IF NOT EXISTS registro (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    busqueda_id       INTEGER NOT NULL REFERENCES busqueda(id) ON DELETE CASCADE,
    red               TEXT    NOT NULL,
    id_externo        TEXT    NOT NULL,
    estrategia        TEXT    NOT NULL,
    criterio_busqueda TEXT,
    texto             TEXT    NOT NULL,
    idioma            TEXT,
    autor             TEXT,
    fecha_publicacion TEXT,
    url               TEXT,
    metricas          TEXT,
    fecha_extraccion  TEXT,
    -- Dedup POR BUSQUEDA, no global: el mismo tweet en dos busquedas debe verse
    -- en ambas. (P6 deduplica global porque acumula un corpus; aca cada busqueda
    -- es una vista independiente.)
    UNIQUE (busqueda_id, red, id_externo)
);

CREATE INDEX IF NOT EXISTS idx_registro_busqueda ON registro (busqueda_id);
CREATE INDEX IF NOT EXISTS idx_registro_red      ON registro (busqueda_id, red);

-- Tabla aparte porque la clasificacion ocurre despues de extraer, y puede fallar
-- o ir con retraso sin invalidar el registro.
CREATE TABLE IF NOT EXISTS sentimiento (
    registro_id INTEGER PRIMARY KEY REFERENCES registro(id) ON DELETE CASCADE,
    sentimiento TEXT,
    sent_score  REAL,
    odio        INTEGER,
    odio_score  REAL
);

-- Espeja `orquestador.ResultadoRed`: alimenta el panel de progreso por red.
CREATE TABLE IF NOT EXISTS resultado_red (
    busqueda_id INTEGER NOT NULL REFERENCES busqueda(id) ON DELETE CASCADE,
    red         TEXT    NOT NULL,
    total       INTEGER NOT NULL DEFAULT 0,
    error       TEXT,
    duracion_s  REAL,
    PRIMARY KEY (busqueda_id, red)
);
