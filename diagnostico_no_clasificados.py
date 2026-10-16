# -*- coding: utf-8 -*-
"""
diagnostico_no_clasificados.py

Aísla los comentarios que el instrumento NO logra clasificar en ningún
Frame (Frame = 0) y analiza cuáles son las palabras más frecuentes
dentro de ese subconjunto, para detectar patrones que quizás falten
en los diccionarios actuales.

Acepta DOS formatos de archivo de entrada (detecta automáticamente
según la extensión):
  - .xlsx: Excel con varias hojas, columna de comentarios.
  - .txt:  una línea por comentario, con el ID y el comentario
           separados por TABULACIÓN, ej: "F01_07[TAB]el comentario"

INSTRUCCIONES:
1. Poné este archivo, 'deteccion.py', y tu corpus (.xlsx o .txt) en la
   misma carpeta.
2. Editá la sección CONFIGURACIÓN de abajo con el nombre real de tu archivo.
3. Ejecutá: python diagnostico_no_clasificados.py
4. Se generan dos archivos:
   - 'no_clasificados.xlsx': todos los comentarios con Frame=0, para leer a mano.
   - 'frecuencia_no_clasificados.xlsx': ranking de palabras más repetidas
     dentro de ese subconjunto (después de sacar palabras vacías).
"""

import pandas as pd
import re
import os
from collections import Counter
from deteccion import detectar_frame, normalizar_texto

# =============================================================================
# CONFIGURACIÓN — Editá con tus datos reales
# =============================================================================
ARCHIVO_CORPUS = "Facebook.xlsx"      # puede ser .xlsx o .txt
NOMBRE_COLUMNA_COMENTARIO = "Comment"  # solo se usa si el archivo es .xlsx

# Palabras vacías a ignorar en el análisis de frecuencia (ampliá esta lista
# si ves que aparecen más conectores/artículos irrelevantes en el resultado)
PALABRAS_VACIAS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
    "al", "a", "y", "o", "u", "que", "en", "es", "por", "para", "con",
    "sin", "se", "su", "sus", "lo", "le", "les", "mi", "tu", "vos", "yo",
    "no", "si", "ya", "mas", "más", "muy", "esto", "eso", "esta", "esta",
    "este", "asi", "así", "porque", "como", "cuando", "donde", "todo",
    "toda", "todos", "todas", "hay", "ser", "esta", "estan", "están",
    "fue", "son", "eso", "pero", "también", "tambien", "solo", "sólo",
    "aca", "acá", "alla", "allá", "ahi", "ahí", "les", "nos",
}

# =============================================================================
# A partir de acá no hace falta tocar nada
# =============================================================================


def cargar_desde_txt(ruta_txt):
    """
    Lee un .txt con una línea por comentario, formato:
    ID_comment[TAB]comentario
    Devuelve una lista de diccionarios {"ID_comment": ..., "comentario": ...}
    """
    filas = []
    with open(ruta_txt, "r", encoding="utf-8") as f:
        for num_linea, linea in enumerate(f, start=1):
            linea = linea.rstrip("\n").rstrip("\r")
            if not linea.strip():
                continue
            partes = linea.split("\t", 1)  # separa solo en la PRIMERA tabulación
            if len(partes) == 2:
                id_comment, comentario = partes
            else:
                # No se encontró tabulación: guardamos igual, con ID vacío,
                # para no perder la línea, pero avisamos.
                id_comment, comentario = "", linea
                print(f"  Aviso: la línea {num_linea} no tiene tabulación, "
                      f"se guarda sin ID separado: '{linea[:50]}...'")
            filas.append({"ID_comment": id_comment.strip(), "comentario": comentario.strip()})
    return filas


