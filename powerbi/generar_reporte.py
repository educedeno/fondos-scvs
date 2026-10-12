"""
Genera las paginas del reporte Power BI (formato PBIR) dentro de Fondos_Mercado.Report,
con la marca de AFP Genesis (logo y colores de fondosgenesis.com).
Power BI Desktop debe estar CERRADO al correrlo.

Uso: python powerbi/generar_reporte.py
"""
import json
import os
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
REPORTE = os.path.join(AQUI, "Fondos_Mercado.Report")
PAGINAS = os.path.join(REPORTE, "definition", "pages")
RECURSOS = os.path.join(REPORTE, "StaticResources", "RegisteredResources")
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

# Paleta AFP Genesis (tomada de fondosgenesis.com)
NAVY = "#223A8F"     # color del logo
AZUL = "#16568A"     # azul corporativo
CELESTE = "#288FD4"
VERDE = "#ABCC61"
DORADO = "#EECF66"
FONDO = "#F3F5F9"
BORDE = "#DCE3EE"
TEXTO = "#3A4656"

LOGO = "logo_genesis.png"
TEMA = "TemaGenesis.json"
P = "Patrimonio"
C = "Composicion"
R = "Rendimiento"
D = "Diario"


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def color(c):
    return {"solid": {"color": lit(f"'{c}'")}}


def color_medida(tabla, nombre):
    return {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": nombre}}}}}


def campo_medida(tabla, nombre):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": nombre}}


def campo_columna(tabla, nombre):
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": nombre}}


def proy(campo, tabla, nombre, alias=None):
    p = {"field": campo, "queryRef": f"{tabla}.{nombre}", "nativeQueryRef": alias or nombre}
    if alias:
        p["displayName"] = alias
    return p


def medida(tabla, nombre, alias=None):
    return proy(campo_medida(tabla, nombre), tabla, nombre, alias)


def columna(tabla, nombre, alias=None):
    return proy(campo_columna(tabla, nombre), tabla, nombre, alias)


def marco(titulo=None, size=13):
    o = {"background": [{"properties": {"show": lit("true"), "color": color("#FFFFFF"), "transparency": lit("0D")}}],
         "border": [{"properties": {"show": lit("true"), "color": color(BORDE), "radius": lit("10D")}}],
         "subTitle": [{"properties": {"show": lit("false")}}]}
    if titulo:
        o["title"] = [{"properties": {"show": lit("true"), "text": lit(f"'{titulo}'"), "fontColor": color(NAVY),
                                      "fontSize": lit(f"{size}D"), "bold": lit("true"), "alignment": lit("'left'")}}]
    else:
        o["title"] = [{"properties": {"show": lit("false")}}]
    return o


def formato_valores(proyecciones, size="12D"):
    """Fondo amarillo suave en filas de AFP Genesis y verde/rojo en variaciones, por cada columna."""
    reglas = [{"properties": {"fontSize": lit(size)}}]
    for p in proyecciones:
        props = {"backColor": color_medida(P, "Color Fila Génesis")}
        if p["queryRef"] == "Patrimonio.Variación Mensual %":
            props["fontColor"] = color_medida(P, "Color Variación Mensual")
        if p["queryRef"] == "Patrimonio.Variación Anual %":
            props["fontColor"] = color_medida(P, "Color Variación Anual")
        reglas.append({"properties": props, "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": p["queryRef"]}})
    return reglas


def contenedor(nombre, x, y, w, h, visual, z):
    return {"$schema": VC_SCHEMA, "name": nombre,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": visual}


def texto(nombre, x, y, w, h, contenido, size, z, bold=False, col=NAVY, align="left", fondo=None):
    v = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [{
        "textRuns": [{"value": contenido, "textStyle": {"fontWeight": "bold" if bold else "normal", "fontSize": f"{size}pt", "color": col}}],
        "horizontalTextAlignment": align}]}}]}}
    if fondo:
        v["visualContainerObjects"] = {"background": [{"properties": {"show": lit("true"), "color": color(fondo), "transparency": lit("0D")}}]}
    return contenedor(nombre, x, y, w, h, v, z)


def imagen(nombre, x, y, w, h, z):
    v = {"visualType": "image", "objects": {
        "general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": LOGO}}}}}],
        "imageScaling": [{"properties": {"imageScalingType": lit("'Fit'")}}]}}
    return contenedor(nombre, x, y, w, h, v, z)


