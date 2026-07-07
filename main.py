import io
import re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="EVALUATEC | Resultados",
    page_icon="📘",
    layout="wide"
)

st.title("📘 Resultados EVALUATEC")
st.caption(
    "Concentrado de participación y desempeño promedio por carrera."
)


# ============================================================
# CATÁLOGOS
# ============================================================

ETIQUETAS_AREAS = {
    "ING": "ING · Inglés",
    "MAT": "MAT · Matemáticas",
    "COM": "COM · Comprensión lectora",
    "RLM": "RLM · Razonamiento lógico-matemático",
    "PM": "PM · Pensamiento matemático",
    "ARQ": "ARQ · Arquitectura",
    "FIS": "FIS · Física",
    "ADMN": "ADMN · Administración"
}

ORDEN_AREAS = [
    "ING",
    "MAT",
    "COM",
    "RLM",
    "PM",
    "FIS",
    "ARQ",
    "ADMN"
]


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def normalizar_texto(valor):
    """Normaliza texto para comparar encabezados y respuestas."""

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return " ".join(texto.split())


def limpiar_nombre_carrera(valor):
    """Limpia espacios y unifica visualmente el nombre de carrera."""

    if pd.isna(valor):
        return "Sin carrera especificada"

    return " ".join(str(valor).strip().split())


def encontrar_columna(df, posibles_nombres):
    """Encuentra una columna ignorando mayúsculas, acentos y espacios."""

    columnas_normalizadas = {
        normalizar_texto(columna): columna
        for columna in df.columns
    }

    for posible in posibles_nombres:
        posible_normalizado = normalizar_texto(posible)

        if posible_normalizado in columnas_normalizadas:
            return columnas_normalizadas[posible_normalizado]

    return None


def leer_csv_archivo(archivo):
    """Lee CSV intentando codificaciones frecuentes."""

    contenido = archivo.getvalue()

    codificaciones = [
        "utf-8",
        "utf-8-sig",
        "latin-1",
        "cp1252"
    ]

    separadores = [
        ",",
        ";"
    ]

    for codificacion in codificaciones:
        for separador in separadores:
            try:
                df = pd.read_csv(
                    io.BytesIO(contenido),
                    encoding=codificacion,
                    sep=separador
                )

                if len(df.columns) > 1:
                    return df

            except UnicodeDecodeError:
                continue
            except Exception:
                continue

    return pd.read_csv(
        io.BytesIO(contenido),
        encoding="latin-1"
    )


def identificar_bloque_archivo(nombre_archivo):
    """Obtiene el bloque académico desde el nombre del archivo."""

    nombre = normalizar_texto(nombre_archivo)

    if "administracion" in nombre:
        return "Administración"

    if "arquitectura" in nombre:
        return "Arquitectura"

    if "ingenieria" in nombre:
        return "Ingeniería"

    return nombre_archivo


def convertir_porcentaje(valor):
    """
    Convierte valores de porcentaje a número entre 0 y 100.
    Soporta texto como 75%, 75.5, 0.75 o campos vacíos.
    """

    if pd.isna(valor):
        return None

    texto = str(valor).strip()

    if texto == "":
        return None

    texto = texto.replace("%", "")
    texto = texto.replace(",", ".")

    try:
        numero = float(texto)
    except ValueError:
        return None

    if 0 <= numero <= 1:
        return numero * 100

    if 0 <= numero <= 100:
        return numero

    return None


# ============================================================
# DETECCIÓN DE ÁREAS
# ============================================================

def detectar_columnas_areas(df):
    """
    Detecta columnas tipo:
    AreaGRALSeccionMATPorcentajeCorrectas
    AreaGRALSeccionINGPorcentajeCorrectas
    """

    areas_detectadas = {}

    for columna in df.columns:
        columna_normalizada = normalizar_texto(columna)

        if not columna_normalizada.startswith("areagral"):
            continue

        if "seccion" not in columna_normalizada:
            continue

        if "porcentajecorrectas" not in columna_normalizada:
            continue

        coincidencia = re.search(
            r"seccion([a-z]+)porcentajecorrectas",
            columna_normalizada
        )

        if coincidencia:
            codigo = coincidencia.group(1).upper()
            areas_detectadas[codigo] = columna

    areas_ordenadas = {}

    for codigo in ORDEN_AREAS:
        if codigo in areas_detectadas:
            areas_ordenadas[codigo] = areas_detectadas[codigo]

    for codigo, columna in areas_detectadas.items():
        if codigo not in areas_ordenadas:
            areas_ordenadas[codigo] = columna

    return areas_ordenadas


# ============================================================
# PROCESAMIENTO
# ============================================================

