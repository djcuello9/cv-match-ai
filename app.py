import json
import os
import io
import streamlit as st
import anthropic
from pypdf import PdfReader

# Importaciones de ReportLab para la generación de PDFs
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="CV-Match AI | Optimiza tu Currículum",
    page_icon="📄",
    layout="centered"
)

# --- SEGURIDAD Y CONFIGURACIÓN DE API KEY ---
api_key = st.secrets.get("KEY") or os.environ.get("KEY")

def init_anthropic_client(key):
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)

client = init_anthropic_client(api_key)

# --- INTERFAZ GRÁFICA (UI) ---
st.title("📄 CV-Match AI")
st.markdown("Optimiza tu currículum para superar los filtros ATS y alinea tu perfil con la oferta de trabajo ideal utilizando inteligencia artificial.")

if not client:
    st.error("⚠️ No se encontró la API Key de Anthropic. Configúrala en los secretos de Streamlit (`st.secrets`) o como variable de entorno.")
    st.stop()

# Sección de Carga de Archivos
st.subheader("1. Sube tu CV actual")
uploaded_file = st.file_uploader("Sube tu currículum en formato PDF", type=["pdf"])

# Sección de Descripción de la Oferta
st.subheader("2. Pega la oferta de trabajo")
job_description = st.text_area(
    "Pega aquí la descripción completa del puesto (requisitos, responsabilidades, etc.):",
    height=200,
    placeholder="Ejemplo: Buscamos un desarrollador Python con experiencia en APIs, SQL y metodologías ágiles..."
)

# --- LÓGICA DE PROCESAMIENTO ---
def extract_text_from_pdf(pdf_file) -> str:
    """Extrae texto plano de un archivo PDF subido de forma segura."""
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        st.error(f"Error al leer el archivo PDF: {e}")
        return ""

def analyze_and_optimize(cv_text: str, job_desc: str) -> dict:
    prompt = f"""
[Rol]
Eres un experto senior en recursos humanos, reclutamiento técnico y optimización de currículums para sistemas ATS (Applicant Tracking Systems). Tu objetivo es reescribir y optimizar la experiencia laboral de un candidato para que haga "match" perfecto con una oferta de empleo específica, manteniendo total veracidad (sin inventar experiencias falsas, solo mejorando la redacción, impacto y palabras clave).

[Entrada]
- CV del candidato: 
{cv_text}

- Descripción de la oferta de trabajo: 
{job_desc}

[Instrucciones de Procesamiento]
1. Identifica las 5 palabras clave técnicas o blandas más importantes de la oferta que falten o estén débiles en el CV.
2. Reescribe las viñetas (bullet points) de la experiencia laboral más reciente utilizando la fórmula de impacto STAR, integrando las palabras clave de forma natural.
3. Redacta una carta de presentación ejecutiva de 3 párrafos dirigida a la empresa, destacando por qué el candidato es ideal.
4. Calcula un "ATS Match Score" estimado antes y después de tu optimización (en porcentaje, ej: "65%" y "92%").

[Formato de Salida Requerido]
Devuelve la respuesta ESTRICTAMENTE en formato JSON válido, sin texto adicional fuera del JSON, con la siguiente estructura exacta:
{{
  "match_score_inicial": "XX%",
  "match_score_optimizado": "XX%",
  "palabras_clave_agregadas": ["keyword1", "keyword2", "keyword3"],
  "experiencia_optimizada": [
    {{
      "puesto": "...",
      "empresa": "...",
      "bullets_nuevos": ["...", "..."]
    }}
  ],
  "carta_presentacion": "Texto completo de la carta..."
}}
"""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_response = response.content[0].text
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
            
        return json.loads(clean_json.strip())
    
    except json.JSONDecodeError:
        st.error("La IA generó una respuesta pero no pudo ser interpretada como JSON. Inténtalo de nuevo.")
        return None
    except anthropic.APIError as e:
        st.error(f"Error de comunicación con la API de Anthropic: {e}")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")
        return None