def tarjeta(nombre, x, y, w, h, p, z, col=AZUL):
    v = {"visualType": "card", "query": {"queryState": {"Values": {"projections": [p]}}},
         "objects": {"labels": [{"properties": {"color": color(col), "fontSize": lit("24D")}}],
                     "categoryLabels": [{"properties": {"fontSize": lit("11D"), "color": color(TEXTO)}}]},
         "visualContainerObjects": marco(), "drillFilterOtherVisuals": True}
    return contenedor(nombre, x, y, w, h, v, z)


def segmentador(nombre, x, y, w, h, p, z, titulo_txt, descendente=False):
    q = {"queryState": {"Values": {"projections": [p]}}}
    if descendente:
        q["sortDefinition"] = {"sort": [{"field": p["field"], "direction": "Descending"}], "isDefaultSort": False}
    v = {"visualType": "slicer", "query": q,
         "objects": {"data": [{"properties": {"mode": lit("'Dropdown'")}}],
                     "header": [{"properties": {"show": lit("true"), "text": lit(f"'{titulo_txt}'"), "fontColor": color(NAVY), "bold": lit("true")}}]},
         "visualContainerObjects": marco(), "drillFilterOtherVisuals": True}
    return contenedor(nombre, x, y, w, h, v, z)


def encabezado(subtitulo):
    """Logo + titulo + linea verde, igual en todas las paginas."""
    return [
        texto("fondoEncabezado", 0, 0, 1920, 96, " ", 8, 0, fondo="#FFFFFF"),
        imagen("logo", 24, 12, 250, 72, 1),
        texto("titulo", 300, 10, 1300, 48, "Panorama del Mercado de Fondos de Inversión", 24, 2, bold=True),
        texto("subtitulo", 300, 54, 1300, 34, subtitulo, 12, 3, col=TEXTO),
        texto("lineaVerde", 0, 96, 1920, 6, " ", 4, 4, fondo=VERDE),
    ]


def pie(y=1036, texto_corte=None):
    v = {"visualType": "card", "query": {"queryState": {"Values": {"projections": [texto_corte or medida(P, "Texto Corte")]}}},
         "objects": {"labels": [{"properties": {"fontSize": lit("11D"), "color": color(TEXTO)}}],
                     "categoryLabels": [{"properties": {"show": lit("false")}}]}}
    return contenedor("pie", 20, y, 1880, 42, v, 90)


