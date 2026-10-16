# -*- coding: utf-8 -*-
"""
deteccion.py
"""
import re
from collections import Counter
from difflib import SequenceMatcher
import unicodedata

LEET_MAP = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "@": "a", "$": "s", "+": "t",
}

def normalizar_caracteres(texto):
    """
    Normalización base, SIN agregar espacios de margen: minúsculas, sin
    tildes, sustitución leetspeak, reducción de letras repetidas.
    Se usa tanto para el texto del comentario como para las palabras de
    los diccionarios, para no duplicar espacios ya presentes en estos
    últimos (ej: la entrada " ia " no debe volver a padearse).
    """
    if not texto:
        return ""
    texto = texto.lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in nfkd if not unicodedata.combining(c))
    texto = "".join(LEET_MAP.get(c, c) for c in texto)
    texto = re.sub(r"(.)\1{2,}", r"\1\1", texto)
    # Reemplaza cualquier signo de puntuación, número suelto o emoji por un
    # espacio (no lo borra, lo reemplaza) para que la puntuación pegada a
    # una palabra ("es IA?") no le coma el espacio de límite de palabra.
    texto = re.sub(r"[^a-z\s]", " ", texto)
    texto = re.sub(r" {2,}", " ", texto)
    return texto

def normalizar_texto(texto):
    """
    Normaliza el TEXTO DEL COMENTARIO antes de buscar coincidencias:
    aplica normalizar_caracteres() y además agrega un margen de espacio
    al inicio/fin, para que los diccionarios puedan usar entradas tipo
    " ia " (palabra suelta con límite de palabra) sin necesidad de
    variantes redundantes según la posición en la oración.

    IMPORTANTE: las palabras de los diccionarios se normalizan con
    normalizar_lista() (que usa normalizar_caracteres, SIN padding
    adicional), no con esta función.
    """
    return f" {normalizar_caracteres(texto)} "

def normalizar_lista(lista):
    """
    Aplica normalizar_caracteres() (SIN padding) a cada término de una
    lista de palabras/frases de diccionario. Si una entrada ya incluye
    espacios propios (ej: " ia ", para marcar límite de palabra), esos
    espacios se preservan tal cual, sin duplicarse.
    """
    return [normalizar_caracteres(p) for p in lista]


diccionario_discriminacion = [
    "boliviana", "bolivianos", "boliviano", "bolita", "boliguayo",
    # Términos codificados culturalmente: en el contexto argentino (AMBA)
    # funcionan como eufemismo/proxy de "boliviano"/"peruano", aludiendo
    # a oficios asociados estereotipadamente a esas comunidades migrantes.
    "verdulero", "verdulera", "verduleros",
    "chileno", "chilena", "chilenos",
    "colombiano", "colombiana", "colombianos",
    "coya", "coyas", "ecuatoriano", "ecuatoriana", "ecuatorianos",
    "extranjero", "extranjeros", "inmigrante", "inmigrantes",
    "paraguayo", "paraguaya", "paraguayos", "peruana", "peruanas", "peruano", "peruanos",
    "veneca", "veneco", "venezolano", "venezolana", "venezolanos",
    "amerindio", "fenotipo", "fisonomía", "indio", "india",
    "indigena", "marrón", "morocha", "morocho", "negra", "negro",
    "negrito", "pinta", "rasgos", "raza", "raza inferior",
    "groncha", "groncho", "gronchos", "marginal", "marginales",
    "planero", "planera", "planeros", "villero", "villera", "villeros",
]
# Nota: se quitaron de acá "nosotros", "ellos", "ustedes", "esta/esa gente",
# "los de aca/alla", "los otros", "los mismos de siempre", "todos iguales",
# porque son pronombres y frases genéricas que aparecen en comentarios de
# cualquier tema (alto riesgo de falso positivo para Frame=Discriminación).
# Ese contenido ya está correctamente ubicado en POLARIZACION_EXPLICITA /
# POLARIZACION_IMPLICITA, que es la variable que realmente mide ese fenómeno.

diccionario_burla = [
    "ajaj", "bobo", "cabeza de termo", "cara de", "cara de boludo", "coqueta",
    "cara de gil", "feo", "fea", "gordo", "gorda", "gordito", "hongo", "honguito", "idiota", "jaj", "jaja", "jajaj", "milo",
    "mongol", "monguito", "payaso", "pelotudo", "pelotudito","pocoyo", "ridículo", "ridicula", "teletubi", "tonto", "thiago","tiago", "pzk",
    "peluquero", "peluquera", "peluqueros",  # mofa por el corte de pelo del sospechoso, no eufemismo étnico (confirmado en corpus real)
]

