# ============================================================
#  Extractor de Coordenadas RTK — v1.2.0
#  by ChrisSilver76
#  Procesador de Puntos de coordenadas CSV a TXT
#
#  Descripción:
#    Convierte archivos CSV generados por receptores GNSS RTK
#    (p.ej. Reach RS2) en archivos TXT de puntos de dibujo
#    listos para Civil 3D, AutoCAD o QGIS.
#
#  Formato de salida: Punto,Este,Norte,Elevación[,Descripción]
# ============================================================

import os
import sys
import csv
import time
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog
from collections import Counter

import customtkinter as ctk
# pandas fue eliminado — se reemplazó por el módulo csv de la stdlib.
# Esto reduce el .exe de ~200 MB a ~35 MB y acelera el arranque.

# ── Importación defensiva de tkinterdnd2 ─────────────────────────────────────
# Si la librería no está instalada, el programa funciona sin Drag & Drop
# pero sigue siendo completamente funcional con el botón "SELECCIONAR .CSV".
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_OK = True
except ImportError:
    DND_OK = False

# ── Metadatos del programa ────────────────────────────────────────────────────
VERSION      = "v1.2.0"
APP_TITLE    = "EXTRACTOR DE COORDENADAS RTK"
APP_SUBTITLE = "Procesador de Puntos de coordenadas CSV a TXT"

# Ruta del icono (ubicado junto al .py o al .exe compilado)
ICON_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "Icono.ico"


# ============================================================
#  SISTEMA DE DISEÑO GLOBAL — Design Tokens (clase T)
#  Centraliza todos los colores, fuentes y métricas de la UI.
#  Cambiar un valor aquí lo propaga a toda la interfaz.
# ============================================================
class T:
    # ── Fondos (de más oscuro a más elevado) ──────────────────────
    BG         = "#21252b"   # Fondo base de la ventana principal
    BG2        = "#181b21"   # Fondo extra-oscuro (header, barra inferior)
    BG_CARD    = "#282c34"   # Tarjetas, frames con elevación visual
    BG_CON     = "#1c2128"   # Inputs, textbox, zonas de escritura
    BG_DROP    = "#1e2229"   # DropZone en reposo
    BG_DROPHOV = "#252b34"   # DropZone al pasar archivo encima
    BG_MODAL   = "#1e2229"   # Fondo de ventanas modales

    # ── Acento azul ───────────────────────────────────────────────
    ACC        = "#32628d"   # Botón primario en reposo
    ACC_H      = "#427aa8"   # Botón primario en hover
    ACC_L      = "#4abae6"   # Acento más claro (bordes activos)
    ACC_BRD    = "#4abae6"   # Borde de DropZone activa

    # ── Texto ─────────────────────────────────────────────────────
    TX         = "#e0e0e0"   # Texto principal
    TX2        = "#999999"   # Texto secundario / muted
    TXD        = "#666666"   # Texto desactivado / placeholders
    TXA        = "#4abae6"   # Texto de acento
    TXOK       = "#a5d6a7"   # Éxito / verde pastel
    TXWN       = "#ffcc80"   # Advertencia / naranja pastel
    TXER       = "#ef9a9a"   # Error / rojo pastel

    # ── Bordes ────────────────────────────────────────────────────
    BRD        = "#3a3f4b"   # Borde estándar

    # ── Tipografía y tamaños ──────────────────────────────────────
    F          = "Segoe UI"  # Fuente principal
    FM         = "Consolas"  # Fuente monoespaciada
    SZT        = 20          # Título principal del header
    SZH        = 14          # Headings
    SZB        = 13          # Texto de botones, body
    SZS        = 10          # Textos secundarios
    R          = 10          # corner_radius global
    P          = 16          # Padding horizontal estándar


# ============================================================
#  FUNCIONES PURAS DE PROCESAMIENTO CSV → TXT
#  Sin referencias a widgets — pueden testearse de forma
#  independiente o ejecutarse desde la línea de comandos.
#  100% stdlib: usa el módulo csv en lugar de pandas.
# ============================================================

def leer_csv(ruta: Path) -> list[dict]:
    """Lee un CSV y devuelve una lista de dicts por fila.

    Equivalente a pd.read_csv() pero usando solo la stdlib.
    Maneja BOM (utf-8-sig) que algunos equipos RTK incluyen,
    y también UTF-8 plano como fallback.
    """
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(ruta, newline="", encoding=encoding) as f:
                return list(csv.DictReader(f))
        except (UnicodeDecodeError, Exception):
            continue
    return []


def _fmt_numero(valor: str) -> str:
    """Formatea un string numérico eliminando ceros decimales finales.

    Replica el comportamiento de pandas al convertir float→str:
      '644773.780' → '644773.78'
      '3714.456'   → '3714.456'   (sin cambio)
      '0'          → '0'
    Usa float() para la conversión; si el valor no es numérico
    lo retorna sin modificar (p. ej. para nombres de puntos).
    """
    v = valor.strip()
    try:
        return str(float(v))
    except (ValueError, TypeError):
        return v

def abreviar_nombre(nombre: str, max_chars: int = 14) -> str:
    """Abrevia un nombre de archivo largo para la UI.

    Regla: Si el nombre tiene varias palabras, usa la inicial de la
    primera + ". " + inicio de la segunda. Ej: 'Cota Challapo' → 'C. Challap'
    Si es una sola palabra larga, la trunca directamente.
    """
    base = Path(nombre).stem  # elimina extensión
    if len(base) <= max_chars:
        return base
    partes = base.split()
    if len(partes) >= 2:
        abrev = f"{partes[0][0].upper()}. {partes[1]}"
        return abrev[:max_chars]
    return base[:max_chars]


