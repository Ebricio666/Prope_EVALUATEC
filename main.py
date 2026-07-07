import io
import unicodedata

import pandas as pd
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
    "Carga y concentración inicial de participantes por carrera."
)


# ============================================================
# FUNCIONES
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


def encontrar_columna(df, posibles_nombres):
    """Encuentra una columna ignorando acentos, mayúsculas y espacios."""

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
    """
    Lee un archivo CSV intentando codificaciones frecuentes.
    """

    contenido = archivo.getvalue()

    codificaciones = [
        "utf-8",
        "utf-8-sig",
        "latin-1",
        "cp1252"
    ]

    for codificacion in codificaciones:
        try:
            return pd.read_csv(
                io.BytesIO(contenido),
                encoding=codificacion
            )
        except UnicodeDecodeError:
            continue

    return pd.read_csv(
        io.BytesIO(contenido),
        encoding="latin-1"
    )


def procesar_archivo(archivo):
    """
    Lee un CSV, valida encabezados y crea variables necesarias.
    """

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
            f"El archivo {archivo.name} no contiene una columna de Carrera."
        )

    if columna_inicio is None:
        raise ValueError(
            f"El archivo {archivo.name} no contiene una columna de InicioExamen."
        )

    df["Archivo_origen"] = archivo.name

    df["Carrera_normalizada"] = (
        df[columna_carrera]
        .fillna("Sin carrera especificada")
        .astype(str)
        .str.strip()
    )

    df["Inicio_normalizado"] = (
        df[columna_inicio]
        .apply(normalizar_texto)
    )

    df["Estatus_inicio"] = df["Inicio_normalizado"].apply(
        lambda valor: "Inició"
        if valor in ["si", "sí", "s", "1", "true"]
        else "No inició"
    )

    return df


def crear_concentrado_carreras(df):
    """
    Genera resumen de participantes por carrera e inicio de evaluación.
    """

    resumen = (
        df
        .groupby(
            ["Carrera_normalizada", "Estatus_inicio"]
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
        resumen["Inició"] + resumen["No inició"]
    )

    resumen["% inició"] = (
        resumen["Inició"]
        / resumen["Participantes"]
        * 100
    ).round(1)

    resumen["% no inició"] = (
        resumen["No inició"]
        / resumen["Participantes"]
        * 100
    ).round(1)

    resumen = resumen.rename(
        columns={
            "Carrera_normalizada": "Carrera"
        }
    )

    resumen = resumen[
        [
            "Carrera",
            "Participantes",
            "Inició",
            "No inició",
            "% inició",
            "% no inició"
        ]
    ].sort_values(
        by="Participantes",
        ascending=False
    )

    return resumen.reset_index(drop=True)


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
bitacora = []

for archivo in archivos_subidos:
    try:
        df_archivo = procesar_archivo(archivo)

        bases.append(df_archivo)

        bitacora.append(
            {
                "Archivo": archivo.name,
                "Registros": len(df_archivo),
                "Carreras detectadas": df_archivo[
                    "Carrera_normalizada"
                ].nunique(),
                "Estatus": "Procesado"
            }
        )

    except Exception as error:
        bitacora.append(
            {
                "Archivo": archivo.name,
                "Registros": 0,
                "Carreras detectadas": 0,
                "Estatus": f"Error: {error}"
            }
        )

if not bases:
    st.error(
        "No fue posible procesar los archivos. Revisa los encabezados."
    )

    st.dataframe(
        pd.DataFrame(bitacora),
        use_container_width=True,
        hide_index=True
    )

    st.stop()

df_general = pd.concat(
    bases,
    ignore_index=True,
    sort=False
)

df_bitacora = pd.DataFrame(bitacora)

concentrado_carreras = crear_concentrado_carreras(df_general)


# ============================================================
# RESULTADOS
# ============================================================

st.subheader("Resumen de carga")

total_participantes = len(df_general)
total_iniciaron = (df_general["Estatus_inicio"] == "Inició").sum()
total_no_iniciaron = (
    df_general["Estatus_inicio"] == "No inició"
).sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Participantes", f"{total_participantes:,}")
col2.metric("Carreras detectadas", f"{concentrado_carreras['Carrera'].nunique():,}")
col3.metric("Iniciaron evaluación", f"{total_iniciaron:,}")
col4.metric("No iniciaron", f"{total_no_iniciaron:,}")


st.markdown("## Participantes por carrera")

st.dataframe(
    concentrado_carreras,
    use_container_width=True,
    hide_index=True
)


st.markdown("## Bitácora de archivos procesados")

st.dataframe(
    df_bitacora,
    use_container_width=True,
    hide_index=True
)


with st.expander("Ver encabezados detectados por archivo"):
    for archivo in archivos_subidos:
        try:
            df_revision = leer_csv_archivo(archivo)

            st.markdown(f"### {archivo.name}")

            st.write(
                list(df_revision.columns)
            )

        except Exception as error:
            st.error(
                f"No fue posible revisar {archivo.name}: {error}"
            )