diccionario_reclamo = [
    "denuncia", "impunidad", "inoperancia", "investigación",
    "investigacion", "justicia", "legalidad", "corrupcion",
    "corrupción", "estado", "gobierno", "ministro", "ministra",
    "policia", "policía", "politica", "política", "políticos",
    "politicos", "bullrich", " k ", "kaka", "kukas",
    "kirchnerismo", "kirchnerista", "macrismo", "mileistas",
    "mileista", "peronismo", "peronista", "peronchos",
    "narcotrafico", "narcotráfico", "narcoestado",
    "sicario", "sicarios", "zona liberada", "perejil", "perejiles",
    "peces gordos", "pez gordo", "chivo expiatorio"
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
    "negro", "negrito", "marrón", "marronazo", "morocho", "indio", "amerindio", 
    "fenotipo", "rasgos", "cara de", "fisonomía", "pinta"
]

diccionario_estigma_tipo_3 = [
    "villero", "villera", "villeros", "planero", "planera",
    "planeros", "vago", "marginal", "cabeza de termo"
]

diccionario_imagen_ia = [
    # Mención explícita de IA como palabra suelta (una sola entrada:
    # el margen de espacio que agrega normalizar_texto ya la detecta
    # en cualquier posición del comentario, sin necesidad de variantes
    # redundantes tipo "es ia"/"con ia" que inflarían el puntaje)
    " ia ", "inteligencia artificial",
    # Variantes de "editada/photoshop/deepfake"
    "esta editada", "la editaron", "foto editada", "foto retocada",
    "le retocaron", "photoshop", "con photoshop", "deepfake", "fake",
    # Slang de "falso" en Argentina
    "foto trucha", "es trucha", "truchada", "esta truchada",
    "no es real esa foto", "foto armada", "cara armada",
    # Cuestionamiento de autenticidad sin nombrar la técnica
    "esa no es su cara", "le cambiaron la cara", "no es la foto real",
    "sacaron una foto vieja", "esa foto no es de el", "esa foto no es de él",
    "no se parece en nada",
]

DICT_FRAMES = {
    "crimen": diccionario_crimen,
    "discriminacion": diccionario_discriminacion,
    "burla": diccionario_burla,
    "reclamo": diccionario_reclamo,
    "imagen_ia": diccionario_imagen_ia,
}

POLARIZACION_EXPLICITA = [
    "nosotros", "ellos", "ustedes", "los de afuera", "los de aca","escoria","mierdas",
    "los de acá", "los otros", "kukas", "los k", "libertarios",  "lacras", "mugre",
    "mileistas", "los de la patria grande"
]
POLARIZACION_IMPLICITA = [
    "esa gente", "esta gente", "esa clase de gente", "esta clase de gente",
    "todos iguales", "siempre igual", "los mismos de siempre", "no juzgo","no discrimino",
    "los morochos", "los extranjeros", "los de esa zona", "los de la villa"
]

# -----------------------------------------------------------
# Versiones normalizadas de los diccionarios (Tipo 1 de camuflaje)
# Se usan dentro de los detectores en vez de las listas originales,
# para que "n3gr0", "fisonomia" (sin tilde), "esooo" (repetido), etc.
# también sean detectados. Las listas originales (arriba) se conservan
# intactas para referencia y para el Apéndice de la tesis.
# -----------------------------------------------------------
DICT_FRAMES_NORM = {
    categoria: normalizar_lista(lista) for categoria, lista in DICT_FRAMES.items()
}
POLARIZACION_EXPLICITA_NORM = normalizar_lista(POLARIZACION_EXPLICITA)
POLARIZACION_IMPLICITA_NORM = normalizar_lista(POLARIZACION_IMPLICITA)
ESTIGMA_TIPO_1_NORM = normalizar_lista(diccionario_estigma_tipo_1)
ESTIGMA_TIPO_2_NORM = normalizar_lista(diccionario_estigma_tipo_2)
ESTIGMA_TIPO_3_NORM = normalizar_lista(diccionario_estigma_tipo_3)