def procesar_archivo(archivo):
    """
    Lee un archivo, identifica carrera, inicio de examen y áreas.
    """

    df = leer_csv_archivo(archivo)

    columna_carrera = encontrar_columna(
        df,
        [
            "Carrera"
        ]
    )

    columna_inicio = encontrar_columna(
        df,
        [
            "InicioExamen",
            "Inicio Examen",
            "Inició examen",
            "Inicio"
        ]
    )

    if columna_carrera is None:
        raise ValueError(
            f"El archivo {archivo.name} no contiene la columna Carrera."
        )

    if columna_inicio is None:
        raise ValueError(
            f"El archivo {archivo.name} no contiene la columna InicioExamen."
        )

    areas_detectadas = detectar_columnas_areas(df)

    if not areas_detectadas:
        raise ValueError(
            f"El archivo {archivo.name} no contiene áreas de evaluación detectables."
        )

    df["Archivo_origen"] = archivo.name
    df["Bloque_academico"] = identificar_bloque_archivo(
        archivo.name
    )

    df["Carrera_normalizada"] = df[columna_carrera].apply(
        limpiar_nombre_carrera
    )

    df["Inicio_normalizado"] = df[columna_inicio].apply(
        normalizar_texto
    )

    df["Estatus_inicio"] = df["Inicio_normalizado"].apply(
        lambda valor: (
            "Inició"
            if valor in ["si", "sí", "s", "1", "true"]
            else "No inició"
        )
    )

    for codigo, columna in areas_detectadas.items():
        df[f"Area_{codigo}"] = df[columna].apply(
            convertir_porcentaje
        )

    return df, areas_detectadas


def crear_resumen_inicio(df):
    """Genera concentración de participantes por carrera e inicio."""

    resumen = (
        df
        .groupby(
            [
                "Carrera_normalizada",
                "Estatus_inicio"
            ]
        )
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    if "Inició" not in resumen.columns:
        resumen["Inició"] = 0

    if "No inició" not in resumen.columns:
        resumen["No inició"] = 0

    resumen["Participantes"] = (
        resumen["Inició"]
        + resumen["No inició"]
    )

    resumen["% inició"] = (
        resumen["Inició"]
        / resumen["Participantes"]
        * 100
    ).round(1)

    return resumen.sort_values(
        "Participantes",
        ascending=False
    ).reset_index(drop=True)


def crear_promedios_radar(df, areas_detectadas):
    """
    Calcula el promedio por área para cada carrera,
    usando únicamente participantes que iniciaron examen.
    """

    df_iniciaron = df[
        df["Estatus_inicio"] == "Inició"
    ].copy()

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
    ]

    if df_iniciaron.empty:
        return pd.DataFrame()

    promedios = (
        df_iniciaron
        .groupby("Carrera_normalizada")[columnas_areas]
        .mean()
        .reset_index()
    )

    conteos = (
        df_iniciaron
        .groupby("Carrera_normalizada")
        .size()
        .reset_index(name="Participantes_iniciaron")
    )

    promedios = promedios.merge(
        conteos,
        on="Carrera_normalizada",
        how="left"
    )

    return promedios


# ============================================================
# GRÁFICAS
# ============================================================

