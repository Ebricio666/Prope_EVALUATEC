import io
import math
import re
import unicodedata

import numpy as np
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
    "Análisis de desempeño, semáforo de resultados y relación entre dimensiones."
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

ETIQUETAS_CORTAS_AREAS = {
    "ING": "ING",
    "MAT": "MAT",
    "COM": "COM",
    "RLM": "RLM",
    "PM": "PM",
    "ARQ": "ARQ",
    "FIS": "FIS",
    "ADMN": "ADM"
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

COLORES_NODOS = [
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#B279A2",
    "#72B7B2",
    "#FF9DA6",
    "#9D755D"
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
    """Limpia espacios repetidos en nombres de carrera."""

    if pd.isna(valor):
        return "Sin carrera especificada"

    return " ".join(str(valor).strip().split())


def encontrar_columna(df, posibles_nombres):
    """Encuentra columnas ignorando acentos, espacios y mayúsculas."""

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
    """Lee archivos CSV con distintos separadores y codificaciones."""

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
    """Identifica ADM, ARQ o ING según el nombre del archivo."""

    nombre = normalizar_texto(nombre_archivo)

    if "administracion" in nombre:
        return "ADM"

    if "arquitectura" in nombre:
        return "ARQ"

    if "ingenieria" in nombre:
        return "ING"

    return None


def clasificar_inicio(valor):
    """Clasifica si la persona inició la evaluación."""

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
    Convierte datos a escala de 0 a 100.

    Acepta valores como:
    75
    75.5
    75%
    0.75
    """

    if pd.isna(valor):
        return np.nan

    texto = str(valor).strip()

    if texto == "":
        return np.nan

    texto = texto.replace("%", "")
    texto = texto.replace(",", ".")

    try:
        numero = float(texto)
    except ValueError:
        return np.nan

    if 0 <= numero <= 1:
        return numero * 100

    if 0 <= numero <= 100:
        return numero

    return np.nan


def hex_a_rgba(color_hex, alpha=0.12):
    """Convierte hexadecimal a rgba para rellenos semitransparentes."""

    color_hex = color_hex.lstrip("#")

    if len(color_hex) != 6:
        return f"rgba(120, 120, 120, {alpha})"

    rojo = int(color_hex[0:2], 16)
    verde = int(color_hex[2:4], 16)
    azul = int(color_hex[4:6], 16)

    return f"rgba({rojo}, {verde}, {azul}, {alpha})"


def partir_etiqueta(texto, limite=18):
    """Parte etiquetas largas para que se lean mejor en la red."""

    palabras = str(texto).split()

    lineas = []
    linea_actual = ""

    for palabra in palabras:
        posible = f"{linea_actual} {palabra}".strip()

        if len(posible) <= limite:
            linea_actual = posible
        else:
            lineas.append(linea_actual)
            linea_actual = palabra

    if linea_actual:
        lineas.append(linea_actual)

    return "<br>".join(lineas)


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
    """Lee y prepara un archivo de EVALUATEC."""

    df = leer_csv_archivo(archivo)

    bloque = identificar_bloque_archivo(archivo.name)

    if bloque is None:
        raise ValueError(
            "No se identificó el bloque académico. "
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
            f"{archivo.name}: no se detectaron columnas de áreas evaluadas."
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


# ============================================================
# TABLAS AUXILIARES
# ============================================================

def crear_mapa_colores_carreras(df):
    """Asigna colores consistentes a cada carrera."""

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
    """Clasifica resultados globales en bloques de 25%."""

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
    """Genera la tabla de semáforo por carrera."""

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
# CORRELACIONES
# ============================================================

def crear_matriz_correlacion(df, areas_detectadas):
    """
    Calcula una matriz de correlaciones Spearman.

    Solo incluye participantes que iniciaron la evaluación.
    """

    df_iniciaron = df[
        df["Estatus_inicio"] == "Inició"
    ].copy()

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
        if f"Area_{codigo}" in df_iniciaron.columns
    ]

    if len(columnas_areas) < 2:
        return pd.DataFrame(), pd.DataFrame()

    datos = df_iniciaron[columnas_areas].copy()

    datos = datos.dropna(
        axis=1,
        how="all"
    )

    datos = datos.loc[
        :,
        datos.nunique(dropna=True) > 1
    ]

    if datos.shape[1] < 2:
        return pd.DataFrame(), pd.DataFrame()

    correlacion = datos.corr(
        method="spearman",
        min_periods=5
    )

    matriz_n = (
        datos.notna()
        .astype(int)
        .T
        .dot(
            datos.notna()
            .astype(int)
        )
    )

    return correlacion, matriz_n


def obtener_diagnostico_correlacion(df_bloque, areas_detectadas):
    """Genera interpretación ejecutiva de la red de correlaciones."""

    correlacion, matriz_n = crear_matriz_correlacion(
        df_bloque,
        areas_detectadas
    )

    if correlacion.empty:
        return [
            "No hay suficientes datos válidos para estimar correlaciones entre dimensiones."
        ]

    nombres = {}

    for columna in correlacion.columns:
        codigo = columna.replace("Area_", "")
        nombres[columna] = ETIQUETAS_AREAS.get(codigo, codigo)

    correlacion = correlacion.rename(
        index=nombres,
        columns=nombres
    )

    matriz_n = matriz_n.rename(
        index=nombres,
        columns=nombres
    )

    dimensiones = list(correlacion.columns)
    pares = []

    for i in range(len(dimensiones)):
        for j in range(i + 1, len(dimensiones)):
            dimension_1 = dimensiones[i]
            dimension_2 = dimensiones[j]

            rho = correlacion.loc[dimension_1, dimension_2]
            n_par = matriz_n.loc[dimension_1, dimension_2]

            if pd.notna(rho):
                pares.append(
                    {
                        "dimension_1": dimension_1,
                        "dimension_2": dimension_2,
                        "rho": float(rho),
                        "abs_rho": abs(float(rho)),
                        "n": int(n_par)
                    }
                )

    if not pares:
        return [
            "No fue posible calcular relaciones consistentes entre las dimensiones."
        ]

    pares_df = pd.DataFrame(pares)

    relacion_principal = pares_df.sort_values(
        "abs_rho",
        ascending=False
    ).iloc[0]

    conectividad = {}

    for dimension in dimensiones:
        valores = correlacion.loc[
            dimension
        ].drop(
            labels=[dimension],
            errors="ignore"
        ).dropna()

        conectividad[dimension] = (
            valores.abs().mean()
            if not valores.empty
            else np.nan
        )

    conectividad = pd.Series(
        conectividad
    ).dropna()

    dimension_mas_conectada = conectividad.idxmax()
    dimension_menos_conectada = conectividad.idxmin()

    df_iniciaron = df_bloque[
        df_bloque["Estatus_inicio"] == "Inició"
    ].copy()

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
        if f"Area_{codigo}" in df_iniciaron.columns
    ]

    promedios = df_iniciaron[
        columnas_areas
    ].mean().dropna()

    promedios.index = [
        ETIQUETAS_AREAS.get(
            columna.replace("Area_", ""),
            columna
        )
        for columna in promedios.index
    ]

    promedio_mas_alto = promedios.idxmax()
    promedio_mas_bajo = promedios.idxmin()

    valor_mas_alto = promedios.loc[promedio_mas_alto]
    valor_mas_bajo = promedios.loc[promedio_mas_bajo]

    rho = relacion_principal["rho"]

    if rho >= 0.70:
        intensidad = "alta"
    elif rho >= 0.50:
        intensidad = "moderada-alta"
    elif rho >= 0.30:
        intensidad = "moderada"
    elif rho >= 0:
        intensidad = "baja"
    else:
        intensidad = "inversa"

    return [
        (
            f"**Relación principal.** Existe una correlación {intensidad} entre "
            f"**{relacion_principal['dimension_1']}** y "
            f"**{relacion_principal['dimension_2']}** "
            f"(`ρ = {rho:.2f}`, n = {relacion_principal['n']}). "
            f"En términos prácticos, quienes obtienen mejores resultados en una "
            f"de estas dimensiones tienden a comportarse de forma similar en la otra."
        ),
        (
            f"**Dimensión más integrada.** "
            f"**{dimension_mas_conectada}** presenta la mayor conexión promedio "
            f"con el resto de habilidades "
            f"(`|ρ| promedio = {conectividad.loc[dimension_mas_conectada]:.2f}`)."
        ),
        (
            f"**Dimensión menos conectada.** "
            f"**{dimension_menos_conectada}** mantiene relaciones más bajas con "
            f"las demás áreas (`|ρ| promedio = "
            f"{conectividad.loc[dimension_menos_conectada]:.2f}`). "
            f"Esto no significa necesariamente bajo desempeño: indica que sus "
            f"resultados varían de forma más independiente."
        ),
        (
            f"**Promedios generales.** El puntaje más alto aparece en "
            f"**{promedio_mas_alto}** ({valor_mas_alto:.1f}%), mientras que "
            f"la dimensión con menor promedio es **{promedio_mas_bajo}** "
            f"({valor_mas_bajo:.1f}%). Esta última puede considerarse un área "
            f"prioritaria para reforzar."
        )
    ]


# ============================================================
# GRÁFICAS: RADAR
# ============================================================

def mostrar_radar_comparativo(
    df_bloque,
    areas_detectadas,
    nombre_bloque,
    mapa_colores_carreras
):
    """Muestra un radar comparativo de carreras por bloque."""

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
        "Puedes seleccionar una carrera en la leyenda para ocultarla o mostrarla."
    )


# ============================================================
# GRÁFICAS: SEMÁFORO
# ============================================================

def mostrar_semaforo_desempeno(df_bloque, nombre_bloque):
    """Muestra semáforo de calificación global por carrera."""

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
# GRÁFICAS: RED DE CORRELACIÓN
# ============================================================

def mostrar_red_correlacion(
    df_bloque,
    areas_detectadas,
    nombre_bloque,
    nombre_carrera,
    umbral=0.30
):
    """
    Muestra red de correlaciones Spearman.

    Cada nodo muestra una sigla y el nombre completo queda fuera del nodo.
    """

    correlacion, matriz_n = crear_matriz_correlacion(
        df_bloque,
        areas_detectadas
    )

    n_participantes = len(
        df_bloque[
            df_bloque["Estatus_inicio"] == "Inició"
        ]
    )

    if correlacion.empty:
        st.info(
            "No hay suficientes datos para construir la red de correlación."
        )
        return

    if n_participantes < 10:
        st.warning(
            f"La selección actual tiene n={n_participantes} participantes que "
            "iniciaron. La red debe interpretarse de manera exploratoria."
        )

    codigos = [
        columna.replace("Area_", "")
        for columna in correlacion.columns
    ]

    etiquetas_largas = [
        ETIQUETAS_AREAS.get(codigo, codigo)
        for codigo in codigos
    ]

    etiquetas_cortas = [
        ETIQUETAS_CORTAS_AREAS.get(codigo, codigo)
        for codigo in codigos
    ]

    correlacion.index = etiquetas_largas
    correlacion.columns = etiquetas_largas

    matriz_n.index = etiquetas_largas
    matriz_n.columns = etiquetas_largas

    total_nodos = len(etiquetas_largas)

    posiciones = {}

    for indice, etiqueta in enumerate(etiquetas_largas):
        angulo = 2 * math.pi * indice / total_nodos

        posiciones[etiqueta] = (
            math.cos(angulo),
            math.sin(angulo)
        )

    fig = go.Figure()

    # Líneas entre dimensiones
    for i in range(total_nodos):
        for j in range(i + 1, total_nodos):
            nodo_1 = etiquetas_largas[i]
            nodo_2 = etiquetas_largas[j]

            rho = correlacion.loc[nodo_1, nodo_2]
            n_par = matriz_n.loc[nodo_1, nodo_2]

            if pd.isna(rho):
                continue

            if abs(rho) < umbral:
                continue

            x0, y0 = posiciones[nodo_1]
            x1, y1 = posiciones[nodo_2]

            color_linea = (
                "#35A96B"
                if rho >= 0
                else "#E45756"
            )

            grosor = 1 + abs(rho) * 8

            fig.add_trace(
                go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode="lines",
                    line=dict(
                        color=color_linea,
                        width=grosor
                    ),
                    hoverinfo="text",
                    text=(
                        f"<b>{nodo_1} ↔ {nodo_2}</b><br>"
                        f"ρ de Spearman: {rho:.2f}<br>"
                        f"Participantes válidos: {int(n_par)}"
                    ),
                    showlegend=False
                )
            )

    # Nodos
    x_nodos = []
    y_nodos = []
    texto_nodos = []
    hover_nodos = []
    colores_nodos = []
    anotaciones = []

    for indice, etiqueta in enumerate(etiquetas_largas):
        x, y = posiciones[etiqueta]

        relaciones = correlacion.loc[
            etiqueta
        ].drop(
            labels=[etiqueta],
            errors="ignore"
        ).dropna()

        conectividad = relaciones.abs().mean()

        x_nodos.append(x)
        y_nodos.append(y)
        texto_nodos.append(etiquetas_cortas[indice])

        colores_nodos.append(
            COLORES_NODOS[indice % len(COLORES_NODOS)]
        )

        hover_nodos.append(
            f"<b>{etiqueta}</b><br>"
            f"Relación promedio con otras dimensiones: "
            f"{conectividad:.2f}<br>"
            f"Participantes analizados: {n_participantes}"
        )

        x_texto = x * 1.42
        y_texto = y * 1.42

        if x > 0.20:
            ancla_x = "left"
        elif x < -0.20:
            ancla_x = "right"
        else:
            ancla_x = "center"

        anotaciones.append(
            dict(
                x=x_texto,
                y=y_texto,
                text=partir_etiqueta(etiqueta),
                showarrow=False,
                xanchor=ancla_x,
                yanchor="middle",
                align="center",
                font=dict(
                    size=14,
                    color="#D9D9D9"
                )
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x_nodos,
            y=y_nodos,
            mode="markers+text",
            text=texto_nodos,
            textposition="middle center",
            textfont=dict(
                color="white",
                size=15
            ),
            hovertext=hover_nodos,
            hoverinfo="text",
            marker=dict(
                size=62,
                color=colores_nodos,
                line=dict(
                    color="white",
                    width=1.5
                )
            ),
            showlegend=False
        )
    )

    fig.update_layout(
        title=(
            f"Red de correlación · {nombre_bloque} · {nombre_carrera}"
        ),
        template="plotly_dark",
        height=730,
        margin=dict(
            t=90,
            b=70,
            l=190,
            r=190
        ),
        xaxis=dict(
            visible=False,
            range=[-1.90, 1.90]
        ),
        yaxis=dict(
            visible=False,
            range=[-1.90, 1.90],
            scaleanchor="x",
            scaleratio=1
        ),
        annotations=anotaciones + [
            dict(
                text=(
                    "Verde: correlación positiva | "
                    "Rojo: correlación inversa | "
                    f"Se muestran relaciones con |ρ| ≥ {umbral:.2f}"
                ),
                x=0.5,
                y=-0.10,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=13)
            )
        ]
    )

    st.plotly_chart(
        fig,
        use_container_width=True
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
        df_archivo, areas_detectadas = procesar_archivo(
            archivo
        )

        bloque = df_archivo["Bloque"].iloc[0]

        datos_por_bloque[bloque] = {
            "df": df_archivo,
            "areas": areas_detectadas,
            "archivo": archivo.name
        }

        bases.append(df_archivo)

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

bloques_disponibles = [
    codigo
    for codigo in BLOQUES
    if codigo in datos_por_bloque
]


# ============================================================
# NAVEGACIÓN
# ============================================================

seccion = st.radio(
    "Sección",
    [
        "📊 Promedio de dimensiones",
        "🚦 Semáforo EVALUATEC 2026",
        "🕸️ Relación entre dimensiones"
    ],
    horizontal=True,
    label_visibility="collapsed"
)


# ============================================================
# SECCIÓN 1: RADAR
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
# SECCIÓN 2: SEMÁFORO
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


# ============================================================
# SECCIÓN 3: RED DE CORRELACIÓN
# ============================================================

elif seccion == "🕸️ Relación entre dimensiones":

    st.subheader("Relación entre dimensiones evaluadas")

    bloque_seleccionado = st.radio(
        "Selecciona el bloque académico",
        options=bloques_disponibles,
        format_func=lambda codigo: f"{codigo} · {BLOQUES[codigo]}",
        horizontal=True,
        key="bloque_correlacion"
    )

    informacion = datos_por_bloque[bloque_seleccionado]
    df_bloque = informacion["df"].copy()

    carreras_disponibles = sorted(
        df_bloque[
            "Carrera_normalizada"
        ]
        .dropna()
        .unique()
    )

    carrera_seleccionada = st.selectbox(
        "Selecciona la carrera",
        options=[
            "Todas las carreras"
        ] + carreras_disponibles,
        key="carrera_correlacion"
    )

    if carrera_seleccionada == "Todas las carreras":
        df_analisis = df_bloque.copy()
        nombre_carrera = "Todas las carreras"

    else:
        df_analisis = df_bloque[
            df_bloque["Carrera_normalizada"]
            == carrera_seleccionada
        ].copy()

        nombre_carrera = carrera_seleccionada

    umbral_correlacion = st.slider(
        "Nivel mínimo de correlación para mostrar una conexión",
        min_value=0.10,
        max_value=0.80,
        value=0.30,
        step=0.05,
        key="umbral_correlacion",
        help=(
            "Un umbral más alto reduce líneas y permite revisar "
            "solo las relaciones más fuertes."
        )
    )

    participantes_analizados = len(
        df_analisis[
            df_analisis["Estatus_inicio"] == "Inició"
        ]
    )

    st.caption(
        f"Archivo: {informacion['archivo']} · "
        f"Carrera: {nombre_carrera} · "
        f"Participantes que iniciaron: n={participantes_analizados}"
    )

    mostrar_red_correlacion(
        df_bloque=df_analisis,
        areas_detectadas=informacion["areas"],
        nombre_bloque=BLOQUES[bloque_seleccionado],
        nombre_carrera=nombre_carrera,
        umbral=umbral_correlacion
    )

    st.markdown("### Diagnóstico automático")

    diagnostico = obtener_diagnostico_correlacion(
        df_bloque=df_analisis,
        areas_detectadas=informacion["areas"]
    )

    for texto in diagnostico:
        st.markdown(f"- {texto}")
