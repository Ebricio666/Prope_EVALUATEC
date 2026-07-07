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
    page_title="EVALUATEC 2026",
    page_icon="📘",
    layout="wide"
)

st.title("📘 Resultados EVALUATEC 2026")
st.caption(
    "Comparativo de desempeño por bloque académico y carrera."
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

BLOQUES = {
    "ADM": "Administración",
    "ARQ": "Arquitectura",
    "ING": "Ingeniería"
}

ORDEN_NIVELES = [
    "Bajo",
    "Básico",
    "Satisfactorio",
    "Alto"
]

COLORES_NIVELES = {
    "Bajo": "#E74C3C",
    "Básico": "#F39C12",
    "Satisfactorio": "#F1C40F",
    "Alto": "#27AE60"
}


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def normalizar_texto(valor):
    """Normaliza texto para comparaciones."""

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
    """Limpia espacios repetidos del nombre de carrera."""

    if pd.isna(valor):
        return "Sin carrera especificada"

    return " ".join(str(valor).strip().split())


def encontrar_columna(df, posibles_nombres):
    """Encuentra una columna ignorando acentos, espacios y mayúsculas."""

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
    """Lee un archivo CSV intentando formatos frecuentes."""

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
    """Identifica ADM, ARQ o ING desde el nombre del archivo."""

    nombre = normalizar_texto(nombre_archivo)

    if "administracion" in nombre:
        return "ADM"

    if "arquitectura" in nombre:
        return "ARQ"

    if "ingenieria" in nombre:
        return "ING"

    return None


def clasificar_inicio(valor):
    """Clasifica si el aspirante inició la evaluación."""

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
    """Convierte datos a una escala de 0 a 100."""

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


def hex_a_rgba(color_hex, alpha=0.12):
    """Convierte un color hexadecimal a rgba."""

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
    Detecta columnas como:
    AreaGRALSeccionINGPorcentajeCorrectas
    AreaGRALSeccionMATPorcentajeCorrectas
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
    """Lee y prepara un archivo de resultados EVALUATEC."""

    df = leer_csv_archivo(archivo)

    bloque = identificar_bloque_archivo(archivo.name)

    if bloque is None:
        raise ValueError(
            "No se identificó el bloque. "
            "El archivo debe contener Administración, Arquitectura o Ingeniería."
        )

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
            f"{archivo.name}: no se encontró la columna Carrera."
        )

    if columna_inicio is None:
        raise ValueError(
            f"{archivo.name}: no se encontró la columna InicioExamen."
        )

    areas_detectadas = detectar_columnas_areas(df)

    if not areas_detectadas:
        raise ValueError(
            f"{archivo.name}: no se detectaron áreas de evaluación."
        )

    df["Archivo_origen"] = archivo.name
    df["Bloque"] = bloque

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

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
    ]

    df["Promedio_global_individual"] = df[
        columnas_areas
    ].mean(axis=1)

    return df, areas_detectadas


def crear_mapa_colores_carreras(df):
    """Asigna colores distintos y consistentes a cada carrera."""

    paleta = (
        px.colors.qualitative.Alphabet
        + px.colors.qualitative.Dark24
        + px.colors.qualitative.Bold
        + px.colors.qualitative.Set3
    )

    carreras = sorted(
        df["Carrera_normalizada"]
        .dropna()
        .astype(str)
        .unique()
    )

    return {
        carrera: paleta[indice % len(paleta)]
        for indice, carrera in enumerate(carreras)
    }


def crear_promedios_por_carrera(df, areas_detectadas):
    """Calcula promedio por dimensión para cada carrera."""

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


def clasificar_nivel_desempeno(valor):
    """
    Clasifica el promedio individual en bloques de 25%.

    Bajo: 0–24%
    Básico: 25–49%
    Satisfactorio: 50–74%
    Alto: 75–100%
    """

    if pd.isna(valor):
        return "Sin dato"

    if 0 <= valor < 25:
        return "Bajo"

    if 25 <= valor < 50:
        return "Básico"

    if 50 <= valor < 75:
        return "Satisfactorio"

    if 75 <= valor <= 100:
        return "Alto"

    return "Sin dato"


