import streamlit as st
import pandas as pd
import re
import io
import zipfile
from collections import Counter
from difflib import SequenceMatcher
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import networkx as nx
import itertools
import unicodedata

# -----------------------------------------------------------
# Configuración UI
# -----------------------------------------------------------
st.set_page_config(
    page_title="Analizador del Discurso - RRSS v2",
    page_icon="📊",
    layout="wide"
)

SUPPORTED_PLATFORMS = ['facebook', 'instagram', 'x']
MAX_FILE_SIZE = 1024  # KB

# -----------------------------------------------------------
# Utilidades básicas y Diccionarios
# -----------------------------------------------------------

def cargar_palabras_vacias():
    return {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'lo', 'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde',
        'durante', 'en', 'entre', 'hacia', 'hasta', 'mediante', 'para','por', 'según', 'sin', 'so', 'sobre', 'tras',
        'y', 'e', 'ni', 'que', 'pero', 'mas', 'although', 'sino', 'o', 'u', 'ora', 'bien', 'ya', 'sea', 'cuando', 'como', 'donde',
        'yo', 'tu', 'tú', 'él', 'ella', 'ello', 'nosotros', 'vosotros', 'ellos', 'ellas', 'me', 'te', 'se', 'nos', 'os', 'le', 'les',
        'mi', 'su', 'nuestro', 'vuestro', 'mío', 'tuyo', 'muy', 'mucho', 'poco', 'bastante', 'demasiado', 'más', 'menos',
        'algo', 'nada', 'todo', 'siempre', 'nunca', 'jamás', 'también', 'tampoco', 'ahora', 'antes', 'después', 'luego', 'ayer', 'hoy',
        'mañana', 'si', 'no', 'tal', 'vez', 'quizás', 'acaso', 'así', 'mal', 'mejor', 'peor', 'cerca', 'lejos', 'aquí', 'ahí',
        'allí', 'allá', 'acá', 'dentro', 'fuera', 'encima', 'debajo', 'es', 'son', 'era', 'eran', 'ser', 'estar', 'está', 'están',
        'tiene', 'tienen', 'tenía', 'tenían', 'haber', 'ha', 'han', 'había', 'habían', 'puede', 'pueden', 'podía', 'podían',
        'debe', 'deben', 'debía', 'debían', 'quiere', 'quieren', 'al', 'del','este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'aquel', 'aquella', 'aquellos', 'aquellas', 'otro', 'otra', 'otros', 'otras', 'mismo', 'misma', 'mismos', 'mismas',
        'entonces', 'pues', 'además', 'incluso', 'hasta', 'inclusive', 'aparte', 'mientras', 'embargo', 'obstante', 'porque', 
        'puesto', 'finalmente', 'últimamente', 'bueno', 'vale', 'ok', 'hola', 'adiós', 'gracias', 'por favor',
        'claro', 'exacto', 'obvio', 'realmente', 'actualmente', 'van', 'fue', 'hacer', 'esto', 'tan', 'hizo', 'hacen', 'alguna', 'eso',
        'hay', 'años', 'qué', 'solo', 'dios', 'sabe', 'hace', 'sus', 'https', 'comentarios', 'seguro', 'vamos', 'gente', 'diciendo',
        'quien', 'todos', 'todas', 'vos'
    }

def similar(a, b, umbral=0.8):
    return SequenceMatcher(None, a, b).ratio() >= umbral

def encontrar_variantes_automatico(palabras_frecuentes, umbral_similitud=0.70):
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

LEET_MAP = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "@": "a", "$": "s", "+": "t",
}

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = texto.lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in nfkd if not unicodedata.combining(c))
    texto = "".join(LEET_MAP.get(c, c) for c in texto)
    texto = re.sub(r"(.)\1{2,}", r"\1\1", texto)
    return texto

def normalizar_lista(lista):
    return [normalizar_texto(p) for p in lista]

# -----------------------------------------------------------
# Diccionarios de categorías
# -----------------------------------------------------------

diccionario_discriminacion = [
    "boliviana", "bolivianos", "boliviano", "bolita", "boliguayo", "chileno", "chilena", "chilenos",
    "colombiano", "colombiana", "colombianos", "coya", "coyas", "ecuatoriano", "ecuatoriana",
    "ecuatorianos", "extranjero", "extranjeros", "inmigrante", "inmigrantes", "paraguayo", "paraguaya",
    "paraguayos", "peruana", "peruanas", "peruano", "peruanos", "veneca", "veneco", "venezolano",
    "venezolana", "venezolanos", "amerindio", "fenotipo", "fisonomía", "indio", "india", "indigena",
    "marrón", "morocha", "morocho", "negra", "negro", "negrito", "pinta", "rasgos", "raza",
    "raza inferior", "groncha", "groncho", "gronchos", "marginal", "marginales", "planero", "planera",
    "planeros", "villero", "villera", "villeros"
]

diccionario_burla = [
    "ajaj", "bobo", "cabeza de termo", "cara de", "cara de boludo", "carita", "coqueta", "cara de gil",
    "feo", "fea", "gordo", "gorda", "gordito", "hongo", "honguito", "idiota", "jaj", "jaja", "jajaj",
    "milo", "mongol", "monguito", "payaso", "pelotudo", "pelotudito","pocoyo", "ridículo", "ridicula",
    "teletubi", "tonto", "thiago","tiago", "pzk"
]

diccionario_reclamo = [
    "denuncia", "humo", "impunidad", "inoperancia", "investigación", "investigacion", "justicia",
    "legalidad", "corrupcion", "corrupción", "estado", "gobierno", "ministro", "ministra", "policia",
    "policía", "politica", "política", "políticos", "politicos", "bullrich", "k", "kaka", "kukas",
    "kirchnerismo", "kirchnerista", "macrismo", "mileistas", "mileista", "peronismo", "peronista",
    "peronchos", "narcotrafico", "narcotráfico", "narcoestado", "sicario", "sicarios", "zona liberada"
]

