# app.py - Versión final integrada (Opción A)
import streamlit as st
import pandas as pd
import re
from collections import Counter
import os
from difflib import SequenceMatcher
import io
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt


# -----------------------------------------------------------
# Configuración UI
# -----------------------------------------------------------
st.set_page_config(
    page_title="Analizador Crítico del Discurso - Redes Sociales",
    page_icon="📊",
    layout="wide"
)

SUPPORTED_PLATFORMS = ['facebook', 'instagram', 'twitter', 'youtube', 'tiktok']
MAX_FILE_SIZE = 1024  # KB

# -----------------------------------------------------------
# Utilidades básicas
# -----------------------------------------------------------

def cargar_palabras_vacias():
    return {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'lo',
        'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde',
        'durante', 'en', 'entre', 'hacia', 'hasta', 'mediante', 'para',
        'por', 'según', 'sin', 'so', 'sobre', 'tras',
        'y', 'e', 'ni', 'que', 'pero', 'mas', 'aunque', 'sino', 'o',
        'u', 'ora', 'bien', 'ya', 'sea', 'cuando', 'como', 'donde',
        'yo', 'tú', 'él', 'ella', 'ello', 'nosotros', 'vosotros',
        'ellos', 'ellas', 'me', 'te', 'se', 'nos', 'os', 'le', 'les',
        'mi', 'tu', 'su', 'nuestro', 'vuestro', 'su', 'mío', 'tuyo',
        'muy', 'mucho', 'poco', 'bastante', 'demasiado', 'más', 'menos',
        'algo', 'nada', 'todo', 'siempre', 'nunca', 'jamás', 'también',
        'tampoco', 'ahora', 'antes', 'después', 'luego', 'ayer', 'hoy',
        'mañana', 'si', 'no', 'tal', 'vez', 'quizás', 'acaso', 'así',
        'bien', 'mal', 'mejor', 'peor', 'cerca', 'lejos', 'aquí', 'ahí',
        'allí', 'allá', 'acá', 'dentro', 'fuera', 'encima', 'debajo',
        'es', 'son', 'era', 'eran', 'ser', 'estar', 'está', 'están',
        'tiene', 'tienen', 'tenía', 'tenían', 'haber', 'ha', 'han',
        'había', 'habían', 'puede', 'pueden', 'podía', 'podían',
        'debe', 'deben', 'debía', 'debían', 'quiere', 'quieren',
        'al', 'del',
        'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'aquel', 'aquella', 'aquellos', 'aquellas', 'otro', 'otra',
        'otros', 'otras', 'mismo', 'misma', 'mismos', 'mismas',
        'entonces', 'pues', 'así', 'además', 'también', 'incluso',
        'hasta', 'inclusive', 'aparte', 'mientras', 'aunque', 'sin',
        'embargo', 'no', 'obstante', 'porque', 'puesto', 'que', 'pues',
        'entonces', 'finalmente', 'últimamente',
        'bueno', 'vale', 'ok', 'hola', 'adiós', 'gracias', 'por favor',
        'claro', 'exacto', 'obvio', 'realmente', 'actualmente', 'van', 'fue',
        'hacer', 'esto', 'tan', 'hizo', 'hacen', 'estar', 'alguna', 'eso', 'este',
        'hay', 'años', 'qué', 'solo', 'dios', 'sabe', 'hace', 'sus',
        'https', 'comentarios', 'seguro', 'vamos', 'gente', 'diciendovos',
        'quien', 'todos'
    }

def similar(a, b, umbral=0.8):
    return SequenceMatcher(None, a, b).ratio() >= umbral

def encontrar_variantes_automatico(palabras_frecuentes, umbral_similitud=0.75):
    variantes = {}
    palabras_procesadas = set()
    palabras_ordenadas = sorted(palabras_frecuentes, key=len, reverse=True)
    for i, palabra1 in enumerate(palabras_ordenadas):
        if palabra1 in palabras_procesadas:
            continue
        grupo = [palabra1]
        palabras_procesadas.add(palabra1)
        for palabra2 in palabras_ordenadas[i+1:]:
            if palabra2 in palabras_procesadas:
                continue
            if similar(palabra1, palabra2, umbral_similitud):
                grupo.append(palabra2)
                palabras_procesadas.add(palabra2)
        if len(grupo) > 1:
            palabra_principal = max(grupo, key=len)
            variantes[palabra_principal] = [p for p in grupo if p != palabra_principal]
    return variantes