def crear_distribucion_desempeno(df):
    """Genera distribución del semáforo por carrera."""

    df_iniciaron = df[
        (
            df["Estatus_inicio"] == "Inició"
        )
        &
        (
            df["Promedio_global_individual"].notna()
        )
    ].copy()

    if df_iniciaron.empty:
        return pd.DataFrame()

    df_iniciaron["Nivel_desempeno"] = df_iniciaron[
        "Promedio_global_individual"
    ].apply(clasificar_nivel_desempeno)

    df_iniciaron = df_iniciaron[
        df_iniciaron["Nivel_desempeno"].isin(ORDEN_NIVELES)
    ].copy()

    if df_iniciaron.empty:
        return pd.DataFrame()

    totales = (
        df_iniciaron
        .groupby("Carrera_normalizada")
        .size()
        .reset_index(name="Total")
        .sort_values("Total", ascending=False)
    )

    tabla = (
        df_iniciaron
        .groupby(
            [
                "Carrera_normalizada",
                "Nivel_desempeno"
            ]
        )
        .size()
        .reset_index(name="Aspirantes")
    )

    carreras = totales["Carrera_normalizada"].tolist()

    combinaciones = pd.MultiIndex.from_product(
        [
            carreras,
            ORDEN_NIVELES
        ],
        names=[
            "Carrera_normalizada",
            "Nivel_desempeno"
        ]
    ).to_frame(index=False)

    tabla = combinaciones.merge(
        tabla,
        on=[
            "Carrera_normalizada",
            "Nivel_desempeno"
        ],
        how="left"
    )

    tabla["Aspirantes"] = tabla["Aspirantes"].fillna(0)

    tabla = tabla.merge(
        totales,
        on="Carrera_normalizada",
        how="left"
    )

    tabla["Porcentaje"] = (
        tabla["Aspirantes"]
        / tabla["Total"]
        * 100
    )

    tabla["Etiqueta"] = tabla["Porcentaje"].apply(
        lambda valor: f"{valor:.0f}%" if valor >= 8 else ""
    )

    tabla["Carrera_etiqueta"] = tabla.apply(
        lambda fila: (
            f"{fila['Carrera_normalizada']} "
            f"(n={int(fila['Total'])})"
        ),
        axis=1
    )

    etiquetas_ordenadas = [
        f"{fila['Carrera_normalizada']} (n={int(fila['Total'])})"
        for _, fila in totales.iterrows()
    ]

    tabla["Carrera_etiqueta"] = pd.Categorical(
        tabla["Carrera_etiqueta"],
        categories=etiquetas_ordenadas[::-1],
        ordered=True
    )

    tabla["Nivel_desempeno"] = pd.Categorical(
        tabla["Nivel_desempeno"],
        categories=ORDEN_NIVELES,
        ordered=True
    )

    return tabla


# ============================================================
# GRÁFICAS
# ============================================================

