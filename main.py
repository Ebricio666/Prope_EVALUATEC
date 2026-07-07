import io
import re
import unicodedata

import numpy as np
import pandas as pd
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
st.caption("Perfil académico por carrera.")


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

RANGOS_NIVELES = {
    "Bajo": "0–24%",
    "Básico": "25–49%",
    "Satisfactorio": "50–74%",
    "Alto": "75–100%"
}

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
    """Normaliza texto para comparar encabezados."""

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
    """Convierte datos a una escala de 0 a 100."""

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


def hex_a_rgba(color_hex, alpha=0.15):
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
# CÁLCULOS
# ============================================================

def clasificar_nivel_desempeno(valor):
    """Clasifica una calificación real en rangos de desempeño."""

    if pd.isna(valor):
        return None

    if 0 <= valor < 25:
        return "Bajo"

    if 25 <= valor < 50:
        return "Básico"

    if 50 <= valor < 75:
        return "Satisfactorio"

    if 75 <= valor <= 100:
        return "Alto"

    return None


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
                    "Promedio": round(float(promedio), 1)
                }
            )

    return pd.DataFrame(resultados)


def crear_matriz_rangos_dimension(df, areas_detectadas):
    """
    Crea una matriz con porcentaje de aspirantes por rango real
    de calificación dentro de cada dimensión.
    """

    df_iniciaron = df[
        df["Estatus_inicio"] == "Inició"
    ].copy()

    registros = []

    for codigo in areas_detectadas.keys():
        columna = f"Area_{codigo}"

        if columna not in df_iniciaron.columns:
            continue

        valores = df_iniciaron[
            columna
        ].dropna()

        if valores.empty:
            continue

        dimension = ETIQUETAS_AREAS.get(
            codigo,
            codigo
        )

        total = len(valores)

        niveles = valores.apply(
            clasificar_nivel_desempeno
        )

        conteos = niveles.value_counts()

        for nivel in ORDEN_NIVELES:
            cantidad = int(conteos.get(nivel, 0))
            porcentaje = cantidad / total * 100

            registros.append(
                {
                    "Código": codigo,
                    "Dimensión": dimension,
                    "Nivel": nivel,
                    "Rango": RANGOS_NIVELES[nivel],
                    "Aspirantes": cantidad,
                    "Total": total,
                    "Porcentaje": porcentaje
                }
            )

    tabla = pd.DataFrame(registros)

    if tabla.empty:
        return tabla

    promedios = crear_promedio_dimensiones(
        df,
        areas_detectadas
    )

    tabla = tabla.merge(
        promedios[
            [
                "Código",
                "Promedio"
            ]
        ],
        on="Código",
        how="left"
    )

    orden_dimensiones = (
        tabla[
            [
                "Dimensión",
                "Promedio"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "Promedio",
            ascending=True
        )["Dimensión"]
        .tolist()
    )

    tabla["Dimensión"] = pd.Categorical(
        tabla["Dimensión"],
        categories=orden_dimensiones,
        ordered=True
    )

    tabla["Nivel"] = pd.Categorical(
        tabla["Nivel"],
        categories=ORDEN_NIVELES,
        ordered=True
    )

    return tabla


def crear_diagnostico_carrera(
    df_carrera,
    df_bloque,
    areas_detectadas,
    carrera_seleccionada
):
    """Genera lectura breve para coordinación."""

    promedio_carrera = crear_promedio_dimensiones(
        df_carrera,
        areas_detectadas
    )

    promedio_bloque = crear_promedio_dimensiones(
        df_bloque,
        areas_detectadas
    )

    if promedio_carrera.empty:
        return "No hay información suficiente para generar un diagnóstico."

    ranking = promedio_carrera.sort_values(
        "Promedio",
        ascending=True
    ).reset_index(drop=True)

    areas_prioritarias = ranking.head(2)
    area_fuerte = ranking.iloc[-1]

    promedio_global_carrera = df_carrera[
        (
            df_carrera["Estatus_inicio"] == "Inició"
        )
        &
        (
            df_carrera["Promedio_global_individual"].notna()
        )
    ]["Promedio_global_individual"].mean()

    promedio_global_bloque = df_bloque[
        (
            df_bloque["Estatus_inicio"] == "Inició"
        )
        &
        (
            df_bloque["Promedio_global_individual"].notna()
        )
    ]["Promedio_global_individual"].mean()

    prioridades = ", ".join(
        [
            (
                f"{fila['Dimensión']} "
                f"({fila['Promedio']:.1f}%)"
            )
            for _, fila in areas_prioritarias.iterrows()
        ]
    )

    diferencia = (
        promedio_global_carrera
        - promedio_global_bloque
    )

    if diferencia >= 0:
        comparacion = (
            f"{diferencia:.1f} puntos por encima"
        )
    else:
        comparacion = (
            f"{abs(diferencia):.1f} puntos por debajo"
        )

    return (
        f"**{carrera_seleccionada}** presenta un promedio global de "
        f"**{promedio_global_carrera:.1f}%**, equivalente a "
        f"**{comparacion}** del promedio general de "
        f"**{BLOQUES[df_bloque['Bloque'].iloc[0]]}**. "
        f"Las principales áreas de fortalecimiento son "
        f"**{prioridades}**. "
        f"La dimensión con mejor resultado es "
        f"**{area_fuerte['Dimensión']}** "
        f"({area_fuerte['Promedio']:.1f}%)."
    )


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
    Muestra carrera seleccionada contra el promedio del archivo.
    Las dos dimensiones más bajas se resaltan en rojo.
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
        st.info("No hay datos suficientes para generar el radar.")
        return

    orden_codigo = {
        codigo: indice
        for indice, codigo in enumerate(ORDEN_AREAS)
    }

    promedio_carrera = promedio_carrera.sort_values(
        "Código",
        key=lambda serie: serie.map(orden_codigo)
    )

    codigos = promedio_carrera["Código"].tolist()
    etiquetas = promedio_carrera["Dimensión"].tolist()
    valores_carrera = promedio_carrera["Promedio"].tolist()

    valores_bloque = []

    for codigo in codigos:
        fila_bloque = promedio_bloque[
            promedio_bloque["Código"] == codigo
        ]

        if fila_bloque.empty:
            valores_bloque.append(0)
        else:
            valores_bloque.append(
                float(fila_bloque["Promedio"].iloc[0])
            )

    ranking_bajo = promedio_carrera.sort_values(
        "Promedio",
        ascending=True
    ).head(2)

    etiquetas_bajas = ranking_bajo["Dimensión"].tolist()
    valores_bajos = ranking_bajo["Promedio"].tolist()

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
                size=6
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
                alpha=0.14
            ),
            hovertemplate=(
                f"<b>{carrera_seleccionada}</b><br>"
                "%{theta}: %{r:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=valores_bajos,
            theta=etiquetas_bajas,
            mode="markers",
            name="Áreas prioritarias",
            marker=dict(
                color="#E74C3C",
                size=14,
                line=dict(
                    color="white",
                    width=2
                )
            ),
            hovertemplate=(
                "<b>Área prioritaria</b><br>"
                "%{theta}: %{r:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title=f"Perfil de dimensiones · {carrera_seleccionada}",
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

    col_grafica, col_prioridades = st.columns(
        [3, 1]
    )

    with col_grafica:
        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col_prioridades:
        st.markdown("### 🔴 Áreas prioritarias")
        st.caption(
            "Las dos dimensiones con menor promedio "
            "en la carrera seleccionada."
        )

        for _, fila in ranking_bajo.iterrows():
            st.metric(
                fila["Dimensión"],
                f"{fila['Promedio']:.1f}%"
            )

        st.markdown("---")

        st.markdown("**Cómo leer el radar**")
        st.caption(
            f"Línea gris punteada: promedio de {nombre_bloque}. "
            "Puntos rojos: áreas prioritarias."
        )


def mostrar_matriz_rangos_dimension(
    df_carrera,
    areas_detectadas,
    carrera_seleccionada
):
    """
    Muestra matriz de distribución por rangos REALES de calificación.

    Las columnas son rangos de puntaje real, no porcentajes acumulados.
    """

    tabla = crear_matriz_rangos_dimension(
        df_carrera,
        areas_detectadas
    )

    if tabla.empty:
        st.info(
            "No hay información suficiente para generar la matriz."
        )
        return

    dimensiones = list(
        tabla["Dimensión"]
        .cat.categories
    )

    fig = go.Figure()

    for nivel in ORDEN_NIVELES:
        datos_nivel = tabla[
            tabla["Nivel"] == nivel
        ].copy()

        datos_nivel = datos_nivel.set_index(
            "Dimensión"
        ).reindex(
            dimensiones
        ).reset_index()

        textos = []

        for _, fila in datos_nivel.iterrows():
            textos.append(
                (
                    f"{fila['Porcentaje']:.0f}%"
                    f"<br><span style='font-size:11px'>"
                    f"n={int(fila['Aspirantes'])}</span>"
                )
            )

        fig.add_trace(
            go.Scatter(
                x=[RANGOS_NIVELES[nivel]] * len(dimensiones),
                y=dimensiones,
                mode="markers+text",
                text=textos,
                textposition="middle center",
                textfont=dict(
                    size=13,
                    color="white"
                    if nivel in ["Bajo", "Alto"]
                    else "#1F2937"
                ),
                marker=dict(
                    symbol="square",
                    size=95,
                    color=COLORES_NIVELES[nivel],
                    line=dict(
                        color="white",
                        width=2
                    )
                ),
                customdata=np.column_stack(
                    [
                        datos_nivel["Aspirantes"],
                        datos_nivel["Total"],
                        datos_nivel["Porcentaje"]
                    ]
                ),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"<b>Rango real:</b> {RANGOS_NIVELES[nivel]}<br>"
                    "<b>Aspirantes:</b> %{customdata[0]} de %{customdata[1]}<br>"
                    "<b>Porcentaje dentro de la dimensión:</b> "
                    "%{customdata[2]:.1f}%"
                    "<extra></extra>"
                ),
                name=f"{nivel} · {RANGOS_NIVELES[nivel]}",
                showlegend=False
            )
        )

    numero_dimensiones = len(dimensiones)

    fig.update_layout(
        title=(
            "Distribución por rangos reales de calificación · "
            f"{carrera_seleccionada}"
        ),
        xaxis=dict(
            title="Rangos reales de calificación",
            categoryorder="array",
            categoryarray=[
                RANGOS_NIVELES[nivel]
                for nivel in ORDEN_NIVELES
            ]
        ),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=dimensiones[::-1]
        ),
        height=max(
            440,
            numero_dimensiones * 95 + 150
        ),
        margin=dict(
            t=90,
            b=60,
            l=260,
            r=60
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Cada celda muestra el porcentaje y número de aspirantes "
        "que obtuvo una calificación dentro de ese rango real. "
        "Las columnas no representan porcentajes acumulados."
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
# PROCESAMIENTO DE ARCHIVOS
# ============================================================

datos_por_bloque = {}
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
        f"{ICONOS_BLOQUES[codigo]} {BLOQUES[codigo]}"
    ),
    label_visibility="collapsed"
)

