"""
Descarga los estados financieros publicos de la Superintendencia de Companias,
Valores y Seguros (SCVS) y genera tablas limpias de los FONDOS DE INVERSION
para Power BI.

Fuente (publica, sin login ni captcha):
  https://mercadodevalores.supercias.gob.ec/reportes/balancesConsolidadosMv.jsf
  -> archivo zip con todos los balances de entes de mercado de valores.

Uso:
  python scripts/actualizar_datos.py            # descarga y procesa
  python scripts/actualizar_datos.py --local X  # procesa un zip ya descargado

Salidas (carpeta datos/):
  fondos_patrimonio_mensual.csv  -> 1 fila por fondo y mes (patrimonio, activo, pasivo)
  fondos_composicion_mensual.csv -> 1 fila por fondo, mes e instrumento (renta fija / variable)
  fondos.csv                     -> dimension de fondos (RUC, nombre, administradora)
  ultima_actualizacion.txt
"""
import argparse
import csv
import datetime as dt
import io
import os
import sys
import urllib.request
import zipfile

URL_ZIP = "https://mercadodevalores.supercias.gob.ec/reportes/zip/balancesConsolidadosMv.zip"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
MAPEO = os.path.join(RAIZ, "config", "fondos_administradoras.csv")

# Instrumentos de inversion (codigo de cuenta sin puntos, sufijo despues de la categoria)
INSTRUMENTOS = {
    "0101": "Acciones y participaciones",
    "0102": "Cuotas de fondos colectivos",
    "0103": "Titularizacion de participacion",
    "0201": "Avales",
    "0202": "Bonos del Estado",
    "0206": "Certificados de inversion",
    "0207": "Certificados de tesoreria",
    "0208": "Certificados de deposito",
    "0209": "Cupones",
    "0210": "Depositos a plazo",
    "0213": "Obligaciones",
    "0216": "Obligaciones convertibles",
    "0217": "Papel comercial",
    "0219": "Polizas de acumulacion",
    "0220": "Titulos del Banco Central",
    "0221": "Titularizaciones",
    "0223": "Otros",
}
GRUPO_INSTRUMENTO = {
    "Bonos del Estado": "Deuda Publica",
    "Certificados de tesoreria": "Deuda Publica",
    "Titulos del Banco Central": "Deuda Publica",
    "Cupones": "Deuda Publica",
    "Obligaciones": "Obligaciones",
    "Obligaciones convertibles": "Obligaciones",
    "Papel comercial": "Papel Comercial",
    "Titularizaciones": "Titularizaciones",
    "Titularizacion de participacion": "Titularizaciones",
    "Certificados de deposito": "Depositos Bancarios",
    "Certificados de inversion": "Depositos Bancarios",
    "Depositos a plazo": "Depositos Bancarios",
    "Polizas de acumulacion": "Depositos Bancarios",
    "Avales": "Depositos Bancarios",
    "Acciones y participaciones": "Renta Variable",
    "Cuotas de fondos colectivos": "Renta Variable",
    "Otros": "Otros",
}


def numero(txt):
    txt = txt.strip()
    if not txt:
        return 0.0
    return float(txt.replace(".", "").replace(",", "."))


def fecha_iso(txt):
    return dt.datetime.strptime(txt.strip(), "%d/%m/%Y").date().isoformat()


def descargar(destino):
    print(f"Descargando {URL_ZIP} ...")
    req = urllib.request.Request(URL_ZIP, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=1800) as r, open(destino, "wb") as f:
        while True:
            bloque = r.read(1 << 20)
            if not bloque:
                break
            f.write(bloque)
    print(f"  ok ({os.path.getsize(destino) / 1e6:.0f} MB)")


def cargar_mapeo():
    mapeo = {}
    if os.path.exists(MAPEO):
        with open(MAPEO, encoding="utf-8-sig") as f:
            for fila in csv.DictReader(f):
                mapeo[fila["ruc_fondo"].strip()] = fila
    return mapeo


