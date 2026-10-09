# Panorama del Mercado de Fondos de Inversión (Ecuador)

Proyecto para AFP Génesis: benchmark y participación de mercado de las administradoras de fondos.
Los datos salen de la información pública de la Superintendencia de Compañías, Valores y Seguros (SCVS) y se actualizan solos.

## Qué hay aquí

| Carpeta / archivo | Para qué sirve |
|---|---|
| `dashboard/Panorama_Fondos.html` | **El dashboard listo para usar.** Se abre con doble clic y funciona sin internet. Sirve para la reunión del martes. |
| `datos/` | Las tablas limpias (CSV) a las que se conecta Power BI. |
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

## Validación contra el dashboard de referencia (capturas en `contexto/`)

Se compararon los totales por administradora en dos fechas: **agosto 2026** y **septiembre 2025**.

- **13 de 16 administradoras cuadran al dólar** en ambas fechas: FIDUCIA, FIDEVAL, ANEFI, AFPGENESIS, ZION, FIDUTLAN, AFPV, SMARTFONDOS, PLUSFONDOS, GENERATRUST, MAXFONDOS, CAPITALIUM, ADMUNIFONDOS y FUTURFID.
- **Los 6 fondos de AFP Génesis cuadran exacto:** Renta Plus, Horizonte, Estratégico, Eficaz, Superior y Master.
- **VANGUARDIA sale 1.67% más alta.** Aquí se incluye su fondo colectivo nuevo CONSTRUYE PATRIMONIO 01, que el dashboard de referencia no tiene.
- **HOPE: no se pudo identificar su fondo.** Hay 4 fondos colectivos pequeños (TERRA 05, ATLAS, PATRIMONIO VERDE 01 y FUTURO BRILLANTE 01; ~$14.5 M en total, 0.4% del mercado) marcados **"POR CONFIRMAR"**. Probablemente TERRA 05 es de HOPE.
- **Composición de AFP Génesis:** Deuda Pública 69.6%, Obligaciones 16.6% y Depósitos 12.5%. En la referencia son 68.4%, 15.5% y 12.2%.

## Pendientes

1. **Confirmar los 4 fondos "POR CONFIRMAR".** Se resuelve editando `config/fondos_administradoras.csv`.
2. **Datos diarios, rendimiento y calificación de riesgo.** Están en el catastro de la SCVS (`appscvsgen.supercias.gob.ec`), que estuvo caído el 9-oct-2026 por una migración de base de datos anunciada para el 10–11 de octubre. Cuando vuelva, se agrega como segunda fuente.
3. **Activar la actualización automática en la nube:** crear un repositorio en GitHub y subir esta carpeta (ver abajo).

## Actualización automática en la nube (para que Power BI solo dé "Actualizar")

1. Crear una cuenta gratuita en https://github.com y un repositorio **público**. Los datos son información pública de la SCVS.
2. Subir esta carpeta al repositorio.
3. GitHub ejecuta `.github/workflows/actualizar.yml` todos los días a las 07:00 (hora de Ecuador). Si la SCVS publicó datos nuevos, actualiza los CSV.
4. En Power BI se conecta con **Obtener datos → Web** a:
   `https://raw.githubusercontent.com/USUARIO/REPOSITORIO/main/datos/fondos_patrimonio_mensual.csv`
   y lo mismo con `fondos.csv` y `fondos_composicion_mensual.csv`.
