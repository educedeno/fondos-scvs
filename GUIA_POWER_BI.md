# Guía: armar el dashboard en Power BI (sin programar)

Esta guía arma el tablero **Panorama del Mercado de Fondos de Inversión** en Power BI Desktop.
Los datos se conectan solos: cuando la Superintendencia publique información nueva, basta con presionar **Actualizar**.

## 0. Ya está hecho: `Panorama_Fondos_Inversion.pbix`

El archivo **`Panorama_Fondos_Inversion.pbix`** ya trae el tablero completo armado y conectado a los datos.

1. Ábrelo con doble clic. Necesitas Power BI Desktop, que es gratis.
2. Presiona **Inicio → Actualizar**. La primera vez, Power BI pregunta cómo conectarse a `raw.githubusercontent.com`: elige **Anónimo** y presiona **Conectar**. Los datos son públicos, así que no hace falta usuario ni clave.
3. Listo. Para ver los fondos de una administradora, haz clic en el **⊞** junto a su nombre en el ranking.
4. **Mes de corte:** si lo dejas vacío, muestra siempre el último mes publicado. Si eliges un mes, todo el tablero muestra ese mes, excepto las gráficas de evolución, que siempre muestran los últimos 24 meses.

El resto de esta guía sirve para modificar el tablero o armar uno nuevo desde cero.

---

## 1. Las 3 tablas de datos

| Archivo | Qué contiene | Una fila por… |
|---|---|---|
| `fondos.csv` | Lista de fondos: nombre, administradora, tipo y plazo | fondo |
| `fondos_patrimonio_mensual.csv` | Patrimonio, activo y pasivo de cada fondo | fondo y mes |
| `fondos_composicion_mensual.csv` | En qué invierte cada fondo (bonos, obligaciones, papel comercial, etc.) | fondo, mes e instrumento |

**¿De dónde se conecta Power BI?** Hay dos opciones:

- **Opción A, internet (recomendada).** Los archivos se publican en GitHub y se actualizan solos todos los días. Funciona en cualquier computadora y no hay que instalar nada.
  - Dirección de cada archivo: `https://raw.githubusercontent.com/educedeno/fondos-scvs/main/datos/NOMBRE_ARCHIVO.csv`
  - Eduardo te pasa las direcciones exactas.
- **Opción B, carpeta local.** Se usa la carpeta `datos` de este proyecto. Para traer datos nuevos, se hace doble clic en `actualizar.bat`.

---

## 2. Conectar los datos (se hace una sola vez)

### Opción A: desde internet
1. Abre Power BI Desktop.
2. Ve a **Inicio → Obtener datos → Web**.
3. Pega la dirección de `fondos.csv` y presiona **Aceptar**. Luego presiona **Transformar datos**.
4. Repite los pasos 2 y 3 con los otros dos archivos.

### Opción B: desde la carpeta
1. Ve a **Inicio → Obtener datos → Texto/CSV**.
2. Elige `datos\fondos.csv` y presiona **Transformar datos**.
3. Repite con los otros dos archivos.

### Revisar los tipos de columna (en las dos opciones)
En el Editor de Power Query, revisa que cada columna tenga el tipo correcto:
- `fecha` debe ser **Fecha**.
- `patrimonio`, `activo`, `pasivo` y `valor` deben ser **Número decimal**.
- Si una fecha o un número sale mal, haz clic en el ícono del tipo de la columna y elige **Usando configuración regional… → Inglés (Estados Unidos)**.

Cambia el nombre de las tablas a: **Fondos**, **Patrimonio** y **Composicion**. Luego presiona **Cerrar y aplicar**.

> Plantilla en código (opcional). Si prefieres pegar el código, ve a **Inicio → Editor avanzado** y usa esto para la tabla Patrimonio (cambia la dirección por la tuya):
> ```
> let
>     Origen = Csv.Document(Web.Contents("https://raw.githubusercontent.com/educedeno/fondos-scvs/main/datos/fondos_patrimonio_mensual.csv"),
>              [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
>     Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),
>     Tipos = Table.TransformColumnTypes(Encabezados,
>              {{"fecha", type date}, {"activo", type number}, {"pasivo", type number}, {"patrimonio", type number}}, "en-US")
> in
>     Tipos
> ```

---

## 3. Tabla de calendario y relaciones

1. Ve a **Modelado → Nueva tabla** y pega:
   ```
   Calendario = ADDCOLUMNS( CALENDAR( DATE(2014,1,1), DATE(2030,12,31) ),
       "Año", YEAR([Date]), "Mes", FORMAT([Date], "mmm yyyy"), "MesOrden", YEAR([Date])*100 + MONTH([Date]) )
   ```
2. Selecciona la tabla Calendario y ve a **Herramientas de tabla → Marcar como tabla de fechas**. Elige la columna `Date`.
3. Abre la vista **Modelo** (el ícono de diagrama a la izquierda) y arrastra para crear estas relaciones:
   - `Fondos[ruc_fondo]` → `Patrimonio[ruc_fondo]` (1 a muchos)
   - `Fondos[ruc_fondo]` → `Composicion[ruc_fondo]` (1 a muchos)
   - `Calendario[Date]` → `Patrimonio[fecha]` (1 a muchos)
   - `Calendario[Date]` → `Composicion[fecha]` (1 a muchos)
4. En la tabla Calendario, selecciona la columna `Mes` y elige **Ordenar por columna → MesOrden**.