def pagina_panorama():
    vis = encabezado("Evolución, participación de mercado y dinámica de crecimiento de las administradoras de fondos en Ecuador")
    kpis = [("kpiPatrimonio", medida(P, "Patrimonio Mercado (mil M)", "Patrimonio Mercado"), AZUL),
            ("kpiAdmins", medida(P, "Nº Administradoras", "Administradoras"), AZUL),
            ("kpiFondos", medida(P, "Nº Fondos", "Fondos Administrados"), AZUL),
            ("kpiMensual", medida(P, "Crecimiento Mensual Mercado %", "Crecimiento mensual del mercado"), AZUL),
            ("kpiAnual", medida(P, "Crecimiento Anual Mercado %", "Incremento anual del patrimonio"), AZUL),
            ("kpiGenesis", medida(P, "Share AFPGENESIS %", "Participación AFP GÉNESIS"), NAVY)]
    w = (1880 - 5 * 14) / 6
    for i, (n, p, col) in enumerate(kpis):
        vis.append(tarjeta(n, round(20 + i * (w + 14)), 116, round(w), 108, p, 10 + i, col))

    vis.append(segmentador("slMes", 20, 236, 330, 82, columna("Meses", "Mes"), 20, "Mes de corte (vacío = último)", descendente=True))
    vis.append(segmentador("slAdmin", 364, 236, 330, 82, columna("Fondos", "Administradora"), 21, "Administradora"))
    vis.append(segmentador("slFondo", 708, 236, 330, 82, columna("Fondos", "Fondo"), 22, "Fondo"))
    vis.append(segmentador("slTipo", 1052, 236, 330, 82, columna("Fondos", "Tipo de fondo"), 23, "Tipo de fondo"))
    vis.append(segmentador("slPlazo", 1396, 236, 504, 82, columna("Fondos", "Plazo de permanencia"), 24, "Plazo de permanencia"))

    valores_p1 = [medida(P, "Patrimonio Total", "Patrimonio Mes Cerrado"), medida(P, "Share %", "Share (%)"),
                  medida(P, "Variación Mensual %", "Variación Mensual %"), medida(P, "Variación Anual %", "Variación YoY %")]
    matriz = {"visualType": "pivotTable",
              "query": {"queryState": {
                  "Rows": {"projections": [columna("Fondos", "Administradora"), columna("Fondos", "Fondo")]},
                  "Values": {"projections": valores_p1}},
                  "sortDefinition": {"sort": [{"field": campo_medida(P, "Patrimonio Total"), "direction": "Descending"}], "isDefaultSort": True}},
              "objects": {"columnHeaders": [{"properties": {"backColor": color(NAVY), "fontColor": color("#FFFFFF"), "bold": lit("true"), "fontSize": lit("11D")}}],
                          "rowHeaders": [{"properties": {"fontSize": lit("12D"), "bold": lit("true"), "fontColor": color(NAVY)}}],
                          "values": formato_valores(valores_p1),
                          "total": [{"properties": {"backColor": color(AZUL), "fontColor": color("#FFFFFF")}}],
                          "subTotals": [{"properties": {"rowSubtotals": lit("true")}}],
                          "grid": [{"properties": {"rowPadding": lit("4D")}}]},
              "visualContainerObjects": marco("Ranking de Administradoras por Patrimonio", 14),
              "drillFilterOtherVisuals": True}
    vis.append(contenedor("ranking", 20, 330, 1060, 706, matriz, 30))

    evol = {"visualType": "lineChart",
            "query": {"queryState": {"Category": {"projections": [columna("Meses", "Fecha", "Mes")]},
                                     "Y": {"projections": [medida(P, "Patrimonio (últimos 24 meses)", "Patrimonio")]}}},
            "objects": {"labels": [{"properties": {"show": lit("true"), "labelDisplayUnits": lit("1000000D"), "labelPrecision": lit("0L"), "color": color(AZUL)}}],
                        "dataPoint": [{"properties": {"fill": color(CELESTE)}}],
                        "lineStyles": [{"properties": {"strokeWidth": lit("3D")}}]},
            "visualContainerObjects": marco("Evolución del Patrimonio del Mercado (US$ millones)"),
            "drillFilterOtherVisuals": True}
    vis.append(contenedor("evolucion", 1094, 330, 806, 362, evol, 40))

    share = {"visualType": "lineChart",
             "query": {"queryState": {"Category": {"projections": [columna("Meses", "Fecha", "Mes")]},
                                      "Y": {"projections": [medida(P, "Share AFPGENESIS (últimos 24 meses)", "Participación AFP GÉNESIS")]}}},
             "objects": {"dataPoint": [{"properties": {"fill": color(NAVY)}}],
                         "labels": [{"properties": {"show": lit("true"), "color": color(NAVY)}}],
                         "lineStyles": [{"properties": {"strokeWidth": lit("3D")}}]},
             "visualContainerObjects": marco("Participación de mercado · AFP GÉNESIS"),
             "drillFilterOtherVisuals": True}
    vis.append(contenedor("shareGenesis", 1094, 704, 396, 332, share, 41))

    comp = {"visualType": "clusteredBarChart",
            "query": {"queryState": {"Category": {"projections": [columna(C, "Grupo de instrumento", "Instrumento")]},
                                     "Y": {"projections": [medida(C, "% del Portafolio")]}},
                      "sortDefinition": {"sort": [{"field": campo_medida(C, "% del Portafolio"), "direction": "Descending"}], "isDefaultSort": True}},
            "objects": {"labels": [{"properties": {"show": lit("true")}}],
                        "dataPoint": [{"properties": {"fill": color(AZUL)}}]},
            "visualContainerObjects": marco("Clasificación por Instrumento"),
            "drillFilterOtherVisuals": True}
    vis.append(contenedor("composicion", 1504, 704, 396, 332, comp, 42))
    vis.append(pie())

    interacciones = [{"source": "slMes", "target": t, "type": "NoFilter"} for t in ("evolucion", "shareGenesis")]
    interacciones += [{"source": s, "target": "shareGenesis", "type": "NoFilter"} for s in ("slAdmin", "slFondo")]
    return "panorama", "Panorama del Mercado", vis, interacciones