def leer_descripcion_frecuente(filas: list[dict]) -> str | None:
    """Detecta la descripción más frecuente en una lista de filas CSV.

    En caso de empate, retorna el primer valor que alcanza esa
    frecuencia máxima según el orden de aparición en el CSV.
    Retorna None si no hay descripciones válidas.

    Args:
        filas: Lista de dicts tal como devuelve leer_csv().
    """
    if not filas or "Description" not in filas[0]:
        return None
    vals = [
        r["Description"].strip()
        for r in filas
        if r.get("Description", "").strip() not in ("", "nan")
    ]
    if not vals:
        return None
    conteo   = Counter(vals)
    max_freq = max(conteo.values())
    for v in vals:
        if conteo[v] == max_freq:
            return v
    return None


def calcular_ruta_salida(nombre_base: str, carpeta: Path) -> Path:
    """Calcula la ruta de salida evitando sobreescribir archivos.

    Si 'cota challapo.txt' ya existe, propone 'cota challapo (1).txt',
    'cota challapo (2).txt', etc., hasta encontrar un nombre libre.
    """
    candidato = carpeta / f"{nombre_base}.txt"
    if not candidato.exists():
        return candidato
    n = 1
    while True:
        candidato = carpeta / f"{nombre_base} ({n}).txt"
        if not candidato.exists():
            return candidato
        n += 1


def exportar_csv_a_txt(
    ruta_csv: Path,
    ruta_salida: Path,
    incluir_elevation: bool,
    incluir_description: bool,
    descripcion_override: str,
    log_fn: callable,
    progress_cb: callable = None,
) -> int:
    """Convierte un archivo CSV RTK a TXT de puntos de dibujo.

    Columnas de salida: Name, Easting, Northing, [Elevation], [Description]
    Usa csv.DictReader (stdlib) — sin dependencia de pandas.

    Args:
        ruta_csv:             Ruta al CSV de entrada.
        ruta_salida:          Ruta calculada para el TXT de salida.
        incluir_elevation:    Si False, exporta "0" como cota.
        incluir_description:  Si True, agrega la columna de descripción.
        descripcion_override: Texto del Entry (puede ser vacío).
        log_fn:               Función log(str) — NO toca widgets.
        progress_cb:          Función progress(float 0..1) — opcional.

    Returns:
        Número de filas exportadas.
    """
    filas = leer_csv(ruta_csv)
    if not filas:
        log_fn(f"❌ Error leyendo {ruta_csv.name}: archivo vacío o formato inválido.")
        return 0

    # Verificar columnas mínimas requeridas
    requeridas = {"Name", "Easting", "Northing"}
    if not requeridas.issubset(set(filas[0].keys())):
        log_fn(f"⚠ {ruta_csv.name}: faltan columnas (Name, Easting, Northing). Omitido.")
        return 0

    lineas = []
    total  = len(filas)

    for i, fila in enumerate(filas):
        nombre_pt = fila.get("Name",     "").strip()
        easting   = _fmt_numero(fila.get("Easting",  ""))
        northing  = _fmt_numero(fila.get("Northing", ""))

        # Elevación: usa el valor real o "0" según configuración
        if incluir_elevation:
            raw_elev = fila.get("Elevation", "").strip()
            elev = _fmt_numero(raw_elev) if raw_elev and raw_elev.lower() != "nan" else "0"
        else:
            elev = "0"

        partes = [nombre_pt, easting, northing, elev]

        # Descripción: usa el override del Entry o cae al valor de la fila
        if incluir_description:
            desc = descripcion_override.strip()
            placeholder = "(sin descripción)"
            if desc and desc.lower() != placeholder:
                partes.append(desc)
            else:
                desc_fila = fila.get("Description", "").strip()
                if desc_fila and desc_fila.lower() not in ("nan", ""):
                    partes.append(desc_fila)

        lineas.append(",".join(partes))

        if progress_cb and total > 0:
            progress_cb((i + 1) / total)

    ruta_salida.write_text("\n".join(lineas), encoding="utf-8")
    log_fn(f"✅ {ruta_csv.name} → {ruta_salida.name}  ({total} puntos)")
    return total


# ============================================================
#  COMPONENTE: Toast — Notificación flotante efímera
# ============================================================
class Toast(ctk.CTkFrame):
    """Notificación flotante que aparece sobre la interfaz.

    Hereda de CTkFrame y se posiciona con place() en la esquina
    inferior derecha de la ventana padre. Se destruye sola después
    de `ms` milisegundos mediante after().
    """
    def __init__(self, master, mensaje: str, ms: int = 3500, ok: bool = True):
        color_borde = T.TXOK if ok else T.TXER
        super().__init__(
            master,
            fg_color=T.BG_CARD,
            corner_radius=T.R,
            border_width=2,
            border_color=color_borde,
        )
        icono = "✅" if ok else "⚠"
        ctk.CTkLabel(
            self,
            text=f"  {icono}  {mensaje}  ",
            font=(T.F, T.SZB),
            text_color=T.TX,
        ).pack(padx=14, pady=10)

        # Posicionar en la esquina inferior derecha usando coordenadas relativas
        self.update_idletasks()
        self.place(relx=1.0, rely=1.0, anchor="se", x=-T.P, y=-T.P)
        self.lift()
        # Destrucción automática
        self.after(ms, self._dismiss)

    def _dismiss(self):
        try:
            self.destroy()
        except Exception:
            pass