# -----------------------------------------------------------
# DICCIONARIOS DEL ANÁLISIS ACD (versión integrada)
# -----------------------------------------------------------

diccionario_discriminacion = [
    "boliviana", "bolivianos", "boliviano", "bolita", "boliguayo",
    "chileno", "chilena", "chilenos",
    "colombiano", "colombiana", "colombianos",
    "coya", "coyas",
    "ecuatoriano", "ecuatoriana", "ecuatorianos",
    "extranjero", "extranjeros",
    "inmigrante", "inmigrantes",
    "paraguayo", "paraguaya", "paraguayos",
    "peruana", "peruanas", "peruano", "peruanos",
    "veneca", "veneco", "venezolano", "venezolana", "venezolanos",
    "amerindio", "fenotipo", "fisonomía", "indio", "india",
    "indigena", "marrón", "morocha", "morocho", "negra", "negro",
    "negrito", "pinta", "rasgos", "raza", "raza inferior",
    "groncha", "groncho", "marginal", "marginales",
    "planero", "planera", "planeros", "villero", "villera", "villeros",
    "ellos", "esta gente", "esa gente", "extranjeros", "gente de bien",
    "gente mala", "los de aca", "los de acá", "los de alla", "los de allá",
    "los extranjeros", "los morochos", "los otros",
    "los mismos de siempre", "nosotros", "todos iguales", "ustedes"
]

diccionario_burla = [
    "ajaj", "bobo", "cabeza de termo", "cara de", "cara de boludo",
    "cara de gil", "feo", "fea", "gordo", "gorda", "gordito",
    "hongo", "honguito", "idiota", "jaj", "jaja", "jajaj", "milo",
    "mongol", "monguito", "payaso", "pelotudo", "pelotudito",
    "pocoyo", "ridículo", "ridicula", "teletubi", "tonto"
]

diccionario_reclamo = [
    "denuncia", "impunidad", "inoperancia", "investigación",
    "investigacion", "justicia", "legalidad", "corrupcion",
    "corrupción", "estado", "gobierno", "ministro", "ministra",
    "policia", "policía", "politica", "política", "políticos",
    "politicos", "bullrich", "k", "kaka", "kukas",
    "kirchnerismo", "kirchnerista", "macrismo", "mileistas",
    "mileista", "peronismo", "peronista", "peronchos",
    "narcotrafico", "narcotráfico", "narcoestado",
    "sicario", "sicarios", "zona liberada"
]

diccionario_crimen = [
    "arma", "armado", "asesina", "asesino", "asesinato", "asesinar",
    "banda", "crimen", "delincuente", "delincuencia", "delincuentes",
    "femicidio", "fuga", "homicida", "homicidio", "ladrón",
    "ladrona", "ladrones", "mafia", "mafioso", "mafiosos",
    "muerte", "muerto", "narco", "narcos", "roba", "robó",
    "robo", "sospechoso", "tiroteo"
]

diccionario_estigma_tipo_1 = [
    "peruano", "peruanos", "boliviano", "bolivianos", "paraguayo",
    "colombiano", "venezolano", "veneco", "extranjero", "inmigrante",
    "sudaca"
]

diccionario_estigma_tipo_2 = [
    "negro", "negrito", "marrón", "morocho", "indio", "amerindio",
    "fenotipo", "rasgos", "cara de", "fisonomía", "pinta"
]

diccionario_estigma_tipo_3 = [
    "villero", "villera", "villeros", "planero", "planera",
    "planeros", "vago", "marginal", "cabeza de termo"
]

