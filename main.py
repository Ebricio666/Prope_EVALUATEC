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
    """Limpia espacios repetidos en el nombre de carrera."""

    if pd.isna(valor):
        return "Sin carrera especificada"

    return " ".join(str(valor).strip().split())


def encontrar_columna(df, posibles_nombres):
    """Encuentra una columna sin importar acentos, espacios o mayúsculas."""

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
    """Lee CSV intentando codificaciones y separadores frecuentes."""

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
    """Clasifica si una persona inició o no su evaluación."""

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
    Convierte valores a porcentaje de 0 a 100.

    Acepta:
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


def hex_a_rgba(color_hex, alpha=0.14):
    """Convierte hexadecimal a rgba para rellenos transparentes."""

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
# PROCESAMIENTO
# ============================================================

def procesar_archivo(archivo):
    """Lee y procesa un archivo CSV de EVALUATEC."""

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
            f"No se detectaron columnas de áreas evaluadas en {archivo.name}."
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

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
    ]

    df["Promedio_global_individual"] = df[
        columnas_areas
    ].mean(axis=1)

    return df, areas_detectadas


def crear_promedios_por_carrera(df, areas_detectadas):
    """
    Calcula promedios por carrera usando solo
    participantes que iniciaron la evaluación.
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


def clasificar_nivel_desempeno(valor):
    """
    Clasifica el promedio global individual en bloques de 25%.

    Bajo: 0 a 24.99
    Básico: 25 a 49.99
    Satisfactorio: 50 a 74.99
    Alto: 75 a 100
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
    """
    Crea distribución porcentual de desempeño global
    por carrera para las personas que iniciaron.
    """

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

    carreras = sorted(
        df_iniciaron["Carrera_normalizada"]
        .unique()
    )

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

    orden_carreras = (
        totales
        .sort_values("Total", ascending=False)
        ["Carrera_normalizada"]
        .tolist()
    )

    etiquetas_carreras = [
        f"{carrera} (n={int(totales.loc[
            totales['Carrera_normalizada'] == carrera,
            'Total'
        ].iloc[0])})"
        for carrera in orden_carreras
    ]

    tabla["Carrera_etiqueta"] = pd.Categorical(
        tabla["Carrera_etiqueta"],
        categories=etiquetas_carreras[::-1],
        ordered=True
    )

    tabla["Nivel_desempeno"] = pd.Categorical(
        tabla["Nivel_desempeno"],
        categories=ORDEN_NIVELES,
        ordered=True
    )

    return tabla


def crear_mapa_colores_carreras(df_general):
    """Asigna un color fijo por carrera para los radares."""

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
    """Muestra un radar comparativo por archivo."""

    promedios = crear_promedios_por_carrera(
        df_bloque,
        areas_detectadas
    )

    if promedios.empty:
        st.info(
            f"No hay participantes que hayan iniciado el examen en {nombre_bloque}."
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
                    alpha=0.11
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


def mostrar_barras_desempeno_global(
    df_bloque,
    nombre_bloque
):
    """
    Muestra barras apiladas al 100% por carrera,
    usando bloques de desempeño de 25%.
    """

    tabla = crear_distribucion_desempeno(df_bloque)

    if tabla.empty:
        st.info(
            f"No hay datos suficientes para calcular desempeño global en {nombre_bloque}."
        )
        return

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
        title=f"Distribución del desempeño global por carrera · {nombre_bloque}",
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
        height=max(450, len(tabla["Carrera_etiqueta"].unique()) * 85),
        margin=dict(
            t=100,
            b=45,
            l=310,
            r=30
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
# RESÚMENES
# ============================================================

def mostrar_resumen_bloque(df_bloque, nombre_bloque):
    """Muestra indicadores generales de cada bloque."""

    participantes = len(df_bloque)

    iniciaron = (
        df_bloque["Estatus_inicio"] == "Inició"
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
# RADARES Y BARRAS POR BLOQUE
# ============================================================

st.markdown("## Comparativo de desempeño por carrera")

for bloque in bloques_disponibles:
    informacion_bloque = datos_por_bloque[bloque]

    st.markdown(f"# {bloque}")
    st.caption(
        f"Archivo analizado: {informacion_bloque['archivo']}"
    )

    mostrar_radar_comparativo(
        df_bloque=informacion_bloque["df"],
        areas_detectadas=informacion_bloque["areas"],
        nombre_bloque=bloque,
        mapa_colores_carreras=mapa_colores_carreras
    )

    mostrar_barras_desempeno_global(
        df_bloque=informacion_bloque["df"],
        nombre_bloque=bloque
    )