def pagina_portafolio():
    vis = encabezado("Ranking de fondos y composición del portafolio por tipo de instrumento")
    vis[2] = texto("titulo", 300, 10, 1300, 48, "Fondos y Composición del Portafolio", 24, 2, bold=True)

    kpis = [("kpiPatrimonio", medida(P, "Patrimonio Seleccionado (M)", "Patrimonio de la selección")),
            ("kpiFondos", medida(P, "Nº Fondos", "Fondos")),
            ("kpiInvertido", medida(C, "Valor Invertido (mil M)", "Valor invertido en instrumentos")),
            ("kpiDeuda", medida(C, "% Deuda Pública", "Deuda Pública en el portafolio")),
            ("kpiPrincipal", medida(C, "Instrumento Principal", "Instrumento dominante"))]
    anchos = [330, 250, 360, 330, 554]
    x = 20
    for i, ((n, p), w) in enumerate(zip(kpis, anchos)):
        vis.append(tarjeta(n, x, 116, w, 108, p, 10 + i))
        x += w + 14

    vis.append(segmentador("slMes", 20, 236, 330, 82, columna("Meses", "Mes"), 20, "Mes de corte (vacío = último)", descendente=True))
    vis.append(segmentador("slAdmin", 364, 236, 450, 82, columna("Fondos", "Administradora"), 21, "Administradora"))
    vis.append(segmentador("slFondo", 828, 236, 450, 82, columna("Fondos", "Fondo"), 22, "Fondo"))
    vis.append(segmentador("slTipo", 1292, 236, 300, 82, columna("Fondos", "Tipo de fondo"), 23, "Tipo de fondo"))
    vis.append(segmentador("slPlazo", 1606, 236, 294, 82, columna("Fondos", "Plazo de permanencia"), 24, "Plazo de permanencia"))

    cols_p2 = [columna("Fondos", "Fondo"), columna("Fondos", "Administradora"), columna("Fondos", "Tipo de fondo", "Tipo"),
               medida(P, "Patrimonio Total", "Patrimonio"), medida(P, "Share %", "Share (%)"),
               medida(P, "Variación Mensual %", "Var. Mensual"), medida(P, "Variación Anual %", "Var. YoY")]
    tabla = {"visualType": "tableEx",
             "query": {"queryState": {"Values": {"projections": cols_p2}},
                 "sortDefinition": {"sort": [{"field": campo_medida(P, "Patrimonio Total"), "direction": "Descending"}], "isDefaultSort": True}},
             "objects": {"columnHeaders": [{"properties": {"backColor": color(NAVY), "fontColor": color("#FFFFFF"), "bold": lit("true"), "fontSize": lit("11D")}}],
                         "values": formato_valores(cols_p2),
                         "total": [{"properties": {"backColor": color(AZUL), "fontColor": color("#FFFFFF")}}],
                         "grid": [{"properties": {"rowPadding": lit("3D")}}]},
             "visualContainerObjects": marco("Ranking de Fondos por Patrimonio", 14),
             "drillFilterOtherVisuals": True}
    vis.append(contenedor("rankingFondos", 20, 330, 1060, 706, tabla, 30))

    barras = {"visualType": "clusteredBarChart",
              "query": {"queryState": {"Category": {"projections": [columna(C, "Grupo de instrumento", "Instrumento")]},
                                       "Y": {"projections": [medida(C, "% del Portafolio")]}},
                        "sortDefinition": {"sort": [{"field": campo_medida(C, "% del Portafolio"), "direction": "Descending"}], "isDefaultSort": True}},
              "objects": {"labels": [{"properties": {"show": lit("true")}}], "dataPoint": [{"properties": {"fill": color(AZUL)}}]},
              "visualContainerObjects": marco("Clasificación por Instrumento"),
              "drillFilterOtherVisuals": True}
    vis.append(contenedor("composicion", 1094, 330, 360, 362, barras, 40))

    detalle = {"visualType": "tableEx",
               "query": {"queryState": {"Values": {"projections": [
                   columna(C, "Instrumento"), medida(C, "Valor Instrumento", "Valor"), medida(C, "% del Portafolio", "%")]}},
                   "sortDefinition": {"sort": [{"field": campo_medida(C, "Valor Instrumento"), "direction": "Descending"}], "isDefaultSort": True}},
               "objects": {"columnHeaders": [{"properties": {"backColor": color(NAVY), "fontColor": color("#FFFFFF"), "bold": lit("true")}}],
                           "total": [{"properties": {"backColor": color(AZUL), "fontColor": color("#FFFFFF")}}]},
               "visualContainerObjects": marco("Detalle por Instrumento"),
               "drillFilterOtherVisuals": True}
    vis.append(contenedor("detalle", 1468, 330, 432, 362, detalle, 41))

    evol = {"visualType": "hundredPercentStackedColumnChart",
            "query": {"queryState": {"Category": {"projections": [columna("Meses", "Fecha", "Mes")]},
                                     "Series": {"projections": [columna(C, "Grupo de instrumento", "Instrumento")]},
                                     "Y": {"projections": [medida(C, "Valor Instrumento (últimos 24 meses)", "Valor")]}}},
            "objects": {"legend": [{"properties": {"show": lit("true"), "position": lit("'Bottom'")}}]},
            "visualContainerObjects": marco("Evolución de la Composición del Portafolio (últimos 24 meses)"),
            "drillFilterOtherVisuals": True}
    vis.append(contenedor("evolComposicion", 1094, 704, 806, 332, evol, 42))
    vis.append(pie())

    interacciones = [{"source": "slMes", "target": "evolComposicion", "type": "NoFilter"}]
    return "portafolio", "Fondos y Portafolio", vis, interacciones


