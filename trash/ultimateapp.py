# app.py - Versión actualizada 17NOB
import streamlit as st
import pandas as pd
import re
from collections import Counter
import os
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
        'https' , 'comentarios',  'seguro', 'vamos', 'gente', 'diciendovos', 'quien', 'todos',
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
# Procesamiento de archivos ->  texto combinado + lista de comentarios
# -----------------------------------------------------------

def procesar_archivo(file):
    """
    Devuelve: (texto_combinado, lista_comentarios)
    Mantiene compatibilidad con la versión anterior pero permite análisis por comentario.
    """
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            return procesar_excel_completo(file)
        elif file.name.endswith('.csv'):
            df = pd.read_csv(file)
            return procesar_dataframe_comments(df, file.name)
        elif file.name.endswith('.txt'):
            text = file.getvalue().decode('utf-8')
            # Para txt devolvemos todo como un único bloque y una lista con comentarios
            comentarios = [line.strip() for line in text.splitlines() if len(line.strip()) > 10]
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
    hojas_procesadas = 0
    try:
        excel_file = pd.ExcelFile(file)
        hojas = excel_file.sheet_names
        st.info(f"📑 Archivo {file.name}: {len(hojas)} hojas detectadas")
        for hoja in hojas:
            try:
                df = pd.read_excel(file, sheet_name=hoja)
                texto_hoja, comentarios = procesar_dataframe_comments(df, f"{file.name} - Hoja: {hoja}")
                if texto_hoja.strip():
                    textos_combinados.append(texto_hoja)
                    comentarios_list.extend(comentarios)
                    hojas_procesadas += 1
            except Exception as e:
                st.warning(f"⚠️ Error procesando hoja '{hoja}': {e}")
                continue
        if hojas_procesadas > 0:
            st.success(f"✅ {hojas_procesadas}/{len(hojas)} hojas procesadas exitosamente")
        else:
            st.error(f"❌ No se pudo procesar ninguna hoja del archivo {file.name}")
    except Exception as e:
        st.error(f"❌ Error leyendo el archivo Excel {file.name}: {e}")
    return ' '.join(textos_combinados), comentarios_list

def procesar_dataframe_comments(df, nombre_archivo):
    textos_combinados = []
    comentarios_list = []
    columnas_comentarios = []
    posibles_nombres = ['Comment', 'comment', 'comments', 'Comentario', 'comentario', 'Texto', 'texto']
    for nombre in posibles_nombres:
        if nombre in df.columns:
            columnas_comentarios.append(nombre)
            break
    if not columnas_comentarios:
        for columna in df.columns:
            if df[columna].dtype == 'object':
                muestra = df[columna].dropna().head(10)
                if any(isinstance(x, str) and len(x.strip()) > 20 for x in muestra):
                    columnas_comentarios.append(columna)
                    break
    if columnas_comentarios:
        for columna in columnas_comentarios:
            try:
                textos = df[columna].dropna().astype(str)
                textos_largos = [t for t in textos if len(t.strip()) > 10]
                textos_combinados.extend(textos_largos)
                comentarios_list.extend(textos_largos)
                if len(textos_largos) > 0:
                    st.success(f"✅ {nombre_archivo} - Columna '{columna}': {len(textos_largos)} comentarios")
                else:
                    st.warning(f"⚠️ {nombre_archivo} - Columna '{columna}': Sin comentarios")
            except Exception as e:
                st.warning(f"⚠️ Error procesando columna '{columna}' en {nombre_archivo}: {e}")
    else:
        st.warning(f"⚠️ {nombre_archivo}: No se encontró columna 'Comment'")
    return ' '.join(textos_combinados), comentarios_list

# -----------------------------------------------------------
# Análisis léxico 
# -----------------------------------------------------------