def procesar(ruta_zip):
    os.makedirs(DATOS, exist_ok=True)
    patrimonio = {}   # (ruc, fecha) -> dict
    composicion = {}  # (ruc, fecha, instrumento, clasificacion) -> valor
    fondos = {}       # ruc -> nombre mas reciente

    with zipfile.ZipFile(ruta_zip) as z:
        nombre = z.namelist()[0]
        with z.open(nombre) as crudo:
            texto = io.TextIOWrapper(crudo, encoding="latin-1", newline="")
            for linea in texto:
                c = linea.rstrip("\r\n").split("\t")
                if len(c) < 9 or not c[1].startswith("FONDO DE INVERSI"):
                    continue
                if c[5].strip() != "MENSUAL":
                    continue
                ruc, nom, fecha = c[2].strip(), c[3].strip(), fecha_iso(c[4])
                cuenta = c[6].replace(".", "").strip()
                valor = numero(c[8])

                if ruc not in fondos or fecha >= fondos[ruc][1]:
                    fondos[ruc] = (nom, fecha)

                clave = (ruc, fecha)
                if cuenta in ("1", "2", "3"):
                    reg = patrimonio.setdefault(clave, {"activo": 0.0, "pasivo": 0.0, "patrimonio": 0.0})
                    reg[{"1": "activo", "2": "pasivo", "3": "patrimonio"}[cuenta]] = valor
                # Inversiones: 10102 01|02|03 (clasificacion) 01|02 (variable|fija) NN (instrumento)
                elif cuenta.startswith("10102") and len(cuenta) == 11 and cuenta[5:7] in ("01", "02", "03"):
                    inst = INSTRUMENTOS.get(cuenta[7:11])
                    if inst:
                        k = (ruc, fecha, inst)
                        composicion[k] = composicion.get(k, 0.0) + valor

    mapeo = cargar_mapeo()
    ultimo = max(f for (_, f) in patrimonio)

    def admin_de(ruc):
        m = mapeo.get(ruc)
        if m and m.get("administradora"):
            return m["administradora"].strip()
        # Fondos que ya no reportan (liquidados) no necesitan administradora asignada
        return "FONDOS CERRADOS" if fondos[ruc][1] < ultimo else "SIN ASIGNAR"

    with open(os.path.join(DATOS, "fondos.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ruc_fondo", "fondo", "nombre_corto", "administradora", "plazo_permanencia", "tipo_fondo", "ultimo_reporte"])
        for ruc, (nom, ult) in sorted(fondos.items(), key=lambda x: x[1][0]):
            m = mapeo.get(ruc, {})
            w.writerow([ruc, nom, m.get("nombre_corto", ""), admin_de(ruc),
                        m.get("plazo_permanencia", ""), m.get("tipo_fondo", ""), ult])

    with open(os.path.join(DATOS, "fondos_patrimonio_mensual.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ruc_fondo", "fecha", "administradora", "activo", "pasivo", "patrimonio"])
        for (ruc, fecha), r in sorted(patrimonio.items(), key=lambda x: (x[0][1], x[0][0])):
            w.writerow([ruc, fecha, admin_de(ruc), round(r["activo"], 2), round(r["pasivo"], 2), round(r["patrimonio"], 2)])

    with open(os.path.join(DATOS, "fondos_composicion_mensual.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ruc_fondo", "fecha", "administradora", "instrumento", "grupo_instrumento", "valor"])
        for (ruc, fecha, inst), v in sorted(composicion.items(), key=lambda x: (x[0][1], x[0][0], x[0][2])):
            if v:
                w.writerow([ruc, fecha, admin_de(ruc), inst, GRUPO_INSTRUMENTO[inst], round(v, 2)])

    sin_asignar = [ruc for ruc, (_, ult) in fondos.items() if ult == ultimo and ruc not in mapeo]
    with open(os.path.join(DATOS, "ultima_actualizacion.txt"), "w", encoding="utf-8") as f:
        f.write(f"Procesado: {dt.datetime.now():%Y-%m-%d %H:%M}\nUltimo mes disponible en SCVS: {ultimo}\n")

    print(f"Fondos: {len(fondos)} | meses-fondo: {len(patrimonio)} | ultimo mes: {ultimo}")
    if sin_asignar:
        print(f"ATENCION: {len(sin_asignar)} fondos vigentes sin administradora en config/fondos_administradoras.csv:")
        for ruc in sin_asignar:
            print(f"   {ruc}  {fondos[ruc][0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="ruta a un zip ya descargado")
    a = ap.parse_args()
    ruta = a.local
    if not ruta:
        ruta = os.path.join(DATOS, "_descarga_scvs.zip")
        os.makedirs(DATOS, exist_ok=True)
        descargar(ruta)
    procesar(ruta)


if __name__ == "__main__":
    sys.exit(main())
