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
    "Análisis de desempeño, distribución de resultados y relación entre dimensiones."
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
    """Limpia espacios repetidos del nombre de carrera."""

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
    """Lee archivos CSV intentando codificaciones y separadores frecuentes."""

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
    """Clasifica si un aspirante inició la evaluación."""

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
    Convierte valores a escala de 0 a 100.

    Acepta:
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
    """Convierte hexadecimal a rgba para áreas semitransparentes."""

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
    """Lee y prepara un archivo CSV de EVALUATEC."""

    df = leer_csv_archivo(archivo)

    bloque = identificar_bloque_archivo(archivo.name)

    if bloque is None:
        raise ValueError(
            "No se identificó el bloque. "
            "El nombre del archivo debe contener Administración, Arquitectura o Ingeniería."
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


def crear_mapa_colores_carreras(df):
    """Asigna colores consistentes para cada carrera."""

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
    """Calcula promedio por dimensión en cada carrera."""

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
    Clasifica promedio individual en bloques de 25%.

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
    """Genera distribución semáforo por carrera."""

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
# RED DE CORRELACIÓN
# ============================================================

def crear_matriz_correlacion(df, areas_detectadas):
    """
    Calcula correlaciones de Spearman entre dimensiones.

    Solo se utilizan aspirantes que iniciaron la evaluación.
    """

    df_iniciaron = df[
        df["Estatus_inicio"] == "Inició"
    ].copy()

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
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
        min_periods=10
    )

    conteos_validos = datos.notna().sum()

    return correlacion, conteos_validos


def crear_diagnostico_correlacion(
    df_bloque,
    areas_detectadas
):
    """Crea diagnóstico ejecutivo de relación entre dimensiones."""

    correlacion, conteos_validos = crear_matriz_correlacion(
        df_bloque,
        areas_detectadas
    )

    if correlacion.empty:
        return [
            "No hay suficientes registros válidos para estimar correlaciones "
            "entre las dimensiones."
        ]

    nombres = {
        f"Area_{codigo}": ETIQUETAS_AREAS.get(codigo, codigo)
        for codigo in areas_detectadas.keys()
    }

    correlacion = correlacion.rename(
        index=nombres,
        columns=nombres
    )

    pares = []

    columnas = list(correlacion.columns)

    for i in range(len(columnas)):
        for j in range(i + 1, len(columnas)):
            dimension_1 = columnas[i]
            dimension_2 = columnas[j]
            valor = correlacion.loc[dimension_1, dimension_2]

            if pd.notna(valor):
                pares.append(
                    {
                        "dimension_1": dimension_1,
                        "dimension_2": dimension_2,
                        "rho": float(valor),
                        "abs_rho": abs(float(valor))
                    }
                )

    if not pares:
        return [
            "No fue posible calcular relaciones consistentes entre las dimensiones."
        ]

    df_pares = pd.DataFrame(pares)

    relacion_fuerte = df_pares.sort_values(
        "abs_rho",
        ascending=False
    ).iloc[0]

    promedio_absoluto = {}

    for dimension in columnas:
        valores = correlacion.loc[
            dimension
        ].drop(
            labels=[dimension],
            errors="ignore"
        ).dropna()

        promedio_absoluto[dimension] = (
            valores.abs().mean()
            if not valores.empty
            else np.nan
        )

    serie_integracion = pd.Series(
        promedio_absoluto
    ).dropna()

    dimension_mas_conectada = serie_integracion.idxmax()
    dimension_menos_conectada = serie_integracion.idxmin()

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
        nombres.get(columna, columna)
        for columna in promedios.index
    ]

    dimension_mas_alta = promedios.idxmax()
    dimension_mas_baja = promedios.idxmin()

    valor_mas_alto = promedios.loc[dimension_mas_alta]
    valor_mas_bajo = promedios.loc[dimension_mas_baja]

    rho = relacion_fuerte["rho"]

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

    diagnostico = []

    diagnostico.append(
        f"**Relación principal.** Se observa una correlación "
        f"{intensidad} entre **{relacion_fuerte['dimension_1']}** y "
        f"**{relacion_fuerte['dimension_2']}** "
        f"(`ρ = {rho:.2f}`). Esto indica que, en general, quienes "
        f"obtienen mejores resultados en una de estas dimensiones suelen "
        f"mostrar un desempeño similar en la otra."
    )

    diagnostico.append(
        f"**Dimensión más integrada.** "
        f"**{dimension_mas_conectada}** presenta la mayor relación promedio "
        f"con el resto de las habilidades "
        f"(`|ρ| promedio = {serie_integracion.loc[dimension_mas_conectada]:.2f}`)."
    )

    diagnostico.append(
        f"**Dimensión menos conectada.** "
        f"**{dimension_menos_conectada}** presenta menor relación con las "
        f"demás áreas (`|ρ| promedio = "
        f"{serie_integracion.loc[dimension_menos_conectada]:.2f}`). "
        f"Esto no implica por sí mismo bajo desempeño; indica que sus resultados "
        f"varían de manera más independiente respecto a las otras dimensiones."
    )

    diagnostico.append(
        f"**Promedios generales.** La dimensión con mejor promedio es "
        f"**{dimension_mas_alta}** ({valor_mas_alto:.1f}%), mientras que "
        f"la dimensión con menor promedio es **{dimension_mas_baja}** "
        f"({valor_mas_bajo:.1f}%). Esta última puede considerarse un área "
        f"prioritaria de fortalecimiento."
    )

    return diagnostico