# -----------------------------------------------------------
# Análisis léxico (tokens, variantes, conteo)
# -----------------------------------------------------------
def cargar_palabras_vacias():
    return {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'lo', 'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde',
        'durante', 'en', 'entre', 'hacia', 'hasta', 'mediante', 'para','por', 'según', 'sin', 'so', 'sobre', 'tras',
        'y', 'e', 'ni', 'que', 'pero', 'mas', 'aunque', 'sino', 'o', 'u', 'ora', 'bien', 'ya', 'sea', 'cuando', 'como', 'donde',
        'yo', 'tu', 'tú', 'él', 'ella', 'ello', 'nosotros', 'vosotros', 'ellos', 'ellas', 'me', 'te', 'se', 'nos', 'os', 'le', 'les',
        'mi', 'tu', 'su', 'nuestro', 'vuestro', 'su', 'mío', 'tuyo', 'muy', 'mucho', 'poco', 'bastante', 'demasiado', 'más', 'menos',
        'algo', 'nada', 'todo', 'siempre', 'nunca', 'jamás', 'también', 'tampoco', 'ahora', 'antes', 'después', 'luego', 'ayer', 'hoy',
        'mañana', 'si', 'no', 'tal', 'vez', 'quizás', 'acaso', 'así', 'bien', 'mal', 'mejor', 'peor', 'cerca', 'lejos', 'aquí', 'ahí',
        'allí', 'allá', 'acá', 'dentro', 'fuera', 'encima', 'debajo', 'es', 'son', 'era', 'eran', 'ser', 'estar', 'está', 'están',
        'tiene', 'tienen', 'tenía', 'tenían', 'haber', 'ha', 'han', 'había', 'habían', 'puede', 'pueden', 'podía', 'podían',
        'debe', 'deben', 'debía', 'debían', 'quiere', 'quieren', 'al', 'del','este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'aquel', 'aquella', 'aquellos', 'aquellas', 'otro', 'otra', 'otros', 'otras', 'mismo', 'misma', 'mismos', 'mismas',
        'entonces', 'pues', 'así', 'además', 'también', 'incluso', 'hasta', 'inclusive', 'aparte', 'mientras', 'aunque', 'sin',
        'embargo', 'no', 'obstante', 'porque', 'puesto', 'que', 'pues', 'entonces', 'finalmente', 'últimamente', 'bueno', 'vale', 'ok', 'hola', 'adiós', 'gracias', 'por favor',
        'claro', 'exacto', 'obvio', 'realmente', 'actualmente', 'van', 'fue', 'hacer', 'esto', 'tan', 'hizo', 'hacen', 'estar', 'alguna', 'eso', 'este',
        'hay', 'años', 'qué', 'solo', 'dios', 'sabe', 'hace', 'sus', 'https', 'comentarios', 'seguro', 'vamos', 'gente', 'diciendovos',
        'quien', 'todos', 'todas', 'creo', 'pais', 'país'
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
    texto = normalizar_texto(texto)
    scores = {"crimen": 0, "discriminacion": 0, "burla": 0, "reclamo": 0, "imagen_ia": 0}
    for categoria, palabras in DICT_FRAMES_NORM.items():
        for p in palabras:
            if p in texto:
                scores[categoria] += 1
    if max(scores.values()) == 0:
        return 0
    ganador = max(scores, key=scores.get)
    mapping = {"crimen": 1, "discriminacion": 2, "burla": 3, "reclamo": 4, "imagen_ia": 5}
    return mapping[ganador]

def detectar_polarizacion(texto):
    texto = normalizar_texto(texto)
    for exp in POLARIZACION_EXPLICITA_NORM:
        if exp in texto:
            return 2
    for imp in POLARIZACION_IMPLICITA_NORM:
        if imp in texto:
            return 1
    return 0

ESTIGMA_TRIBAL_NORM = set(ESTIGMA_TIPO_1_NORM + ESTIGMA_TIPO_2_NORM + ESTIGMA_TIPO_3_NORM)
def detectar_estigma_act(texto):
    """0 = No se detecta estigma tribal | 1 = Sí se detecta (según libro de códigos 4.3.1)"""
    texto = normalizar_texto(texto)
    for p in ESTIGMA_TRIBAL_NORM:
        if p in texto:
            return 1
    return 0

def detectar_estigma_tipo(texto):
    texto = normalizar_texto(texto)
    for p in ESTIGMA_TIPO_1_NORM:
        if p in texto:
            return 1
    for p in ESTIGMA_TIPO_2_NORM:
        if p in texto:
            return 2
    for p in ESTIGMA_TIPO_3_NORM:
        if p in texto:
            return 3
    return 0

TONO_CRITICO = ["que desastre", "que vergüenza", "vergonzoso", "como puede ser", "falta de justicia", "no deberia", "no debería"]
TONO_HOSTIL = ["pelotudo", "idiota", "rata", "basura", "asqueroso", "mierda", "hdp", "forro", "deportarlos", "que se muera", "que se pudra"]
TONO_SARCASMO = ["jaj", "jaja", "jajaj", "ajaj", "sí claro", "si claro", "dale genio", "ok campeón", "ok campeon"]
TONO_CRITICO_NORM = normalizar_lista(TONO_CRITICO)
TONO_HOSTIL_NORM = normalizar_lista(TONO_HOSTIL)
TONO_SARCASMO_NORM = normalizar_lista(TONO_SARCASMO)
def detectar_tono(texto):
    """
    0 = Sin marca de tono detectada (neutral / no clasificado)
    1 = Crítico | 2 = Hostil | 3 = Sarcástico

    Orden de prioridad ante ambigüedad: Hostil antes que Sarcástico,
    según criterio de desempate definido en 4.3.2 (se prioriza la
    categoría más explícita cuando un comentario activa más de una).
    """
    texto = normalizar_texto(texto)
    for p in TONO_HOSTIL_NORM:
        if p in texto:
            return 2
    for p in TONO_SARCASMO_NORM:
        if p in texto:
            return 3
    for p in TONO_CRITICO_NORM:
        if p in texto:
            return 1
    return 0
