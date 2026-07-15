#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.." || exit 1   # → practica_06/

# ── Parámetros (ajustables) ──
BURST=2            # queries por ciclo (ráfaga chica = huella baja)
PAUSA=12           # segundos entre queries dentro de la ráfaga
POR_QUERY=200      # tope de tweets por query
ESPERA_MIN=45      # minutos de espera ENTRE ciclos (el anti-throttle real)
ESPERA_INI_MIN=30  # minutos de espera inicial (venimos throttled)
MAX_CICLOS=24      # tope de seguridad (~ toda la noche aunque nada progrese)

LOG="data/x_nocturna.log"
log(){ echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# Cuenta cuántas queries del preset otros-ejes faltan en el dataset.
pendientes(){
  uv run --group x python - <<'PY'
import re, json
from pathlib import Path
txt = Path('scripts/recoleccion_x.py').read_text()
m = re.search(r'QUERIES_OTROS_EJES\s*=\s*\[(.*?)\]', txt, re.S)
qs = [a or b for a, b in re.findall(r'"(.*?)"|\'(.*?)\'', m.group(1))]
hechas = set()
p = Path('data/dataset.jsonl')
if p.exists():
    for l in p.read_text(encoding='utf-8').splitlines():
        if not l.strip():
            continue
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get('red') == 'x' and d.get('criterio_busqueda'):
            hechas.add(d['criterio_busqueda'])
print(sum(1 for q in qs if q not in hechas))
PY
}

# Backup ÚNICO al inicio (los ciclos corren con --sin-backup para no llenar disco).
ts=$(date '+%Y%m%d_%H%M%S')
mkdir -p "data/backups/$ts"
for f in dataset.jsonl dataset.csv dataset.json; do
  [ -f "data/$f" ] && cp -p "data/$f" "data/backups/$ts/"
done
log "=== Recolección nocturna X — inicio (backup en data/backups/$ts) ==="
log "Espera inicial ${ESPERA_INI_MIN} min (dejar enfriar el throttle previo)..."
sleep $((ESPERA_INI_MIN*60))

for ((c=1; c<=MAX_CICLOS; c++)); do
  pend=$(pendientes | tail -1)
  log "Ciclo $c/$MAX_CICLOS — quedan ${pend} queries pendientes"
  if [ "${pend:-0}" -eq 0 ] 2>/dev/null; then
    log "✔ No quedan queries pendientes. Recolección completa."
    break
  fi
  log "Ciclo $c — ráfaga de hasta ${BURST} queries (pausa ${PAUSA}s, tope ${POR_QUERY}/query)"
  uv run --group x python scripts/recoleccion_x.py \
      --otros-ejes --saltar-hechos --sin-backup \
      --max-queries "$BURST" --pausa "$PAUSA" --por-query "$POR_QUERY" >>"$LOG" 2>&1
  if [ "$c" -lt "$MAX_CICLOS" ]; then
    log "Ciclo $c hecho — durmiendo ${ESPERA_MIN} min antes del próximo."
    sleep $((ESPERA_MIN*60))
  fi
done
log "=== Fin de la recolección nocturna ==="
