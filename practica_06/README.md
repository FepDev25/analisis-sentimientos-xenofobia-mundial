# Práctica 6 — Extracción paralela de datos sobre xenofobia en el Mundial FIFA 2026

Materia: **Computación Paralela** · Entregable de la Práctica de laboratorio 06.

Sistema que extrae, **de forma concurrente**, comentarios y publicaciones de varias redes sociales para analizar la **xenofobia durante el Mundial FIFA 2026**.

## Problemática y diseño

- **Problemática y estrategia de búsqueda:** ver [`../ESTRATEGIA_BUSQUEDA.md`](../ESTRATEGIA_BUSQUEDA.md)
- **Contrato de datos (esquema común):** ver [`../CONTRATO.md`](../CONTRATO.md)

## Fuentes

| Fuente | Alcance | Mecanismo | Estado |
|--------|---------|-----------|--------|
| YouTube | Comentarios de videos/playlists de resúmenes | `yt-dlp` + `youtube-comment-downloader` (sin API key) | ✅ |
| TikTok | Búsqueda global por hashtag | — | ⏳ |
| X | Búsqueda global por query | — | ⏳ |
| Reddit | Por subreddit — **respaldo** de X | — | ⏳ |

> **YouTube:** se usan librerías que leen la API interna (sin API key ni cuota), justificado por la rúbrica ("librerías de terceros u otros mecanismos justificados") y mejor para grandes volúmenes. Marcado de 2 capas: los comentarios que contienen términos del léxico se etiquetan `dirigida`, el resto `amplia`.

## Paralelismo

Los extractores se lanzan **en paralelo con hilos (`threading`)** y se comunican con un controlador central mediante una **cola (`queue.Queue`)**. El scraping es I/O-bound (dominado por la espera de red), por lo que los hilos dan paralelismo real sin el costo de los procesos. Detalle en `src/extractor_mundial/orquestador.py`.

```
   Hilo X ──────►┐
   Hilo TikTok ─►│ queue.Queue ──► controlador ──► CSV/JSON (por red + consolidado)
   Hilo YouTube►┘
```

## Estructura

```
practica_06/
├── config/
│   ├── busqueda.toml        # Capa A: hashtags, selecciones, jugadores, canales, ventana
│   └── lexico.txt           # Capa B: léxico xenófobo semilla
├── src/extractor_mundial/
│   ├── contrato.py          # esquema de datos (dataclass validada)
│   ├── config.py            # carga de config/
│   ├── almacenamiento.py    # CSV por red + consolidado, dedup
│   ├── orquestador.py       # hilos + cola (núcleo del paralelismo)
│   ├── main.py              # entrypoint
│   └── extractores/         # youtube, tiktok, x, reddit (+ base común)
├── data/                    # salida (ignorada por git)
└── evidencia/               # capturas/logs para la rúbrica
```

## Uso

```bash
# Instalar dependencias / sincronizar entorno
uv sync

# Configurar credenciales
cp .env.example .env        # y rellenar las API keys

# Ejecutar la extracción paralela
uv run --env-file .env extractor-mundial
```

## Estado

Orquestador + contrato + almacenamiento funcionando. **Extractor de YouTube implementado y probado** (playlist ESPN Fans, 172 videos). Faltan TikTok y X (Reddit de respaldo). Ver `../CLAUDE.md` para el estado detallado.