def analizar_texto(texto_completo):
    palabras_vacias = cargar_palabras_vacias()
    texto_sin_menciones = re.sub(r'@\w+\b', '', texto_completo)
    palabras = re.findall(r'\b[a-zA-Záéíóúñü]+\b', texto_sin_menciones.lower())
    palabras_filtradas = [
        palabra for palabra in palabras 
        if (palabra not in palabras_vacias and len(palabra) > 2)
    ]
    contador_inicial = Counter(palabras_filtradas)
    palabras_frecuentes = [palabra for palabra, freq in contador_inicial.most_common(200) if freq > 1]
    variantes = encontrar_variantes_automatico(palabras_frecuentes)
    conteo_final = {}
    palabras_procesadas = set()
    for palabra, frecuencia in contador_inicial.most_common():
        if palabra in palabras_procesadas:
            continue
        encontrada = False
        for principal, vars_list in variantes.items():
            if palabra == principal or palabra in vars_list:
                if principal not in conteo_final:
                    conteo_final[principal] = {'total': 0, 'variantes': {}}
                conteo_final[principal]['total'] += frecuencia
                if palabra != principal:
                    conteo_final[principal]['variantes'][palabra] = frecuencia
                palabras_procesadas.add(palabra)
                encontrada = True
                break
        if not encontrada:
            conteo_final[palabra] = {'total': frecuencia, 'variantes': {}}
            palabras_procesadas.add(palabra)
    return conteo_final, variantes, len(palabras_filtradas)


# Funciones dedicadas al analisis por comentario
# -----------------------------------------------------------

# Diccionario de frames 
DICT_FRAMES = {
    "crimen": [
        "narco", "delincuente", "delincuentes", "robo", "robó", "ladrón",
        "sospechoso", "asesino", "crimen", "banda", "fuga", "detenido"
    ],
    "discriminacion": [
        "peruano", "boliviano", "paraguayo", "extranjero", "negro",
        "marrón", "indio", "pueblo", "rasgos", "cara de", "fenotipo"
    ],
    "burla": [
        "pelotudo", "virgo", "gordito", "hongo", "teletubi", "tonto",
        "cara de tonto", "feo", "milo", "jaj", "jaja", "jajaj"
    ],
    "reclamo": [
        "justicia", "impunidad", "policia", "policía", "estado",
        "gobierno", "políticos", "politicos", "inoperancia",
        "corrupción", "corrupcion"
    ]
}

def detectar_frame(texto):
    texto = texto.lower()
    scores = {"crimen": 0, "discriminacion": 0, "burla": 0, "reclamo": 0}
    for categoria, palabras in DICT_FRAMES.items():
        for p in palabras:
            if p in texto:
                scores[categoria] += 1
    if max(scores.values()) == 0:
        return 0
    categoria_ganadora = max(scores, key=scores.get)
    mapping = {"crimen": 1, "discriminacion": 2, "burla": 3, "reclamo": 4}
    return mapping[categoria_ganadora]

# Polarización
POLARIZACION_EXPLICITA = [
    "nosotros", "ellos", "ustedes", "los de afuera", "los de aca", "los de acá",
    "los otros", "kukas", "los k", "libertarios", "mileistas", "los de la patria grande"
]
POLARIZACION_IMPLICITA = [
    "esa gente", "esta gente", "esa clase de gente", "esta clase de gente",
    "todos iguales", "siempre igual", "los mismos de siempre", "los que vienen",
    "los morochos", "los extranjeros", "los de esa zona", "los de la villa"
]
def detectar_polarizacion(texto):
    texto = texto.lower()
    for exp in POLARIZACION_EXPLICITA:
        if exp in texto:
            return 2
    for imp in POLARIZACION_IMPLICITA:
        if imp in texto:
            return 1
    return 0

