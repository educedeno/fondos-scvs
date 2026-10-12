"""
Descarga el RESUMEN DIARIO de cada fondo de inversion vigente desde el catastro
publico de la SCVS (valor de la unidad, participes, activo y patrimonio por dia)
y calcula el rendimiento de cada fondo.

Fuente (publica, sin login):
  https://appscvsgen.supercias.gob.ec/consultaCompanias/mercadoValores/catastroEntesMv.jsf
  -> Fondos de inversion -> detalle de cada fondo -> Resumen diario -> EXCEL

El portal no tiene un link fijo: cada pagina se abre con un codigo que caduca,
asi que el programa navega igual que una persona (catastro -> listado -> fondo).

Uso:
  python scripts/actualizar_diario.py             # todos los fondos vigentes
  python scripts/actualizar_diario.py --max 3     # prueba rapida con 3 fondos

Salidas (carpeta datos/):
  fondos_catastro.csv     -> listado oficial de fondos (vigentes y cancelados)
  fondos_diario.csv       -> 1 fila por fondo y dia
  fondos_rendimiento.csv  -> rendimiento anualizado de cada fondo a la ultima fecha
  ultima_actualizacion_diario.txt

Si un fondo no se puede descargar, se conservan sus datos anteriores.
"""
import argparse
import csv
import datetime as dt
import html
import http.cookiejar
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

HOST = "https://appscvsgen.supercias.gob.ec"
BASE = HOST + "/consultaCompanias/mercadoValores"
# El firewall de la SCVS rechaza peticiones que no parecen de un navegador
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
BOTON_FONDOS = "frmCatastroEntesMv:j_idt70"  # icono "Fondos de inversion" del catastro
TABLA = "frmListadoEntesMv:tblEntesMv"
FILAS_POR_PAGINA = 15

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
MAPEO = os.path.join(RAIZ, "config", "fondos_administradoras.csv")

COLUMNAS_DIARIO = ["ruc_fondo", "fecha", "valor_unidad", "unidades", "participes",
                   "participes_naturales", "participes_juridicas", "activo", "patrimonio"]
# Encabezados del Excel de la SCVS. Los fondos colectivos dicen "cuota" y "cuotahabientes".
ENCABEZADOS = [
    ("fecha", r"^FECHA DE CORTE"),
    ("valor_unidad", r"^VALOR DE LA (UNIDAD|CUOTA)"),
    ("unidades", r"^N.MERO TOTAL DE (UNIDADES|CUOTAS)"),
    ("participes", r"^N.MERO TOTAL DE (PART.CIPES|CUOTAHAB)"),
    ("participes_naturales", r"^N.MERO (DE PART.CIPES|CUOTAHAB\w*) PERSONAS NATURALES"),
    ("participes_juridicas", r"^N.MERO (DE PART.CIPES|CUOTAHAB\w*) PERSONAS JUR.DICAS"),
    ("activo", r"^ACTIVO TOTAL"),
    ("patrimonio", r"^PATRIMONIO NETO"),
]
# Rendimiento anualizado sobre estos plazos (dias calendario)
PLAZOS = [("rend_30d", 30), ("rend_90d", 90), ("rend_180d", 180), ("rend_365d", 365)]


class ErrorPortal(Exception):
    pass