---

## 4. Medidas (copiar y pegar)

Selecciona la tabla **Patrimonio** y ve a **Modelado → Nueva medida**. Pega cada medida por separado.

```
Patrimonio Total = SUM( Patrimonio[patrimonio] )
```
```
Patrimonio Mercado = CALCULATE( [Patrimonio Total], REMOVEFILTERS( Fondos ) )
```
```
Share % = DIVIDE( [Patrimonio Total], [Patrimonio Mercado] )
```
```
Patrimonio Mes Anterior = CALCULATE( [Patrimonio Total], DATEADD( Calendario[Date], -1, MONTH ) )
```
```
Variación Mensual % = DIVIDE( [Patrimonio Total] - [Patrimonio Mes Anterior], [Patrimonio Mes Anterior] )
```
```
Patrimonio Año Anterior = CALCULATE( [Patrimonio Total], SAMEPERIODLASTYEAR( Calendario[Date] ) )
```
```
Variación Anual % = DIVIDE( [Patrimonio Total] - [Patrimonio Año Anterior], [Patrimonio Año Anterior] )
```
```
Nº Administradoras = CALCULATE( DISTINCTCOUNT( Fondos[administradora] ), Patrimonio[patrimonio] > 0, Fondos[administradora] <> "POR CONFIRMAR" )
```
```
Nº Fondos = CALCULATE( DISTINCTCOUNT( Patrimonio[ruc_fondo] ), Patrimonio[patrimonio] > 0 )
```
```
Ranking Administradora =
RANKX( ALL( Fondos[administradora] ), CALCULATE( [Patrimonio Total] ), , DESC, Dense )
```
```
Último Mes = CALCULATE( MAX( Patrimonio[fecha] ), REMOVEFILTERS() )
```

Para la tabla **Composicion**, crea estas medidas:
```
Valor Instrumento = SUM( Composicion[valor] )
```
```
% del Portafolio = DIVIDE( [Valor Instrumento], CALCULATE( [Valor Instrumento], REMOVEFILTERS( Composicion[grupo_instrumento], Composicion[instrumento] ) ) )
```

Para que los porcentajes se vean con el símbolo %: selecciona cada medida de porcentaje y en **Herramientas de medidas** elige **Formato → Porcentaje**.

---

## 5. Armar los visuales (igual al tablero de referencia)

| Visual | Cómo armarlo |
|---|---|
| **Tarjetas de arriba** | Usa visuales de **Tarjeta** con: `Patrimonio Mercado`, `Nº Administradoras`, `Nº Fondos`, `Variación Mensual %` y `Variación Anual %`. |
| **Ranking de Administradoras** | Usa un visual de **Matriz**. En *Filas* pon `Fondos[administradora]` y debajo `Fondos[nombre_corto]` (así aparece el ⊞ para expandir los fondos). En *Valores* pon `Patrimonio Total`, `Share %`, `Variación Mensual %` y `Variación Anual %`. Ordena por Patrimonio, de mayor a menor. |
| **Flechas verdes y rojas** | Selecciona la matriz y ve a **Formato → Elementos de celda**. En `Variación Mensual %` activa **Iconos → Reglas**: si el valor es mayor o igual a 0, flecha verde hacia arriba; si es menor a 0, flecha roja hacia abajo. Haz lo mismo con `Variación Anual %`. |
| **Evolución del Patrimonio** | Usa un **Gráfico de líneas**. En el eje X pon `Calendario[Mes]` y en el eje Y `Patrimonio Total`. |
| **Participación de AFPGENESIS** | Usa un **Gráfico de líneas** con el eje X en `Calendario[Mes]` y el eje Y en `Share %`. Agrega un filtro de visual con `Fondos[administradora] = AFPGENESIS`. |
| **Clasificación por instrumento** | Usa un **Gráfico de columnas**. En el eje X pon `Composicion[grupo_instrumento]` y en el eje Y `% del Portafolio`. |
| **Filtros (segmentaciones)** | Agrega una segmentación con `Calendario[Mes]` en modo *Lista desplegable* y *Selección única*. Agrega otras con `Fondos[administradora]`, `Fondos[nombre_corto]` y `Fondos[tipo_fondo]`. |

Pon este texto en el pie del tablero: *"Fuente: Superintendencia de Compañías, Valores y Seguros (SCVS) – Información pública."*

---

## 6. Actualizar (el día a día)

- **En Power BI Desktop:** presiona **Inicio → Actualizar**. Eso es todo.
- **En Power BI Service** (si publicas el tablero en la web): abre el conjunto de datos, ve a **Configuración → Actualización programada** y actívala una vez al día. Con la opción A no necesitas gateway, porque los datos vienen de internet.

### ¿Cada cuánto cambian los datos?
La Superintendencia publica los balances de los fondos **una vez al mes**. Los datos de un mes aparecen aproximadamente el día 1 del mes subsiguiente (por ejemplo, agosto apareció el 1 de octubre).

---

## 7. Si aparece un fondo nuevo

Cuando una administradora crea un fondo nuevo, aparece en la tabla con la administradora **"SIN ASIGNAR"**. Para corregirlo:
1. Abre `config/fondos_administradoras.csv` con Excel.
2. Agrega una fila con el RUC del fondo (está en `datos/fondos.csv`), su nombre y su administradora.
3. Guarda el archivo como CSV.

En la próxima actualización ya aparece con su administradora.
