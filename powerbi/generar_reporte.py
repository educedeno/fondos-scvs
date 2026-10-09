"""
Genera la pagina "Panorama del Mercado" del reporte Power BI (formato PBIR)
dentro de Fondos_Mercado.Report. Power BI Desktop debe estar CERRADO al correrlo.

Uso: python powerbi/generar_reporte.py
"""
import json
import os
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
PAGINAS = os.path.join(AQUI, "Fondos_Mercado.Report", "definition", "pages")
PAGINA = "panorama"
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"
NAVY = "#0D2B5E"


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def medida(tabla, nombre, alias=None):
    p = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": nombre}},
         "queryRef": f"{tabla}.{nombre}", "nativeQueryRef": alias or nombre}
    if alias:
        p["displayName"] = alias
    return p


def columna(tabla, nombre, alias=None):
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": nombre}},
         "queryRef": f"{tabla}.{nombre}", "nativeQueryRef": alias or nombre}
    if alias:
        p["displayName"] = alias
    return p


def titulo(texto, size=14):
    return {"title": [{"properties": {
        "show": lit("true"), "text": lit(f"'{texto}'"), "fontColor": {"solid": {"color": lit(f"'{NAVY}'")}},
        "fontSize": lit(f"{size}D"), "bold": lit("true"), "alignment": lit("'center'")}}],
        "subTitle": [{"properties": {"show": lit("false")}}],
        "border": [{"properties": {"show": lit("true"), "color": {"solid": {"color": lit("'#D9E1EC'")}}, "radius": lit("8D")}}]}


def contenedor(nombre, x, y, w, h, visual, z=0):
    return {"$schema": VC_SCHEMA, "name": nombre,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
            "visual": visual}


def texto(nombre, x, y, w, h, contenido, size, bold=False, color=NAVY):
    v = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": [{
        "textRuns": [{"value": contenido, "textStyle": {"fontWeight": "bold" if bold else "normal", "fontSize": f"{size}pt", "color": color}}],
        "horizontalTextAlignment": "center"}]}}]}}
    return contenedor(nombre, x, y, w, h, v)


def tarjeta(nombre, x, y, w, h, proy, z):
    v = {"visualType": "card", "query": {"queryState": {"Values": {"projections": [proy]}}},
         "objects": {"labels": [{"properties": {"color": {"solid": {"color": lit(f"'{NAVY}'")}}, "fontSize": lit("26D")}}],
                     "categoryLabels": [{"properties": {"fontSize": lit("12D")}}]},
         "visualContainerObjects": {"border": [{"properties": {"show": lit("true"), "color": {"solid": {"color": lit("'#D9E1EC'")}}, "radius": lit("8D")}}]},
         "drillFilterOtherVisuals": True}
    return contenedor(nombre, x, y, w, h, v, z)


def segmentador(nombre, x, y, w, h, proy, z, titulo_txt, unico=False, descendente=False):
    objs = {"data": [{"properties": {"mode": lit("'Dropdown'")}}],
            "header": [{"properties": {"show": lit("true"), "text": lit(f"'{titulo_txt}'"), "fontColor": {"solid": {"color": lit(f"'{NAVY}'")}}}}]}
    if unico:
        objs["selection"] = [{"properties": {"strictSingleSelect": lit("true")}}]
    q = {"queryState": {"Values": {"projections": [proy]}}}
    if descendente:
        q["sortDefinition"] = {"sort": [{"field": proy["field"], "direction": "Descending"}], "isDefaultSort": False}
    v = {"visualType": "slicer", "query": q, "objects": objs, "drillFilterOtherVisuals": True}
    return contenedor(nombre, x, y, w, h, v, z)