diccionario_crimen = [
    "justicia", "investigacion", "investigación", "condena", "condenar", "pena", "carcel", "cárcel",
    "prision", "prisión", "perpetua", "cadena perpetua", "fiscal", "fiscalia", "fiscalía", "juez",
    "jueza", "tribunal", "juicio", "allanamiento", "detencion", "detención", "detenido", "detenida",
    "aprehendido", "captura", "profugo", "prófugo", "operativo", "policia", "policía", "gendarmeria",
    "gendarmería", "comisaria", "comisaría", "causa", "expediente", "imputado", "imputada",
    "arma", "armado", "asesina", "asesino", "asesinato", "asesinar", "banda", "crimen", "delincuente",
    "delincuencia", "delincuentes", "femicidio", "fuga", "homicida", "homicidio", "ladrón", "ladrona",
    "ladrones", "mafia", "mafioso", "mafiosos", "muerte", "muerto", "narco", "narcos", "roba", "robó",
    "robo", "sospechoso", "tiroteo", "victima", "víctima", "matar", "mato", "mató", "disparo", "bala",
    "familia", "madre", "padre", "hijo", "hija", "dolor", "duelo", "que se haga justicia",
    "preso", "presa", "presos", "presas", "prision preventiva", "reclusion", "reclusión",
    "condenado", "condenada", "condenados", "condenadas",
    "que pague", "que paguen", "que lo agarren", "que lo atrapen",
    "que no salga", "que se pudra", "se merece", "merece lo peor",
    "penitenciaria", "reo", "reos", "celda", "celdas",
    "pagara", "pagará", "pagaran", "pagarán",
]

diccionario_estigma_tipo_1 = [
    "colla", "coya", "peruano", "peruanos", "boliviano", "bolivianos", "paraguayo", "colombiano",
    "venezolano", "veneco", "extranjero", "inmigrante", "sudaca"
]

diccionario_estigma_tipo_2 = [
    "negro", "negrito", "marrón", "marronazo", "morocho", "indio", "amerindio", "fenotipo", "rasgos",
    "cara de", "fisonomía", "pinta"
]

diccionario_estigma_tipo_3 = [
    "villero", "villera", "villeros", "planero", "planera", "planeros", "vago", "marginal",
    "cabeza de termo"
]

diccionario_imagen_ia = [
    "inteligencia artificial", "es ia", "es una ia", "con ia", "hecho con ia",
    "hecha con ia", "hecho por ia", "hecha por ia", "por la ia", "por ia",
    "diseñado por ia", "diseñada por ia", "diseñado por la ia", "diseñada por la ia",
    "creado con ia", "creada con ia", "generado por ia", "generada por ia",
    "generado con ia", "generada con ia", "esta editada", "la editaron",
    "foto editada", "foto retocada", "retocaron", "photoshop", "con photoshop",
    "deepfake", "foto trucha", "es trucha", "truchada", "esta truchada",
    "no es real esa foto", "foto armada", "cara armada", "no es la foto real",
    "no se parece en nada", "parece ia", "es de ia",
]

DICT_FRAMES = {
    "crimen": diccionario_crimen,
    "discriminacion": diccionario_discriminacion,
    "burla": diccionario_burla,
    "reclamo": diccionario_reclamo,
    "imagen_ia": diccionario_imagen_ia,
}

POLARIZACION_EXPLICITA = [
    "nosotros", "ellos", "ustedes", "los de afuera", "los de aca","escoria","mierdas", "los de acá",
    "los otros", "kukas", "los k", "libertarios",  "lacras", "mugre", "mileistas", "los de la patria grande"
]

POLARIZACION_IMPLICITA = [
    "esa gente", "esta gente", "esa clase de gente", "esta clase de gente", "todos iguales",
    "siempre igual", "los mismos de siempre", "no juzgo","no discrimino", "los morochos",
    "los extranjeros", "los de esa zona", "los de la villa"
]

DICT_FRAMES_NORM = {categoria: normalizar_lista(lista) for categoria, lista in DICT_FRAMES.items()}
POLARIZACION_EXPLICITA_NORM = normalizar_lista(POLARIZACION_EXPLICITA)
POLARIZACION_IMPLICITA_NORM = normalizar_lista(POLARIZACION_IMPLICITA)
ESTIGMA_TIPO_1_NORM = normalizar_lista(diccionario_estigma_tipo_1)
ESTIGMA_TIPO_2_NORM = normalizar_lista(diccionario_estigma_tipo_2)
ESTIGMA_TIPO_3_NORM = normalizar_lista(diccionario_estigma_tipo_3)
ESTIGMA_TRIBAL_NORM = set(ESTIGMA_TIPO_1_NORM + ESTIGMA_TIPO_2_NORM + ESTIGMA_TIPO_3_NORM)

TONO_CRITICO = ["que desastre", "que vergüenza", "vergonzoso", "como puede ser", "falta de justicia", "no deberia", "no debería"]
TONO_HOSTIL = ["pelotudo", "idiota", "rata", "basura", "asqueroso", "mierda", "hdp", "forro", "deportarlos", "que se muera", "que se pudra"]
TONO_SARCASMO = ["jaj", "jaja", "jajaj", "ajaj", "sí claro", "si claro", "dale genio", "ok campeón", "ok campeon"]
TONO_CRITICO_NORM = normalizar_lista(TONO_CRITICO)
TONO_HOSTIL_NORM = normalizar_lista(TONO_HOSTIL)
TONO_SARCASMO_NORM = normalizar_lista(TONO_SARCASMO)

# -----------------------------------------------------------
# Esquema de frames
# -----------------------------------------------------------
FRAME_MAPPING = {
    "crimen": 0,
    "discriminacion": 1,
    "burla": 2,
    "reclamo": 3,
    "imagen_ia": 4,
}

FRAME_LABELS = {
    0: "Crimen",
    1: "Discriminación",
    2: "Burla",
    3: "Reclamo",
    4: "Sospecha IA",
    5: "Otra categoría",
    6: "Multimodal/Residual",
}

LABEL_A_KEY = {
    0: "crimen",
    1: "discriminacion",
    2: "burla",
    3: "reclamo",
    4: "imagen_ia",
}

# Patrón de emojis
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F000-\U0001F02F"
    "]+",
    flags=re.UNICODE
)

