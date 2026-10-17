# Analizador del Discurso - Reframing en RRSS

Herramienta de clasificación automática de comentarios de redes sociales
(Facebook, Instagram, X) según su encuadre (frame) sobre de un hecho delictivo.

## Qué hace

Clasifica comentarios en categorías, con una lógica de "desplazamiento de encuadre":

| Valor | Categoría | Descripción |
|-------|-----------|-------------|
| 0 | Crimen | Frame esperado: el comentario se centra en el hecho delictivo |
| 1 | Discriminación | Desplaza el foco hacia nacionalidad, fenotipo, etnia u origen |
| 2 | Burla | Ridiculiza al sospechoso sin eje discriminatorio |
| 3 | Reclamo | Queja institucional o política sobre inseguridad, migración, policía |
| 4 | Sospecha IA | Cuestiona la autenticidad de la imagen difundida |
| 5 | Otra categoría | Información no relacionada con el crimen (off-topic) |
| 6 | Multimodal/Residual | Solo emoji, link, meme o risa sin contexto frameable |

## Uso online

La app está desplegada en Streamlit Cloud:
https://adispro.streamlit.app

## Uso local

```bash
pip install -r requirements.txt
streamlit run app.py