informacion_bloque = datos_por_bloque[
    bloque_seleccionado
]

df_bloque = informacion_bloque["df"].copy()
areas_detectadas = informacion_bloque["areas"]
nombre_bloque = BLOQUES[bloque_seleccionado]

st.markdown(f"## {nombre_bloque}")

st.caption(
    f"Archivo analizado: {informacion_bloque['archivo']}"
)


# ============================================================
# SELECTOR DE CARRERA
# ============================================================

carreras_disponibles = sorted(
    df_bloque["Carrera_normalizada"]
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
# INDICADORES PRINCIPALES
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
]["Promedio_global_individual"].mean()

st.markdown(f"### Perfil de {carrera_seleccionada}")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Registrados", f"{total_registrados:,}")
col2.metric("Iniciaron", f"{total_iniciaron:,}")
col3.metric("No iniciaron", f"{total_no_iniciaron:,}")
col4.metric("% de inicio", f"{porcentaje_inicio:.1f}%")
col5.metric(
    "Promedio global",
    f"{promedio_global:.1f}%"
    if pd.notna(promedio_global)
    else "Sin dato"
)


# ============================================================
# RADAR Y ÁREAS PRIORITARIAS
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
# MATRIZ DE RANGOS REALES
# ============================================================

st.markdown("## Distribución de calificaciones por dimensión")

mostrar_matriz_rangos_dimension(
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
