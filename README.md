<div align="center">

# 📡 EXTRACTOR DE COORDENADAS RTK

**Convierte archivos CSV de receptores GNSS RTK en archivos TXT de puntos de dibujo**
<br>
*Listos para importar en Civil 3D, AutoCAD o QGIS — con un solo clic*
<br><br>

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/ChrisSilver76?tab=repositories)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey.svg)](https://github.com/ChrisSilver76?tab=repositories)
[![Language](https://img.shields.io/badge/language-Python%203.11-yellow.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)

</div>

---

## 📌 ¿Qué problema resuelve?

Los receptores GNSS RTK (como el **Reach RS2** de Emlid) generan archivos CSV extremadamente densos: más de 40 columnas con metadatos de satélites, errores RMS, coordenadas geográficas y geodésicas, timestamps, etc.

Si intentas importar ese archivo directamente en **Civil 3D**, **AutoCAD** o **QGIS**, obtendrás errores de formato o tendrás que abrir Excel, eliminar columnas manualmente, revisar si hay descripciones vacías, guardar como texto delimitado… y repetir eso para cada levantamiento.

**El Extractor de Coordenadas RTK automatiza ese proceso completo:**

| Antes (manual) | Después (con este programa) |
|---|---|
| Abrir Excel, eliminar 35+ columnas a mano | Arrastrar el CSV al programa |
| Revisar descripciones vacías una por una | Auto-detección de la descripción más frecuente |
| Guardar como CSV, renombrar a .txt | Un clic en "PROCESAR ARCHIVOS" |
| Repetir para cada archivo | Procesar varios archivos en lote |
| ~10–15 minutos por levantamiento | ~3 segundos por levantamiento |

---

## 📋 Formato de transformación

**Entrada:** CSV RTK con 40+ columnas (generado por Reach RS2, Trimble, Leica, etc.)

```
Name,Code,Code description,Easting,Northing,Elevation,Description,Longitude,Latitude,...
1,,,644773.780,7813339.694,3714.456,sembrando,-67.618...,
2,,,644854.952,7813310.184,3715.155,sembrando,-67.617...,
...
```

**Salida:** TXT limpio, delimitado por comas, sin encabezados

```
1,644773.78,7813339.694,3714.456,sembrando
2,644854.952,7813310.184,3715.155,sembrando
3,644868.581,7813303.298,3715.12,sembrando
...
```

Formato: `Punto, Este (Easting), Norte (Northing), Elevación, [Descripción]`

---

## 🚀 Instalación

### Opción A — Ejecutable portátil (recomendado)

1. Ve a la sección [**Releases**](https://github.com/ChrisSilver76?tab=repositories)
2. Descarga `Extractor de Coordenadas RTK.exe`
3. Colócalo en cualquier carpeta (no requiere instalación)
4. ¡Haz doble clic y úsalo!

> ✅ No requiere instalar Python ni ninguna librería  
> ✅ Incluye el ícono en la barra de tareas y en la barra superior  
> ✅ Compatible con Windows 10 y Windows 11

### Opción B — Desde el código fuente (desarrolladores)

**Requisitos previos:**
- Python 3.11 o superior
- pip actualizado

```bash
# 1. Clona el repositorio
git clone https://github.com/ChrisSilver76/extractor-coordenadas-rtk.git
cd extractor-coordenadas-rtk

# 2. Instala las dependencias
pip install -r requirements.txt

# 3. Ejecuta el programa
python extractor_rtk.py
```

---

## 🛠️ Compilar el ejecutable

### Requisitos
- Python 3.11+
- PyInstaller instalado: `pip install pyinstaller`
- Archivo `Icono.ico` en la carpeta raíz

### Pasos

1. Coloca todos los archivos en la misma carpeta:
   ```
   Extractor_de_Coordenadas_RTK/
   ├── extractor_rtk.py
   ├── Icono.ico
   ├── compilar.bat
   └── requirements.txt
   ```

2. Ejecuta `compilar.bat`

3. El ejecutable aparecerá en `dist\Extractor de Coordenadas RTK.exe`

```bat
:: El bat ejecuta internamente:
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Extractor de Coordenadas RTK" ^
    --icon=Icono.ico ^
    --add-data "Icono.ico;." ^
    extractor_rtk.py
```

---

## 🖱️ Cómo usar el programa

### 1. Cargar archivos CSV

**Opción A — Arrastrar y soltar:**  
Arrastra uno o más archivos `.csv` directamente sobre la zona de carga. También puedes arrastrar una **carpeta** completa y el programa importará todos los `.csv` que encuentre dentro.

**Opción B — Botón de selección:**  
Haz clic en `📁 SELECCIONAR .CSV` y elige los archivos desde el explorador de Windows.

---

### 2. Configurar opciones por archivo

Cuando se cargan los archivos, aparece una lista con una fila de controles por cada CSV:

| Control | Función |
|---|---|
| `Name` | Número de punto — siempre incluido, no se puede desmarcar |
| `Easting` | Coordenada Este — siempre incluida |
| `Northing` | Coordenada Norte — siempre incluida |
| `Elevation` ✅ | Activado por defecto. Si lo desactivas, la cota se exporta como `0` |
| `Description` ☐ | Desactivado por defecto. Al activarlo, se incluye la columna de descripción |
| Caja de texto | Descripción manual. El programa auto-detecta el valor más frecuente del CSV |

> **Nota sobre las descripciones:**  
> El programa analiza la columna `Description` del CSV y pre-llena la caja de texto con el valor más repetido (p.ej. `sembrando`). Si el CSV no tiene descripciones, aparece `(Sin Descripción)` en rojo — puedes escribir una descripción personalizada haciendo clic en la caja.

---

### 3. Controles globales

Encima de la lista de archivos hay dos controles que aplican cambios a **todos los archivos a la vez**:

- ☑ **Todas Elevaciones** — activa/desactiva la elevación en todos los archivos
- ☑ **Todas Descripciones** — activa/desactiva la descripción en todos los archivos

---

### 4. Procesar y exportar

1. Haz clic en **`PROCESAR ARCHIVOS`** (esquina inferior derecha)
2. Elige la carpeta de destino en el explorador
3. El programa exporta los `.txt` y muestra el progreso con la barra de avance y el ETA
4. Al terminar, aparece una notificación con el resumen

> **Archivos duplicados:**  
> Si ya existe un archivo con el mismo nombre en la carpeta destino, el programa guarda el nuevo con un sufijo numérico.  
> Ej: `cota challapo.txt` → `cota challapo (1).txt` → `cota challapo (2).txt`

---

## 📸 Screenshots

> *Capturas de pantalla del programa en funcionamiento*

### Estado vacío (sin archivos)
> La zona de carga muestra instrucciones y el botón de selección

### Archivos cargados
> Cada archivo muestra su fila de controles con los checkboxes y la descripción auto-detectada

### Procesamiento en curso
> La barra de progreso reemplaza el botón "PROCESAR ARCHIVOS" y muestra el ETA en tiempo real

---

## 📁 Estructura del repositorio

```
Extractor_de_Coordenadas_RTK/
├── extractor_rtk.py         # Código fuente principal (Python / CustomTkinter)
├── Icono.ico                # Ícono del programa
├── compilar.bat             # Script de compilación con PyInstaller
├── requirements.txt         # Dependencias Python
├── LICENSE                  # Licencia MIT
└── README.md                # Este archivo
```

---

## 🧰 Tecnologías usadas

| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.11+ | Lenguaje principal |
| CustomTkinter | 5.2+ | Framework de interfaz gráfica moderna |
| pandas | 2.0+ | Lectura y procesamiento de archivos CSV |
| tkinterdnd2 | 0.3+ | Funcionalidad de Drag & Drop |
| threading | stdlib | Procesamiento asíncrono sin bloquear la UI |
| PyInstaller | 6.0+ | Compilación a ejecutable .exe |

---

## 🔧 Compatibilidad de CSV

El programa detecta automáticamente las columnas por nombre (no por posición), por lo que es compatible con cualquier receptor GNSS que genere CSV con los encabezados estándar:

| Columna requerida | Descripción |
|---|---|
| `Name` | Número o identificador del punto |
| `Easting` | Coordenada Este (UTM) |
| `Northing` | Coordenada Norte (UTM) |
| `Elevation` | Elevación / cota (opcional) |
| `Description` | Descripción del punto (opcional) |

**Receptores probados:**
- Emlid Reach RS2 / RS2+ / RS3
- Compatible con cualquier receptor que exporte CSV con los encabezados anteriores

---

## 📄 Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).  
Eres libre de usarlo, modificarlo y distribuirlo con o sin fines comerciales.

---

## 💛 APOYA ESTE PROYECTO

Si este programa te fue útil en tus levantamientos topográficos, considera apoyar su desarrollo:

[![Apoyar en Ko-Fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/chrissilver76)

---

<div align="center">

Hecho con ❤️ por <a href="https://github.com/ChrisSilver76">ChrisSilver76</a> — <strong>Archetris</strong>  
Bolivia, 2026

</div>