# ============================================================
#  COMPONENTE: ProgressBar con ETA
# ============================================================
class ProgressBar(ctk.CTkFrame):
    """Barra de progreso con texto de estado y estimación de tiempo restante.

    Cálculo del ETA (Estimated Time of Arrival / tiempo restante):
    ─────────────────────────────────────────────────────────────
    Sea:
      t₀    = timestamp al iniciar (guardado en self._t_start)
      t_now = timestamp actual
      p     = progreso actual (0.0 a 1.0)

    Tiempo transcurrido:  Δt = t_now − t₀
    Velocidad promedio:   v  = p / Δt            [fracción por segundo]
    Tiempo restante:      ETA = (1 − p) / v
                             = (1 − p) × Δt / p

    Esta es una proyección lineal: asume que la velocidad de
    procesamiento se mantendrá constante. Funciona bien para
    archivos CSV de tamaño similar.
    """

    def __init__(self, master, on_start: callable = None, **kwargs):
        super().__init__(master, fg_color=T.BG2, corner_radius=0, **kwargs)
        self._on_start_cb = on_start
        self._t_start: float | None = None
        self._build()

    def _build(self):
        self.configure(height=64)
        self.pack_propagate(False)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=T.P, pady=10)

        # ── Texto de estado (izquierda) ───────────────────────────
        self.lbl_status = ctk.CTkLabel(
            row, text="Listo. Carga archivos CSV para comenzar.",
            font=(T.F, T.SZS), text_color=T.TX2, anchor="w"
        )
        self.lbl_status.pack(side="left", fill="x", expand=True)

        # ── ETA (centro-derecha) ──────────────────────────────────
        self.lbl_eta = ctk.CTkLabel(
            row, text="", font=(T.FM, T.SZS),
            text_color=T.TXA, width=110, anchor="e"
        )
        self.lbl_eta.pack(side="left", padx=(0, 12))

        # ── Barra de progreso (oculta hasta busy()) ───────────────
        self.bar = ctk.CTkProgressBar(
            row, width=220, height=18,
            fg_color=T.BG_CON, progress_color=T.ACC_L,
            corner_radius=5
        )
        self.bar.set(0)
        # Ocultar inicialmente: se mostrará cuando empiece el proceso
        self.bar.pack_forget()

        # ── Botón principal ───────────────────────────────────────
        self.btn = ctk.CTkButton(
            row,
            text="PROCESAR ARCHIVOS",
            font=(T.F, T.SZB, "bold"),
            fg_color=T.ACC, hover_color=T.ACC_H,
            corner_radius=T.R, height=42, width=220,
            command=self._on_click,
        )
        self.btn.pack(side="right")

    def _on_click(self):
        if self._on_start_cb:
            self._on_start_cb()

    def busy(self):
        """Activa el estado de proceso: oculta el botón y muestra la barra."""
        self._t_start = time.time()
        self.btn.pack_forget()
        self.bar.set(0)
        self.bar.pack(side="right", pady=4)
        self.lbl_status.configure(text="Iniciando...", text_color=T.TXA)
        self.lbl_eta.configure(text="ETA: --:--")

    def idle(self):
        """Restaura el estado de reposo: oculta la barra y muestra el botón."""
        self.bar.pack_forget()
        self.btn.pack(side="right")
        self.lbl_eta.configure(text="")

    def set(self, value: float, status: str = ""):
        """Actualiza la barra de progreso y recalcula el ETA.

        Args:
            value:  Fracción de progreso entre 0.0 y 1.0.
            status: Mensaje de estado opcional.
        """
        self.bar.set(value)
        if status:
            self.lbl_status.configure(
                text=status,
                text_color=(T.TXOK if value >= 1.0 else T.TXA)
            )
        # Calcular ETA solo si hay suficiente progreso para una estimación útil
        if self._t_start and 0.02 < value < 1.0:
            transcurrido = time.time() - self._t_start
            # ETA = Δt × (1 − p) / p  (proyección lineal)
            restante = transcurrido * (1.0 - value) / value
            mins, secs = divmod(int(restante), 60)
            self.lbl_eta.configure(text=f"ETA: {mins:02d}:{secs:02d}")
        elif value >= 1.0:
            self.lbl_eta.configure(text="✓ Listo")