# Patrón de URLs ampliado
URL_PATTERN = re.compile(
    r"(https?://\S+)"
    r"|(www\.\S+)"
    r"|(\b[\w-]+\.(?:com|net|org|co|ar|uy|cl|pe|bo|py|ve|mx|es|io|be|tv|ly|gl|me)\b(?:/\S*)?)",
    flags=re.IGNORECASE
)

# STOPWORDS residual
STOPWORDS_RESIDUAL = {
    "jaja", "jajaja", "jajajaja", "jajajajaja", "jajaj", "jeje", "jejeje", "jejejeje",
    "jij", "jiji", "lol", "xd", "xdd", "xddd", "jsjs", "jsjsjs",
    "nooo", "noooo", "nooooo", "sii", "siii", "siiii", "nop", "nel",
    "ok", "oki", "okay", "dale", "wow", "uf", "uff", "ay", "epa", "ups", "eh", "ah",
    "hola", "chau", "gracias", "saludos",
    "mmm", "mmmm", "mm", "hmm", "hmmm", "ahh", "ahhh", "ohh", "ohhh",
    "uhh", "uhhh", "ehh", "ehhh", "bah", "puff", "grr",
    "nan", "none", "null", "undefined",
}

def es_multimodal_residual(texto):
    if not texto or not str(texto).strip():
        return True

    texto_str = str(texto)
    if texto_str.strip().lower() in {"nan", "none", "null", "n/a", "undefined"}:
        return True

    marcadores = ["[imagen]", "[foto]", "[video]", "[meme]", "[gif]",
                  "[sticker]", "imagen:", "foto:"]
    for m in marcadores:
        if m in texto_str.lower():
            return True

    tiene_url = bool(URL_PATTERN.search(texto_str))

    sin_url = URL_PATTERN.sub("", texto_str)
    sin_emoji = EMOJI_PATTERN.sub("", sin_url)
    sin_puntuacion = re.sub(r"[\s\W_]+", "", sin_emoji, flags=re.UNICODE)

    if len(sin_puntuacion) < 3:
        return True

    palabras = re.findall(r"\b\w+\b", sin_emoji.lower(), flags=re.UNICODE)
    if palabras and all(p in STOPWORDS_RESIDUAL for p in palabras):
        return True

    if tiene_url:
        texto_sin_url_norm = normalizar_texto(sin_url)
        matchea_diccionario = False
        for categoria, palabras_dict in DICT_FRAMES_NORM.items():
            for p in palabras_dict:
                if p and p in texto_sin_url_norm:
                    matchea_diccionario = True
                    break
            if matchea_diccionario:
                break
        if not matchea_diccionario:
            return True

    return False

# -----------------------------------------------------------
# Procesamiento de archivos
# -----------------------------------------------------------

def procesar_archivo(file):
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            return procesar_excel_completo(file)
        elif file.name.endswith('.csv'):
            return procesar_csv(file)
        elif file.name.endswith('.txt'):
            return procesar_txt(file)
        else:
            st.error(f"Formato no soportado: {file.name}")
            return "", [], []
    except Exception as e:
        st.error(f"Error procesando archivo: {e}")
        return "", [], []

def _csv_parece_tener_header(df):
    id_pattern = re.compile(r'^[A-Za-z]\d+_\d+$')
    for col in df.columns:
        col_str = str(col)
        if id_pattern.match(col_str):
            return False
        if len(col_str) > 40:
            return False
    return True

def procesar_csv(file):
    raw = file.getvalue()
    df = pd.read_csv(io.BytesIO(raw))
    if not _csv_parece_tener_header(df):
        df = pd.read_csv(io.BytesIO(raw), header=None)
    # mostrar_mensajes=False para evitar el doble anuncio
    return _extraer_columnas(df, file.name, mostrar_mensajes=False)

def procesar_txt(file):
    raw = file.getvalue().decode('utf-8', errors='ignore')
    comentarios = []
    ids = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        if '\t' in line:
            id_, comentario = line.split('\t', 1)
            ids.append(id_.strip())
            comentarios.append(comentario.strip())
        else:
            ids.append("")
            comentarios.append(line.strip())
    texto_para_conteo = ' '.join(c for c in comentarios if len(c.strip()) > 5)
    return texto_para_conteo, comentarios, ids

def procesar_excel_completo(file):
    textos_combinados = []
    comentarios_list = []
    ids_list = []
    try:
        excel = pd.ExcelFile(file)
        for hoja in excel.sheet_names:
            try:
                df = pd.read_excel(file, sheet_name=hoja)
                texto_hoja, comentarios, ids = _extraer_columnas(df, f"{file.name}:{hoja}", mostrar_mensajes=False)
                if comentarios:
                    textos_combinados.append(texto_hoja)
                    comentarios_list.extend(comentarios)
                    ids_list.extend(ids)
            except Exception:
                continue
        return ' '.join(textos_combinados), comentarios_list, ids_list
    except Exception as e:
        st.error(f"Error leyendo Excel: {e}")
        return "", [], []