DICT_FRAMES = {
    "crimen": diccionario_crimen,
    "discriminacion": diccionario_discriminacion,
    "burla": diccionario_burla,
    "reclamo": diccionario_reclamo
}
# -----------------------------------------------------------
# Procesamiento de archivos -> texto combinado + lista de comentarios
# -----------------------------------------------------------

def procesar_archivo(file):
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            return procesar_excel_completo(file)
        elif file.name.endswith('.csv'):
            df = pd.read_csv(file)
            return procesar_dataframe_comments(df, file.name)
        elif file.name.endswith('.txt'):
            text = file.getvalue().decode('utf-8', errors='ignore')
            comentarios = [line.strip() for line in text.splitlines() if len(line.strip()) > 5]
            return ' '.join(comentarios), comentarios
        else:
            st.error(f"Formato no soportado: {file.name}")
            return "", []
    except Exception as e:
        st.error(f"Error procesando archivo: {e}")
        return "", []


def procesar_excel_completo(file):
    textos_combinados = []
    comentarios_list = []
    try:
        excel = pd.ExcelFile(file)
        for hoja in excel.sheet_names:
            try:
                df = pd.read_excel(file, sheet_name=hoja)
                texto_hoja, comentarios = procesar_dataframe_comments(df, f"{file.name}:{hoja}")
                textos_combinados.append(texto_hoja)
                comentarios_list.extend(comentarios)
            except Exception as e:
                st.warning(f"⚠️ Hoja '{hoja}' con error: {e}")
        return ' '.join(textos_combinados), comentarios_list
    except Exception as e:
        st.error(f"Error en archivo Excel: {e}")
        return "", []


def procesar_dataframe_comments(df, nombre_archivo):
    textos = []
    comentarios_list = []

    posibles_cols = ["comment", "Comment", "comments", "Comentario", "comentario", "texto", "Texto"]
    col_comentarios = None

    for col in posibles_cols:
        if col in df.columns:
            col_comentarios = col
            break

    if not col_comentarios:
        # búsqueda heurística
        for col in df.columns:
            if df[col].dtype == object:
                muestra = df[col].dropna().astype(str).head(12)
                if any(len(s) > 10 for s in muestra):
                    col_comentarios = col
                    break

    if col_comentarios:
        try:
            comentarios = df[col_comentarios].dropna().astype(str)
            comentarios_largos = [c for c in comentarios if len(c.strip()) > 5]
            textos.extend(comentarios_largos)
            comentarios_list.extend(comentarios_largos)
            st.success(f"📄 {nombre_archivo}: {len(comentarios_largos)} comentarios")
        except Exception as e:
            st.error(f"Error leyendo columna de comentarios ({col_comentarios}): {e}")
    else:
        st.warning(f"⚠️ {nombre_archivo}: No hay columna con comentarios detectada.")

    return " ".join(textos), comentarios_list


# -----------------------------------------------------------
# Análisis léxico: tokenización + variantes + conteo
# -----------------------------------------------------------

def analizar_texto(texto):
    palabras_vacias = cargar_palabras_vacias()

    texto = re.sub(r'@\w+\b', '', texto)
    tokens = re.findall(r'\b[a-zA-Záéíóúñü]+\b', texto.lower())

    tokens_filtrados = [
        t for t in tokens
        if t not in palabras_vacias and len(t) > 2
    ]

    conteo_bruto = Counter(tokens_filtrados)

    palabras_frecuentes = [
        palabra for palabra, freq in conteo_bruto.most_common(200) if freq > 1
    ]

    variantes = encontrar_variantes_automatico(palabras_frecuentes)
    conteo_final = {}
    usadas = set()

    for palabra, freq in conteo_bruto.most_common():
        if palabra in usadas:
            continue

        asignada = False
        for principal, variaciones in variantes.items():
            if palabra == principal or palabra in variaciones:
                if principal not in conteo_final:
                    conteo_final[principal] = {'total': 0, 'variantes': {}}
                conteo_final[principal]['total'] += freq

                if palabra != principal:
                    conteo_final[principal]['variantes'][palabra] = freq

                usadas.add(palabra)
                asignada = True
                break

        if not asignada:
            conteo_final[palabra] = {'total': freq, 'variantes': {}}
            usadas.add(palabra)

    return conteo_final, variantes, len(tokens_filtrados)