# ============================================================
#  COMPONENTE: FileRow — Fila de configuración por archivo
# ============================================================
class FileRow(ctk.CTkFrame):
    """Fila de controles para un archivo CSV individual.

    Muestra el nombre abreviado del archivo y permite configurar:
    - Incluir Elevation (activado por defecto)
    - Incluir Description (desactivado por defecto)
    - Texto de la descripción (auto-detectado del CSV o manual)
    """

    def __init__(self, master, ruta: Path, **kwargs):
        super().__init__(
            master,
            fg_color=T.BG_CARD,
            corner_radius=6,
            border_width=1,
            border_color=T.BRD,
            **kwargs
        )
        self.ruta = ruta
        # StringVar vinculada al Entry para leer/escribir sin importar el estado
        self._var_desc = ctk.StringVar(value="")
        self._tiene_desc_csv = False   # True si el CSV tenía descripciones
        self._build()
        self._cargar_descripcion_defecto()

    def _build(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=5)

        # ── Nombre abreviado ──────────────────────────────────────
        nombre_abrev = abreviar_nombre(self.ruta.name, 14)
        ctk.CTkLabel(
            row, text=nombre_abrev,
            font=(T.F, T.SZS, "bold"), text_color=T.TX,
            width=104, anchor="w"
        ).pack(side="left", padx=(4, 6))

        # ── Checkboxes obligatorios (deshabilitados, siempre activos) ─
        for label in ("Name", "Easting", "Northing"):
            ctk.CTkCheckBox(
                row, text=label,
                variable=ctk.BooleanVar(value=True),
                font=(T.F, T.SZS), text_color=T.TXD,
                state="disabled", width=68,
                checkmark_color=T.TXD,
                fg_color=T.BRD, hover_color=T.BRD,
            ).pack(side="left", padx=3)

        # ── Checkbox Elevation ────────────────────────────────────
        self.var_elev = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            row, text="Elevation",
            variable=self.var_elev,
            font=(T.F, T.SZS), text_color=T.TX,
            fg_color=T.ACC, hover_color=T.ACC_H,
            width=78,
        ).pack(side="left", padx=3)

        # ── Checkbox Description ──────────────────────────────────
        self.var_desc_check = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            row, text="Description",
            variable=self.var_desc_check,
            font=(T.F, T.SZS), text_color=T.TX,
            fg_color=T.ACC, hover_color=T.ACC_H,
            width=88,
            command=self._on_desc_toggle,
        ).pack(side="left", padx=3)

        # ── Entry de descripción ──────────────────────────────────
        self.entry_desc = ctk.CTkEntry(
            row,
            textvariable=self._var_desc,
            font=(T.F, T.SZS),
            fg_color=T.BG_CON, text_color=T.TX,
            border_color=T.BRD, corner_radius=6,
            height=28, width=155,
            state="disabled",
        )
        self.entry_desc.pack(side="left", padx=(4, 8))

    def _cargar_descripcion_defecto(self):
        """Lee el CSV, detecta la descripción más frecuente y pre-llena el Entry.

        Usa leer_csv() (stdlib) en lugar de pandas.
        Si el CSV no tiene descripciones válidas, muestra '(Sin Descripción)'
        en rojo como indicador visual al usuario.
        """
        try:
            filas = leer_csv(self.ruta)
            desc  = leer_descripcion_frecuente(filas)
            if desc:
                self._tiene_desc_csv = True
                self._var_desc.set(desc)
                self.entry_desc.configure(text_color=T.TX, border_color=T.BRD)
            else:
                self._tiene_desc_csv = False
                self._var_desc.set("(Sin Descripción)")
                self.entry_desc.configure(text_color=T.TXER, border_color=T.TXER)
        except Exception:
            self._tiene_desc_csv = False
            self._var_desc.set("(Sin Descripción)")
            self.entry_desc.configure(text_color=T.TXER, border_color=T.TXER)

    def _on_desc_toggle(self):
        """Habilita o deshabilita el Entry según el estado del checkbox."""
        if self.var_desc_check.get():
            self.entry_desc.configure(state="normal")
        else:
            self.entry_desc.configure(state="disabled")

    # ── Getters (llamados desde el hilo de trabajo) ───────────────

    def get_elevation(self) -> bool:
        return self.var_elev.get()

    def get_description_active(self) -> bool:
        return self.var_desc_check.get()

    def get_desc_texto(self) -> str:
        """Retorna el texto actual del Entry (funciona incluso si está disabled)."""
        return self._var_desc.get().strip()

    # ── Setters (llamados por los controles globales) ─────────────

    def set_elevation(self, value: bool):
        self.var_elev.set(value)

    def set_description_active(self, value: bool):
        self.var_desc_check.set(value)
        self._on_desc_toggle()