def _extraer_columnas(df, nombre_archivo, mostrar_mensajes=True):
    col_comentarios = None
    col_id = None

    posibles_comment = ["comment", "Comment", "comments", "Comentario", "comentario",
                        "texto", "Texto", "Comment Text"]
    for c in posibles_comment:
        if c in df.columns:
            col_comentarios = c
            break

    posibles_id = ["id", "ID", "Id", "comment_id", "commentId", "post_id"]
    for c in posibles_id:
        if c in df.columns:
            col_id = c
            break

    if col_comentarios is None:
        if df.shape[1] >= 2:
            col_id = df.columns[0]
            col_comentarios = df.columns[1]
        elif df.shape[1] == 1:
            col_comentarios = df.columns[0]

    if col_comentarios is None:
        for c in df.columns:
            if df[c].dtype == object:
                muestra = df[c].dropna().astype(str).head(12)
                if any(len(s.strip()) > 10 for s in muestra):
                    col_comentarios = c
                    break

    if col_id is None and col_comentarios is not None and df.shape[1] >= 2:
        for c in df.columns:
            if c != col_comentarios:
                col_id = c
                break

    textos = []
    comentarios_list = []
    ids_list = []

    if col_comentarios is not None:
        try:
            comentarios = df[col_comentarios].fillna("").astype(str).tolist()
            if col_id is not None:
                ids = df[col_id].fillna("").astype(str).tolist()
            else:
                ids = [""] * len(comentarios)

            comentarios_list.extend(comentarios)
            ids_list.extend(ids)

            comentarios_para_conteo = [c for c in comentarios if len(c.strip()) > 5]
            textos.extend(comentarios_para_conteo)

            if mostrar_mensajes:
                st.success(
                    f"Archivo {nombre_archivo}: "
                    f"{len(comentarios)} comentarios cargados "
                    f"({len(comentarios_para_conteo)} para conteo de palabras)."
                )
        except Exception as e:
            if mostrar_mensajes:
                st.warning(f"Error leyendo columnas en {nombre_archivo}: {e}")
    else:
        if mostrar_mensajes:
            st.warning(f"{nombre_archivo}: No se detectó columna de comentarios.")

    return " ".join(textos), comentarios_list, ids_list

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
# Detección de categorías
# -----------------------------------------------------------

def detectar_frame(texto):
    if not texto or not str(texto).strip():
        return 6
    if es_multimodal_residual(texto):
        return 6

    texto_norm = normalizar_texto(str(texto))

    scores = {k: 0 for k in FRAME_MAPPING.keys()}
    for categoria, palabras in DICT_FRAMES_NORM.items():
        for p in palabras:
            if p and p in texto_norm:
                scores[categoria] += 1

    if scores["imagen_ia"] > 0:
        return 4
    if scores["discriminacion"] > 0:
        return 1

    max_score = max(scores.values())
    if max_score == 0:
        return 5

    for cat in ["burla", "reclamo", "crimen"]:
        if scores[cat] == max_score:
            return FRAME_MAPPING[cat]

    return 5

def detectar_polarizacion(texto):
    texto = normalizar_texto(texto)
    for exp in POLARIZACION_EXPLICITA_NORM:
        if exp in texto: return 2
    for imp in POLARIZACION_IMPLICITA_NORM:
        if imp in texto: return 1
    return 0

def detectar_estigma_act(texto):
    texto = normalizar_texto(texto)
    for p in ESTIGMA_TRIBAL_NORM:
        if p in texto: return 1
    return 0

def detectar_estigma_tipo(texto):
    texto = normalizar_texto(texto)
    for p in ESTIGMA_TIPO_1_NORM:
        if p in texto: return 1
    for p in ESTIGMA_TIPO_2_NORM:
        if p in texto: return 2
    for p in ESTIGMA_TIPO_3_NORM:
        if p in texto: return 3
    return 0

def detectar_tono(texto):
    texto = normalizar_texto(texto)
    for p in TONO_HOSTIL_NORM:
        if p in texto: return 2
    for p in TONO_SARCASMO_NORM:
        if p in texto: return 3
    for p in TONO_CRITICO_NORM:
        if p in texto: return 1
    return 0

# -----------------------------------------------------------
# FUNCIONES DE UI Y GRÁFICOS
# -----------------------------------------------------------

def categorizar_palabras_interactivo(platform_data):
    st.subheader("🏷️ Lista consolidada de palabras frecuentes")
    palabras_agregadas = {}
    for platform, pdata in platform_data.items():
        resultados = pdata.get('resultados', {})
        for palabra, info in resultados.items():
            palabras_agregadas[palabra] = palabras_agregadas.get(palabra, 0) + int(info.get('total', 0))

    if not palabras_agregadas:
        st.info("No se detectaron palabras frecuentes aún. Procesá archivos primero.")
        return

    top_items = sorted(palabras_agregadas.items(), key=lambda x: x[1], reverse=True)[:50]
    df_top = pd.DataFrame(top_items, columns=["Palabra", "Frecuencia Total"])
    st.dataframe(df_top, use_container_width=True)

def mostrar_top10_por_categoria(platform_data):
    """Tarjetas compactas con el top 10 de palabras por categoría."""
    st.subheader("🏆 Top 10 palabras por categoría")
    st.caption("Palabras más frecuentes dentro de cada frame (excluye stopwords).")

    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        st.info("No hay datos cargados.")
        return

    stopwords = cargar_palabras_vacias()
    tops_por_cat = {}
    conteo_por_cat = {}

    for cat_val in FRAME_LABELS.keys():
        df_cat = df_all[df_all["frame_label"] == cat_val]
        conteo_por_cat[cat_val] = len(df_cat)
        if df_cat.empty:
            tops_por_cat[cat_val] = []
            continue
        palabras = []
        for texto in df_cat["clean_comment"].dropna():
            palabras.extend(re.findall(r'\b[a-záéíóúñü]+\b', str(texto).lower()))
        palabras = [p for p in palabras if p not in stopwords and len(p) > 2]
        tops_por_cat[cat_val] = Counter(palabras).most_common(10)

    cat_keys = list(FRAME_LABELS.keys())
    for start in range(0, len(cat_keys), 4):
        cols = st.columns(4)
        for i, cat_val in enumerate(cat_keys[start:start+4]):
            with cols[i]:
                nombre = FRAME_LABELS[cat_val]
                top = tops_por_cat[cat_val]
                conteo = conteo_por_cat[cat_val]
                with st.container(border=True):
                    st.markdown(f"**{nombre}**  \n<small>{conteo} comentarios</small>", unsafe_allow_html=True)
                    st.markdown("")
                    if top:
                        for palabra, freq in top:
                            st.markdown(f"<small>• {palabra} <span style='color:gray'>({freq})</span></small>", unsafe_allow_html=True)
                    else:
                        st.caption("Sin datos")