# -----------------------------------------------------------
# Detectores ACD basados en los diccionarios nuevos
# -----------------------------------------------------------

def detectar_frame(texto):
    texto = texto.lower()
    scores = {"crimen": 0, "discriminacion": 0, "burla": 0, "reclamo": 0}

    for categoria, palabras in DICT_FRAMES.items():
        for p in palabras:
            if p in texto:
                scores[categoria] += 1

    if max(scores.values()) == 0:
        return 0  # sin frame

    categoria = max(scores, key=scores.get)
    mapping = {"crimen": 1, "discriminacion": 2, "burla": 3, "reclamo": 4}
    return mapping[categoria]


# Polarización
POLARIZACION_EXPLICITA = [
    "nosotros", "ellos", "ustedes", "los de afuera", "los de aca",
    "los de acá", "los otros", "kukas", "los k", "libertarios",
    "mileistas", "los de la patria grande"
]

POLARIZACION_IMPLICITA = [
    "esa gente", "esta gente", "esa clase de gente", "esta clase de gente",
    "todos iguales", "siempre igual", "los mismos de siempre",
    "los morochos", "los extranjeros", "los de esa zona", "los de la villa"
]

def detectar_polarizacion(texto):
    texto = texto.lower()
    for p in POLARIZACION_EXPLICITA:
        if p in texto:
            return 2
    for p in POLARIZACION_IMPLICITA:
        if p in texto:
            return 1
    return 0


# Estigma activo (sí/no)
ESTIGMA_TRIBAL = (
    diccionario_estigma_tipo_1 +
    diccionario_estigma_tipo_2 +
    diccionario_estigma_tipo_3
)

def detectar_estigma_act(texto):
    texto = texto.lower()
    for p in ESTIGMA_TRIBAL:
        if p in texto:
            return 1
    return 2


# Subtipos de estigma
def detectar_estigma_tipo(texto):
    texto = texto.lower()

    for p in diccionario_estigma_tipo_1:
        if p in texto:
            return 1

    for p in diccionario_estigma_tipo_2:
        if p in texto:
            return 2

    for p in diccionario_estigma_tipo_3:
        if p in texto:
            return 3

    return 0


# Tono discursivo
TONO_CRITICO = [
    "que desastre", "que vergüenza", "vergonzoso", "como puede ser",
    "falta de justicia", "no deberia", "no debería"
]

TONO_HOSTIL = [
    "pelotudo", "idiota", "rata", "basura", "asqueroso", "mierda", "hdp",
    "forro", "deportarlos", "que se muera", "que se pudra", "latigazos",
    "ratas", "cerdos", "bestias"
]

TONO_SARCASMO = [
    "jaj", "jaja", "jajaj", "ajaj", "sí claro", "dale genio",
    "ok campeón", "ok campeon", "seguro que"
]

def detectar_tono(texto):
    texto = texto.lower()

    for p in TONO_SARCASMO:
        if p in texto:
            return 3  # sarcástico

    for p in TONO_HOSTIL:
        if p in texto:
            return 2  # hostil

    for p in TONO_CRITICO:
        if p in texto:
            return 1  # crítico

    return 1  # por defecto crítico
# -----------------------------------------------------------
# GRÁFICOS Y VISUALIZACIÓN
# -----------------------------------------------------------

def chart_categorias_frames(df, platform):
    st.subheader(f"📊 Distribución de Frames - {platform}")

    conteo = df['frame'].value_counts().sort_index()
    categorias = {0: "Sin frame", 1: "Crimen", 2: "Discriminación", 3: "Burla", 4: "Reclamo"}

    datos = pd.DataFrame({
        "Categoría": [categorias.get(i, i) for i in conteo.index],
        "Frecuencia": conteo.values
    })

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Categoría"], datos["Frecuencia"])
    ax.set_title("Frames detectados")
    ax.set_ylabel("Frecuencia")
    plt.xticks(rotation=45)

    st.pyplot(fig)


