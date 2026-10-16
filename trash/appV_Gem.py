# app.py - Versión final integrada y unificada para Tesis (ACD)
import streamlit as st
import pandas as pd
import re
from collections import Counter
import os
from difflib import SequenceMatcher
import io
# Importaciones necesarias para los gráficos
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
# DICCIONARIOS DEL ANÁLISIS ACD (Libro de Códigos)
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

# Estigma activo (sí/no)
ESTIGMA_TRIBAL = (
    diccionario_estigma_tipo_1 +
    diccionario_estigma_tipo_2 +
    diccionario_estigma_tipo_3
)

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
# Detectores ACD (Codificación del Libro de Códigos)
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


def detectar_polarizacion(texto):
    texto = texto.lower()
    for p in POLARIZACION_EXPLICITA:
        if p in texto:
            return 2
    for p in POLARIZACION_IMPLICITA:
        if p in texto:
            return 1
    return 0


def detectar_estigma_act(texto):
    texto = texto.lower()
    for p in ESTIGMA_TRIBAL:
        if p in texto:
            return 1
    return 2


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
# GRÁFICOS Y VISUALIZACIÓN (ESENCIALES PARA LA TESIS)
# -----------------------------------------------------------

def chart_torta_frames_principal(df, platform):
    st.subheader(f"🥧 1. Distribución del Foco Principal (Prueba de Desplazamiento)")

    # Nos centramos en Crimen, Discriminación y Reclamo (los Frames serios)
    conteo = df['frame'].value_counts()
    
    # Mapeo de valores
    etiquetas = {1: "Crimen/Justicia", 2: "Discriminación/Xenofobia", 4: "Reclamo Político"}
    
    # Filtrar solo los frames principales para la torta
    frames_principales = {k: conteo.get(k, 0) for k in [1, 2, 4]}

    total_frames = sum(frames_principales.values())
    if total_frames == 0:
        st.warning("No hay frames principales detectados para graficar.")
        return

    valores = list(frames_principales.values())
    labels_final = [f"{etiquetas[k]} ({v})" for k, v in frames_principales.items()]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        valores, 
        labels=labels_final, 
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops={'edgecolor': 'black'}
    )
    ax.set_title(f"Participación de Frames Principales en {platform}")
    ax.legend(loc='lower left', bbox_to_anchor=(-0.1, 0.5))
    st.pyplot(fig)


def chart_estigma_tipo(df, platform):
    st.subheader(f"🏷 2. Frecuencia de Tipos de Estigma (Interseccionalidad)")

    conteo = df['estigma_tipo'].value_counts().sort_index()
    
    # 0 = Ausente, pero lo quitamos para centrarnos en los tipos 1, 2, 3
    etiquetas = {1: "Nacionalidad", 2: "Color/Rasgos", 3: "Clase/Territorio"}
    
    datos = pd.DataFrame({
        "Tipo": [etiquetas.get(i) for i in conteo.index if i != 0],
        "Frecuencia": [conteo.get(i) for i in conteo.index if i != 0]
    })
    
    if datos.empty:
        st.warning("No hay subtipos de estigma detectados para graficar.")
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Tipo"], datos["Frecuencia"], color=['#4CAF50', '#FFC107', '#F44336'])
    ax.set_title(f"Subtipos de Estigma Activo en {platform}")
    ax.set_ylabel("Frecuencia")
    plt.xticks(rotation=45, ha='right')

    st.pyplot(fig)


def chart_tono(df, platform):
    st.subheader(f"🎙 3. Tono del Discurso (Racismo Inferencial)")

    conteo = df['tono'].value_counts().sort_index()
    etiquetas = {1: "Crítico", 2: "Hostil", 3: "Sarcástico"}

    datos = pd.DataFrame({
        "Tono": [etiquetas.get(i) for i in conteo.index],
        "Frecuencia": conteo.values
    })
    
    if datos.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Tono"], datos["Frecuencia"], color=['#2196F3', '#FF9800', '#9C27B0'])
    ax.set_title(f"Tono Discursivo en {platform}")
    ax.set_ylabel("Frecuencia")

    st.pyplot(fig)