def obtener_top20_global(platform_data, top_n=20):
    palabras_agregadas = {}
    for platform, pdata in platform_data.items():
        resultados = pdata.get('resultados', {})
        for palabra, info in resultados.items():
            freq = int(info.get('total', 0))
            palabras_agregadas[palabra] = palabras_agregadas.get(palabra, 0) + freq
    top = sorted(palabras_agregadas.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return top

def grafico_top20_discriminacion(platform_data):
    top20 = obtener_top20_global(platform_data, top_n=20)
    if not top20: return None
    df = pd.DataFrame(top20, columns=["palabra", "frecuencia"])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(df["palabra"], df["frecuencia"])
    ax.set_title("Palabras más frecuentes (Top 20)")
    ax.set_ylabel("Frecuencia")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig

def grafico2_barras_agrupadas(platform_data):
    datos = []
    for platform, pdata in platform_data.items():
        df = pdata.get("comments_df", pd.DataFrame())
        for val, nombre in FRAME_LABELS.items():
            if "frame_label" in df.columns:
                freq = int((df["frame_label"] == val).sum())
            else:
                freq = 0
            datos.append({"Plataforma": platform.capitalize(), "Categoria": nombre, "Frecuencia": freq})
    if not datos: return None
    df_chart = pd.DataFrame(datos)
    fig = px.bar(df_chart, x="Categoria", y="Frecuencia", color="Plataforma", barmode="group",
                 title="Comparación de categorías por plataforma (Frames ACD)")
    return fig

def grafico4_torta_frames(platform_data):
    df = pd.concat([pdata.get("comments_df", pd.DataFrame({"clean_comment": []})) for pdata in platform_data.values()], ignore_index=True)
    if df.empty: return None
    data = {nombre: int((df.get("frame_label") == val).sum()) for val, nombre in FRAME_LABELS.items()}
    df_chart = pd.DataFrame({"Categoria": list(data.keys()), "Frecuencia": list(data.values())})
    df_chart = df_chart[df_chart["Frecuencia"] > 0]
    fig = px.pie(df_chart, names="Categoria", values="Frecuencia", title="Distribución general de Frames (ACD)")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def calcular_coocurrencia(df_comments, top_palabras):
    coocurrencia = Counter()
    for comentario in df_comments["clean_comment"].dropna():
        palabras_en_comentario = set(re.findall(r'\b[a-z]+\b', str(comentario).lower()))
        palabras_presentes = [p for p in top_palabras if p in palabras_en_comentario]
        for par in itertools.combinations(palabras_presentes, 2):
            par_ordenado = tuple(sorted(par))
            coocurrencia[par_ordenado] += 1
    return coocurrencia

def grafico6_red_coocurrencia(platform_data, top_n=30, umbral=2):
    top_items = obtener_top20_global(platform_data, top_n=top_n)
    if not top_items: return None
    top_palabras = [item[0] for item in top_items]
    df_global = pd.concat([pdata.get("comments_df", pd.DataFrame({"clean_comment": []})) for pdata in platform_data.values()], ignore_index=True)
    coocurrencias = calcular_coocurrencia(df_global, top_palabras)
    G = nx.Graph()
    for (w1, w2), peso in coocurrencias.items():
        if peso >= umbral: G.add_edge(w1, w2, weight=peso)
    if len(G.nodes) == 0: return None
    pos = nx.spring_layout(G, k=0.8, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#cccccc'), hoverinfo='none', mode='lines')
    node_x, node_y, textos, tamanos = [], [], [], []
    for node in G.nodes():
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        textos.append(node)
        tamanos.append(G.degree(node) * 4 + 12)
    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=textos, textposition="top center", hoverinfo='text', marker=dict(showscale=False, color='#FF7F0E', size=tamanos, line=dict(width=2, color='white')))
    fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(title=f'Red Semántica de Co-ocurrencia (Top {top_n} palabras)', showlegend=False, hovermode='closest', margin=dict(b=20, l=5, r=5, t=40), xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), plot_bgcolor='rgba(0,0,0,0)'))
    return fig

# -----------------------------------------------------------
# NUEVAS FUNCIONES PARA EXPORTACIÓN AVANZADA
# -----------------------------------------------------------

def extraer_post_desde_id(id_str):
    if not id_str:
        return ""
    s = str(id_str).strip()
    if "_" in s:
        return s.split("_")[0]
    return ""

def clasificar_tipo_residual(texto):
    if not texto or not str(texto).strip():
        return "vacío"
    if str(texto).strip().lower() in {"nan", "none", "null", "n/a", "undefined"}:
        return "vacío"

    texto_str = str(texto)
    texto_lower = texto_str.lower()
    marcadores = ["[imagen]", "[foto]", "[video]", "[meme]", "[gif]", "[sticker]", "imagen:", "foto:"]
    for m in marcadores:
        if m in texto_lower:
            return "marcador_multimedia"

    tiene_url = bool(URL_PATTERN.search(texto_str))
    tiene_emoji = bool(EMOJI_PATTERN.search(texto_str))

    sin_url = URL_PATTERN.sub("", texto_str)
    sin_emoji = EMOJI_PATTERN.sub("", sin_url)
    sin_puntuacion = re.sub(r"[\s\W_]+", "", sin_emoji, flags=re.UNICODE)

    if len(sin_puntuacion) < 3:
        if tiene_emoji and tiene_url:
            return "emoji_y_link"
        if tiene_emoji:
            return "solo_emoji"
        if tiene_url:
            return "solo_link"
        return "otro"

    palabras = re.findall(r"\b\w+\b", sin_emoji.lower(), flags=re.UNICODE)
    if palabras and all(p in STOPWORDS_RESIDUAL for p in palabras):
        return "risa_sin_contexto"

    if tiene_url:
        return "link_dominante"

    return "otro"

def contar_matcheos(texto):
    if not texto or not str(texto).strip():
        return None
    if es_multimodal_residual(texto):
        return None

    texto_norm = normalizar_texto(str(texto))
    matches = {}
    for categoria, palabras_dict in DICT_FRAMES_NORM.items():
        matches[categoria] = []
        for p in palabras_dict:
            if p and p in texto_norm:
                matches[categoria].append(p)
    return matches