def aislar_no_clasificados(ruta_archivo, columna_comentario):
    """
    Aplica detectar_frame() a cada comentario del archivo (.xlsx o .txt) y
    devuelve un DataFrame solo con los comentarios que dieron Frame=0.
    """
    extension = os.path.splitext(ruta_archivo)[1].lower()
    filas = []

    if extension == ".txt":
        print(f"Detectado archivo .txt, leyendo '{ruta_archivo}'...")
        comentarios_txt = cargar_desde_txt(ruta_archivo)
        print(f"  {len(comentarios_txt)} líneas leídas del .txt")
        for item in comentarios_txt:
            comentario = item["comentario"]
            frame = detectar_frame(comentario)
            if frame == 0:
                filas.append({
                    "hoja": "-",
                    "ID_comment": item["ID_comment"],
                    "comentario": comentario,
                })

    elif extension in (".xlsx", ".xls"):
        print(f"Detectado archivo Excel, leyendo '{ruta_archivo}'...")
        xls = pd.ExcelFile(ruta_archivo)
        print(f"  Hojas encontradas: {xls.sheet_names}")
        for nombre_hoja in xls.sheet_names:
            df_hoja = pd.read_excel(xls, sheet_name=nombre_hoja)
            if columna_comentario not in df_hoja.columns:
                print(f"  Aviso: la hoja '{nombre_hoja}' no tiene una columna "
                      f"llamada '{columna_comentario}'. Columnas disponibles: "
                      f"{list(df_hoja.columns)}. Se omite esta hoja.")
                continue
            for _, fila in df_hoja.iterrows():
                comentario = str(fila[columna_comentario])
                frame = detectar_frame(comentario)
                if frame == 0:
                    filas.append({
                        "hoja": nombre_hoja,
                        "ID_comment": fila.get("ID_comment", ""),
                        "comentario": comentario,
                    })
    else:
        raise ValueError(
            f"Extensión '{extension}' no soportada. Usá un archivo .xlsx o .txt."
        )

    return pd.DataFrame(filas)


def analizar_frecuencia(df_no_clasificados, columna_comentario="comentario"):
    """
    Cuenta la frecuencia de palabras dentro del subconjunto de comentarios
    sin clasificar, sacando palabras vacías. Reutiliza normalizar_texto()
    para que las variantes evasivas también queden agrupadas correctamente.
    """
    contador = Counter()

    for comentario in df_no_clasificados[columna_comentario]:
        texto_norm = normalizar_texto(comentario)
        palabras = re.findall(r"[a-záéíóúñ]+", texto_norm)
        for palabra in palabras:
            if palabra not in PALABRAS_VACIAS and len(palabra) > 2:
                contador[palabra] += 1

    df_frecuencia = pd.DataFrame(
        contador.most_common(), columns=["palabra", "frecuencia"]
    )
    return df_frecuencia


def main():
    print("=" * 70)
    print("PASO 1: Aislando comentarios con Frame = 0 (sin clasificar)")
    print("=" * 70)

    if not os.path.exists(ARCHIVO_CORPUS):
        print(f"\n❌ ERROR: no se encontró el archivo '{ARCHIVO_CORPUS}' en esta carpeta.")
        print(f"   Archivos que SÍ hay en esta carpeta: {os.listdir('.')}")
        print("   Revisá que el nombre en ARCHIVO_CORPUS sea EXACTAMENTE igual")
        print("   (mayúsculas y extensión incluidas) al archivo real.")
        return

    no_clasificados = aislar_no_clasificados(ARCHIVO_CORPUS, NOMBRE_COLUMNA_COMENTARIO)
    print(f"\nTotal de comentarios sin clasificar encontrados: {len(no_clasificados)}")

    if len(no_clasificados) == 0:
        print("\n⚠️  No se encontró ningún comentario. Esto puede significar:")
        print("   - El archivo no tiene el formato esperado (revisá los avisos de arriba)")
        print("   - O realmente todos los comentarios ya están clasificados (poco probable)")
        return

    no_clasificados.to_excel("no_clasificados.xlsx", index=False)
    print("Guardado en 'no_clasificados.xlsx'\n")

    print("=" * 70)
    print("PASO 2: Analizando palabras más frecuentes dentro de ese subconjunto")
    print("=" * 70)
    frecuencia = analizar_frecuencia(no_clasificados)
    frecuencia.to_excel("frecuencia_no_clasificados.xlsx", index=False)

    print("\nTop 25 palabras más frecuentes entre los NO clasificados:")
    print(frecuencia.head(25).to_string(index=False))
    print("\nGuardado completo en 'frecuencia_no_clasificados.xlsx'")
    print("\nRevisá esa lista: si ves palabras con carga discriminatoria, de")
    print("reclamo o de burla que no estén en tus diccionarios, son las")
    print("primeras candidatas para ampliar el instrumento.")


if __name__ == "__main__":
    main()