# ============================================================
#  COMPONENTE: DropZone — Zona de arrastrar y soltar
# ============================================================
class DropZone(ctk.CTkFrame):
    """Zona de carga de archivos con dos estados visuales.

    ┌─────────────────────────────────────────────────────────┐
    │ Patrón de dos estados:                                  │
    │                                                         │
    │ ESTADO VACÍO:                                           │
    │   El contenido (ícono, texto, botón) se posiciona con   │
    │   place(relx=0.5, rely=0.5, anchor="center") para       │
    │   centrarse en el frame. Cuando hay archivos, se oculta │
    │   completamente con place_forget().                     │
    │                                                         │
    │ ESTADO CARGADO:                                         │
    │   Un frame con la lista de archivos se posiciona con    │
    │   place(relx=0, rely=0, relwidth=1, relheight=1) para   │
    │   cubrir todo el espacio disponible. Se oculta cuando   │
    │   se limpia la lista.                                   │
    └─────────────────────────────────────────────────────────┘

    Usar place() en lugar de pack()/grid() para los estados
    internos permite intercambiarlos sin reconfigurar el layout
    del frame padre, ya que los hijos con place() no participan
    en el cálculo de geometría del contenedor.
    """

    def __init__(self, master, on_files_loaded: callable, **kwargs):
        super().__init__(
            master,
            fg_color=T.BG_DROP,
            corner_radius=T.R,
            border_width=2,
            border_color=T.BRD,
            **kwargs
        )
        self._on_files_loaded = on_files_loaded
        self._archivos: list[Path] = []

        self._build_estado_vacio()
        self._build_estado_cargado()
        self._mostrar_estado_vacio()
        self._configurar_dnd()

    # ── Estado vacío ──────────────────────────────────────────────
    def _build_estado_vacio(self):
        self._frame_vacio = ctk.CTkFrame(self, fg_color="transparent")

        ctk.CTkLabel(
            self._frame_vacio, text="📂",
            font=(T.F, 25)
        ).pack(pady=(0, 5))
        ctk.CTkLabel(
            self._frame_vacio,
            text="ARRASTRAR Y SOLTAR",
            font=(T.F, T.SZH, "bold"), text_color=T.TXA
        ).pack()
        ctk.CTkLabel(
            self._frame_vacio,
            text="Arrastre sus archivos .csv o carpetas aquí\n\n"
                 "El programa analizará sus documentos .CSV y los convertirá en .TXT, archivos de puntos de dibujo listos\n"
                 "para importar en Civil 3D, AutoCAD o QGIS con Coordenadas, Elevaciones y Descripciones organizadas.",
            font=(T.F, T.SZS), text_color=T.TX2, justify="center"
        ).pack(pady=(1, 6))

        ctk.CTkButton(
            self._frame_vacio,
            text="📁  SELECCIONAR .CSV",
            font=(T.F, T.SZB, "bold"),
            fg_color=T.ACC, hover_color=T.ACC_H,
            corner_radius=T.R, height=32, width=180,
            command=self._seleccionar_archivos,
        ).pack()

    # ── Estado cargado ────────────────────────────────────────────
    def _build_estado_cargado(self):
        self._frame_cargado = ctk.CTkFrame(self, fg_color="transparent")

        # Barra superior con título y botón de limpiar
        top = ctk.CTkFrame(self._frame_cargado, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            top, text="📋  Archivos cargados:",
            font=(T.F, T.SZS, "bold"), text_color=T.TXA
        ).pack(side="left")
        ctk.CTkButton(
            top, text="✕  Limpiar todo",
            font=(T.F, T.SZS), width=110, height=24,
            fg_color=T.BG_CON, hover_color=T.TXER,
            text_color=T.TX2, corner_radius=6,
            command=self._limpiar,
        ).pack(side="right")

        # Lista scrollable de archivos
        self._scroll_archivos = ctk.CTkScrollableFrame(
            self._frame_cargado,
            fg_color=T.BG_CON,
            corner_radius=6,
        )
        self._scroll_archivos.pack(
            fill="both", expand=True, padx=10, pady=(0, 8)
        )

    # ── Gestión de visibilidad de estados ─────────────────────────
    def _mostrar_estado_vacio(self):
        """Oculta estado cargado, centra y muestra estado vacío."""
        self._frame_cargado.place_forget()
        self._frame_vacio.place(relx=0.5, rely=0.5, anchor="center")

    def _mostrar_estado_cargado(self):
        """Oculta estado vacío y expande estado cargado a todo el frame."""
        self._frame_vacio.place_forget()
        self._frame_cargado.place(relx=0, rely=0, relwidth=1, relheight=1)

    # ── Interfaz pública ──────────────────────────────────────────
    def show_files(self, rutas: list[Path]):
        """Muestra el estado cargado con la lista de archivos."""
        # Limpiar entradas anteriores
        for w in self._scroll_archivos.winfo_children():
            w.destroy()
        for ruta in rutas:
            fila = ctk.CTkFrame(self._scroll_archivos, fg_color="transparent")
            fila.pack(fill="x", pady=1)
            ctk.CTkLabel(
                fila, text="📄", font=(T.F, 11), width=20
            ).pack(side="left")
            ctk.CTkLabel(
                fila, text=ruta.name,
                font=(T.F, T.SZS), text_color=T.TX, anchor="w"
            ).pack(side="left", fill="x")
        self._mostrar_estado_cargado()

    def get_archivos(self) -> list[Path]:
        return list(self._archivos)

    # ── Manejo de archivos ────────────────────────────────────────
    def _seleccionar_archivos(self):
        rutas_str = filedialog.askopenfilenames(
            title="Seleccionar archivos CSV RTK",
            filetypes=[
                ("Archivos CSV", "*.csv"),
                ("Todos los archivos", "*.*")
            ]
        )
        if rutas_str:
            self._agregar_archivos([Path(r) for r in rutas_str])

    def _agregar_archivos(self, nuevas: list[Path]):
        """Agrega archivos a la lista evitando duplicados por ruta absoluta."""
        existentes = {r.resolve() for r in self._archivos}
        for r in nuevas:
            if r.suffix.lower() == ".csv" and r.resolve() not in existentes:
                self._archivos.append(r)
                existentes.add(r.resolve())
        if self._archivos:
            self.show_files(self._archivos)
            self._on_files_loaded(self._archivos)

    def _limpiar(self):
        self._archivos = []
        self._mostrar_estado_vacio()
        self._on_files_loaded([])

    # ── Drag & Drop ───────────────────────────────────────────────
    def _configurar_dnd(self):
        """Registra los eventos DnD si tkinterdnd2 está disponible."""
        if not DND_OK:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>",      self._on_drop)
            self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        except Exception:
            pass

    def _on_drop(self, event):
        """Procesa los archivos/carpetas soltados sobre la zona."""
        self.configure(fg_color=T.BG_DROP, border_color=T.BRD)
        try:
            # tk.splitlist parsea correctamente rutas con espacios
            rutas_raw = self.tk.splitlist(event.data.strip())
        except Exception:
            rutas_raw = event.data.strip().split()

        rutas: list[Path] = []
        for r in rutas_raw:
            p = Path(r)
            if p.is_dir():
                rutas.extend(sorted(p.glob("*.csv")))
            elif p.suffix.lower() == ".csv":
                rutas.append(p)
        if rutas:
            self._agregar_archivos(rutas)

    def _on_drag_enter(self, event):
        self.configure(fg_color=T.BG_DROPHOV, border_color=T.ACC_BRD)

    def _on_drag_leave(self, event):
        self.configure(fg_color=T.BG_DROP, border_color=T.BRD)