def _unir_dataframes(platform_data):
    dfs = []
    for plat, pdata in platform_data.items():
        df = pdata.get("comments_df", pd.DataFrame())
        if not df.empty:
            df = df.copy()
            df["platform"] = plat
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def construir_dataset_maestro(platform_data):
    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        return pd.DataFrame()

    return pd.DataFrame({
        "id": df_all["id"],
        "platform": df_all["platform"],
        "post": df_all["id"].apply(extraer_post_desde_id),
        "comment": df_all["comment"],
        "clean_comment": df_all["clean_comment"],
        "frame_label": df_all["frame_label"],
        "frame_nombre": df_all["frame_label"].map(FRAME_LABELS),
        "longitud": df_all["clean_comment"].astype(str).str.len(),
    })

def construir_metricas_reframing(platform_data):
    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        return pd.DataFrame()

    def calcular(df, nombre):
        total = len(df)
        crimen = int((df["frame_label"] == 0).sum())
        reframing = total - crimen
        indice = (reframing / total * 100) if total > 0 else 0

        alternativos = df[~df["frame_label"].isin([0, 6])]["frame_label"]
        if not alternativos.empty:
            top = alternativos.mode().iloc[0]
            frame_dom = FRAME_LABELS.get(int(top), "")
        else:
            frame_dom = ""

        return {
            "nivel": nombre,
            "total": total,
            "crimen": crimen,
            "reframing": reframing,
            "indice_reframing_pct": round(indice, 1),
            "frame_alternativo_dominante": frame_dom,
        }

    filas = [calcular(df_all, "Global")]
    for plat in sorted(platform_data.keys()):
        df_p = df_all[df_all["platform"] == plat]
        if not df_p.empty:
            filas.append(calcular(df_p, plat.capitalize()))

    return pd.DataFrame(filas)

def construir_resumen_categorias(platform_data):
    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        return pd.DataFrame()

    total = len(df_all)
    stopwords = cargar_palabras_vacias()

    filas = []
    for cat_val, cat_nombre in FRAME_LABELS.items():
        df_cat = df_all[df_all["frame_label"] == cat_val]
        conteo = len(df_cat)

        if conteo == 0:
            filas.append({
                "frame_label": cat_val,
                "frame_nombre": cat_nombre,
                "conteo": 0,
                "porcentaje": 0.0,
                "top_palabras": "",
                "top_bigramas": "",
                "ejemplos_ids": "",
            })
            continue

        porcentaje = round(conteo / total * 100, 1)

        palabras = []
        for texto in df_cat["clean_comment"].dropna():
            palabras.extend(re.findall(r'\b[a-záéíóúñü]+\b', str(texto).lower()))
        palabras = [p for p in palabras if p not in stopwords and len(p) > 2]
        top_palabras = Counter(palabras).most_common(20)
        top_palabras_str = "; ".join(f"{p} ({c})" for p, c in top_palabras)

        bigramas = Counter()
        for texto in df_cat["clean_comment"].dropna():
            palabras_t = re.findall(r'\b[a-záéíóúñü]+\b', str(texto).lower())
            palabras_t = [p for p in palabras_t if p not in stopwords and len(p) > 2]
            for i in range(len(palabras_t) - 1):
                bigramas[f"{palabras_t[i]} {palabras_t[i+1]}"] += 1
        top_bigramas = bigramas.most_common(10)
        top_bigramas_str = "; ".join(f"{b} ({c})" for b, c in top_bigramas)

        ids_ejemplo = df_cat["id"].head(15).tolist()
        ids_str = "; ".join(str(i) for i in ids_ejemplo if i)

        filas.append({
            "frame_label": cat_val,
            "frame_nombre": cat_nombre,
            "conteo": conteo,
            "porcentaje": porcentaje,
            "top_palabras": top_palabras_str,
            "top_bigramas": top_bigramas_str,
            "ejemplos_ids": ids_str,
        })

    return pd.DataFrame(filas)

def construir_reframing_por_post(platform_data):
    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        return pd.DataFrame()

    df_all["post"] = df_all["id"].apply(extraer_post_desde_id)
    df_all = df_all[df_all["post"] != ""]
    if df_all.empty:
        return pd.DataFrame()

    filas = []
    for (plat, post), grupo in df_all.groupby(["platform", "post"]):
        total = len(grupo)
        crimen = int((grupo["frame_label"] == 0).sum())
        reframing = total - crimen
        crimen_pct = round(crimen / total * 100, 1) if total > 0 else 0
        reframing_pct = round(reframing / total * 100, 1) if total > 0 else 0

        alternativos = grupo[~grupo["frame_label"].isin([0, 6])]["frame_label"]
        frame_alt = ""
        if not alternativos.empty:
            top = alternativos.mode().iloc[0]
            frame_alt = FRAME_LABELS.get(int(top), "")

        filas.append({
            "post": post,
            "plataforma": plat.capitalize(),
            "total": total,
            "crimen_pct": crimen_pct,
            "reframing_pct": reframing_pct,
            "frame_alternativo_dominante": frame_alt,
        })

    df_out = pd.DataFrame(filas).sort_values("reframing_pct", ascending=False).reset_index(drop=True)
    return df_out

def construir_fronterizos(platform_data):
    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        return pd.DataFrame()

    df_front = df_all[df_all["frame_label"] == 5].copy()
    if df_front.empty:
        return pd.DataFrame()

    return pd.DataFrame({
        "id": df_front["id"],
        "platform": df_front["platform"],
        "post": df_front["id"].apply(extraer_post_desde_id),
        "comment": df_front["comment"],
    })

def construir_residuales(platform_data):
    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        return pd.DataFrame()

    df_res = df_all[df_all["frame_label"] == 6].copy()
    if df_res.empty:
        return pd.DataFrame()

    return pd.DataFrame({
        "id": df_res["id"],
        "platform": df_res["platform"],
        "post": df_res["id"].apply(extraer_post_desde_id),
        "comment": df_res["comment"],
        "tipo_residual": df_res["comment"].apply(clasificar_tipo_residual),
    })