# Estigma_act
ESTIGMA_TRIBAL = [
    "peruano", "boliviano", "paraguayo", "colombiano", "venezolano",
    "extranjero", "inmigrante", "morocho", "marrón", "negro", "indio",
    "amerindio", "etnia", "raza", "cara de", "rasgos", "fenotipo", "pinta", "fisonomía", "aspecto"
]
def detectar_estigma_act(texto):
    texto = texto.lower()
    for palabra in ESTIGMA_TRIBAL:
        if palabra in texto:
            return 1
    return 2

# Estigma_tipo
ESTIGMA_TIPO_1 = ["peruano", "boliviano", "paraguayo", "colombiano", "venezolano", "extranjero", "inmigrante", "sudaca"]
ESTIGMA_TIPO_2 = ["morocho", "marrón", "negro", "indio", "amerindio", "cara de", "rasgos", "fenotipo", "pinta", "fisonomía"]
ESTIGMA_TIPO_3 = ["villero", "villa", "planero", "vago", "marginal", "cabeza", "cabeza de termo", "negro de mierda", "pobre tipo"]
def detectar_estigma_tipo(texto):
    texto = texto.lower()
    for p in ESTIGMA_TIPO_1:
        if p in texto:
            return 1
    for p in ESTIGMA_TIPO_2:
        if p in texto:
            return 2
    for p in ESTIGMA_TIPO_3:
        if p in texto:
            return 3
    return 0

# Tono
TONO_CRITICO = ["que desastre", "que vergüenza", "vergonzoso", "cómo puede ser", "como puede ser", "falta de justicia", "no debería", "no deberia"]
TONO_HOSTIL = ["pelotudo", "idiota", "rata", "basura", "asqueroso", "mierda", "hdp", "forro", "deportarlos", "que se muera", "que se pudra", "latigazos", "ratas", "cerdos", "bestias"]
TONO_SARCASMO = ["jaj", "jaja", "jajaj", "ajaj", "sí claro", "si claro", "dale genio", "ok campeón", "ok campeon", "seguro que"]
def detectar_tono(texto):
    texto = texto.lower()
    for p in TONO_SARCASMO:
        if p in texto:
            return 3
    for p in TONO_HOSTIL:
        if p in texto:
            return 2
    for p in TONO_CRITICO:
        if p in texto:
            return 1
    return 1  # por defecto crítico

# -----------------------------------------------------------
# Funciones para graficar las variables basadas en comentarios
# -----------------------------------------------------------

def grafico_frames_from_comments(df_comments, platform_name):
    counts = df_comments['frame_label'].value_counts().sort_index()
    labels = {0: "Sin frame", 1: "Crimen", 2: "Discriminación", 3: "Burla", 4: "Reclamo"}
    x = [labels[i] for i in counts.index]
    y = counts.values
    fig = px.bar(x=x, y=y, title=f"Mecanismos comunicacionales - {platform_name}", labels={'x':'Frame', 'y':'Cantidad'})
    return fig

def grafico_polarizacion_from_comments(df_comments, platform_name):
    counts = df_comments['polarizacion'].value_counts().sort_index()
    labels = {0: "Ausente", 1: "Implícita", 2: "Explícita"}
    x = [labels[i] for i in counts.index]
    y = counts.values
    fig = px.bar(x=x, y=y, title=f"Polarización - {platform_name}", labels={'x':'Polarización', 'y':'Cantidad'})
    return fig

def grafico_estigma_act_from_comments(df_comments, platform_name):
    counts = df_comments['estigma_act'].value_counts().sort_index()
    labels = {1: "Sí (estigma)", 2: "No"}
    x = [labels[i] for i in counts.index]
    y = counts.values
    fig = px.pie(names=x, values=y, title=f"Estigma activo - {platform_name}")
    return fig

def grafico_estigma_tipo_from_comments(df_comments, platform_name):
    counts = df_comments['estigma_tipo'].value_counts().sort_index()
    labels = {0: "Ausente", 1: "Nacionalidad", 2: "Rasgos/color", 3: "Clase social"}
    x = [labels[i] for i in counts.index]
    y = counts.values
    fig = px.bar(x=x, y=y, title=f"Subtipos de Estigma - {platform_name}", labels={'x':'Subtipo','y':'Cantidad'})
    return fig