def chart_estrategias_acd(df, platform):
    st.subheader(f"📈 4. Frecuencia de Estrategias Discursivas (Van Dijk)")
    
    # 1. Polarización Explícita (código 2 en la variable 'polarizacion')
    polarizacion_exp = (df['polarizacion'] == 2).sum()
    
    # 2. Hostilidad (código 2 en la variable 'tono') - Usado para medir Deshumanización/Agresión
    hostilidad = (df['tono'] == 2).sum()
    
    # 3. Estigma de Clase (código 3 en la variable 'estigma_tipo') - Usado para medir Interseccionalidad
    estigma_clase = (df['estigma_tipo'] == 3).sum()

    datos = pd.DataFrame({
        "Estrategia": ["Polarización Explícita", "Hostilidad (Deshumanización)", "Estigma Clase/Territorio"],
        "Frecuencia": [polarizacion_exp, hostilidad, estigma_clase]
    })
    
    if datos["Frecuencia"].sum() == 0:
        st.warning("No hay suficientes estrategias ACD detectadas para graficar.")
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(datos["Estrategia"], datos["Frecuencia"], color=['#795548', '#FF5722', '#607D8B'])
    ax.set_title(f"Estrategias ACD más Frecuentes en {platform}")
    ax.set_ylabel("Frecuencia")
    plt.xticks(rotation=45, ha='right')

    st.pyplot(fig)


def chart_frame_vs_tono(df, platform):
    st.subheader(f"🤝 5. Cruce: Discriminación vs Tono Hostil/Sarcástico")

    # Filtra los comentarios que son de Frame de Discriminación (código 2)
    df_disc = df[df['frame'] == 2]

    if df_disc.empty:
        st.warning("No hay comentarios de Frame Discriminación (código 2) para el cruce.")
        return

    # Contar la distribución del tono DENTRO del Frame de Discriminación
    conteo_tono = df_disc['tono'].value_counts().sort_index()
    
    etiquetas = {1: "Crítico", 2: "Hostil", 3: "Sarcástico"}
    
    # Asegurar que todas las categorías de tono estén presentes, aunque sea con 0
    df_cruce = pd.DataFrame({
        "Tono": [etiquetas[i] for i in range(1, 4)],
        "Frecuencia": [conteo_tono.get(i, 0) for i in range(1, 4)]
    })

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(df_cruce["Tono"], df_cruce["Frecuencia"], color=['#1A237E', '#C62828', '#4A148C'])
    ax.set_title(f"Tono en Comentarios con Frame de Discriminación en {platform}")
    ax.set_ylabel("Frecuencia")
    
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

    # Aplicar análisis ACD (Codificación)
    df["frame"] = df["texto"].apply(detectar_frame)
    df["polarizacion"] = df["texto"].apply(detectar_polarizacion)
    df["estigma_act"] = df["texto"].apply(detectar_estigma_act)
    df["estigma_tipo"] = df["texto"].apply(detectar_estigma_tipo)
    df["tono"] = df["texto"].apply(detectar_tono)

    return df


def display_key_charts(nombre, df):
    # Fila 1: Torta (Prueba de Hipótesis) y Estigma por Tipo (Interseccionalidad)
    colA, colB = st.columns(2)
    with colA:
        chart_torta_frames_principal(df, nombre)
    with colB:
        chart_estigma_tipo(df, nombre)

    # Fila 2: Tono (Racismo Inferencial) y Estrategias ACD (Van Dijk)
    colC, colD = st.columns(2)
    with colC:
        chart_tono(df, nombre)
    with colD:
        chart_estrategias_acd(df, nombre)

    # Fila 3: Cruce de Variables (Relación)
    colE, colF = st.columns(2)
    with colE:
        chart_frame_vs_tono(df, nombre)
    # colF queda vacío para mantener la alineación


def exportar_csv(plataformas):
    st.subheader("📤 Exportación de Datos")

    for nombre, df in plataformas.items():
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"⬇ Descargar CSV - {nombre} (Datos Codificados)",
            data=csv,
            file_name=f"{nombre}_analisis_codificado.csv",
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
            
            # LLAMADA A LA FUNCIÓN DE GRÁFICOS ESENCIALES
            display_key_charts(nombre, df)
            
            st.divider()
            
        st.header("📈 Comparación General (Solo métricas léxicas)")
        
        # Opcional: Si quieres mantener el conteo de palabras para la descripción del corpus
        # Se puede añadir una sección aquí para análisis léxico si lo necesitas en el Capítulo 4
        
        st.divider()
        exportar_csv(plataformas_procesadas)


# -----------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# -----------------------------------------------------------

if __name__ == "__main__":
    main()