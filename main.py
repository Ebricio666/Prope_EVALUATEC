import io
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
    "Perfil integral de desempeño por carrera."
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

ICONOS_BLOQUES = {
    "ADM": "📘",
    "ARQ": "🏛️",
    "ING": "⚙️"
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

ORDEN_ALERTAS = [
    "Sin alerta",
    "Alerta media",
    "Alerta alta"
]

COLORES_ALERTAS = {
    "Sin alerta": "#27AE60",
    "Alerta media": "#F39C12",
    "Alerta alta": "#E74C3C"
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

    for posible in posibles_nombres:
        posible_normalizado = normalizar_texto(posible)

        for columna_normalizada, columna_original in columnas_normalizadas.items():
            if posible_normalizado in columna_normalizada:
                return columna_original

    return None


def leer_csv_archivo(archivo):
    """Lee CSV intentando distintas codificaciones y separadores."""

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
    """Identifica ADM, ARQ o ING mediante el nombre del archivo."""

    nombre = normalizar_texto(nombre_archivo)

    if "administracion" in nombre:
        return "ADM"

    if "arquitectura" in nombre:
        return "ARQ"

    if "ingenieria" in nombre:
        return "ING"

    return None


def clasificar_inicio(valor):
    """Clasifica si la persona inició o no la evaluación."""

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

    Soporta:
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
    """Convierte hexadecimal a rgba."""

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
        texto = normalizar_texto(columna)

        texto_compacto = re.sub(
            r"[^a-z0-9]",
            "",
            texto
        )

        if "seccion" not in texto_compacto:
            continue

        if "porcentajecorrectas" not in texto_compacto:
            continue

        coincidencia = re.search(
            r"seccion([a-z0-9]+?)porcentajecorrectas",
            texto_compacto
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
    """Lee y prepara un archivo de EVALUATEC."""

    df = leer_csv_archivo(archivo)

    bloque = identificar_bloque_archivo(
        archivo.name
    )

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

    df["Carrera_normalizada"] = df[
        columna_carrera
    ].apply(
        limpiar_nombre_carrera
    )

    df["Estatus_inicio"] = df[
        columna_inicio
    ].apply(
        clasificar_inicio
    )

    for codigo, columna in areas_detectadas.items():
        df[f"Area_{codigo}"] = df[
            columna
        ].apply(
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
# FUNCIONES DE CÁLCULO
# ============================================================

def clasificar_nivel_desempeno(valor):
    """Clasifica el puntaje global individual en cuatro niveles."""

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


def calcular_alertas(df, areas_detectadas):
    """
    Genera alertas sin mostrar nombres.

    Alerta alta:
    - promedio global menor a 25%, o
    - tres o más dimensiones debajo de 50%.

    Alerta media:
    - promedio global menor a 50%, o
    - dos dimensiones debajo de 50%.
    """

    df_alertas = df[
        (
            df["Estatus_inicio"] == "Inició"
        )
        &
        (
            df["Promedio_global_individual"].notna()
        )
    ].copy()

    if df_alertas.empty:
        return df_alertas

    columnas_areas = [
        f"Area_{codigo}"
        for codigo in areas_detectadas.keys()
        if f"Area_{codigo}" in df_alertas.columns
    ]

    df_alertas["Dimensiones_bajo_50"] = df_alertas[
        columnas_areas
    ].lt(50).sum(axis=1)

    def asignar_alerta(fila):
        promedio = fila["Promedio_global_individual"]
        dimensiones_bajas = fila["Dimensiones_bajo_50"]

        if promedio < 25 or dimensiones_bajas >= 3:
            return "Alerta alta"

        if promedio < 50 or dimensiones_bajas >= 2:
            return "Alerta media"

        return "Sin alerta"

    df_alertas["Nivel_alerta"] = df_alertas.apply(
        asignar_alerta,
        axis=1
    )

    return df_alertas


def crear_promedio_dimensiones(df, areas_detectadas):
    """Calcula promedio por dimensión para una selección de aspirantes."""

    df_iniciaron = df[
        df["Estatus_inicio"] == "Inició"
    ].copy()

    resultados = []

    for codigo in areas_detectadas.keys():
        columna = f"Area_{codigo}"

        if columna not in df_iniciaron.columns:
            continue

        promedio = df_iniciaron[columna].mean()

        if pd.notna(promedio):
            resultados.append(
                {
                    "Código": codigo,
                    "Dimensión": ETIQUETAS_AREAS.get(
                        codigo,
                        codigo
                    ),
                    "Promedio": round(float(promedio), 1),
                    "Nivel": clasificar_nivel_desempeno(
                        promedio
                    )
                }
            )

    return pd.DataFrame(resultados)


def crear_distribucion_niveles(df):
    """Crea la distribución porcentual del semáforo para una carrera."""

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
    ].apply(
        clasificar_nivel_desempeno
    )

    total = len(df_iniciaron)

    resumen = (
        df_iniciaron
        .groupby("Nivel_desempeno")
        .size()
        .reindex(
            ORDEN_NIVELES,
            fill_value=0
        )
        .reset_index(name="Aspirantes")
    )

    resumen.columns = [
        "Nivel_desempeno",
        "Aspirantes"
    ]

    resumen["Porcentaje"] = (
        resumen["Aspirantes"]
        / total
        * 100
    )

    resumen["Etiqueta"] = resumen[
        "Porcentaje"
    ].apply(
        lambda valor: f"{valor:.0f}%"
        if valor >= 7
        else ""
    )

    resumen["Total"] = total

    return resumen


def crear_distribucion_alertas(df, areas_detectadas):
    """Crea el concentrado porcentual de alertas de una carrera."""

    df_alertas = calcular_alertas(
        df,
        areas_detectadas
    )

    if df_alertas.empty:
        return pd.DataFrame()

    total = len(df_alertas)

    resumen = (
        df_alertas
        .groupby("Nivel_alerta")
        .size()
        .reindex(
            ORDEN_ALERTAS,
            fill_value=0
        )
        .reset_index(name="Aspirantes")
    )

    resumen.columns = [
        "Nivel_alerta",
        "Aspirantes"
    ]

    resumen["Porcentaje"] = (
        resumen["Aspirantes"]
        / total
        * 100
    )

    resumen["Etiqueta"] = resumen[
        "Porcentaje"
    ].apply(
        lambda valor: f"{valor:.0f}%"
        if valor >= 7
        else ""
    )

    resumen["Total"] = total

    return resumen


def crear_comparativo_bloque(df_bloque):
    """Calcula el promedio global y posición de cada carrera del bloque."""

    df_iniciaron = df_bloque[
        (
            df_bloque["Estatus_inicio"] == "Inició"
        )
        &
        (
            df_bloque["Promedio_global_individual"].notna()
        )
    ].copy()

    if df_iniciaron.empty:
        return pd.DataFrame()

    comparativo = (
        df_iniciaron
        .groupby("Carrera_normalizada")
        .agg(
            Promedio_global=(
                "Promedio_global_individual",
                "mean"
            ),
            Evaluados=(
                "Promedio_global_individual",
                "size"
            )
        )
        .reset_index()
        .sort_values(
            "Promedio_global",
            ascending=False
        )
        .reset_index(drop=True)
    )

    comparativo["Promedio_global"] = comparativo[
        "Promedio_global"
    ].round(1)

    comparativo["Posición"] = (
        comparativo.index + 1
    )

    return comparativo


# ============================================================
# VISUALIZACIONES
# ============================================================

def mostrar_radar_carrera(
    df_carrera,
    df_bloque,
    areas_detectadas,
    carrera_seleccionada,
    nombre_bloque
):
    """
    Radar de carrera seleccionada frente al promedio
    general del bloque.
    """

    promedio_carrera = crear_promedio_dimensiones(
        df_carrera,
        areas_detectadas
    )

    promedio_bloque = crear_promedio_dimensiones(
        df_bloque,
        areas_detectadas
    )

    if promedio_carrera.empty:
        st.info(
            "No hay datos suficientes para generar el radar."
        )
        return

    codigos = promedio_carrera[
        "Código"
    ].tolist()

    etiquetas = promedio_carrera[
        "Dimensión"
    ].tolist()

    valores_carrera = promedio_carrera[
        "Promedio"
    ].tolist()

    valores_bloque = []

    for codigo in codigos:
        fila_bloque = promedio_bloque[
            promedio_bloque["Código"] == codigo
        ]

        if fila_bloque.empty:
            valores_bloque.append(0)
        else:
            valores_bloque.append(
                float(
                    fila_bloque["Promedio"].iloc[0]
                )
            )

    etiquetas_cerradas = etiquetas + [etiquetas[0]]
    valores_carrera_cerrados = valores_carrera + [
        valores_carrera[0]
    ]
    valores_bloque_cerrados = valores_bloque + [
        valores_bloque[0]
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=valores_bloque_cerrados,
            theta=etiquetas_cerradas,
            mode="lines+markers",
            name=f"Promedio {nombre_bloque}",
            line=dict(
                color="#9E9E9E",
                width=2,
                dash="dash"
            ),
            marker=dict(
                color="#9E9E9E",
                size=5
            ),
            hovertemplate=(
                "<b>Promedio del bloque</b><br>"
                "%{theta}: %{r:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=valores_carrera_cerrados,
            theta=etiquetas_cerradas,
            mode="lines+markers",
            name=carrera_seleccionada,
            line=dict(
                color="#4C78A8",
                width=4
            ),
            marker=dict(
                color="#4C78A8",
                size=8
            ),
            fill="toself",
            fillcolor=hex_a_rgba(
                "#4C78A8",
                alpha=0.16
            ),
            hovertemplate=(
                f"<b>{carrera_seleccionada}</b><br>"
                "%{theta}: %{r:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title=(
            f"Perfil de dimensiones · {carrera_seleccionada}"
        ),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix="%"
            )
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        height=560,
        margin=dict(
            t=80,
            b=80,
            l=40,
            r=40
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


def mostrar_semaforo_carrera(
    df_carrera,
    carrera_seleccionada
):
    """Muestra una barra semáforo al 100% para la carrera."""

    tabla = crear_distribucion_niveles(
        df_carrera
    )

    if tabla.empty:
        st.info(
            "No hay resultados suficientes para generar el semáforo."
        )
        return

    fig = px.bar(
        tabla,
        x="Porcentaje",
        y=["Desempeño"] * len(tabla),
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
            "<b>Nivel:</b> %{fullData.name}<br>"
            "<b>Aspirantes:</b> %{customdata[0]} de %{customdata[1]}<br>"
            "<b>Porcentaje:</b> %{x:.1f}%"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        title=(
            f"Semáforo de desempeño global · {carrera_seleccionada}"
        ),
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
        yaxis=dict(
            showticklabels=False,
            title=""
        ),
        height=350,
        margin=dict(
            t=90,
            b=50,
            l=20,
            r=20
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


def mostrar_ranking_dimensiones(
    df_carrera,
    areas_detectadas,
    carrera_seleccionada
):
    """Muestra dimensiones de menor a mayor promedio."""

    ranking = crear_promedio_dimensiones(
        df_carrera,
        areas_detectadas
    )

    if ranking.empty:
        st.info(
            "No hay resultados suficientes para construir el ranking."
        )
        return

    ranking = ranking.sort_values(
        "Promedio",
        ascending=True
    )

    fig = px.bar(
        ranking,
        x="Promedio",
        y="Dimensión",
        color="Nivel",
        orientation="h",
        text="Promedio",
        color_discrete_map=COLORES_NIVELES,
        category_orders={
            "Nivel": ORDEN_NIVELES,
            "Dimensión": ranking[
                "Dimensión"
            ].tolist()
        }
    )

    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Promedio: %{x:.1f}%"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        title=(
            f"Ranking de dimensiones · {carrera_seleccionada}"
        ),
        showlegend=False,
        xaxis=dict(
            title="Promedio obtenido",
            range=[0, 100],
            ticksuffix="%"
        ),
        yaxis_title="",
        height=480,
        margin=dict(
            t=80,
            b=45,
            l=240,
            r=90
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


def mostrar_alertas_carrera(
    df_carrera,
    areas_detectadas,
    carrera_seleccionada
):
    """Muestra concentrado de alertas académicas sin nombres."""

    tabla = crear_distribucion_alertas(
        df_carrera,
        areas_detectadas
    )

    if tabla.empty:
        st.info(
            "No hay información suficiente para calcular alertas."
        )
        return

    fig = px.bar(
        tabla,
        x="Porcentaje",
        y=["Alertas"] * len(tabla),
        color="Nivel_alerta",
        orientation="h",
        barmode="stack",
        text="Etiqueta",
        custom_data=[
            "Aspirantes",
            "Total"
        ],
        category_orders={
            "Nivel_alerta": ORDEN_ALERTAS
        },
        color_discrete_map=COLORES_ALERTAS
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate=(
            "<b>Nivel:</b> %{fullData.name}<br>"
            "<b>Aspirantes:</b> %{customdata[0]} de %{customdata[1]}<br>"
            "<b>Porcentaje:</b> %{x:.1f}%"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        title=(
            f"Alertas académicas · {carrera_seleccionada}"
        ),
        legend_title_text="Nivel de alerta",
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
        yaxis=dict(
            showticklabels=False,
            title=""
        ),
        height=350,
        margin=dict(
            t=90,
            b=50,
            l=20,
            r=20
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Alerta media: promedio global menor a 50% o dos dimensiones "
        "debajo de 50%. Alerta alta: promedio global menor a 25% o "
        "tres o más dimensiones debajo de 50%."
    )


# ============================================================
# DIAGNÓSTICO DE CARRERA
# ============================================================

def crear_diagnostico_carrera(
    df_carrera,
    df_bloque,
    areas_detectadas,
    carrera_seleccionada
):
    """Crea texto ejecutivo para la carrera seleccionada."""

    ranking = crear_promedio_dimensiones(
        df_carrera,
        areas_detectadas
    )

    alertas = crear_distribucion_alertas(
        df_carrera,
        areas_detectadas
    )

    comparativo = crear_comparativo_bloque(
        df_bloque
    )

    if ranking.empty:
        return "No hay suficientes datos para generar un diagnóstico."

    ranking = ranking.sort_values(
        "Promedio",
        ascending=True
    )

    area_prioritaria = ranking.iloc[0]
    area_fuerte = ranking.iloc[-1]

    dimensiones_bajas = ranking[
        ranking["Promedio"] < 50
    ]

    total_dimensiones_bajas = len(
        dimensiones_bajas
    )

    promedio_carrera = df_carrera[
        (
            df_carrera["Estatus_inicio"] == "Inició"
        )
        &
        (
            df_carrera["Promedio_global_individual"].notna()
        )
    ][
        "Promedio_global_individual"
    ].mean()

    promedio_bloque = df_bloque[
        (
            df_bloque["Estatus_inicio"] == "Inició"
        )
        &
        (
            df_bloque["Promedio_global_individual"].notna()
        )
    ][
        "Promedio_global_individual"
    ].mean()

    fila_comparativo = comparativo[
        comparativo["Carrera_normalizada"]
        == carrera_seleccionada
    ]

    if fila_comparativo.empty:
        posicion_texto = ""
    else:
        posicion = int(
            fila_comparativo["Posición"].iloc[0]
        )
        total_carreras = len(comparativo)

        posicion_texto = (
            f" Se ubica en la posición {posicion} de "
            f"{total_carreras} carreras del bloque."
        )

    porcentaje_alerta_alta = 0

    if not alertas.empty:
        fila_alerta_alta = alertas[
            alertas["Nivel_alerta"] == "Alerta alta"
        ]

        if not fila_alerta_alta.empty:
            porcentaje_alerta_alta = float(
                fila_alerta_alta["Porcentaje"].iloc[0]
            )

    texto = (
        f"**{carrera_seleccionada}** presenta un promedio global de "
        f"**{promedio_carrera:.1f}%**, frente a **{promedio_bloque:.1f}%** "
        f"del bloque de referencia.{posicion_texto} "
        f"La principal área prioritaria es **{area_prioritaria['Dimensión']}** "
        f"({area_prioritaria['Promedio']:.1f}%), mientras que la dimensión "
        f"más alta es **{area_fuerte['Dimensión']}** "
        f"({area_fuerte['Promedio']:.1f}%). "
    )

    if total_dimensiones_bajas > 0:
        texto += (
            f"Se identifican {total_dimensiones_bajas} dimensión(es) con "
            f"promedio inferior a 50%, por lo que se recomienda reforzarlas "
            f"durante el propedéutico. "
        )

    if porcentaje_alerta_alta > 0:
        texto += (
            f"Además, {porcentaje_alerta_alta:.1f}% de quienes iniciaron "
            f"presenta alerta académica alta, por lo que conviene priorizar "
            f"acciones de nivelación temprana."
        )
    else:
        texto += (
            "No se observa presencia de alerta académica alta en la carrera."
        )

    return texto


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
# PROCESAMIENTO DE ARCHIVOS
# ============================================================

datos_por_bloque = {}
errores = []

for archivo in archivos_subidos:
    try:
        df_archivo, areas_detectadas = procesar_archivo(
            archivo
        )

        bloque = df_archivo[
            "Bloque"
        ].iloc[0]

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

if not datos_por_bloque:
    st.stop()

bloques_disponibles = [
    codigo
    for codigo in BLOQUES
    if codigo in datos_por_bloque
]


# ============================================================
# NAVEGACIÓN POR ARCHIVO
# ============================================================

bloque_seleccionado = st.radio(
    "Selecciona el archivo o bloque académico",
    options=bloques_disponibles,
    horizontal=True,
    format_func=lambda codigo: (
        f"{ICONOS_BLOQUES[codigo]} "
        f"{BLOQUES[codigo]}"
    ),
    label_visibility="collapsed"
)

informacion_bloque = datos_por_bloque[
    bloque_seleccionado
]

df_bloque = informacion_bloque[
    "df"
].copy()

areas_detectadas = informacion_bloque[
    "areas"
]

nombre_bloque = BLOQUES[
    bloque_seleccionado
]

st.markdown(f"## {nombre_bloque}")

st.caption(
    f"Archivo analizado: {informacion_bloque['archivo']}"
)


# ============================================================
# SELECTOR DE CARRERA
# ============================================================

carreras_disponibles = sorted(
    df_bloque[
        "Carrera_normalizada"
    ]
    .dropna()
    .unique()
)

carrera_seleccionada = st.selectbox(
    "Selecciona la carrera",
    options=carreras_disponibles,
    key=f"carrera_{bloque_seleccionado}"
)

df_carrera = df_bloque[
    df_bloque["Carrera_normalizada"]
    == carrera_seleccionada
].copy()


# ============================================================
# INDICADORES EJECUTIVOS
# ============================================================

total_registrados = len(df_carrera)

total_iniciaron = int(
    (
        df_carrera["Estatus_inicio"] == "Inició"
    ).sum()
)

total_no_iniciaron = int(
    (
        df_carrera["Estatus_inicio"] == "No inició"
    ).sum()
)

porcentaje_inicio = (
    total_iniciaron / total_registrados * 100
    if total_registrados > 0
    else 0
)

promedio_global = df_carrera[
    (
        df_carrera["Estatus_inicio"] == "Inició"
    )
    &
    (
        df_carrera["Promedio_global_individual"].notna()
    )
][
    "Promedio_global_individual"
].mean()

st.markdown(f"### Perfil de {carrera_seleccionada}")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Registrados",
    f"{total_registrados:,}"
)

col2.metric(
    "Iniciaron",
    f"{total_iniciaron:,}"
)

col3.metric(
    "No iniciaron",
    f"{total_no_iniciaron:,}"
)

col4.metric(
    "% de inicio",
    f"{porcentaje_inicio:.1f}%"
)

col5.metric(
    "Promedio global",
    (
        f"{promedio_global:.1f}%"
        if pd.notna(promedio_global)
        else "Sin dato"
    )
)


# ============================================================
# RADAR
# ============================================================

st.markdown("## Perfil de dimensiones")

mostrar_radar_carrera(
    df_carrera=df_carrera,
    df_bloque=df_bloque,
    areas_detectadas=areas_detectadas,
    carrera_seleccionada=carrera_seleccionada,
    nombre_bloque=nombre_bloque
)


# ============================================================
# SEMÁFORO Y ALERTAS
# ============================================================

st.markdown("## Desempeño y alertas académicas")

col_semaforo, col_alertas = st.columns(2)

with col_semaforo:
    mostrar_semaforo_carrera(
        df_carrera=df_carrera,
        carrera_seleccionada=carrera_seleccionada
    )

with col_alertas:
    mostrar_alertas_carrera(
        df_carrera=df_carrera,
        areas_detectadas=areas_detectadas,
        carrera_seleccionada=carrera_seleccionada
    )


# ============================================================
# RANKING DE DIMENSIONES
# ============================================================

st.markdown("## Ranking de dimensiones")

mostrar_ranking_dimensiones(
    df_carrera=df_carrera,
    areas_detectadas=areas_detectadas,
    carrera_seleccionada=carrera_seleccionada
)


# ============================================================
# DIAGNÓSTICO EJECUTIVO
# ============================================================

st.markdown("## Diagnóstico ejecutivo")

diagnostico = crear_diagnostico_carrera(
    df_carrera=df_carrera,
    df_bloque=df_bloque,
    areas_detectadas=areas_detectadas,
    carrera_seleccionada=carrera_seleccionada
)

st.info(diagnostico)


# ============================================================
# COMPARATIVO DEL BLOQUE
# ============================================================

st.markdown("## Comparativo dentro del bloque")

comparativo_bloque = crear_comparativo_bloque(
    df_bloque
)

if comparativo_bloque.empty:
    st.info(
        "No hay información suficiente para comparar carreras."
    )
else:
    fig_comparativo = px.bar(
        comparativo_bloque.sort_values(
            "Promedio_global",
            ascending=True
        ),
        x="Promedio_global",
        y="Carrera_normalizada",
        orientation="h",
        text="Promedio_global"
    )

    fig_comparativo.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Promedio global: %{x:.1f}%"
            "<extra></extra>"
        )
    )

    fig_comparativo.update_layout(
        title=(
            f"Promedio global por carrera · {nombre_bloque}"
        ),
        xaxis=dict(
            title="Promedio global",
            range=[0, 100],
            ticksuffix="%"
        ),
        yaxis_title="",
        showlegend=False,
        height=max(
            420,
            len(comparativo_bloque) * 70
        ),
        margin=dict(
            t=80,
            b=40,
            l=250,
            r=90
        )
    )

    st.plotly_chart(
        fig_comparativo,
        use_container_width=True
    )