def mostrar_radar_carrera(
    fila_carrera,
    areas_detectadas,
    titulo
):
    """Genera radar de desempeño promedio para una carrera."""

    codigos_areas = list(areas_detectadas.keys())

    etiquetas = [
        ETIQUETAS_AREAS.get(
            codigo,
            codigo
        )
        for codigo in codigos_areas
    ]

    valores = []

    for codigo in codigos_areas:
        valor = fila_carrera.get(f"Area_{codigo}")

        if pd.isna(valor):
            valor = 0

        valores.append(round(float(valor), 1))

    etiquetas_cerradas = etiquetas + [etiquetas[0]]
    valores_cerrados = valores + [valores[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=valores_cerrados,
            theta=etiquetas_cerradas,
            fill="toself",
            name="Promedio",
            hovertemplate=(
                "<b>%{theta}</b><br>"
                "Promedio: %{r:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title=titulo,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix="%"
            )
        ),
        showlegend=False,
        height=440,
        margin=dict(
            t=70,
            b=35,
            l=45,
            r=45
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


def mostrar_radares_bloque(
    df_bloque,
    areas_detectadas,
    nombre_bloque
):
    """Muestra un radar por carrera dentro de cada archivo."""

    promedios = crear_promedios_radar(
        df_bloque,
        areas_detectadas
    )

    if promedios.empty:
        st.info(
            f"No hay participantes que hayan iniciado la evaluación en {nombre_bloque}."
        )
        return

    carreras = promedios.sort_values(
        "Participantes_iniciaron",
        ascending=False
    ).reset_index(drop=True)

    columnas = st.columns(2)

    for indice, (_, fila) in enumerate(carreras.iterrows()):
        carrera = fila["Carrera_normalizada"]
        participantes = int(fila["Participantes_iniciaron"])

        with columnas[indice % 2]:
            mostrar_radar_carrera(
                fila,
                areas_detectadas,
                f"{carrera} · n={participantes}"
            )

    etiquetas = [
        ETIQUETAS_AREAS.get(codigo, codigo)
        for codigo in areas_detectadas.keys()
    ]

    st.caption(
        "Dimensiones evaluadas: " + " | ".join(etiquetas)
    )


# ============================================================
# CARGA DE ARCHIVOS
# ============================================================

st.sidebar.header("Carga de archivos")

archivos_subidos = st.sidebar.file_uploader(
    "Carga los 3 archivos oficiales de EVALUATEC",
    type=["csv"],
    accept_multiple_files=True
)

if not archivos_subidos:
    st.info(
        "Carga los tres archivos CSV: Administración, Arquitectura e Ingeniería."
    )
    st.stop()

if len(archivos_subidos) != 3:
    st.warning(
        f"Actualmente cargaste {len(archivos_subidos)} archivo(s). "
        "Para este módulo deben cargarse exactamente 3."
    )
    st.stop()


# ============================================================
# PROCESAMIENTO DE ARCHIVOS
# ============================================================

bases = []
datos_por_bloque = {}
errores = []

for archivo in archivos_subidos:
    try:
        df_archivo, areas_detectadas = procesar_archivo(
            archivo
        )

        bloque = df_archivo["Bloque_academico"].iloc[0]

        bases.append(df_archivo)

        datos_por_bloque[bloque] = {
            "df": df_archivo,
            "areas": areas_detectadas,
            "archivo": archivo.name
        }

    except Exception as error:
        errores.append(
            f"{archivo.name}: {error}"
        )

if errores:
    for error in errores:
        st.error(error)

if not bases:
    st.stop()

df_general = pd.concat(
    bases,
    ignore_index=True,
    sort=False
)


# ============================================================
# RESUMEN GENERAL
# ============================================================

st.subheader("Resumen general")

total_participantes = len(df_general)
total_iniciaron = (
    df_general["Estatus_inicio"] == "Inició"
).sum()

total_no_iniciaron = (
    df_general["Estatus_inicio"] == "No inició"
).sum()

total_carreras = df_general[
    "Carrera_normalizada"
].nunique()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Participantes", f"{total_participantes:,}")
col2.metric("Carreras detectadas", f"{total_carreras:,}")
col3.metric("Iniciaron evaluación", f"{total_iniciaron:,}")
col4.metric("No iniciaron", f"{total_no_iniciaron:,}")


# ============================================================
# RESUMEN DE INICIO POR BLOQUE
# ============================================================

st.markdown("## Participación por bloque académico")

bloques_ordenados = [
    "Administración",
    "Arquitectura",
    "Ingeniería"
]

bloques_disponibles = [
    bloque
    for bloque in bloques_ordenados
    if bloque in datos_por_bloque
]

for bloque in bloques_disponibles:
    df_bloque = datos_por_bloque[bloque]["df"]

    participantes = len(df_bloque)
    iniciaron = (
        df_bloque["Estatus_inicio"] == "Inició"
    ).sum()

    no_iniciaron = (
        df_bloque["Estatus_inicio"] == "No inició"
    ).sum()

    porcentaje_inicio = (
        iniciaron / participantes * 100
        if participantes > 0
        else 0
    )

    st.markdown(f"### {bloque}")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Participantes", f"{participantes:,}")
    col2.metric("Carreras", f"{df_bloque['Carrera_normalizada'].nunique():,}")
    col3.metric("Iniciaron", f"{iniciaron:,}")
    col4.metric(
        "% de inicio",
        f"{porcentaje_inicio:.1f}%"
    )


# ============================================================
# RADARES POR ARCHIVO Y CARRERA
# ============================================================

st.markdown("## Desempeño promedio por carrera")

for bloque in bloques_disponibles:
    df_bloque = datos_por_bloque[bloque]["df"]
    areas_detectadas = datos_por_bloque[bloque]["areas"]
    archivo_origen = datos_por_bloque[bloque]["archivo"]

    st.markdown(f"# {bloque}")
    st.caption(f"Archivo: {archivo_origen}")

    mostrar_radares_bloque(
        df_bloque,
        areas_detectadas,
        bloque
    )