def grafico_tono_from_comments(df_comments, platform_name):
    counts = df_comments['tono'].value_counts().sort_index()
    labels = {1: "Crítico", 2: "Hostil", 3: "Sarcástico"}
    x = [labels[i] for i in counts.index]
    y = counts.values
    fig = px.bar(x=x, y=y, title=f"Tono del discurso - {platform_name}", labels={'x':'Tono','y':'Cantidad'})
    return fig

# -----------------------------------------------------------
# UI principal: almacena comments_df con etiquetas
# -----------------------------------------------------------

def display_top_words(platform_data):
    st.subheader("🔤 Top 20 Palabras por Plataforma")
    for platform, data in platform_data.items():
        with st.expander(f"{platform.capitalize()} - Top 20 palabras"):
            resultados = data.get('resultados', {})
            items_ordenados = sorted(resultados.items(), key=lambda x: x[1]['total'], reverse=True)[:20]
            for i, (palabra, datos) in enumerate(items_ordenados, 1):
                col1, col2 = st.columns([3, 1])
                with col1:
                    if datos['variantes']:
                        variantes_texto = ", ".join([f"{v}" for v in datos['variantes'].keys()])
                        st.markdown(f"**{i}. {palabra}** ({datos['total']})")
                        st.caption(f"🔄 Variantes: {variantes_texto}")
                    else:
                        st.markdown(f"**{i}. {palabra}** ({datos['total']})")
                with col2:
                    max_freq = items_ordenados[0][1]['total'] if items_ordenados else 1
                    st.progress(min(datos['total'] / max_freq, 1.0))

def categorizar_palabras_interactivo(platform_data):
    st.subheader("🏷️ Categorizar Palabras")
    if 'categorias_palabras' not in st.session_state:
        st.session_state.categorias_palabras = {}
    for platform, data in platform_data.items():
        with st.expander(f"📋 Categorizar palabras - {platform.capitalize()}"):
            st.write("**Selecciona la categoría para cada palabra:**")
            st.caption("🔹 **Racistas**: Palabras con contenido racial discriminatorio")
            st.caption("🔹 **Burlas**: Palabras que ridiculizan o se burlan")
            st.caption("🔹 **Reclamo político/de justicia**: Palabras relacionadas con demandas políticas o de justicia")
            resultados = data.get('resultados', {})
            top_words = sorted(resultados.items(), key=lambda x: x[1]['total'], reverse=True)[:20]
            platform_key = f"{platform}_categorias"
            if platform_key not in st.session_state.categorias_palabras:
                st.session_state.categorias_palabras[platform_key] = {}
            for palabra, datos in top_words:
                col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
                with col1:
                    st.write(f"**{palabra}** ({datos['total']})")
                with col2:
                    racista = st.checkbox("Racista", key=f"rac_{platform}_{palabra}",
                                          value=st.session_state.categorias_palabras[platform_key].get(palabra) == 'racista')
                    if racista:
                        st.session_state.categorias_palabras[platform_key][palabra] = 'racista'

                with col3:
                    burlas = st.checkbox("Burlas", key=f"bur_{platform}_{palabra}",
                                         value=st.session_state.categorias_palabras[platform_key].get(palabra) == 'burlas')
                    if burlas:
                        st.session_state.categorias_palabras[platform_key][palabra] = 'burlas'

                with col4:
                    reclamo = st.checkbox("Reclamo", key=f"rec_{platform}_{palabra}",
                          value=st.session_state.categorias_palabras[platform_key].get(palabra) == 'reclamo')
                    if reclamo:
                        st.session_state.categorias_palabras[platform_key][palabra] = 'reclamo'

                with col5:
                    crimen = st.checkbox("Crimen", key=f"cri_{platform}_{palabra}",
                                         value=st.session_state.categorias_palabras[platform_key].get(palabra) == 'crimen')
                    if crimen:
                        st.session_state.categorias_palabras[platform_key][palabra] = 'crimen'

                with col6:
                    if st.button("🗑️", key=f"clear_{platform}_{palabra}"):
                        if palabra in st.session_state.categorias_palabras[platform_key]:
                            del st.session_state.categorias_palabras[platform_key][palabra]
                        st.experimental_rerun()