# ============================================================
#  MODAL: Acerca del programa
# ============================================================
class AboutModal(ctk.CTkToplevel):
    """Ventana informativa sobre el programa.

    No usa grab_set() ya que es solo informativa (no bloquea el flujo).
    Se centra sobre la ventana padre.
    """

    def __init__(self, master):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.title("Acerca del Programa")
        self.configure(fg_color=T.BG_MODAL)
        self.resizable(False, False)

        # ── Lógica de centrado corregida (Solución GitHub) ─────────
        w, h = 500, 600
        
        # Obtenemos el factor de escala de la ventana
        scale_factor = self._get_window_scaling()
        
        # Dimensiones de la pantalla
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        
        # Calculamos la posición compensando el escalado de Windows
        x = int(((sw / 2) - (w / 2)) * scale_factor)
        y = int(((sh / 2) - (h / 2)) * scale_factor)
        
        self.geometry(f"{w}x{h}+{x}+{y}")
        # ──────────────────────────────────────────────────────────

        # Ícono
        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

        self._build()
        self.focus_set()
        self.lift()

    def _build(self):
        scr = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scr.pack(fill="both", expand=True, padx=22, pady=18)

        # ── Encabezado ────────────────────────────────────────────
        ctk.CTkLabel(
            scr, text="📡",
            font=(T.F, 40)
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            scr, text="Extractor de Coordenadas RTK",
            font=(T.F, 16, "bold"), text_color=T.TXA
        ).pack()
        ctk.CTkLabel(
            scr, text=APP_SUBTITLE,
            font=(T.F, T.SZS), text_color=T.TX2
        ).pack(pady=(2, 4))
        ctk.CTkLabel(
            scr,
            text="Convierte archivos CSV densos de receptores GNSS RTK\n"
                  "en archivos TXT de puntos listos para Civil 3D, AutoCAD y QGIS.",
            font=(T.F, T.SZS), text_color=T.TX2, justify="center"
        ).pack(pady=(0, 14))

        # ── Separador ─────────────────────────────────────────────
        ctk.CTkFrame(scr, fg_color=T.BRD, height=1).pack(fill="x", pady=6)

        # ── Identificación ────────────────────────────────────────
        self._fila_info(scr, "Software:",  "Extractor de Coordenadas RTK")
        self._fila_info(scr, "Versión:",    VERSION)
        self._fila_info(scr, "Plataforma:", "Windows 10 / 11")

        ctk.CTkFrame(scr, fg_color=T.BRD, height=1).pack(fill="x", pady=6)

        # ── Propiedad y legal ─────────────────────────────────────
        self._fila_info(scr, "Copyright:",  "© 2026 — Archetris")
        self._fila_info(scr, "Creador:",    "ChrisSilver76")

        lnk = ctk.CTkLabel(
            scr, text="🔗  github.com/ChrisSilver76/repositories",
            font=(T.F, T.SZS), text_color="#4abae6", cursor="hand2"
        )
        lnk.pack(pady=(2, 2))
        lnk.bind(
            "<Button-1>",
            lambda e: webbrowser.open(
                "https://github.com/ChrisSilver76?tab=repositories"
            )
        )

        self._fila_info(scr, "Licencia:",   "MIT License — libre de usar y modificar")

        ctk.CTkFrame(scr, fg_color=T.BRD, height=1).pack(fill="x", pady=6)

        # ── Instrucciones de uso ──────────────────────────────────
        ctk.CTkLabel(
            scr, text="📖  Cómo usar el programa",
            font=(T.F, 13, "bold"), text_color=T.TX
        ).pack(pady=(4, 4), anchor="w")

        instrucciones = (
            "1. Arrastra uno o más archivos .CSV a la zona de carga,\n"
            "   o usa el botón 'SELECCIONAR .CSV'.\n\n"
            "2. Configura las opciones de cada archivo:\n"
            "   • Elevation: si lo desactivas, la cota se exporta como 0.\n"
            "   • Description: actívalo para incluir la columna de descripción.\n"
            "     Puedes editar el texto de la descripción manualmente.\n\n"
            "3. Usa los controles globales para aplicar la misma configuración\n"
            "   a todos los archivos a la vez.\n\n"
            "4. Haz clic en 'PROCESAR ARCHIVOS', elige la carpeta de destino\n"
            "   y espera a que finalice la exportación."
        )
        ctk.CTkLabel(
            scr, text=instrucciones,
            font=(T.F, T.SZS), text_color=T.TX2,
            justify="left", wraplength=440
        ).pack(pady=(0, 10), anchor="w")

        ctk.CTkFrame(scr, fg_color=T.BRD, height=1).pack(fill="x", pady=6)

        # ── Donaciones ────────────────────────────────────────────
        ctk.CTkLabel(
            scr, text="💛  APOYA ESTE PROYECTO",
            font=(T.F, 13, "bold"), text_color=T.TXWN
        ).pack(pady=(4, 2))
        ctk.CTkLabel(
            scr,
            text="Si este programa te fue útil, considera apoyar su desarrollo.",
            font=(T.F, T.SZS), text_color=T.TX2, justify="center"
        ).pack()
        ctk.CTkButton(
            scr, text="☕  Apoyar en Ko-Fi",
            font=(T.F, T.SZB, "bold"),
            fg_color="#FF5E5B", hover_color="#cc4b48",
            text_color="white", corner_radius=T.R,
            height=40, width=200,
            command=lambda: webbrowser.open("https://ko-fi.com/chrissilver76"),
        ).pack(pady=(10, 14))

        # ── Cerrar ────────────────────────────────────────────────
        ctk.CTkButton(
            scr, text="Cerrar",
            font=(T.F, T.SZS),
            fg_color=T.BG_CARD, hover_color=T.BRD,
            text_color=T.TX2, corner_radius=6,
            height=30, width=90,
            command=self.destroy,
        ).pack(pady=(0, 6))

    @staticmethod
    def _fila_info(parent, etiqueta: str, valor: str):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=1)
        ctk.CTkLabel(
            f, text=etiqueta,
            font=(T.F, T.SZS, "bold"), text_color=T.TX2,
            width=88, anchor="e"
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            f, text=valor,
            font=(T.F, T.SZS), text_color=T.TX, anchor="w"
        ).pack(side="left")


