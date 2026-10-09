"""
Genera dashboard/Panorama_Fondos.html (un solo archivo, se abre con doble clic)
a partir de los CSV de la carpeta datos/.

Uso:  python scripts/generar_dashboard.py
"""
import csv
import json
import os
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
SALIDA = os.path.join(RAIZ, "dashboard", "Panorama_Fondos.html")
DESDE = "2023-01-01"


def leer(nombre):
    with open(os.path.join(DATOS, nombre), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    fondos = {f["ruc_fondo"]: f for f in leer("fondos.csv")}
    pat = [r for r in leer("fondos_patrimonio_mensual.csv") if r["fecha"] >= DESDE]
    comp = [r for r in leer("fondos_composicion_mensual.csv") if r["fecha"] >= DESDE]

    usados = sorted({r["ruc_fondo"] for r in pat})
    idx = {ruc: i for i, ruc in enumerate(usados)}
    lista_fondos = []
    for ruc in usados:
        f = fondos[ruc]
        lista_fondos.append({
            "n": f["nombre_corto"] or f["fondo"],
            "a": f["administradora"],
            "p": f["plazo_permanencia"],
            "t": f["tipo_fondo"] or "Administrado",
        })

    fechas = sorted({r["fecha"] for r in pat})
    fidx = {f: i for i, f in enumerate(fechas)}
    # patrimonio[fecha_idx] = {fondo_idx: valor}
    serie = [dict() for _ in fechas]
    for r in pat:
        v = float(r["patrimonio"])
        if v:
            serie[fidx[r["fecha"]]][idx[r["ruc_fondo"]]] = round(v)

    composicion = defaultdict(lambda: defaultdict(float))
    for r in comp:
        if r["ruc_fondo"] in idx:
            composicion[(fidx[r["fecha"]], idx[r["ruc_fondo"]])][r["grupo_instrumento"]] += float(r["valor"])
    comp_out = [[fi, fo, {k: round(v) for k, v in d.items()}] for (fi, fo), d in composicion.items()]

    with open(os.path.join(DATOS, "ultima_actualizacion.txt"), encoding="utf-8") as f:
        actualizado = f.read().strip().splitlines()[0].replace("Procesado: ", "")

    datos = {"fechas": fechas, "fondos": lista_fondos, "serie": serie, "comp": comp_out, "actualizado": actualizado}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "plantilla_dashboard.html"), encoding="utf-8") as f:
        html = f.read()
    html = html.replace("/*__DATOS__*/null", json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard generado: {SALIDA} ({os.path.getsize(SALIDA) / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