def generate_pdf_report(result: dict) -> bytes:
    """Genera un archivo PDF profesional en memoria utilizando ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=10
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
        leading=14
    )
    
    story = []
    
    # Título del Reporte
    story.append(Paragraph("Reporte de Optimización ATS - CV-Match AI", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=15))
    
    # Resumen de Métricas
    story.append(Paragraph("<b>Métricas de Compatibilidad:</b>", heading_style))
    story.append(Paragraph(f"• <b>Compatibilidad Inicial (ATS):</b> {result.get('match_score_inicial', 'N/A')}", body_style))
    story.append(Paragraph(f"• <b>Compatibilidad Optimizada:</b> {result.get('match_score_optimizado', 'N/A')}", body_style))
    
    # Palabras Clave
    story.append(Paragraph("Palabras Clave Integradas", heading_style))
    keywords = ", ".join([f"`{kw}`" for kw in result.get("palabras_clave_agregadas", [])])
    story.append(Paragraph(keywords, body_style))
    
    story.append(Spacer(1, 10))
    
    # Experiencia Optimizada
    story.append(Paragraph("Experiencia Laboral Optimizada (Método STAR)", heading_style))
    for exp in result.get("experiencia_optimizada", []):
        story.append(Paragraph(f"<b>{exp.get('puesto')}</b> en <i>{exp.get('empresa')}</i>", body_style))
        for bullet in exp.get("bullets_nuevos", []):
            story.append(Paragraph(f"• {bullet}", body_style))
        story.append(Spacer(1, 6))
        
    story.append(Spacer(1, 10))
    
    # Carta de Presentación
    story.append(Paragraph("Carta de Presentación Profesional", heading_style))
    story.append(Paragraph(result.get("carta_presentacion", "").replace("\n", "<br/>"), body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- BOTÓN DE EJECUCIÓN ---
if st.button("🚀 Optimizar mi CV ahora", type="primary"):
    if not uploaded_file:
        st.warning("Por favor, sube tu currículum en formato PDF.")
    elif not job_description.strip():
        st.warning("Por favor, ingresa la descripción de la oferta de trabajo.")
    else:
        with st.spinner("Analizando tu perfil y optimizando para sistemas ATS... Esto toma unos segundos."):
            cv_raw_text = extract_text_from_pdf(uploaded_file)
            
            if cv_raw_text:
                result = analyze_and_optimize(cv_raw_text, job_description)
                
                if result:
                    st.success("¡Optimización completada con éxito!")
                    
                    # Guardar el resultado en el estado de sesión para permitir la descarga del PDF sin reejecutar
                    st.session_state["optimization_result"] = result

# Mostrar resultados y botón de descarga si existen en la sesión
if "optimization_result" in st.session_state:
    result = st.session_state["optimization_result"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Compatibilidad Inicial (ATS)", result.get("match_score_inicial", "N/A"))
    with col2:
        st.metric("Compatibilidad Optimizada", result.get("match_score_optimizado", "N/A"), delta="Alto impacto")
    
    st.divider()
    
    st.subheader("🔑 Palabras Clave Clave Integradas")
    keywords = result.get("palabras_clave_agregadas", [])
    if keywords:
        st.write(" ".join([f"`{kw}`" for kw in keywords]))
        
    st.divider()
    
    st.subheader("💼 Experiencia Laboral Optimizada (Formato STAR)")
    for exp in result.get("experiencia_optimizada", []):
        st.markdown(f"**{exp.get('puesto')}** en *{exp.get('empresa')}*")
        for bullet in exp.get("bullets_nuevos", []):
            st.markdown(f"- {bullet}")
        st.write("")
        
    st.divider()
    
    st.subheader("✍️ Carta de Presentación Sugerida")
    st.text_area("Copia tu carta aquí:", value=result.get("carta_presentacion", ""), height=200)
    
    st.divider()
    
    # --- BOTÓN DE DESCARGA PDF ---
    pdf_bytes = generate_pdf_report(result)
    st.download_button(
        label="📥 Descargar Reporte y CV Optimizado en PDF",
        data=pdf_bytes,
        file_name="CV_Optimizado_CV_Match_AI.pdf",
        mime="application/pdf",
        type="primary"
    )