# ============================================================
#  VENTANA PRINCIPAL
# ============================================================
class App(ctk.CTk):
    """Ventana principal del Extractor de Coordenadas RTK.

    Hereda de ctk.CTk. Si DND_OK, inyecta TkinterDnD en el
    constructor antes de crear cualquier widget.
    """

    def __init__(self):
        super().__init__()

        # ── Inyectar Drag & Drop en la ventana CTk ────────────────
        if DND_OK:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                pass

        # ── Configuración visual ──────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=T.BG)

        # ── Título y geometría ────────────────────────────────────
        self.title(f"{APP_TITLE}  |  by ChrisSilver76  {VERSION}")
        
        # Dimensiones deseadas
        width, height = 860, 600
        
        # Lógica de centrado de GitHub
        scale_factor = self._get_window_scaling()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Usamos /2 para un centro exacto (o /1.5 si prefieres que esté un poco más arriba)
        x = int(((screen_width / 2) - (width / 2)) * scale_factor)
        y = int(((screen_height / 2) - (height / 2)) * scale_factor)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(width, height)

        # ── Icono ─────────────────────────────────────────────────
        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

        # ── Estado interno ────────────────────────────────────────
        self._busy   = False
        self._filas: list[FileRow] = []

        # ── Construir interfaz ────────────────────────────────────
        self._build()

    # ── Construcción de la interfaz ───────────────────────────────

    def _build(self):
        main = ctk.CTkFrame(self, fg_color=T.BG)
        main.pack(fill="both", expand=True)

        # Header fijo en la parte superior
        self._construir_header(main)

        # Separador visual
        ctk.CTkFrame(main, fg_color=T.BRD, height=1).pack(
            fill="x", padx=0
        )

        # ProgressBar anclada en la parte inferior ANTES que el contenido central
        # (pack en bottom)
        self.prog = ProgressBar(main, on_start=self._on_procesar_click)
        self.prog.pack(fill="x", side="bottom")

        # Contenedor central (DropZone + panel de config)
        self._frame_central = ctk.CTkFrame(main, fg_color=T.BG)
        self._frame_central.pack(fill="both", expand=True)

        # DropZone
        self.drop_zone = DropZone(
            self._frame_central,
            on_files_loaded=self._on_archivos_cargados
        )
        self.drop_zone.pack(fill="x", padx=T.P, pady=(T.P, 0))
        self.drop_zone.configure(height=180)

        # Panel de configuración (aparece cuando hay archivos)
        self.panel_config = ctk.CTkFrame(
            self._frame_central,
            fg_color=T.BG2,
            corner_radius=T.R,
        )
        # No se empaqueta hasta que haya archivos

    def _construir_header(self, parent):
        hdr = ctk.CTkFrame(parent, fg_color=T.BG2, height=58, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=T.P)

        # Ícono colorido a la izquierda
        ic = ctk.CTkFrame(inner, fg_color=T.ACC, corner_radius=6, width=38, height=38)
        ic.pack(side="left", padx=(0, 10), pady=10)
        ic.pack_propagate(False)
        ctk.CTkLabel(
            ic, text="RTK", font=(T.FM, 9, "bold"), text_color="white"
        ).place(relx=.5, rely=.5, anchor="center")

        # Título principal
        ctk.CTkLabel(
            inner, text=APP_TITLE,
            font=(T.F, T.SZT, "bold"), text_color=T.TX
        ).pack(side="left")

        # "by ChrisSilver76" + versión
        ctk.CTkLabel(
            inner, text="  by ChrisSilver76",
            font=(T.F, T.SZS), text_color=T.TXA
        ).pack(side="left", pady=(5, 0))
        ctk.CTkLabel(
            inner, text=f"  {VERSION}",
            font=(T.FM, T.SZS), text_color=T.TX2
        ).pack(side="left", pady=(5, 0))

        # Botón Info (esquina derecha)
        ctk.CTkButton(
            inner, text="ℹ  Acerca de",
            font=(T.F, T.SZS), width=110, height=30,
            fg_color=T.BG_CARD, hover_color=T.ACC,
            text_color=T.TX2, corner_radius=6,
            command=self._mostrar_about,
        ).pack(side="right", padx=4, pady=14)

    def _construir_panel_config(self, archivos: list[Path]):
        """Reconstruye el panel de configuración con los archivos actuales."""
        for w in self.panel_config.winfo_children():
            w.destroy()
        self._filas = []

        # ── Controles globales ────────────────────────────────────
        ctrl = ctk.CTkFrame(self.panel_config, fg_color="transparent")
        ctrl.pack(fill="x", padx=T.P, pady=(10, 4))

        ctk.CTkLabel(
            ctrl, text="Aplicar a todos:",
            font=(T.F, T.SZS, "bold"), text_color=T.TX2
        ).pack(side="left", padx=(0, 12))

        self.var_global_elev = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            ctrl, text="Todas Elevaciones",
            variable=self.var_global_elev,
            font=(T.F, T.SZS), text_color=T.TX,
            fg_color=T.ACC, hover_color=T.ACC_H,
            command=self._on_global_elev,
        ).pack(side="left", padx=8)

        self.var_global_desc = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            ctrl, text="Todas Descripciones",
            variable=self.var_global_desc,
            font=(T.F, T.SZS), text_color=T.TX,
            fg_color=T.ACC, hover_color=T.ACC_H,
            command=self._on_global_desc,
        ).pack(side="left", padx=8)

        # ── Encabezado de columnas ────────────────────────────────
        hdr_cols = ctk.CTkFrame(self.panel_config, fg_color="transparent")
        hdr_cols.pack(fill="x", padx=T.P, pady=(0, 2))
        columnas = [
            ("Archivo",           104),
            ("Name",               68),
            ("Easting",            68),
            ("Northing",           68),
            ("Elevation",          78),
            ("Description",        88),
            ("Descripción manual", 155),
        ]
        for nombre_col, ancho in columnas:
            ctk.CTkLabel(
                hdr_cols, text=nombre_col,
                font=(T.F, 9, "bold"), text_color=T.TXD,
                width=ancho, anchor="w"
            ).pack(side="left", padx=3)

        # ── Lista scrollable de filas ─────────────────────────────
        scroll = ctk.CTkScrollableFrame(
            self.panel_config,
            fg_color="transparent",
            corner_radius=0,
        )
        scroll.pack(fill="both", expand=True, padx=T.P, pady=(0, 8))

        for ruta in archivos:
            fila = FileRow(scroll, ruta)
            fila.pack(fill="x", pady=3)
            self._filas.append(fila)

    # ── Eventos ───────────────────────────────────────────────────

    def _on_archivos_cargados(self, archivos: list[Path]):
        """Callback del DropZone — muestra u oculta el panel de config."""
        if not archivos:
            self.panel_config.pack_forget()
            return
        self._construir_panel_config(archivos)
        self.panel_config.pack(
            fill="both", expand=True,
            padx=T.P, pady=(6, 0),
        )

    def _on_global_elev(self):
        val = self.var_global_elev.get()
        for fila in self._filas:
            fila.set_elevation(val)

    def _on_global_desc(self):
        val = self.var_global_desc.get()
        for fila in self._filas:
            fila.set_description_active(val)

    # ── Procesamiento ─────────────────────────────────────────────

    def _on_procesar_click(self):
        """Punto de entrada del procesamiento: valida, pide destino y lanza hilo."""
        if self._busy:
            return
        archivos = self.drop_zone.get_archivos()
        if not archivos:
            Toast(self, "Primero carga al menos un archivo CSV.", ok=False)
            return

        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if not carpeta:
            return

        # Capturar configuración de las filas en el hilo principal
        # (para no acceder a widgets desde el hilo de trabajo)
        config_filas = []
        for i, fila in enumerate(self._filas):
            config_filas.append({
                "incluir_elev":  fila.get_elevation(),
                "incluir_desc":  fila.get_description_active(),
                "desc_texto":    fila.get_desc_texto(),
            })

        self._busy = True
        self.prog.busy()

        threading.Thread(
            target=self._worker,
            args=(archivos, Path(carpeta), config_filas),
            daemon=True,
        ).start()

    def _worker(
        self,
        archivos: list[Path],
        carpeta_destino: Path,
        config_filas: list[dict],
    ):
        """Hilo de trabajo — NUNCA toca widgets directamente.

        Toda actualización de la UI se delega a self.after(0, lambda: ...)
        para garantizar thread-safety con Tkinter.
        """
        total        = len(archivos)
        puntos_total = 0

        for idx, ruta in enumerate(archivos):
            cfg = config_filas[idx] if idx < len(config_filas) else {}

            ruta_salida = calcular_ruta_salida(ruta.stem, carpeta_destino)

            # Función de progreso: proyecta el progreso local al global
            def cb_progreso(p_local, i=idx):
                p_global = (i + p_local) / total
                msg = f"Procesando ({i + 1}/{total}): {ruta.name}"
                self.after(0, lambda v=p_global, m=msg: self.prog.set(v, m))

            puntos = exportar_csv_a_txt(
                ruta_csv=ruta,
                ruta_salida=ruta_salida,
                incluir_elevation=cfg.get("incluir_elev", True),
                incluir_description=cfg.get("incluir_desc", False),
                descripcion_override=cfg.get("desc_texto", ""),
                log_fn=lambda m: None,  # Sin consola en esta versión
                progress_cb=cb_progreso,
            )
            puntos_total += puntos

        # Notificar al hilo principal que terminó
        self.after(0, lambda: self._proceso_terminado(total, puntos_total))

    def _proceso_terminado(self, n_archivos: int, n_puntos: int):
        """Restaura la UI al estado de reposo una vez finalizado el proceso."""
        self._busy = False
        self.prog.idle()
        self.prog.set(1.0, f"✅ {n_archivos} archivo(s) exportados — {n_puntos} puntos totales")
        Toast(
            self,
            f"¡Proceso completado!  {n_archivos} archivo(s)  •  {n_puntos} puntos",
            ms=4000,
        )

    # ── Modal Acerca de ───────────────────────────────────────────

    def _mostrar_about(self):
        AboutModal(self)


# ============================================================
#  PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    app = App()
    app.mainloop()