def pagina_rendimiento():
    vis = encabezado("Valor de la unidad, rendimiento y patrimonio diario de cada fondo (resumen diario del catastro SCVS)")
    vis[2] = texto("titulo", 300, 10, 1300, 48, "Rendimiento Diario de los Fondos", 24, 2, bold=True)

    kpis = [("kpiFecha", medida(R, "Fecha Último Día", "Último día publicado"), AZUL),
            ("kpiPatrimonio", medida(R, "Patrimonio Al Día (M)", "Patrimonio al último día"), AZUL),
            ("kpiParticipes", medida(R, "Partícipes", "Partícipes"), AZUL),
            ("kpiRendMercado", medida(R, "Rend. 365 días Mercado", "Rendimiento 365 días · mercado"), AZUL),
            ("kpiRendGenesis", medida(R, "Rend. 365 días AFPGENESIS", "Rendimiento 365 días · AFP GÉNESIS"), NAVY)]
    w = (1880 - 4 * 14) / 5
    for i, (n, p, col) in enumerate(kpis):
        vis.append(tarjeta(n, round(20 + i * (w + 14)), 116, round(w), 108, p, 10 + i, col))

    vis.append(segmentador("slAdmin", 20, 236, 520, 82, columna("Fondos", "Administradora"), 20, "Administradora"))
    vis.append(segmentador("slFondo", 554, 236, 520, 82, columna("Fondos", "Fondo"), 21, "Fondo"))
    vis.append(segmentador("slTipo", 1088, 236, 380, 82, columna("Fondos", "Tipo de fondo"), 22, "Tipo de fondo"))
    vis.append(segmentador("slPlazo", 1482, 236, 418, 82, columna("Fondos", "Plazo de permanencia"), 23, "Plazo de permanencia"))

    cols = [columna("Fondos", "Fondo"), columna("Fondos", "Administradora"),
            medida(R, "Valor de la Unidad", "Valor unidad"),
            medida(R, "Rend. 30 días", "30 días"), medida(R, "Rend. 90 días", "90 días"),
            medida(R, "Rend. 180 días", "180 días"), medida(R, "Rend. 365 días", "365 días"),
            medida(R, "Rend. Año Corrido", "Año corrido"), medida(R, "Patrimonio Al Día", "Patrimonio")]
    tabla = {"visualType": "tableEx",
             "query": {"queryState": {"Values": {"projections": cols}},
                 "sortDefinition": {"sort": [{"field": campo_medida(R, "Rend. 365 días"), "direction": "Descending"}], "isDefaultSort": True}},
             "objects": {"columnHeaders": [{"properties": {"backColor": color(NAVY), "fontColor": color("#FFFFFF"), "bold": lit("true"), "fontSize": lit("11D")}}],
                         "values": formato_valores(cols),
                         "total": [{"properties": {"backColor": color(AZUL), "fontColor": color("#FFFFFF")}}],
                         "grid": [{"properties": {"rowPadding": lit("3D")}}]},
             "visualContainerObjects": marco("Rendimiento anualizado por fondo", 14),
             "drillFilterOtherVisuals": True}
    vis.append(contenedor("rankingRendimiento", 20, 330, 1060, 706, tabla, 30))

    evol = {"visualType": "lineChart",
            "query": {"queryState": {"Category": {"projections": [columna(D, "fecha", "Día")]},
                                     "Y": {"projections": [medida(D, "Patrimonio Diario (12 meses)", "Patrimonio")]}}},
            "objects": {"dataPoint": [{"properties": {"fill": color(CELESTE)}}],
                        "lineStyles": [{"properties": {"strokeWidth": lit("2D")}}]},
            "visualContainerObjects": marco("Patrimonio diario (últimos 12 meses)"),
            "drillFilterOtherVisuals": True}
    vis.append(contenedor("patrimonioDiario", 1094, 330, 806, 362, evol, 40))

    vu = {"visualType": "lineChart",
          "query": {"queryState": {"Category": {"projections": [columna(D, "fecha", "Día")]},
                                   "Y": {"projections": [medida(D, "Valor de la Unidad (12 meses)", "Valor de la unidad")]}}},
          "objects": {"dataPoint": [{"properties": {"fill": color(NAVY)}}],
                      "lineStyles": [{"properties": {"strokeWidth": lit("2D")}}]},
          "visualContainerObjects": marco("Valor de la unidad · elija un fondo en el filtro"),
          "drillFilterOtherVisuals": True}
    vis.append(contenedor("valorUnidad", 1094, 704, 806, 332, vu, 41))
    vis.append(pie(texto_corte=medida(R, "Texto Corte Diario")))
    return "rendimiento", "Rendimiento Diario", vis, []