def main():
    # Borra otras paginas (p. ej. la "Page 1" vacia). Los archivos de esta pagina se sobrescriben
    # en lugar de borrarse porque OneDrive a veces bloquea carpetas mientras sincroniza.
    for d in os.listdir(PAGINAS):
        ruta = os.path.join(PAGINAS, d)
        if os.path.isdir(ruta) and d != PAGINA:
            shutil.rmtree(ruta, ignore_errors=True)
    base = os.path.join(PAGINAS, PAGINA)
    os.makedirs(os.path.join(base, "visuals"), exist_ok=True)

    P = "Patrimonio"
    vis = []
    vis.append(texto("titulo", 20, 8, 1880, 55, "Panorama del Mercado de Fondos de Inversión", 26, bold=True))
    vis.append(texto("subtitulo", 20, 60, 1880, 40, "Evolución, participación de mercado y dinámica de crecimiento de las administradoras de fondos en Ecuador", 13, color="#404B5A"))

    kpis = [("kpiPatrimonio", medida(P, "Patrimonio Mercado (mil M)", "Patrimonio Mercado")),
            ("kpiAdmins", medida(P, "Nº Administradoras", "Administradoras")),
            ("kpiFondos", medida(P, "Nº Fondos", "Fondos Administrados")),
            ("kpiMensual", medida(P, "Crecimiento Mensual Mercado %", "Crecimiento mensual del mercado")),
            ("kpiAnual", medida(P, "Crecimiento Anual Mercado %", "Incremento anual del patrimonio")),
            ("kpiGenesis", medida(P, "Share AFPGENESIS %", "Participación AFPGENESIS"))]
    w = (1880 - 5 * 14) / 6
    for i, (n, proy) in enumerate(kpis):
        vis.append(tarjeta(n, round(20 + i * (w + 14)), 108, round(w), 115, proy, 10 + i))

    vis.append(segmentador("slMes", 20, 238, 330, 80, columna("Meses", "Mes"), 20, "Mes de corte (vacío = último)", descendente=True))
    vis.append(segmentador("slAdmin", 365, 238, 330, 80, columna("Fondos", "Administradora"), 21, "Administradora"))
    vis.append(segmentador("slFondo", 710, 238, 330, 80, columna("Fondos", "Fondo"), 22, "Fondo"))
    vis.append(segmentador("slTipo", 1055, 238, 330, 80, columna("Fondos", "Tipo de fondo"), 23, "Tipo de fondo"))
    vis.append(segmentador("slPlazo", 1400, 238, 500, 80, columna("Fondos", "Plazo de permanencia"), 24, "Plazo de permanencia"))

    # Ranking (matriz expandible administradora -> fondos)
    matriz = {"visualType": "pivotTable",
              "query": {"queryState": {
                  "Rows": {"projections": [columna("Fondos", "Administradora"), columna("Fondos", "Fondo")]},
                  "Values": {"projections": [medida(P, "Patrimonio Total", "Patrimonio Mes Cerrado"), medida(P, "Share %", "Share (%)"),
                                             medida(P, "Variación Mensual %", "Variación Mensual %"), medida(P, "Variación Anual %", "Variación YoY %")]}},
                  "sortDefinition": {"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": P}}, "Property": "Patrimonio Total"}}, "direction": "Descending"}], "isDefaultSort": True}},
              "objects": {"columnHeaders": [{"properties": {"backColor": {"solid": {"color": lit(f"'{NAVY}'")}}, "fontColor": {"solid": {"color": lit("'#FFFFFF'")}}, "bold": lit("true"), "fontSize": lit("11D")}}],
                          "rowHeaders": [{"properties": {"fontSize": lit("11D"), "bold": lit("true"), "fontColor": {"solid": {"color": lit(f"'{NAVY}'")}}}}],
                          "values": [{"properties": {"fontSize": lit("11D")}},
                                     {"properties": {"fontColor": {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": P}}, "Property": "Color Variación Mensual"}}}}}},
                                      "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": "Patrimonio.Variación Mensual %"}},
                                     {"properties": {"fontColor": {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": P}}, "Property": "Color Variación Anual"}}}}}},
                                      "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": "Patrimonio.Variación Anual %"}}],
                          "total": [{"properties": {"backColor": {"solid": {"color": lit(f"'{NAVY}'")}}, "fontColor": {"solid": {"color": lit("'#FFFFFF'")}}}}],
                          "subTotals": [{"properties": {"rowSubtotals": lit("true")}}]},
              "visualContainerObjects": titulo("Ranking de Administradoras por Patrimonio", 15),
              "drillFilterOtherVisuals": True}
    vis.append(contenedor("ranking", 20, 333, 1060, 700, matriz, 30))

    evol = {"visualType": "lineChart",
            "query": {"queryState": {"Category": {"projections": [columna("Meses", "Fecha", "Mes")]},
                                     "Y": {"projections": [medida(P, "Patrimonio (últimos 24 meses)", "Patrimonio")]}}},
            "objects": {"labels": [{"properties": {"show": lit("true"), "labelDisplayUnits": lit("1000000D"), "labelPrecision": lit("0L")}}],
                        "dataPoint": [{"properties": {"fill": {"solid": {"color": lit("'#1F6FD1'")}}}}]},
            "visualContainerObjects": titulo("Evolución del Patrimonio del Mercado (US$ millones)", 14),
            "drillFilterOtherVisuals": True}
    vis.append(contenedor("evolucion", 1095, 333, 805, 360, evol, 40))

    share = {"visualType": "lineChart",
             "query": {"queryState": {"Category": {"projections": [columna("Meses", "Fecha", "Mes")]},
                                      "Y": {"projections": [medida(P, "Share AFPGENESIS (últimos 24 meses)", "Participación AFPGENESIS")]}}},
             "objects": {"dataPoint": [{"properties": {"fill": {"solid": {"color": lit("'#E3A008'")}}}}],
                         "labels": [{"properties": {"show": lit("true")}}]},
             "visualContainerObjects": titulo("Participación de mercado · AFPGENESIS", 14),
             "drillFilterOtherVisuals": True}
    vis.append(contenedor("shareGenesis", 1095, 705, 395, 328, share, 41))

    comp = {"visualType": "clusteredBarChart",
            "query": {"queryState": {"Category": {"projections": [columna("Composicion", "Grupo de instrumento", "Instrumento")]},
                                     "Y": {"projections": [medida("Composicion", "% del Portafolio")]}},
                      "sortDefinition": {"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Composicion"}}, "Property": "% del Portafolio"}}, "direction": "Descending"}], "isDefaultSort": True}},
            "objects": {"labels": [{"properties": {"show": lit("true")}}],
                        "dataPoint": [{"properties": {"fill": {"solid": {"color": lit("'#1F6FD1'")}}}}]},
            "visualContainerObjects": titulo("Clasificación por Instrumento", 14),
            "drillFilterOtherVisuals": True}
    vis.append(contenedor("composicion", 1505, 705, 395, 328, comp, 42))

    pie = {"visualType": "card", "query": {"queryState": {"Values": {"projections": [medida(P, "Texto Corte")]}}},
           "objects": {"labels": [{"properties": {"fontSize": lit("11D"), "color": {"solid": {"color": lit("'#404B5A'")}}}}],
                       "categoryLabels": [{"properties": {"show": lit("false")}}]}}
    vis.append(contenedor("pie", 20, 1038, 1880, 40, pie, 50))

    nombres = {v["name"] for v in vis}
    for d in os.listdir(os.path.join(base, "visuals")):
        if d not in nombres:
            shutil.rmtree(os.path.join(base, "visuals", d), ignore_errors=True)
    for v in vis:
        os.makedirs(os.path.join(base, "visuals", v["name"]), exist_ok=True)
        with open(os.path.join(base, "visuals", v["name"], "visual.json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=2)

    # Las graficas de evolucion muestran la historia completa aunque se elija un mes de corte;
    # la de participacion de Genesis tampoco se filtra por administradora/fondo.
    interacciones = [{"source": "slMes", "target": t, "type": "NoFilter"} for t in ("evolucion", "shareGenesis")]
    interacciones += [{"source": s, "target": "shareGenesis", "type": "NoFilter"} for s in ("slAdmin", "slFondo")]
    page = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": PAGINA, "displayName": "Panorama del Mercado", "displayOption": "FitToPage",
            "height": 1080, "width": 1920, "visualInteractions": interacciones}
    with open(os.path.join(base, "page.json"), "w", encoding="utf-8") as f:
        json.dump(page, f, ensure_ascii=False, indent=2)
    pages = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
             "pageOrder": [PAGINA], "activePageName": PAGINA}
    with open(os.path.join(PAGINAS, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"Pagina generada con {len(vis)} visuales")


if __name__ == "__main__":
    main()