def create_racist_words_chart(platform_data):
    try:
        if 'categorias_palabras' not in st.session_state:
            st.warning("Primero categoriza las palabras en la sección anterior")
            return None
        chart_data = []
        for platform, data in platform_data.items():
            platform_key = f"{platform}_categorias"
            categorias = st.session_state.categorias_palabras.get(platform_key, {})
            palabras_crimen = [palabra for palabra, categoria in categorias.items() if categoria == 'crimen']
            frecuencia_crimen = sum(data.get('resultados', {}).get(palabra, {}).get('total', 0) for palabra in palabras_crimen)
            palabras_racistas = [palabra for palabra, categoria in categorias.items() if categoria == 'racista']
            frecuencia_racistas = sum(data.get('resultados', {}).get(palabra, {}).get('total', 0) for palabra in palabras_racistas)
            palabras_burlas = [palabra for palabra, categoria in categorias.items() if categoria == 'burlas']
            frecuencia_burlas = sum(data.get('resultados', {}).get(palabra, {}).get('total', 0) for palabra in palabras_burlas)
            palabras_reclamo = [palabra for palabra, categoria in categorias.items() if categoria == 'reclamo']
            frecuencia_reclamo = sum(data.get('resultados', {}).get(palabra, {}).get('total', 0) for palabra in palabras_reclamo)
            chart_data.extend([
                {'Plataforma': platform.capitalize(), 'Categoría': 'Crimen', 'Frecuencia': frecuencia_crimen},
                {'Plataforma': platform.capitalize(), 'Categoría': 'Racistas', 'Frecuencia': frecuencia_racistas},
                {'Plataforma': platform.capitalize(), 'Categoría': 'Burlas', 'Frecuencia': frecuencia_burlas},
                {'Plataforma': platform.capitalize(), 'Categoría': 'Reclamo político', 'Frecuencia': frecuencia_reclamo}
            ])
        if not chart_data or all(item['Frecuencia'] == 0 for item in chart_data):
            st.info("💡 Categoriza algunas palabras como 'Racistas', 'Burlas' o 'Reclamo político' para ver el gráfico")
            return None
        df_chart = pd.DataFrame(chart_data)
        fig = px.bar(df_chart, x='Plataforma', y='Frecuencia', color='Categoría', barmode='group',
                     title="📊 Frecuencia de Palabras por Categoría y Plataforma")
        return fig
    except Exception as e:
        st.error(f"Error creando gráfico de categorías: {e}")
        return None

def create_category_pie_chart(platform_data):
    try:
        if 'categorias_palabras' not in st.session_state:
            return None
        categorias_totales = {'racista': 0, 'burlas': 0, 'reclamo': 0, 'sin_categoria': 0}
        for platform, data in platform_data.items():
            platform_key = f"{platform}_categorias"
            categorias = st.session_state.categorias_palabras.get(platform_key, {})
            for categoria in ['racista', 'burlas', 'reclamo']:
                palabras_categoria = [palabra for palabra, cat in categorias.items() if cat == categoria]
                frecuencia = sum(data.get('resultados', {}).get(palabra, {}).get('total', 0) for palabra in palabras_categoria)
                categorias_totales[categoria] += frecuencia
            top_words = sorted(data.get('resultados', {}).items(), key=lambda x: x[1]['total'], reverse=True)[:20]
            for palabra, datos in top_words:
                if palabra not in categorias:
                    categorias_totales['sin_categoria'] += datos['total']
        labels = ['Racistas', 'Burlas', 'Reclamo político', 'Sin categoría']
        values = [categorias_totales['racista'], categorias_totales['burlas'], categorias_totales['reclamo'], categorias_totales['sin_categoria']]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#95A5A6']
        if sum(values) == 0:
            return None
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3, marker_colors=colors)])
        fig.update_layout(title_text="📈 Distribución de Palabras por Categoría (Todas las Plataformas)", showlegend=True)
        return fig
    except Exception as e:
        st.error(f"Error creando gráfico de torta: {e}")
        return None