def mostrar_radar_comparativo(
    df_bloque,
    areas_detectadas,
    nombre_bloque,
    mapa_colores_carreras
):
    """Muestra solo un radar comparativo por bloque."""

    promedios = crear_promedios_por_carrera(
        df_bloque,
        areas_detectadas
    )

    if promedios.empty:
        st.info(
            f"No hay participantes que hayan iniciado la evaluación en {nombre_bloque}."
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
                    alpha=0.10
                ),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{theta}: %{r:.1f}%"
                    "<extra></extra>"
                )
            )
        )

    fig.update_layout(
        title=f"Promedio de dimensiones · {nombre_bloque}",
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
        height=680,
        margin=dict(
            t=80,
            b=40,
            l=50,
            r=260
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Selecciona una carrera en la leyenda para ocultarla o mostrarla."
    )


def mostrar_semaforo_desempeno(
    df_bloque,
    nombre_bloque
):
    """Muestra semáforo de desempeño global por carrera."""

    tabla = crear_distribucion_desempeno(df_bloque)

    if tabla.empty:
        st.info(
            f"No hay datos suficientes para generar el semáforo en {nombre_bloque}."
        )
        return

    altura = max(
        470,
        len(tabla["Carrera_etiqueta"].unique()) * 90
    )

    fig = px.bar(
        tabla,
        x="Porcentaje",
        y="Carrera_etiqueta",
        color="Nivel_desempeno",
        orientation="h",
        barmode="stack",
        text="Etiqueta",
        custom_data=[
            "Aspirantes",
            "Total"
        ],
        category_orders={
            "Nivel_desempeno": ORDEN_NIVELES
        },
        color_discrete_map=COLORES_NIVELES
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate=(
            "<b>Carrera:</b> %{y}<br>"
            "<b>Nivel:</b> %{fullData.name}<br>"
            "<b>Aspirantes:</b> %{customdata[0]} de %{customdata[1]}<br>"
            "<b>Porcentaje:</b> %{x:.1f}%"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        title=f"Semáforo de calificación obtenida · {nombre_bloque}",
        template="plotly_dark",
        legend_title_text="Nivel de desempeño",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="center",
            x=0.5
        ),
        xaxis=dict(
            title="Porcentaje de aspirantes",
            range=[0, 100],
            ticksuffix="%"
        ),
        yaxis_title="",
        height=altura,
        margin=dict(
            t=100,
            b=45,
            l=330,
            r=35
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Bajo: 0–24% | Básico: 25–49% | "
        "Satisfactorio: 50–74% | Alto: 75–100%"
    )


# ============================================================
# CARGA DE ARCHIVOS
# ============================================================

st.sidebar.header("Carga de archivos")

archivos_subidos = st.sidebar.file_uploader(
    "Carga los 3 archivos oficiales EVALUATEC",
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
        "Deben cargarse exactamente 3."
    )
    st.stop()


# ============================================================
# PROCESAMIENTO
# ============================================================

datos_por_bloque = {}
bases = []
errores = []

for archivo in archivos_subidos:
    try:
        df_archivo, areas_detectadas = procesar_archivo(archivo)

        bloque = df_archivo["Bloque"].iloc[0]

        datos_por_bloque[bloque] = {
            "df": df_archivo,
            "areas": areas_detectadas,
            "archivo": archivo.name
        }

        bases.append(df_archivo)

    except Exception as error:
        errores.append(f"{archivo.name}: {error}")

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

bloques_disponibles = [
    codigo
    for codigo in BLOQUES
    if codigo in datos_por_bloque
]


# ============================================================
# NAVEGACIÓN PRINCIPAL
# ============================================================

seccion = st.radio(
    "Sección",
    [
        "📊 Promedio de dimensiones",
        "🚦 Semáforo EVALUATEC 2026"
    ],
    horizontal=True,
    label_visibility="collapsed"
)


# ============================================================
# PESTAÑA 1: RADAR
# ============================================================

if seccion == "📊 Promedio de dimensiones":

    st.subheader("Promedio de dimensiones por carrera")

    bloque_seleccionado = st.radio(
        "Selecciona el bloque académico",
        options=bloques_disponibles,
        format_func=lambda codigo: f"{codigo} · {BLOQUES[codigo]}",
        horizontal=True,
        key="bloque_radar"
    )

    informacion = datos_por_bloque[bloque_seleccionado]

    st.caption(
        f"Archivo: {informacion['archivo']}"
    )

    mostrar_radar_comparativo(
        df_bloque=informacion["df"],
        areas_detectadas=informacion["areas"],
        nombre_bloque=BLOQUES[bloque_seleccionado],
        mapa_colores_carreras=mapa_colores_carreras
    )


# ============================================================
# PESTAÑA 2: SEMÁFORO
# ============================================================

elif seccion == "🚦 Semáforo EVALUATEC 2026":

    st.subheader("Semáforo de calificación obtenida en EVALUATEC 2026")

    bloque_seleccionado = st.radio(
        "Selecciona el bloque académico",
        options=bloques_disponibles,
        format_func=lambda codigo: f"{codigo} · {BLOQUES[codigo]}",
        horizontal=True,
        key="bloque_semaforo"
    )

    informacion = datos_por_bloque[bloque_seleccionado]

    st.caption(
        f"Archivo: {informacion['archivo']}"
    )

    mostrar_semaforo_desempeno(
        df_bloque=informacion["df"],
        nombre_bloque=BLOQUES[bloque_seleccionado]
    )
