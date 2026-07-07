import io
import re
import unicodedata

import pandas as pd
import plotly.express as px
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
    "Participación y desempeño promedio de aspirantes por bloque académico."
)


# ============================================================
# CATÁLOGOS
# ============================================================

ETIQUETAS_AREAS = {
    "ING": "Inglés",
    "MAT": "Matemáticas",
    "COM": "Comprensión lectora",
    "RLM": "Razonamiento lógico-matemático",
    "PM": "Pensamiento matemático",
    "ARQ": "Arquitectura",
    "FIS": "Física",
    "ADMN": "Administración"
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

ORDEN_BLOQUES = [
    "Administración",
    "Arquitectura",
    "Ingeniería"
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
    """Limpia espacios en el nombre de carrera."""

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
    """Lee un CSV intentando codificaciones y separadores frecuentes."""

    contenido = archivo.getvalue()

    codificaciones = [
        "utf-8",
        "utf-8-sig",
        "latin-1",
        "cp1252"
    ]

    separadores = [
        ",",
        ";",
        "\t"
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

            except Exception:
                continue

    return pd.read_csv(
        io.BytesIO(contenido),
        encoding="latin-1"
    )


def identificar_bloque_archivo(nombre_archivo):
    """Identifica el bloque académico desde el nombre del archivo."""

    nombre = normalizar_texto(nombre_archivo)

    if "administracion" in nombre:
        return "Administración"

    if "arquitectura" in nombre:
        return "Arquitectura"

    if "ingenieria" in nombre:
        return "Ingeniería"

    return nombre_archivo


def clasificar_inicio(valor):
    """
    Clasifica si la persona inició el examen.

    Considera como no iniciado:
    vacío, no, falso, 0, no iniciado, pendiente, etc.
    Cualquier fecha, hora o valor positivo se considera iniciado.
    """

    if pd.isna(valor):
        return "No inició"

    texto = normalizar_texto(valor)

    valores_no_inicio = [
        "",
        "no",
        "n",
        "false",
        "falso",
        "0",
        "no inicio",
        "no iniciado",
        "pendiente",
        "null",
        "nan",
        "none"
    ]

    if texto in valores_no_inicio:
        return "No inició"

    if "no inicio" in texto:
        return "No inició"

    return "Inició"


def convertir_porcentaje(valor):
    """
    Convierte valores a porcentaje 0-100.

    Acepta formatos como:
    75
    75.5
    75%
    0.75
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


def hex_a_rgba(color_hex, alpha=0.18):
    """Convierte color hexadecimal a rgba para rellenos semitransparentes."""

    color_hex = color_hex.lstrip("#")

    if len(color_hex) != 6:
        return f"rgba(120, 120, 120, {alpha})"

    rojo = int(color_hex[0:2], 16)
    verde = int(color_hex[2:4], 16)
    azul = int(color_hex[4:6], 16)

    return f"rgba({rojo}, {verde}, {azul}, {alpha})"


# ============================================================
# DETECCIÓN DE ÁREAS
# ============================================================

def detectar_columnas_areas(df):
    """
    Detecta encabezados de áreas como:

    AreaGRALSeccionINGPorcentajeCorrectas
    AreaGRALSeccionMATPorcentajeCorrectas
    AreaGRALSeccionCOMPorcentajeCorrectas
    """

    areas_detectadas = {}

    for columna in df.columns:
        columna_normalizada = normalizar_texto(columna)

        if "seccion" not in columna_normalizada:
            continue

        if "porcentajecorrectas" not in columna_normalizada:
            continue

        coincidencia = re.search(
            r"seccion([a-z0-9]+?)porcentajecorrectas",
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
# PROCESAMIENTO DE ARCHIVOS
# ============================================================

def procesar_archivo(archivo):
    """Lee y prepara un archivo EVALUATEC."""

    df = leer_csv_archivo(archivo)

    columna_carrera = encontrar_columna(
        df,
        ["Carrera"]
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
            f"No se detectaron columnas Area...PorcentajeCorrectas "
            f"en {archivo.name}."
        )

    df["Archivo_origen"] = archivo.name
    df["Bloque_academico"] = identificar_bloque_archivo(
        archivo.name
    )

    df["Carrera_normalizada"] = df[columna_carrera].apply(
        limpiar_nombre_carrera
    )

    df["Estatus_inicio"] = df[columna_inicio].apply(
        clasificar_inicio
    )

    for codigo, columna in areas_detectadas.items():
        df[f"Area_{codigo}"] = df[columna].apply(
            convertir_porcentaje
        )

    return df, areas_detectadas


def crear_promedios_por_carrera(df, areas_detectadas):
    """
    Calcula promedios por carrera usando solamente
    aspirantes que iniciaron la evaluación.
    """

    df_iniciaron = df[
        df["Estatus_inicio"] == "Inició"
    ].copy()

    if df_iniciaron.empty:
        return pd.DataFrame()

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
    ]

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

    return promedios.sort_values(
        "Participantes_iniciaron",
        ascending=False
    ).reset_index(drop=True)


def crear_mapa_colores_carreras(df_general):
    """Asigna colores fijos por carrera para todos los radares."""

    paleta = (
        px.colors.qualitative.Alphabet
        + px.colors.qualitative.Dark24
        + px.colors.qualitative.Bold
        + px.colors.qualitative.Set3
    )

    carreras = sorted(
        df_general["Carrera_normalizada"]
        .dropna()
        .astype(str)
        .unique()
    )

    return {
        carrera: paleta[indice % len(paleta)]
        for indice, carrera in enumerate(carreras)
    }


# ============================================================
# GRÁFICAS
# ============================================================

def mostrar_radar_comparativo(
    df_bloque,
    areas_detectadas,
    nombre_bloque,
    mapa_colores_carreras
):
    """
    Muestra un solo radar por archivo.

    Cada carrera se representa con una línea y color diferente.
    """

    promedios = crear_promedios_por_carrera(
        df_bloque,
        areas_detectadas
    )

    if promedios.empty:
        st.info(
            f"No hay aspirantes que hayan iniciado el examen en {nombre_bloque}."
        )
        return

    codigos_areas = list(areas_detectadas.keys())

    etiquetas = [
        ETIQUETAS_AREAS.get(codigo, codigo)
        for codigo in codigos_areas
    ]

    etiquetas_cerradas = etiquetas + [etiquetas[0]]

    fig = go.Figure()

    for _, fila in promedios.iterrows():
        carrera = fila["Carrera_normalizada"]
        participantes = int(fila["Participantes_iniciaron"])

        valores = []

        for codigo in codigos_areas:
            valor = fila.get(f"Area_{codigo}")

            if pd.isna(valor):
                valor = 0

            valores.append(round(float(valor), 1))

        valores_cerrados = valores + [valores[0]]

        color = mapa_colores_carreras.get(
            carrera,
            "#808080"
        )

        fig.add_trace(
            go.Scatterpolar(
                r=valores_cerrados,
                theta=etiquetas_cerradas,
                mode="lines+markers",
                name=f"{carrera} · n={participantes}",
                line=dict(
                    color=color,
                    width=3
                ),
                marker=dict(
                    color=color,
                    size=7
                ),
                fill="toself",
                fillcolor=hex_a_rgba(
                    color,
                    alpha=0.12
                ),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{theta}: %{r:.1f}%"
                    "<extra></extra>"
                )
            )
        )

    fig.update_layout(
        title=f"Desempeño promedio por carrera · {nombre_bloque}",
        template="plotly_dark",
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix="%",
                gridcolor="rgba(190,190,190,0.45)",
                linecolor="rgba(190,190,190,0.45)"
            ),
            angularaxis=dict(
                gridcolor="rgba(190,190,190,0.45)",
                linecolor="rgba(190,190,190,0.45)"
            )
        ),
        legend=dict(
            title="Carreras",
            orientation="v",
            x=1.05,
            y=1
        ),
        height=650,
        margin=dict(
            t=80,
            b=35,
            l=50,
            r=260
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Puedes seleccionar una carrera en la leyenda para ocultarla o mostrarla."
    )


# ============================================================
# RESÚMENES VISUALES
# ============================================================

def mostrar_resumen_bloque(df_bloque, nombre_bloque):
    """Muestra indicadores generales del bloque."""

    participantes = len(df_bloque)

    iniciaron = (
        df_bloque["Estatus_inicio"] == "Inició"
    ).sum()

    no_iniciaron = (
        df_bloque["Estatus_inicio"] == "No inició"
    ).sum()

    carreras = df_bloque[
        "Carrera_normalizada"
    ].nunique()

    porcentaje_inicio = (
        iniciaron / participantes * 100
        if participantes > 0
        else 0
    )

    st.markdown(f"### {nombre_bloque}")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Participantes", f"{participantes:,}")
    col2.metric("Carreras", f"{carreras:,}")
    col3.metric("Iniciaron", f"{iniciaron:,}")
    col4.metric("% de inicio", f"{porcentaje_inicio:.1f}%")


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
# LECTURA E INTEGRACIÓN
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

mapa_colores_carreras = crear_mapa_colores_carreras(
    df_general
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
# PARTICIPACIÓN POR BLOQUE
# ============================================================

st.markdown("## Participación por bloque académico")

bloques_disponibles = [
    bloque
    for bloque in ORDEN_BLOQUES
    if bloque in datos_por_bloque
]

for bloque in bloques_disponibles:
    mostrar_resumen_bloque(
        datos_por_bloque[bloque]["df"],
        bloque
    )


# ============================================================
# RADARES COMPARATIVOS
# ============================================================

st.markdown("## Comparativo de desempeño por carrera")

for bloque in bloques_disponibles:
    informacion_bloque = datos_por_bloque[bloque]

    st.markdown(f"## {bloque}")
    st.caption(
        f"Archivo analizado: {informacion_bloque['archivo']}"
    )

    mostrar_radar_comparativo(
        df_bloque=informacion_bloque["df"],
        areas_detectadas=informacion_bloque["areas"],
        nombre_bloque=bloque,
        mapa_colores_carreras=mapa_colores_carreras
    )