def mostrar_red_correlacion(
    df_bloque,
    areas_detectadas,
    nombre_bloque,
    umbral=0.30
):
    """
    Muestra una red de correlación Spearman.

    Solo se dibujan relaciones con |rho| mayor o igual al umbral.
    """

    correlacion, _ = crear_matriz_correlacion(
        df_bloque,
        areas_detectadas
    )

    if correlacion.empty:
        st.info(
            "No hay suficientes datos para construir la red de correlación."
        )
        return

    codigos_disponibles = [
        columna.replace("Area_", "")
        for columna in correlacion.columns
    ]

    etiquetas = [
        ETIQUETAS_AREAS.get(codigo, codigo)
        for codigo in codigos_disponibles
    ]

    total_nodos = len(etiquetas)

    posiciones = {}

    for indice, etiqueta in enumerate(etiquetas):
        angulo = (
            2 * math.pi * indice / total_nodos
        )

        posiciones[etiqueta] = (
            math.cos(angulo),
            math.sin(angulo)
        )

    correlacion.index = etiquetas
    correlacion.columns = etiquetas

    fig = go.Figure()

    for i in range(total_nodos):
        for j in range(i + 1, total_nodos):
            nodo_1 = etiquetas[i]
            nodo_2 = etiquetas[j]

            rho = correlacion.loc[nodo_1, nodo_2]

            if pd.isna(rho):
                continue

            if abs(rho) < umbral:
                continue

            x0, y0 = posiciones[nodo_1]
            x1, y1 = posiciones[nodo_2]

            color_linea = (
                "#36A269"
                if rho >= 0
                else "#E45756"
            )

            grosor = 1 + abs(rho) * 7

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
                        f"{nodo_1} ↔ {nodo_2}<br>"
                        f"ρ de Spearman: {rho:.2f}"
                    ),
                    showlegend=False
                )
            )

    x_nodos = []
    y_nodos = []
    texto_nodos = []
    hover_nodos = []
    colores_nodos = []

    for indice, etiqueta in enumerate(etiquetas):
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
        texto_nodos.append(etiqueta)
        colores_nodos.append(
            COLORES_NODOS[indice % len(COLORES_NODOS)]
        )

        hover_nodos.append(
            f"<b>{etiqueta}</b><br>"
            f"Relación promedio con otras dimensiones: "
            f"{conectividad:.2f}"
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
                size=12
            ),
            hovertext=hover_nodos,
            hoverinfo="text",
            marker=dict(
                size=58,
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
            f"Red de correlación entre dimensiones · {nombre_bloque}"
        ),
        template="plotly_dark",
        height=650,
        margin=dict(
            t=80,
            b=30,
            l=30,
            r=30
        ),
        xaxis=dict(
            visible=False,
            range=[-1.35, 1.35]
        ),
        yaxis=dict(
            visible=False,
            range=[-1.35, 1.35],
            scaleanchor="x",
            scaleratio=1
        ),
        annotations=[
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
# GRÁFICAS: RADAR
# ============================================================

def mostrar_radar_comparativo(
    df_bloque,
    areas_detectadas,
    nombre_bloque,
    mapa_colores_carreras
):
    """Muestra un radar comparativo por bloque académico."""

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


# ============================================================
# GRÁFICAS: SEMÁFORO
# ============================================================

def mostrar_semaforo_desempeno(
    df_bloque,
    nombre_bloque
):
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

    umbral_correlacion = st.slider(
        "Nivel mínimo de correlación para mostrar una conexión",
        min_value=0.10,
        max_value=0.80,
        value=0.30,
        step=0.05,
        help=(
            "Un umbral mayor muestra menos conexiones y facilita "
            "la lectura de relaciones fuertes."
        )
    )

    st.caption(
        f"Archivo: {informacion['archivo']} · "
        "Correlación de Spearman con aspirantes que iniciaron la evaluación."
    )

    mostrar_red_correlacion(
        df_bloque=informacion["df"],
        areas_detectadas=informacion["areas"],
        nombre_bloque=BLOQUES[bloque_seleccionado],
        umbral=umbral_correlacion
    )

    st.markdown("### Diagnóstico automático")

    diagnostico = crear_diagnostico_correlacion(
        df_bloque=informacion["df"],
        areas_detectadas=informacion["areas"]
    )

    for texto in diagnostico:
        st.markdown(f"- {texto}")
