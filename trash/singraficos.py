# app.py — Versión 17/11 22h (sin gráficos)
import streamlit as st
import pandas as pd
import re
from collections import Counter
from difflib import SequenceMatcher
import io
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------
# Configuración UI
# -----------------------------------------------------------
st.set_page_config(
    page_title="Analizador Crítico del Discurso - Redes Sociales",
    page_icon="📊",
    layout="wide"
)

SUPPORTED_PLATFORMS = ['facebook', 'instagram', 'x']  # X = Twitter
MAX_FILE_SIZE = 1024  # KB

# -----------------------------------------------------------
# Utilidades básicas
# -----------------------------------------------------------
def cargar_palabras_vacias():
    return {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'lo', 'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde',
        'durante', 'en', 'entre', 'hacia', 'hasta', 'mediante', 'para','por', 'según', 'sin', 'so', 'sobre', 'tras',
        'y', 'e', 'ni', 'que', 'pero', 'mas', 'aunque', 'sino', 'o','u', 'ora', 'bien', 'ya', 'sea', 'cuando', 'como', 'donde',
        'yo', 'tu', 'tú', 'él', 'ella', 'ello', 'nosotros', 'vosotros', 'ellos', 'ellas', 'me', 'te', 'se', 'nos', 'os', 'le', 'les',
        'mi', 'tu', 'su', 'nuestro', 'vuestro', 'su', 'mío', 'tuyo', 'muy', 'mucho', 'poco', 'bastante', 'demasiado', 'más', 'menos',
        'algo', 'nada', 'todo', 'siempre', 'nunca', 'jamás', 'también', 'tampoco', 'ahora', 'antes', 'después', 'luego', 'ayer', 'hoy',
        'mañana', 'si', 'no', 'tal', 'vez', 'quizás', 'acaso', 'así', 'bien', 'mal', 'mejor', 'peor', 'cerca', 'lejos', 'aquí', 'ahí',
        'allí', 'allá', 'acá', 'dentro', 'fuera', 'encima', 'debajo', 'es', 'son', 'era', 'eran', 'ser', 'estar', 'está', 'están',
        'tiene', 'tienen', 'tenía', 'tenían', 'haber', 'ha', 'han', 'había', 'habían', 'puede', 'pueden', 'podía', 'podían',
        'debe', 'deben', 'debía', 'debían', 'quiere', 'quieren', 'al', 'del', 'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'aquel', 'aquella', 'aquellos', 'aquellas', 'otro', 'otra', 'otros', 'otras', 'mismo', 'misma', 'mismos', 'mismas',
        'entonces', 'pues', 'así', 'además', 'también', 'incluso', 'hasta', 'inclusive', 'aparte', 'mientras', 'aunque', 'sin',
        'embargo', 'no', 'obstante', 'porque', 'puesto', 'que', 'pues', 'entonces', 'finalmente', 'últimamente',
        'bueno', 'vale', 'ok', 'hola', 'adiós', 'gracias', 'por favor', 'claro', 'exacto', 'obvio', 'realmente', 'actualmente', 'van', 'fue',
        'hacer', 'esto', 'tan', 'hizo', 'hacen', 'estar', 'alguna', 'eso', 'este', 'hay', 'años', 'qué', 'solo', 'dios', 'sabe', 'hace', 'sus',
        'https', 'comentarios', 'seguro', 'vamos', 'gente', 'diciendo', 'vos', 'quien', 'todos',
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
# DICCIONARIOS LÉXICOS (limpios)
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
    "groncha", "groncho", "gronchos",
    "marginal", "marginales",
    "planero", "planera", "planeros",
    "villero", "villera", "villeros",
    "ellos", "esta gente", "esa gente", "extranjeros",
    "gente de bien", "gente mala",
    "los de aca", "los de acá", "los de alla", "los de allá",
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

# Polarización (listas para búsqueda por regex)
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

# -----------------------------------------------------------
# Procesamiento de archivos 
# -----------------------------------------------------------
def procesar_archivo(file):
    """
    Devuelve: (texto_combinado, lista_comentarios)
    Maneja xlsx/csv/txt. No muestra mensajes por hoja.
    """
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            return procesar_excel_completo(file)
        elif file.name.endswith('.csv'):
            df = pd.read_csv(file)
            return procesar_dataframe_comments(df, file.name)
        elif file.name.endswith('.txt'):
            raw = file.getvalue().decode('utf-8', errors='ignore')
            comentarios = [line.strip() for line in raw.splitlines() if len(line.strip()) > 5]
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
                texto_hoja, comentarios = procesar_dataframe_comments(df, f"{file.name}:{hoja}", mostrar_mensajes=False)
                if texto_hoja:
                    textos_combinados.append(texto_hoja)
                    comentarios_list.extend(comentarios)
            except Exception:
                # NO mostrar mensajes por hoja
                continue
        return ' '.join(textos_combinados), comentarios_list
    except Exception as e:
        st.error(f"Error leyendo el archivo Excel: {e}")
        return "", []

def procesar_dataframe_comments(df, nombre_archivo, mostrar_mensajes=True):
    textos = []
    comentarios_list = []
    posibles_cols = ["comment", "Comment", "comments", "Comentario", "comentario", "texto", "Texto", "Comment Text"]
    col_comentarios = None
    for col in posibles_cols:
        if col in df.columns:
            col_comentarios = col
            break
    if not col_comentarios:
        # heurística
        for col in df.columns:
            if df[col].dtype == object:
                muestra = df[col].dropna().astype(str).head(12)
                if any(len(s.strip()) > 10 for s in muestra):
                    col_comentarios = col
                    break
    if col_comentarios:
        try:
            comentarios = df[col_comentarios].dropna().astype(str)
            comentarios_largos = [c for c in comentarios if len(c.strip()) > 5]
            textos.extend(comentarios_largos)
            comentarios_list.extend(comentarios_largos)
            # no mostramos mensajes por hoja acá (para evitar spam)
            if mostrar_mensajes:
                st.success(f"Archivo {nombre_archivo}: {len(comentarios_largos)} comentarios detectados.")
        except Exception as e:
            st.warning(f"Error leyendo columna de comentarios ({col_comentarios}): {e}")
    else:
        # si no se detecta, devolvemos vacío
        if mostrar_mensajes:
            st.warning(f"{nombre_archivo}: No se detectó columna de comentarios.")
    return " ".join(textos), comentarios_list

# -----------------------------------------------------------
# Análisis léxico (tokens, variantes, conteo)
# -----------------------------------------------------------
def analizar_texto(texto):
    palabras_vacias = cargar_palabras_vacias()
    texto_sin_menciones = re.sub(r'@\w+\b', '', texto)
    palabras = re.findall(r'\b[a-zA-Záéíóúñü]+\b', texto_sin_menciones.lower())
    palabras_filtradas = [p for p in palabras if p not in palabras_vacias and len(p) > 2]
    contador_inicial = Counter(palabras_filtradas)
    palabras_frecuentes = [palabra for palabra, freq in contador_inicial.most_common(200) if freq > 1]
    variantes = encontrar_variantes_automatico(palabras_frecuentes)
    conteo_final = {}
    procesadas = set()
    for palabra, frecuencia in contador_inicial.most_common():
        if palabra in procesadas:
            continue
        encontrada = False
        for principal, vars_list in variantes.items():
            if palabra == principal or palabra in vars_list:
                if principal not in conteo_final:
                    conteo_final[principal] = {'total': 0, 'variantes': {}}
                conteo_final[principal]['total'] += frecuencia
                if palabra != principal:
                    conteo_final[principal]['variantes'][palabra] = frecuencia
                procesadas.add(palabra)
                encontrada = True
                break
        if not encontrada:
            conteo_final[palabra] = {'total': frecuencia, 'variantes': {}}
            procesadas.add(palabra)
    return conteo_final, variantes, len(palabras_filtradas)

# -----------------------------------------------------------
# Detectores ACD usando diccionarios
# -----------------------------------------------------------
def detectar_frame(texto):
    texto = (texto or "").lower()
    scores = {"crimen": 0, "discriminacion": 0, "burla": 0, "reclamo": 0}
    for categoria, palabras in DICT_FRAMES.items():
        for p in palabras:
            if p in texto:
                scores[categoria] += 1
    if max(scores.values()) == 0:
        return 0
    ganador = max(scores, key=scores.get)
    mapping = {"crimen": 1, "discriminacion": 2, "burla": 3, "reclamo": 4}
    return mapping[ganador]

def detectar_polarizacion(texto):
    texto = (texto or "").lower()
    for exp in POLARIZACION_EXPLICITA:
        if exp in texto:
            return 2
    for imp in POLARIZACION_IMPLICITA:
        if imp in texto:
            return 1
    return 0

ESTIGMA_TRIBAL = set(diccionario_estigma_tipo_1 + diccionario_estigma_tipo_2 + diccionario_estigma_tipo_3)
def detectar_estigma_act(texto):
    texto = (texto or "").lower()
    for p in ESTIGMA_TRIBAL:
        if p in texto:
            return 1
    return 2

def detectar_estigma_tipo(texto):
    texto = (texto or "").lower()
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

TONO_CRITICO = ["