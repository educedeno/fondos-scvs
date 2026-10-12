# Panorama del Mercado de Fondos de Inversión (Ecuador)

Proyecto para AFP Génesis: benchmark y participación de mercado de las administradoras de fondos.
Los datos salen de la información pública de la Superintendencia de Compañías, Valores y Seguros (SCVS) y se actualizan solos.

## Qué hay aquí

| Carpeta / archivo | Para qué sirve |
|---|---|
| `dashboard/Panorama_Fondos.html` | **El dashboard listo para usar.** Se abre con doble clic y funciona sin internet. Sirve para la reunión del martes. |
| `datos/` | Las tablas limpias (CSV) a las que se conecta Power BI: mensuales (balances) y diarias (valor de la unidad, rendimiento). |
| `GUIA_POWER_BI.md` | Paso a paso para armar el mismo tablero en Power BI, con las fórmulas listas para copiar. |
| `actualizar.bat` | Doble clic para bajar los datos más nuevos y regenerar el dashboard. Necesita Python instalado. |
| `config/fondos_administradoras.csv` | Indica a qué administradora pertenece cada fondo. Se edita con Excel. |
| `scripts/` | Los programas que descargan y procesan los datos. No hace falta tocarlos. |
| `.github/workflows/actualizar.yml` | Hace la actualización automática diaria en la nube (GitHub). |

## De dónde vienen los datos

Reporte público de la SCVS **"Estados financieros de los entes de mercado de valores"**:
https://mercadodevalores.supercias.gob.ec/reportes/balancesConsolidadosMv.jsf

- No pide usuario, clave ni captcha. Es un archivo zip con los balances mensuales de todos los fondos.
- Patrimonio de cada fondo = cuenta **3 – Patrimonio neto**.
- Composición del portafolio = cuentas **101.02.xx – Activos financieros** (bonos del Estado, obligaciones, papel comercial, certificados de depósito, titularizaciones, etc.).
- Historia desde 2014. Los datos llegan con ~1 mes de rezago: el corte de agosto 2026 se publicó el 1 de octubre de 2026.

### Segunda fuente: resumen diario de cada fondo

Catastro público de la SCVS → **Fondos de inversión** → detalle de cada fondo → **Resumen diario**:
https://appscvsgen.supercias.gob.ec/consultaCompanias/mercadoValores/catastroEntesMv.jsf

- Tampoco pide usuario ni clave. El portal no tiene links fijos: cada página se abre con un código que caduca. Por eso `scripts/actualizar_diario.py` navega igual que una persona (catastro → listado → fondo → Excel).
- Trae, por fondo y por día: **valor de la unidad**, número de unidades, partícipes (naturales y jurídicos), activo y **patrimonio neto**. Hay historia desde 2015.
- Con el valor de la unidad se calcula el **rendimiento anualizado** de 30, 90, 180 y 365 días y del año corrido (`datos/fondos_rendimiento.csv`).
- El patrimonio diario al cierre de mes cuadra al centavo con los balances mensuales (se probó con Estratégico, Master y Fondo Real a ago-2026).
- El portal tiene un captcha que hoy no se activa. Si un día lo pide, la descarga se detiene y se conservan los datos anteriores. Si un fondo falla, también conserva sus datos anteriores.
- La pestaña "Calificadoras de riesgos" solo dice **qué calificadora** contrató cada fondo, no la calificación. Por eso no se incluye.

## Validación contra el dashboard de referencia (capturas en `contexto/`)

Se compararon los totales por administradora en dos fechas: **agosto 2026** y **septiembre 2025**.

- **13 de 16 administradoras cuadran al dólar** en ambas fechas: FIDUCIA, FIDEVAL, ANEFI, AFPGENESIS, ZION, FIDUTLAN, AFPV, SMARTFONDOS, PLUSFONDOS, GENERATRUST, MAXFONDOS, CAPITALIUM, ADMUNIFONDOS y FUTURFID.
- **Los 6 fondos de AFP Génesis cuadran exacto:** Renta Plus, Horizonte, Estratégico, Eficaz, Superior y Master.
- **VANGUARDIA sale 1.67% más alta.** Aquí se incluye su fondo colectivo nuevo CONSTRUYE PATRIMONIO 01, que el dashboard de referencia no tiene.
- **HOPE: no se pudo identificar su fondo.** Hay 4 fondos colectivos pequeños (TERRA 05, ATLAS, PATRIMONIO VERDE 01 y FUTURO BRILLANTE 01; ~$14.5 M en total, 0.4% del mercado) marcados **"POR CONFIRMAR"**. Probablemente TERRA 05 es de HOPE.
- **Composición de AFP Génesis:** Deuda Pública 69.6%, Obligaciones 16.6% y Depósitos 12.5%. En la referencia son 68.4%, 15.5% y 12.2%.

## Pendientes

1. **Confirmar los 4 fondos "POR CONFIRMAR".** Se resuelve editando `config/fondos_administradoras.csv`.
2. **Calificación de riesgo de cada fondo.** El catastro solo dice qué calificadora tiene cada fondo, no la nota. Habría que buscarla en los informes de las calificadoras. (Los datos diarios y el rendimiento ya se bajan solos desde el catastro, ver arriba.)
3. **Activar la actualización automática en la nube:** crear un repositorio en GitHub y subir esta carpeta (ver abajo).

## Actualización automática en la nube (para que Power BI solo dé "Actualizar")

1. Crear una cuenta gratuita en https://github.com y un repositorio **público**. Los datos son información pública de la SCVS.
2. Subir esta carpeta al repositorio.
3. GitHub ejecuta `.github/workflows/actualizar.yml` todos los días a las 07:00 (hora de Ecuador). Si la SCVS publicó datos nuevos, actualiza los CSV.
4. En Power BI se conecta con **Obtener datos → Web** a:
   `https://raw.githubusercontent.com/educedeno/fondos-scvs/main/datos/fondos_patrimonio_mensual.csv`
   y lo mismo con `fondos.csv`, `fondos_composicion_mensual.csv`, `fondos_diario.csv` y `fondos_rendimiento.csv`.