def chart_torta_frames(df, platform):
    st.subheader(f"🥧 Distribución porcentual de Frames - {platform}")

    conteo = df['frame'].value_counts()
    etiquetas = ["Sin frame", "Crimen", "Discriminación", "Burla", "Reclamo"]

    valores = [
        conteo.get(0, 0),
        conteo.get(1, 0),
        conteo.get(2, 0),
        conteo.get(3, 0),
        conteo.get(4, 0)
    ]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(valores, labels=etiquetas, autopct='%1.1f%%')
    ax.set_title("Participación de Frames")

    st.pyplot(fig)


# ----------------------------- POLARIZACIÓN -----------------------------

def chart_polarizacion(df, platform):
    st.subheader(f"⚡ Polarización - {platform}")

    conteo = df['polarizacion'].value_counts().sort_index()
    etiquetas = {0: "Ausente", 1: "Implícita", 2: "Explícita"}

    datos = pd.DataFrame({
        "Tipo": [etiquetas.get(i) for i in conteo.index],
        "Frecuencia": conteo.values
    })

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Tipo"], datos["Frecuencia"])
    ax.set_title("Polarización detectada")
    plt.xticks(rotation=45)

    st.pyplot(fig)


# ----------------------------- ESTIGMA -----------------------------

def chart_estigma_act(df, platform):
    st.subheader(f"🔍 Estigma Activo - {platform}")

    conteo = df['estigma_act'].value_counts().sort_index()
    etiquetas = {1: "Sí", 2: "No"}

    datos = pd.DataFrame({
        "Presencia": [etiquetas.get(i) for i in conteo.index],
        "Frecuencia": conteo.values
    })

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Presencia"], datos["Frecuencia"])
    ax.set_title("Estigma Tribal Presente")
    plt.xticks(rotation=45)

    st.pyplot(fig)


def chart_estigma_tipo(df, platform):
    st.subheader(f"🏷 Tipos de Estigma - {platform}")

    conteo = df['estigma_tipo'].value_counts().sort_index()
    etiquetas = {0: "Ausente", 1: "Nacionalidad", 2: "Color/Rasgos", 3: "Clase"}

    datos = pd.DataFrame({
        "Tipo": [etiquetas.get(i) for i in conteo.index],
        "Frecuencia": conteo.values
    })

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Tipo"], datos["Frecuencia"])
    ax.set_title("Subtipos de Estigma")
    plt.xticks(rotation=45)

    st.pyplot(fig)


# ----------------------------- TONO ----------------------------- 

def chart_tono(df, platform):
    st.subheader(f"🎙 Tono del Discurso - {platform}")

    conteo = df['tono'].value_counts().sort_index()
    etiquetas = {1: "Crítico", 2: "Hostil", 3: "Sarcástico"}

    datos = pd.DataFrame({
        "Tono": [etiquetas.get(i) for i in conteo.index],
        "Frecuencia": conteo.values
    })

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Tono"], datos["Frecuencia"])
    ax.set_title("Tono Discursivo")
    plt.xticks(rotation=45)

    st.pyplot(fig)


# ----------------------------- COMPARATIVOS ENTRE PLATAFORMAS ----------------------------- 

def comparar_frames(plataformas):
    st.subheader("📈 Comparación de Frames entre Plataformas")

    data = []
    for name, df in plataformas.items():
        conteo = df['frame'].value_counts()
        for frame, freq in conteo.items():
            data.append({
                "Plataforma": name,
                "Frame": frame,
                "Frecuencia": freq
            })

    df_comp = pd.DataFrame(data)
    df_comp['Frame'] = df_comp['Frame'].replace({
        0: "Sin frame",
        1: "Crimen",
        2: "Discriminación",
        3: "Burla",
        4: "Reclamo"
    })

    fig, ax = plt.subplots(figsize=(8, 5))
    for frame in df_comp['Frame'].unique():
        sub = df_comp[df_comp['Frame'] == frame]
        ax.plot(sub["Plataforma"], sub["Frecuencia"], marker="o", label=frame)

    ax.legend()
    ax.set_title("Comparación de Frames entre Plataformas")
    ax.set_ylabel("Frecuencia")

    st.pyplot(fig)