class Portal:
    """Sesion con el portal JSF/PrimeFaces de la SCVS."""

    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self, url, params=None):
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-EC,es;q=0.9"})
        with self.op.open(req, timeout=60) as r:
            return r.geturl(), r.read()

    def ajax(self, pagina, form, fuente, extra=None):
        """Simula un clic de PrimeFaces. pagina = dict(url, action, viewstate); actualiza el viewstate."""
        datos = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": fuente,
            "javax.faces.partial.execute": fuente,
            fuente: fuente,
            form: form,
            "javax.faces.ViewState": pagina["viewstate"],
        }
        datos.update(extra or {})
        req = urllib.request.Request(
            HOST + pagina["action"], data=urllib.parse.urlencode(datos).encode(),
            headers={"User-Agent": UA, "Referer": pagina["url"], "Origin": HOST,
                     "Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest",
                     "Accept": "application/xml, text/xml, */*; q=0.01",
                     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        with self.op.open(req, timeout=60) as r:
            xml = r.read().decode("utf-8", "replace")
        if "<partial-response" not in xml:
            raise ErrorPortal("respuesta inesperada del portal (posible bloqueo del firewall)")
        m = re.search(r'ViewState:0"><!\[CDATA\[([^\]]+)', xml)
        if m:
            pagina["viewstate"] = m.group(1)
        m = re.search(r'<extension ln="primefaces" type="args">(.*?)</extension>', xml)
        args = json.loads(m.group(1)) if m else {}
        if args.get("presentarPopupCaptcha"):
            raise ErrorPortal("el portal pidio captcha")
        return xml, args

    def pagina(self, url, params=None, form=None):
        url, cuerpo = self.get(url, params)
        texto = cuerpo.decode("utf-8", "replace")
        if "caducado" in texto:
            raise ErrorPortal("el codigo de acceso caduco")
        vs = re.search(r'javax.faces.ViewState:0" value="([^"]+)', texto)
        act = re.search(r'<form id="%s"[^>]*action="([^"]+)' % re.escape(form), texto) if form else None
        if not vs or (form and not act):
            raise ErrorPortal(f"pagina inesperada: {url}")
        return {"url": url, "html": texto, "viewstate": vs.group(1),
                "action": html.unescape(act.group(1)) if act else None}


def parametro(args):
    p = args.get("parametro")
    if not args.get("procesamientoCorrecto") or not p:
        raise ErrorPortal("el portal no devolvio el codigo de acceso")
    return p


def abrir_listado(portal):
    """Catastro -> Fondos de inversion -> listado (dos redirecciones con codigo temporal)."""
    cat = portal.pagina(BASE + "/catastroEntesMv.jsf", form="frmCatastroEntesMv")
    _, args = portal.ajax(cat, "frmCatastroEntesMv", BOTON_FONDOS)
    F = "frmListadoEntesMvPreliminar"
    pre = portal.pagina(BASE + "/listadoEntesMvPreliminar.jsf", {"p": parametro(args)}, form=F)
    _, args = portal.ajax(pre, F, F + ":cmdlnkListadoEntesMvPreliminar", {
        F + ":browser": "Chrome", F + ":altoBrowser": "900", F + ":anchoBrowser": "1600",
        F + ":menuDispositivoMovil": "hidden"})
    # El codigo viene como "?p=..." y el portal lo espera sin codificar
    return portal.pagina(BASE + "/listadoEntesMv.jsf" + parametro(args), form="frmListadoEntesMv")


def texto_celda(c):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())


def filas_tabla(fragmento):
    """Filas del listado: (indice, [identificacion, nombre, administradora, inscripcion, fecha, estado, localidad, sector], id_boton)."""
    filas = []
    for m in re.finditer(r'<tr data-ri="(\d+)"[^>]*>(.*?)</tr>', fragmento, re.S):
        celdas = [texto_celda(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(2), re.S)]
        # boton "Consultar detalle" de la fila
        boton = re.search(r'id="(%s:%s:[^"]+)"[^>]*onclick="[^"]*handleMostrarPaginaInformacionEnteMv'
                          % (re.escape(TABLA), m.group(1)), m.group(2))
        if len(celdas) >= 8 and boton:
            filas.append((int(m.group(1)), celdas[:8], boton.group(1)))
    return filas


def ir_a_pagina(portal, listado, n):
    """Pagina n (desde 0) del listado; devuelve sus filas."""
    if n == 0:
        return filas_tabla(listado["html"])
    xml, _ = portal.ajax(listado, "frmListadoEntesMv", TABLA, {
        "javax.faces.partial.render": TABLA,
        TABLA + "_pagination": "true", TABLA + "_first": str(n * FILAS_POR_PAGINA),
        TABLA + "_rows": str(FILAS_POR_PAGINA), TABLA + "_skipChildren": "true",
        TABLA + "_encodeFeature": "true"})
    return filas_tabla(xml)


def leer_xlsx(contenido):
    """Lee la primera hoja de un .xlsx sin librerias externas. Devuelve lista de filas (listas de texto)."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        compartidos = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
                compartidos.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
        hoja = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        filas = []
        for row in ET.fromstring(z.read(hoja)).iter("{%s}row" % ns["m"]):
            fila = {}
            for c in row.findall("m:c", ns):
                col = re.match(r"[A-Z]+", c.get("r")).group(0)
                idx = 0
                for ch in col:
                    idx = idx * 26 + ord(ch) - 64
                tipo = c.get("t")
                if tipo == "inlineStr":
                    val = "".join(t.text or "" for t in c.iter("{%s}t" % ns["m"]))
                else:
                    v = c.find("m:v", ns)
                    val = v.text if v is not None else ""
                    if tipo == "s" and val:
                        val = compartidos[int(val)]
                fila[idx - 1] = (val or "").strip()
            filas.append([fila.get(i, "") for i in range(max(fila) + 1)] if fila else [])
        return filas


def interpretar_resumen(filas, ruc):
    """Convierte el Excel de 'Resumen diario' en filas con COLUMNAS_DIARIO."""
    for i, fila in enumerate(filas):
        if fila and fila[0].upper().startswith("FECHA DE CORTE"):
            break
    else:
        raise ErrorPortal("el Excel no tiene la tabla esperada")
    posicion = {}
    for j, enc in enumerate(filas[i]):
        for nombre, patron in ENCABEZADOS:
            if nombre not in posicion and re.search(patron, enc.upper()):
                posicion[nombre] = j
    faltan = [n for n, _ in ENCABEZADOS if n not in posicion]
    if faltan:
        raise ErrorPortal(f"columnas no encontradas en el Excel: {faltan}")
    salida = {}
    for fila in filas[i + 1:]:
        if not fila or not re.match(r"\d{4}/\d{2}/\d{2}", fila[0]):
            continue
        reg = {"ruc_fondo": ruc, "fecha": fila[0][:10].replace("/", "-")}
        for nombre, _ in ENCABEZADOS[1:]:
            txt = fila[posicion[nombre]] if posicion[nombre] < len(fila) else ""
            reg[nombre] = float(txt) if txt else 0.0
        salida[reg["fecha"]] = reg  # si la SCVS repite una fecha, queda la ultima
    return [salida[f] for f in sorted(salida)]


def descargar_resumen(portal, listado, boton, ruc):
    """Abre el detalle del fondo, entra a 'Resumen diario' y descarga su Excel."""
    _, args = portal.ajax(listado, "frmListadoEntesMv", boton)
    det = portal.pagina(BASE + "/informacionEntesMv.jsf",
                        {"p": parametro(args), "o": args.get("origen", "")}, form="frmMenuMovil")
    det["action"] = html.unescape(re.search(r'<form id="frmMenuMovil"[^>]*action="([^"]+)', det["html"]).group(1))
    xml, _ = portal.ajax(det, "frmMenuMovil", "frmMenuMovil:menuResumenDiario", {
        "javax.faces.partial.render": "frmInformacionEntesMv:panelGroupInformacionEntesMv frmCaptcha:panelCaptcha"})
    excel = None
    for m in re.finditer(r'<button id="(frmInformacionEntesMv:[^"]+)"(.*?)</button>', xml, re.S):
        if "EXCEL" in texto_celda(m.group(2)).upper():
            excel = m.group(1)
    if not excel:
        raise ErrorPortal("no se encontro el boton EXCEL del resumen diario")
    act = re.search(r'<form id="frmInformacionEntesMv"[^>]*action="([^"]+)', det["html"])
    det_inf = dict(det, action=html.unescape(act.group(1)))
    _, args = portal.ajax(det_inf, "frmInformacionEntesMv", excel)
    ruta = args.get("rutaArchivoExcel")
    if not ruta:
        raise ErrorPortal("el portal no genero el Excel")
    _, contenido = portal.get(ruta)
    return interpretar_resumen(leer_xlsx(contenido), ruc)


def cargar_mapeo():
    mapeo = {}
    if os.path.exists(MAPEO):
        with open(MAPEO, encoding="utf-8-sig") as f:
            for fila in csv.DictReader(f):
                mapeo[fila["ruc_fondo"].strip()] = fila
    return mapeo


def leer_diario_anterior():
    ruta = os.path.join(DATOS, "fondos_diario.csv")
    previo = {}
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8-sig") as f:
            for fila in csv.DictReader(f):
                previo.setdefault(fila["ruc_fondo"], []).append(fila)
    return previo


def numero_csv(v):
    return f"{v:.8f}".rstrip("0").rstrip(".") if isinstance(v, float) else v


def rendimientos(filas):
    """Rendimiento anualizado simple (base 365) del valor de la unidad a la ultima fecha."""
    validas = [f for f in filas if float(f["valor_unidad"]) > 0]
    if not validas:
        return None
    # Un fondo nuevo publica un valor de unidad provisional (1 o 100) mientras su patrimonio es 0.
    # El rendimiento se mide desde el primer dia con patrimonio, para no leer ese salto como ganancia.
    arranque = next((i for i, f in enumerate(validas) if float(f["patrimonio"] or 0) > 0), None)
    serie = [(dt.date.fromisoformat(f["fecha"]), float(f["valor_unidad"])) for f in validas[arranque or 0:]]
    corte, vu = serie[-1]
    res = {"fecha_corte": corte.isoformat(), "valor_unidad": vu,
           "patrimonio": validas[-1]["patrimonio"], "participes": validas[-1]["participes"]}
    if arranque is None:
        serie = []  # nunca tuvo patrimonio: sin rendimiento

    def valor_en(fecha):
        # ultimo valor publicado en o antes de la fecha (fines de semana y feriados no se publican)
        previos = [v for d, v in serie if d <= fecha]
        return previos[-1] if previos and serie[0][0] <= fecha else None

    for nombre, dias in PLAZOS:
        base = valor_en(corte - dt.timedelta(days=dias))
        res[nombre] = round((vu / base - 1) * 365 / dias, 6) if base else ""
    inicio = dt.date(corte.year - 1, 12, 31)
    base = valor_en(inicio)
    dias = (corte - inicio).days
    res["rend_anio_corrido"] = round((vu / base - 1) * 365 / dias, 6) if base and dias > 0 else ""
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, help="descargar solo N fondos (para pruebas)")
    ap.add_argument("--pausa", type=float, default=3.0, help="segundos entre fondos (el firewall de la SCVS bloquea si se piden muy rapido)")
    a = ap.parse_args()
    os.makedirs(DATOS, exist_ok=True)

    portal = Portal()
    listado = abrir_listado(portal)
    total = int(re.search(r"rowCount:(\d+)", listado["html"]).group(1))
    paginas = (total + FILAS_POR_PAGINA - 1) // FILAS_POR_PAGINA
    print(f"Catastro SCVS: {total} fondos en {paginas} paginas")

    catastro, nuevos, fallidos = [], {}, []
    detener = False  # captcha o portal sin responder: no insistir
    seguidos = 0     # fondos fallidos consecutivos
    for n in range(paginas):
        if detener:
            break  # el catastro queda incompleto y no se sobrescribe
        filas = None
        for intento in range(3):
            try:
                if intento:
                    # sesion nueva por si la anterior quedo invalida
                    time.sleep(5 * intento)
                    portal = Portal()
                    listado = abrir_listado(portal)
                filas = ir_a_pagina(portal, listado, n)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  pagina {n + 1}: {e}; reintentando")
        if filas is None:
            print(f"ATENCION: no se pudo leer la pagina {n + 1} del listado. Se conservan los datos anteriores de los fondos que falten.")
            break
        for _, celdas, boton in filas:
            catastro.append(celdas)
            ruc, nombre, estado = celdas[0], celdas[1], celdas[5]
            if estado != "VIGENTE" or detener or (a.max and len(nuevos) + len(fallidos) >= a.max):
                continue
            for intento in range(3):
                try:
                    if intento:
                        # sesion nueva por si la anterior quedo invalida
                        time.sleep(5 * intento)
                        portal = Portal()
                        listado = abrir_listado(portal)
                        ir_a_pagina(portal, listado, n)
                    datos = descargar_resumen(portal, listado, boton, ruc)
                    nuevos[ruc] = datos
                    ultimo = datos[-1]["fecha"] if datos else "sin datos"
                    print(f"  ok  {ruc}  {nombre[:60]:60}  {len(datos):5} dias, ultimo {ultimo}")
                    break
                except Exception as e:  # noqa: BLE001
                    if "captcha" in str(e):
                        # No insistir: se conservan los datos anteriores de los fondos que falten
                        print(f"ATENCION: {e}. Se dejan de descargar fondos por hoy.")
                        detener = True
                        break
                    print(f"  ... {ruc}: {e}; reintentando")
            if ruc not in nuevos:
                fallidos.append(f"{ruc} {nombre}")
                seguidos += 1
                if seguidos >= 3 and not detener:
                    print("ATENCION: 3 fondos seguidos fallaron; el portal no responde o bloqueo las consultas. "
                          "Se dejan de descargar fondos por hoy y se conservan los datos anteriores.")
                    detener = True
            else:
                seguidos = 0
            time.sleep(a.pausa)

    if not nuevos:
        raise ErrorPortal("no se pudo descargar ningun fondo")

    mapeo = cargar_mapeo()

    def admin_de(ruc):
        m = mapeo.get(ruc)
        return m["administradora"].strip() if m and m.get("administradora") else "SIN ASIGNAR"

    # Si la descarga se corto (captcha/prueba), el catastro puede venir incompleto: no se sobrescribe.
    if len(catastro) == total:
        with open(os.path.join(DATOS, "fondos_catastro.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["ruc_fondo", "fondo", "administradora", "administradora_legal", "tipo_fondo",
                        "estado", "no_inscripcion", "fecha_inscripcion", "localidad", "sector"])
            for c in sorted(catastro, key=lambda c: (c[5] != "VIGENTE", c[1])):
                tipo = "Colectivo" if "COLECTIVO" in c[1].upper() else "Administrado"
                w.writerow([c[0], c[1], admin_de(c[0]), c[2], tipo, c[5], c[3], c[4], c[6], c[7]])

    # Fondos que fallaron hoy conservan lo que ya habia
    diario = leer_diario_anterior()
    for ruc, filas in nuevos.items():
        diario[ruc] = [{k: numero_csv(v) for k, v in fila.items()} for fila in filas]
    todas = sorted((fila for filas in diario.values() for fila in filas), key=lambda r: (r["fecha"], r["ruc_fondo"]))
    with open(os.path.join(DATOS, "fondos_diario.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_DIARIO, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(todas)

    ultima = max(r["fecha"] for r in todas)
    # Fondos que dejaron de reportar hace mas de 15 dias no cuentan en los totales del mercado
    limite = (dt.date.fromisoformat(ultima) - dt.timedelta(days=15)).isoformat()
    with open(os.path.join(DATOS, "fondos_rendimiento.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ruc_fondo", "administradora", "fecha_corte", "al_dia", "valor_unidad", "patrimonio", "participes"]
                   + [n for n, _ in PLAZOS] + ["rend_anio_corrido"])
        for ruc in sorted(diario):
            r = rendimientos(diario[ruc])
            if r:
                w.writerow([ruc, admin_de(ruc), r["fecha_corte"], "SI" if r["fecha_corte"] >= limite else "NO",
                            r["valor_unidad"], r["patrimonio"], r["participes"]]
                           + [r[n] for n, _ in PLAZOS] + [r["rend_anio_corrido"]])

    with open(os.path.join(DATOS, "ultima_actualizacion_diario.txt"), "w", encoding="utf-8") as f:
        f.write(f"Procesado: {dt.datetime.now():%Y-%m-%d %H:%M}\nUltimo dia disponible en SCVS: {ultima}\n"
                f"Fondos descargados hoy: {len(nuevos)}\n")
        if fallidos:
            f.write("No se pudieron descargar (se conservan sus datos anteriores):\n")
            f.writelines(f"  {x}\n" for x in fallidos)

    print(f"Fondos descargados: {len(nuevos)} | filas diarias: {len(todas)} | ultimo dia: {ultima}")
    sin_asignar = [r for r in nuevos if r not in mapeo]
    if sin_asignar:
        print(f"ATENCION: {len(sin_asignar)} fondos vigentes sin administradora en config/fondos_administradoras.csv:")
        for ruc in sin_asignar:
            print(f"   {ruc}")
    if fallidos:
        print(f"ATENCION: {len(fallidos)} fondos no se pudieron descargar:")
        for x in fallidos:
            print(f"   {x}")


if __name__ == "__main__":
    sys.exit(main())