def construir_prototipicos(platform_data, top_n_por_cat=20):
    df_all = _unir_dataframes(platform_data)
    if df_all.empty:
        return pd.DataFrame()

    df_valid = df_all[~df_all["frame_label"].isin([5, 6])].copy()
    if df_valid.empty:
        return pd.DataFrame()

    filas = []
    for _, row in df_valid.iterrows():
        cat = int(row["frame_label"])
        key = LABEL_A_KEY.get(cat)
        if not key:
            continue
        matches = contar_matcheos(row["clean_comment"])
        if matches is None:
            continue
        palabras = matches.get(key, [])
        filas.append({
            "id": row["id"],
            "platform": row["platform"],
            "post": extraer_post_desde_id(row["id"]),
            "comment": row["comment"],
            "frame_label": cat,
            "frame_nombre": FRAME_LABELS.get(cat, ""),
            "n_matcheos": len(palabras),
            "palabras_matcheadas": "; ".join(palabras),
        })

    df_out = pd.DataFrame(filas)
    if df_out.empty:
        return df_out

    top_rows = []
    for cat in sorted(df_out["frame_label"].unique()):
        sub = df_out[df_out["frame_label"] == cat].sort_values(
            "n_matcheos", ascending=False
        ).head(top_n_por_cat)
        top_rows.append(sub)

    return pd.concat(top_rows, ignore_index=True)

def empaquetar_zip(archivos_dict):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, df in archivos_dict.items():
            if df is None or df.empty:
                continue
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            zf.writestr(nombre, csv_bytes)
    buffer.seek(0)
    return buffer

def construir_excel(archivos_dict):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre, df in archivos_dict.items():
            if df is None or df.empty:
                continue
            sheet_name = nombre.replace(".csv", "")[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    return buffer

def export_results(platform_data):
    st.header("📥 Exportar Resultados")

    if not platform_data:
        st.info("No hay datos para exportar.")
        return

    metricas_df = construir_metricas_reframing(platform_data)
    dataset_df = construir_dataset_maestro(platform_data)
    resumen_df = construir_resumen_categorias(platform_data)
    por_post_df = construir_reframing_por_post(platform_data)
    fronterizos_df = construir_fronterizos(platform_data)
    residuales_df = construir_residuales(platform_data)
    prototipicos_df = construir_prototipicos(platform_data)

    if not metricas_df.empty:
        st.subheader("📊 Métricas de reframing")
        st.caption(
            "Índice de reframing = (total − crimen) / total. "
            "Mide qué proporción de comentarios desplazó el foco del hecho delictivo "
            "hacia otro frame (discriminación, burla, reclamo, etc.)."
        )
        fila_global = metricas_df[metricas_df["nivel"] == "Global"]
        if not fila_global.empty:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Total comentarios", int(fila_global["total"].iloc[0]))
            with c2:
                st.metric("Crimen (frame esperado)", int(fila_global["crimen"].iloc[0]))
            with c3:
                st.metric("Reframing", int(fila_global["reframing"].iloc[0]))
            with c4:
                st.metric("Índice de reframing", f"{fila_global['indice_reframing_pct'].iloc[0]}%")
        st.dataframe(metricas_df, use_container_width=True)

    archivos = {
        "metricas_reframing.csv": metricas_df,
        "comentarios_completo.csv": dataset_df,
        "resumen_categorias.csv": resumen_df,
        "reframing_por_post.csv": por_post_df,
        "fronterizos.csv": fronterizos_df,
        "residuales.csv": residuales_df,
        "prototipicos.csv": prototipicos_df,
    }

    st.markdown("---")
    st.subheader("⬇️ Descargar todo")
    col_zip, col_excel = st.columns(2)

    with col_zip:
        try:
            zip_buf = empaquetar_zip(archivos)
            st.download_button(
                "📦 Descargar TODO (ZIP con los CSVs)",
                data=zip_buf,
                file_name="resultados_analisis.zip",
                mime="application/zip",
                use_container_width=True,
                key="dl_zip_todo",
            )
        except Exception as e:
            st.error(f"Error armando ZIP: {e}")

    with col_excel:
        try:
            excel_buf = construir_excel(archivos)
            st.download_button(
                "📗 Descargar TODO (Excel consolidado)",
                data=excel_buf,
                file_name="resultados_analisis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_excel_todo",
            )
        except Exception as e:
            st.error(f"Error armando Excel: {e}")

    st.markdown("---")
    st.subheader("⬇️ Descargas individuales")
    columnas = st.columns(3)
    for i, (nombre, df) in enumerate(archivos.items()):
        if df is None or df.empty:
            continue
        with columnas[i % 3]:
            try:
                csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    f"⬇️ {nombre}",
                    data=csv_bytes,
                    file_name=nombre,
                    mime="text/csv",
                    use_container_width=True,
                    key=f"dl_{nombre}",
                )
            except Exception as e:
                st.error(f"Error en {nombre}: {e}")

# -----------------------------------------------------------
# Panel de revisión manual con emojis
# -----------------------------------------------------------
def revisar_comentarios_emojis(platform_data):
    st.subheader("🤔 Panel de Control: Comentarios con Emojis y Ambigüedad")
    st.markdown("Los emojis suelen ocultar ironía, burla o doble sentido. Acá podés clasificarlos manualmente.")

    df_list = []
    for platform, pdata in platform_data.items():
        df_p = pdata.get("comments_df", pd.DataFrame())
        if not df_p.empty:
            df_p = df_p.copy()
            df_p["platform"] = platform
            df_list.append(df_p)

    if not df_list:
        st.info("No hay datos cargados todavía.")
        return

    df_global = pd.concat(df_list, ignore_index=True)
    df_emojis = df_global[df_global["comment"].astype(str).str.contains(EMOJI_PATTERN)]

    if df_emojis.empty:
        st.info("No se detectaron comentarios con emojis en el corpus actual.")
        return

    st.write(f"Se encontraron **{len(df_emojis)} comentarios** que contienen emojis. Revisalos y asígnales el Frame correcto:")

    frames_dict = {
        0: "0 = Crimen",
        1: "1 = Discriminación",
        2: "2 = Burla",
        3: "3 = Reclamo",
        4: "4 = Sospecha IA",
        5: "5 = Otra categoría",
        6: "6 = Multimodal/Residual",
    }
    opciones_lista = list(frames_dict.values())
    keys_list = list(frames_dict.keys())

    if 'manual_emoji_labels' not in st.session_state:
        st.session_state.manual_emoji_labels = {}

    for idx, row in df_emojis.head(30).iterrows():
        comentario = row["comment"]
        plat = row["platform"].capitalize()
        frame_actual = row["frame_label"]
        id_com = row.get("id", "")

        key_sel = f"emoji_frame_{idx}"
        default_idx = keys_list.index(frame_actual) if frame_actual in keys_list else 5

        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.markdown(f"**[{plat}]** `{id_com}` {comentario}")
        with col_b:
            seleccion = st.selectbox(
                label=f"Frame #{idx}",
                options=opciones_lista,
                index=default_idx,
                key=key_sel,
                label_visibility="collapsed"
            )
            num_frame = int(seleccion.split(" = ")[0])
            st.session_state.manual_emoji_labels[idx] = num_frame

    if len(df_emojis) > 30:
        st.caption("*(Mostrando los primeros 30 comentarios con emojis para agilizar la interfaz).*")

    st.success("Tus selecciones manuales quedan guardadas en la sesión para el análisis cualitativo.")