def comparar_metricas(plataformas):
    st.subheader("📊 Métricas Totales vs Únicas (Palabras)")

    data = []
    for name, df in plataformas.items():
        total_palabras = df['texto'].str.split().map(len).sum()
        unicas = len(set(" ".join(df['texto']).split()))

        data.append({
            "Plataforma": name,
            "Total Palabras": total_palabras,
            "Palabras Únicas": unicas
        })

    df_comp = pd.DataFrame(data)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(df_comp["Plataforma"], df_comp["Total Palabras"], alpha=0.6, label="Total")
    ax.bar(df_comp["Plataforma"], df_comp["Palabras Únicas"], alpha=0.6, label="Únicas")

    ax.legend()
    ax.set_title("Totales vs. Únicas")
    plt.xticks(rotation=45)

    st.pyplot(fig)
# -----------------------------------------------------------
# INTERFAZ STREAMLIT
# -----------------------------------------------------------

def procesar_plataforma(nombre, archivo):
    texto, comentarios = procesar_archivo(archivo)

    df = pd.DataFrame({"texto": comentarios})

    if df.empty:
        st.warning(f"No hay comentarios válidos para {nombre}")
        return None

    # Aplicar análisis ACD
    df["frame"] = df["texto"].apply(detectar_frame)
    df["polarizacion"] = df["texto"].apply(detectar_polarizacion)
    df["estigma_act"] = df["texto"].apply(detectar_estigma_act)
    df["estigma_tipo"] = df["texto"].apply(detectar_estigma_tipo)
    df["tono"] = df["texto"].apply(detectar_tono)

    return df



def exportar_csv(plataformas):
    st.subheader("📤 Exportación de Datos")

    for nombre, df in plataformas.items():
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"⬇ Descargar CSV - {nombre}",
            data=csv,
            file_name=f"{nombre}_analisis.csv",
            mime="text/csv"
        )



def main():
    st.title("🔎 Análisis Automático de Discurso en Redes Sociales")
    st.write("Tesis – Análisis Crítico del Discurso (ACD) • Racismo, Estigma y Frames")

    st.divider()

    st.header("📁 Subida de archivos por plataforma")

    col1, col2, col3 = st.columns(3)

    archivos = {
        "Facebook": col1.file_uploader("Facebook", type=["txt", "csv", "xlsx"]),
        "Instagram": col2.file_uploader("Instagram", type=["txt", "csv", "xlsx"]),
        "X": col3.file_uploader("X / Twitter", type=["txt", "csv", "xlsx"])
    }

    plataformas_procesadas = {}

    if st.button("🚀 Procesar archivos"):
        for nombre, archivo in archivos.items():
            if archivo is not None:
                st.write(f"### Procesando {nombre}...")
                df = procesar_plataforma(nombre, archivo)
                if df is not None:
                    plataformas_procesadas[nombre] = df

        if not plataformas_procesadas:
            st.error("No se cargó ningún archivo válido. Intenta nuevamente.")
            return

        st.success("Archivos procesados correctamente.")

        st.divider()
        st.header("📊 Resultados por Plataforma")

        for nombre, df in plataformas_procesadas.items():
            st.subheader(f"📌 Plataforma: {nombre}")
            st.write(df.head())

            chart_categorias_frames(df, nombre)
            chart_torta_frames(df, nombre)
            chart_polarizacion(df, nombre)
            chart_estigma_act(df, nombre)
            chart_estigma_tipo(df, nombre)
            chart_tono(df, nombre)

            st.divider()

        st.header("📈 Comparaciones entre plataformas")
        comparar_frames(plataformas_procesadas)
        comparar_metricas(plataformas_procesadas)

        st.divider()
        exportar_csv(plataformas_procesadas)


# -----------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# -----------------------------------------------------------

if __name__ == "__main__":
    main()