def create_comparison_chart(platform_data):
    try:
        chart_data = []
        for platform, data in platform_data.items():
            resultados = data.get('resultados', {})
            top_words = sorted(resultados.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
            for palabra, datos in top_words:
                chart_data.append({'Plataforma': platform.capitalize(), 'Palabra': palabra, 'Frecuencia': datos['total']})
        if not chart_data:
            return None
        df_chart = pd.DataFrame(chart_data)
        fig = px.bar(df_chart, x='Palabra', y='Frecuencia', color='Plataforma', barmode='group', title="Comparación de Palabras Más Frecuentes por Plataforma")
        fig.update_layout(xaxis_tickangle=-45)
        return fig
    except Exception as e:
        st.error(f"Error creando gráfico: {e}")
        return None

def create_metrics_chart(platform_data):
    metrics_data = []
    for platform, data in platform_data.items():
        metrics_data.append({'Plataforma': platform.capitalize(), 'Palabras Totales': data.get('total_palabras', 0), 'Palabras Únicas': len(data.get('resultados', {})), 'Variantes Detectadas': data.get('variantes_detectadas', 0)})
    if metrics_data:
        df_metrics = pd.DataFrame(metrics_data)
        fig = px.bar(df_metrics, x='Plataforma', y=['Palabras Totales', 'Palabras Únicas'], title="Métricas de Análisis por Plataforma", barmode='group')
        return fig
    return None

def display_extended_analysis(platform_data):
    st.subheader("📋 Análisis Extendido")
    for platform, data in platform_data.items():
        with st.expander(f"📊 Análisis Detallado - {platform.capitalize()}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Palabras Analizadas", f"{data.get('total_palabras', 0):,}")
            with col2:
                st.metric("Palabras Únicas", len(data.get('resultados', {})))
            with col3:
                st.metric("Variantes Detectadas", data.get('variantes_detectadas', 0))
            variantes = data.get('variantes', {})
            if variantes:
                st.write("**🔄 Variantes Detectadas:**")
                for principal, vars_list in variantes.items():
                    if vars_list:
                        st.write(f"• **{principal}**: {', '.join(vars_list)}")
            # Mostrar resumen de etiquetas por comentario (si existe)
            comments_df = data.get('comments_df')
            if comments_df is not None:
                st.write("**🔎 Muestra de Comentarios con Etiquetas ACD**")
                st.dataframe(comments_df.head(10))

# -----------------------------------------------------------
# Main UI + integración de la analítica por comentario
# -----------------------------------------------------------

def main():
    st.title("📊 Análisis del Discurso - Redes Sociales (Solo Python + ACD)")
    st.markdown("---")
    if 'platform_data' not in st.session_state:
        st.session_state.platform_data = {}

    st.header("📥 Cargar Archivos de Comentarios")
    cols = st.columns(3)
    uploaded_files = {}
    for i, platform in enumerate(SUPPORTED_PLATFORMS[:3]):
        with cols[i]:
            st.subheader(f"{platform.capitalize()}")
            uploaded_file = st.file_uploader(f"Subir archivo {platform}", type=['txt', 'csv', 'xlsx', 'xls'], key=f"upload_{platform}")
            if uploaded_file:
                file_size = len(uploaded_file.getvalue()) / 1024
                if file_size <= MAX_FILE_SIZE:
                    uploaded_files[platform] = uploaded_file
                    st.success(f"✅ Archivo listo ({file_size:.1f} KB)")
                else:
                    st.error(f"❌ Archivo muy grande ({file_size:.1f} KB > {MAX_FILE_SIZE} KB)")

    if uploaded_files:
        st.markdown("---")
        st.header("🔍 Análisis Individual por Plataforma")
        analysis_cols = st.columns(len(uploaded_files))
        for i, (platform, file) in enumerate(uploaded_files.items()):
            with analysis_cols[i]:
                if st.button(f"Analizar {platform.capitalize()}", key=f"btn_{platform}"):
                    with st.spinner(f"Analizando {platform}..."):
                        try:
                            texto_combinado, comentarios_list = procesar_archivo(file)
                            if texto_combinado and len(texto_combinado.strip()) > 50:
                                resultados, variantes, total_palabras = analizar_texto(texto_combinado)
                                # --- Integración del análisis por comentario ---
                                # Limpiar comentarios y crear dataframe
                                clean_comments = []
                                for c in comentarios_list:
                                    # limpieza léxica básica: quitar menciones y espacios - reusa el proceso
                                    c_clean = re.sub(r'@\w+\b', '', c).strip()
                                    clean_comments.append(c_clean)
                                comments_df = pd.DataFrame({'comment': comentarios_list, 'clean_comment': clean_comments})
                                # Aplicar detecciones ACD por comentario
                                comments_df['frame_label'] = comments_df['clean_comment'].apply(detectar_frame)
                                comments_df['polarizacion'] = comments_df['clean_comment'].apply(detectar_polarizacion)
                                comments_df['estigma_act'] = comments_df['clean_comment'].apply(detectar_estigma_act)
                                comments_df['estigma_tipo'] = comments_df['clean_comment'].apply(detectar_estigma_tipo)
                                comments_df['tono'] = comments_df['clean_comment'].apply(detectar_tono)
                                # Guardar todo en session_state para usar luego
                                st.session_state.platform_data[platform] = {
                                    'resultados': resultados,
                                    'variantes': variantes,
                                    'total_palabras': total_palabras,
                                    'variantes_detectadas': sum(len(v) for v in variantes.values()),
                                    'comments_df': comments_df
                                }
                                st.success(f"✅ {platform.capitalize()} analizado! ({total_palabras} palabras procesadas, {len(comments_df)} comentarios etiquetados)")
                            else:
                                st.error(f"❌ Texto insuficiente en {platform}")
                        except Exception as e:
                            st.error(f"❌ Error analizando {platform}: {str(e)}")

    if st.session_state.platform_data:
        st.markdown("---")
        st.header("📊 Resultados del Análisis")
        display_top_words(st.session_state.platform_data)
        st.markdown("---")
        categorizar_palabras_interactivo(st.session_state.platform_data)
        st.markdown("---")
        st.header("📈 Gráficos Comparativos")
        col1, col2 = st.columns(2)
        with col1:
            comparison_chart = create_comparison_chart(st.session_state.platform_data)
            if comparison_chart:
                st.plotly_chart(comparison_chart, use_container_width=True)
        with col2:
            metrics_chart = create_metrics_chart(st.session_state.platform_data)
            if metrics_chart:
                st.plotly_chart(metrics_chart, use_container_width=True)
        st.markdown("---")
        st.header("🎯 Análisis por Categorías (Léxico y ACD por Comentario)")
        col1, col2 = st.columns(2)
        with col1:
            racist_chart = create_racist_words_chart(st.session_state.platform_data)
            if racist_chart:
                st.plotly_chart(racist_chart, use_container_width=True)
            else:
                st.info("💡 Categoriza palabras para ver el análisis por categorías")
        with col2:
            pie_chart = create_category_pie_chart(st.session_state.platform_data)
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True)
        # Mostrar gráficos por plataforma basados en comentarios (ACD)
        st.markdown("---")
        st.header("🧭 Resultados ACD por Plataforma (por comentario)")
        for platform, data in st.session_state.platform_data.items():
            st.subheader(f"🔎 {platform.capitalize()}")
            comments_df = data.get('comments_df')
            if comments_df is not None and not comments_df.empty:
                cols = st.columns(3)
                with cols[0]:
                    fig_f = grafico_frames_from_comments(comments_df, platform.capitalize())
                    st.plotly_chart(fig_f, use_container_width=True)
                with cols[1]:
                    fig_p = grafico_polarizacion_from_comments(comments_df, platform.capitalize())
                    st.plotly_chart(fig_p, use_container_width=True)
                with cols[2]:
                    fig_e = grafico_estigma_act_from_comments(comments_df, platform.capitalize())
                    st.plotly_chart(fig_e, use_container_width=True)
                # Segunda fila
                cols2 = st.columns(2)
                with cols2[0]:
                    fig_et = grafico_estigma_tipo_from_comments(comments_df, platform.capitalize())
                    st.plotly_chart(fig_et, use_container_width=True)
                with cols2[1]:
                    fig_t = grafico_tono_from_comments(comments_df, platform.capitalize())
                    st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.info("No hay comentarios procesados para esta plataforma.")
        st.markdown("---")
        display_extended_analysis(st.session_state.platform_data)
        st.markdown("---")
        st.header("📥 Exportar Resultados")
        for platform, data in st.session_state.platform_data.items():
            with st.expander(f"📋 Descargar resultados - {platform.capitalize()}"):
                resultados = data.get('resultados', {})
                df_resultados = pd.DataFrame([{'Palabra': palabra, 'Frecuencia': datos['total'], 'Variantes': ', '.join(datos['variantes'].keys()) if datos['variantes'] else ''} for palabra, datos in resultados.items()])
                col1, col2 = st.columns(2)
                with col1:
                    csv = df_resultados.to_csv(index=False)
                    st.download_button(label=f"📥 Descargar CSV - {platform}", data=csv, file_name=f"analisis_{platform}.csv", mime="text/csv", key=f"csv_{platform}")
                with col2:
                    excel_buffer = io.BytesIO()
                    df_resultados.to_excel(excel_buffer, index=False)
                    st.download_button(label=f"📥 Descargar Excel - {platform}", data=excel_buffer.getvalue(), file_name=f"analisis_{platform}.xlsx", mime="application/vnd.ms-excel", key=f"excel_{platform}")
                # Exportar comentarios con etiquetas ACD
                comments_df = data.get('comments_df')
                if comments_df is not None:
                    csv2 = comments_df.to_csv(index=False)
                    st.download_button(label=f"📥 Descargar Comentarios+Etiquetas CSV - {platform}", data=csv2, file_name=f"comentarios_etiquetas_{platform}.csv", mime="text/csv", key=f"csv_comments_{platform}")
                    excel2 = io.BytesIO()
                    comments_df.to_excel(excel2, index=False)
                    st.download_button(label=f"📥 Descargar Comentarios+Etiquetas Excel - {platform}", data=excel2.getvalue(), file_name=f"comentarios_etiquetas_{platform}.xlsx", mime="application/vnd.ms-excel", key=f"excel_comments_{platform}")
    else:
        st.markdown("---")
        st.info("""
        ### ℹ️ Instrucciones de uso:
        1. Subí archivos de cada plataforma (TXT, CSV, Excel - máximo 1024KB cada uno)
        2. Haz click en los botones para analizar cada plataforma individualmente
        3. Visualizá los resultados en gráficos comparativos
        4. Explorá el análisis extendido con métricas detalladas
        5. Descargá los resultados en formato CSV o Excel
        """)
if __name__ == "__main__":
    main()