def escribir_pagina(nombre, titulo, vis, interacciones):
    base = os.path.join(PAGINAS, nombre)
    os.makedirs(os.path.join(base, "visuals"), exist_ok=True)
    nombres = {v["name"] for v in vis}
    for d in os.listdir(os.path.join(base, "visuals")):
        if d not in nombres:
            shutil.rmtree(os.path.join(base, "visuals", d), ignore_errors=True)
    for v in vis:
        os.makedirs(os.path.join(base, "visuals", v["name"]), exist_ok=True)
        with open(os.path.join(base, "visuals", v["name"], "visual.json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=2)
    page = {"$schema": PAGE_SCHEMA, "name": nombre, "displayName": titulo, "displayOption": "FitToPage",
            "height": 1080, "width": 1920,
            "objects": {"background": [{"properties": {"color": color(FONDO), "transparency": lit("0D")}}]},
            "visualInteractions": interacciones}
    with open(os.path.join(base, "page.json"), "w", encoding="utf-8") as f:
        json.dump(page, f, ensure_ascii=False, indent=2)


def registrar_marca():
    """Copia logo y tema al reporte y los registra en report.json."""
    os.makedirs(RECURSOS, exist_ok=True)
    for archivo in (LOGO, TEMA):
        shutil.copyfile(os.path.join(AQUI, "marca", archivo), os.path.join(RECURSOS, archivo))
    ruta = os.path.join(REPORTE, "definition", "report.json")
    with open(ruta, encoding="utf-8") as f:
        rep = json.load(f)
    base = rep["themeCollection"]["baseTheme"]
    rep["themeCollection"]["customTheme"] = {"name": TEMA, "reportVersionAtImport": base["reportVersionAtImport"], "type": "RegisteredResources"}
    paquetes = [p for p in rep.get("resourcePackages", []) if p["name"] != "RegisteredResources"]
    paquetes.append({"name": "RegisteredResources", "type": "RegisteredResources", "items": [
        {"name": TEMA, "path": TEMA, "type": "CustomTheme"},
        {"name": LOGO, "path": LOGO, "type": "Image"}]})
    rep["resourcePackages"] = paquetes
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)


def main():
    registrar_marca()
    paginas = [pagina_panorama(), pagina_portafolio(), pagina_rendimiento()]
    nombres = [p[0] for p in paginas]
    for d in os.listdir(PAGINAS):
        if os.path.isdir(os.path.join(PAGINAS, d)) and d not in nombres:
            shutil.rmtree(os.path.join(PAGINAS, d), ignore_errors=True)
    for p in paginas:
        escribir_pagina(*p)
    with open(os.path.join(PAGINAS, "pages.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
                   "pageOrder": nombres, "activePageName": nombres[0]}, f, ensure_ascii=False, indent=2)
    print("Paginas generadas:", ", ".join(f"{p[1]} ({len(p[2])} visuales)" for p in paginas))


if __name__ == "__main__":
    main()