# -----------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------
def main():
    st.title("📊 Análisis Crítico del Discurso - Reframing.1")
    st.markdown("---")

    if 'platform_data' not in st.session_state: st.session_state.platform_data = {}

    st.header("📥 Cargar Archivos")
    cols = st.columns(3)
    uploaded = {}
    with cols[0]:
        st.markdown("<h2 style='margin-bottom:-10px;'>📘 Facebook</h2>", unsafe_allow_html=True)
        fb_file = st.file_uploader(label="Subir archivo FB", type=['txt', 'csv', 'xlsx', 'xls'], key="upload_fb")
        if fb_file: uploaded['facebook'] = fb_file
    with cols[1]:
        st.markdown("<h2 style='margin-bottom:-10px;'>📸 Instagram</h2>", unsafe_allow_html=True)
        ig_file = st.file_uploader(label="Subir archivo IG", type=['txt', 'csv', 'xlsx', 'xls'], key="upload_ig")
        if ig_file: uploaded['instagram'] = ig_file
    with cols[2]:
        st.markdown("<h2 style='margin-bottom:-10px;'>𝕏 (X-Twitter)</h2>", unsafe_allow_html=True)
        x_file = st.file_uploader(label="Subir archivo X", type=['txt', 'csv', 'xlsx', 'xls'], key="upload_x")
        if x_file: uploaded['x'] = x_file

    if st.button("🚀 Procesar archivos"):
        st.session_state.platform_data = {}
        if not uploaded:
            st.warning("No cargaste archivos. Subí al menos uno.")
        else:
            for platform, file in uploaded.items():
                with st.spinner(f"Analizando {platform}..."):
                    texto_combinado, comentarios_list, ids_list = procesar_archivo(file)
                    if not comentarios_list:
                        st.warning(f"No se detectaron comentarios en {platform}.")
                        continue

                    resultados, variantes, total_palabras = analizar_texto(texto_combinado)
                    clean_comments = [re.sub(r'@\w+\b', '', c).strip() for c in comentarios_list]

                    comments_df = pd.DataFrame({
                        'id': ids_list,
                        'comment': comentarios_list,
                        'clean_comment': clean_comments,
                    })
                    comments_df['frame_label'] = comments_df['clean_comment'].apply(detectar_frame)
                    comments_df['polarizacion'] = comments_df['clean_comment'].apply(detectar_polarizacion)
                    comments_df['estigma_act'] = comments_df['clean_comment'].apply(detectar_estigma_act)
                    comments_df['estigma_tipo'] = comments_df['clean_comment'].apply(detectar_estigma_tipo)
                    comments_df['tono'] = comments_df['clean_comment'].apply(detectar_tono)

                    st.session_state.platform_data[platform] = {
                        'resultados': resultados, 'variantes': variantes,
                        'total_palabras': total_palabras,
                        'variantes_detectadas': sum(len(v) for v in variantes.values()),
                        'comments_df': comments_df
                    }
                    st.success(f"✅ {platform.capitalize()} analizado ({len(comments_df)} comentarios).")

    st.markdown("---")

    if st.session_state.platform_data:
        st.header("🔎 Resultados y categorización")

        st.subheader("📊 Palabras más frecuentes (TOP 20)")
        fig_top20 = grafico_top20_discriminacion(st.session_state.platform_data)
        if fig_top20:
            st.pyplot(fig_top20)
        else:
            st.info("No hay suficientes datos para mostrar el Top20.")

        st.markdown("---")
        mostrar_top10_por_categoria(st.session_state.platform_data)

        st.markdown("---")
        categorizar_palabras_interactivo(st.session_state.platform_data)

        st.markdown("---")
        st.header("📈 Gráficos Comparativos y ACD")

        col1, col2 = st.columns([2,1])
        with col1:
            fig2 = grafico2_barras_agrupadas(st.session_state.platform_data)
            if fig2: st.plotly_chart(fig2, use_container_width=True)
            else: st.info("No hay datos para la comparativa por plataforma.")
        with col2:
            fig4 = grafico4_torta_frames(st.session_state.platform_data)
            if fig4: st.plotly_chart(fig4, use_container_width=True)

        st.markdown("---")
        st.header("🕸️ Red Semántica (¿Qué palabras se asocian entre sí?)")
        st.write("Exploración Inductiva: Conexiones entre las 30 palabras más frecuentes en todo el corpus.")
        fig6 = grafico6_red_coocurrencia(st.session_state.platform_data, top_n=20, umbral=2)
        if fig6:
            st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("No hay asociaciones fuertes para armar la red. Cargá más datos.")

        st.markdown("---")
        revisar_comentarios_emojis(st.session_state.platform_data)

        st.markdown("---")
        export_results(st.session_state.platform_data)

    st.info("""
        📌 Instrucciones:
        1) Subí archivos (TXT/CSV/XLSX) en las columnas de arriba.
        2) Clic en 'Procesar archivos'.
        3) Analizá las redes y los gráficos generados.
        4) Descargá resultados en 'Exportar Resultados'.
        """)

if __name__ == "__main__":
    main()
