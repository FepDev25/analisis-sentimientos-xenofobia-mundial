# App FastAPI. Publica el contrato en /docs (OpenAPI) para el frontend.

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import bd, busqueda as busq, config, esquemas, sentimiento


@asynccontextmanager
async def _ciclo(app: FastAPI):
    app.state.con = bd.conectar(config.RUTA_BD)
    sentimiento.arrancar()  # carga los modelos ahora, no en la 1a busqueda
    yield
    sentimiento.apagar()
    app.state.con.close()


app = FastAPI(
    title="Plataforma de analisis de xenofobia",
    description="Extraccion concurrente por query + analisis de sentimientos.",
    version="0.1.0",
    lifespan=_ciclo,
)

# El frontend se sirve aparte durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/redes", response_model=list[str])
def redes() -> list[str]:
    return list(config.REDES_EN_VIVO)


# Abre la busqueda y devuelve su id de inmediato: la extraccion tarda decenas de
# segundos, asi que corre en segundo plano y el cliente consulta el estado.
@app.post("/busquedas", response_model=esquemas.Busqueda, status_code=202)
def crear_busqueda(cuerpo: esquemas.BusquedaNueva, tareas: BackgroundTasks):
    if cuerpo.redes:
        invalidas = set(cuerpo.redes) - set(config.REDES_EN_VIVO)
        if invalidas:
            raise HTTPException(400, f"redes no soportadas en vivo: {sorted(invalidas)}")

    con = app.state.con
    bid = bd.crear_busqueda(con, cuerpo.query)
    tareas.add_task(busq.ejecutar, con, bid, cuerpo.query, cuerpo.redes)
    return bd.obtener_busqueda(con, bid)


@app.get("/busquedas/{busqueda_id}", response_model=esquemas.Busqueda)
def obtener_busqueda(busqueda_id: int):
    b = bd.obtener_busqueda(app.state.con, busqueda_id)
    if b is None:
        raise HTTPException(404, "no existe esa busqueda")
    return b


@app.get("/busquedas/{busqueda_id}/registros", response_model=list[esquemas.Registro])
def registros(
    busqueda_id: int,
    red: str | None = None,
    limite: int = Query(200, ge=1, le=1000),
    desplazamiento: int = Query(0, ge=0),
):
    if bd.obtener_busqueda(app.state.con, busqueda_id) is None:
        raise HTTPException(404, "no existe esa busqueda")
    return bd.registros_de(app.state.con, busqueda_id, red, limite, desplazamiento)


@app.get("/busquedas/{busqueda_id}/resumen", response_model=esquemas.Resumen)
def resumen(busqueda_id: int):
    if bd.obtener_busqueda(app.state.con, busqueda_id) is None:
        raise HTTPException(404, "no existe esa busqueda")
    return bd.resumen(app.state.con, busqueda_id)
