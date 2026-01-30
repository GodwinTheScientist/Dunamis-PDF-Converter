if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter team password", type="password")
    if st.button("Login"):
        if password == "dunamisT2026":  # ← change this to your secret password
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop()

#Begin

import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import fitz  # PyMuPDF
import re
from io import BytesIO

logo_url = "https://i.postimg.cc/sxSLVk2D/church-logo-cmyk-1-white.png"
bg_image_url = "https://images.unsplash.com/photo-1530688957198-8570b1819eeb?q=80&w=2114&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"

st.markdown(f"""
    <style>
    .stApp {{
        background: radial-gradient(circle, rgba(15, 23, 42, 0.9) 0%, rgba(0, 0, 20, 0.98) 100%), 
                    url("{bg_image_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .header-box {{
        text-align: center;
        padding: 30px 0 20px 0;
    }}
    .mini-logo {{
        width: 120px;
        filter: drop-shadow(0px 0px 12px rgba(255, 255, 255, 0.2));
        margin-bottom: 15px;
    }}
    .main-title {{
        color: #FFD700 !important;
        font-size: 2.4rem !important;
        font-weight: 900 !important;
        margin: 0 !important;
        text-shadow: 0 4px 12px rgba(0,0,0,0.7);
    }}
    .subtitle {{
        color: #94A3B8;
        font-size: 1.1rem;
        margin: 8px 0 0 0;
    }}
    /* Centered compact tabs */
    [data-testid="stTabList"] {{
        display: flex !important;
        justify-content: center !important;
        max-width: 600px !important;
        margin: 0 auto 20px auto !important;
        background: rgba(255,255,255,0.06) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        backdrop-filter: blur(12px) !important;
    }}
    [data-testid="stTab"] {{
        color: #CBD5E1 !important;
        font-weight: 600;
        padding: 10px 24px !important;
        font-size: 1rem !important;
    }}
    [aria-selected="true"] {{
        background: rgba(255,215,0,0.25) !important;
        color: #FFD700 !important;
        border-radius: 8px !important;
    }}
    /* Compact glass panels */
    .block-container {{
        max-width: 900px !important;
        margin: 0 auto !important;
        padding: 0 20px !important;
    }}
    .stTabs > div > div {{
        background: rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(16px) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
        padding: 25px 20px !important;
        margin: 15px auto !important;
    }}
    /* Big centered Generate button - no scroll needed */
    .generate-container {{
        text-align: center;
        margin: 40px 0 40px 0;
    }}
    .generate-btn {{
        width: 360px !important;
        height: 64px !important;
        font-size: 1.5rem !important;
        font-weight: bold !important;
        background: linear-gradient(90deg, #FFD700, #FFEA00) !important;
        color: #001F3F !important;
        border: none !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 28px rgba(255,215,0,0.5) !important;
        transition: all 0.3s !important;
    }}
    .generate-btn:hover {{
        transform: translateY(-4px) !important;
        box-shadow: 0 16px 40px rgba(255,215,0,0.7) !important;
    }}
    /* Compact metric cards */
    .metric-card {{
        background: rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(16px) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.5) !important;
        padding: 20px !important;
        text-align: center;
    }}
    .metric-card h3 {{
        color: #FFD700 !important;
        font-size: 2.4rem !important;
        margin: 0 !important;
    }}
    .metric-card p {{
        color: #CBD5E1 !important;
        font-size: 0.95rem !important;
        margin: 6px 0 0 !important;
    }}
    </style>

    <div class="header-box">
        <img src="{logo_url}" class="mini-logo">
        <h1 class="main-title">Dunamis Prayer Converter</h1>
        <p class="subtitle">PDF to PPTX Dashboard</p>
    </div>
""", unsafe_allow_html=True)

# ── Compact Metrics ─────────────────────────────────────────────────────────
cols = st.columns(3)
with cols[0]:
    num_pdfs = len(st.session_state.get('uploaded_files', []))
    st.markdown(f"<div class='metric-card'><h3>{num_pdfs}</h3><p>Total PDFs</p></div>", unsafe_allow_html=True)
with cols[1]:
    st.markdown("<div class='metric-card'><h3>-</h3><p>Prayers</p></div>", unsafe_allow_html=True)
with cols[2]:
    st.markdown("<div class='metric-card'><h3>-</h3><p>Sessions</p></div>", unsafe_allow_html=True)

# ── Two compact centered tabs ───────────────────────────────────────────────
tab1, tab2 = st.tabs(["📁 Upload", "🎨 Customise"])

with tab1:
    uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        st.success(f"Uploaded {len(uploaded_files)} PDF(s)")

with tab2:
    col_left, col_right = st.columns([1, 1])
    with col_left:
        bg_option = st.radio("Background", ["Dark Navy", "Black", "Deep Purple", "Custom"])
        if bg_option == "Dark Navy":
            bg_rgb = (10, 20, 60)
        elif bg_option == "Black":
            bg_rgb = (0, 0, 0)
        elif bg_option == "Deep Purple":
            bg_rgb = (25, 0, 50)
        else:
            bg_hex = st.color_picker("Custom RGB", "#0A143C")
            bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (1, 3, 5))

        header_color = st.color_picker("Header", "#FFD700")
        body_color = st.color_picker("Body", "#FFFFFF")

    with col_right:
        header_size = st.slider("Header size", 50, 100, 72)
        body_size = st.slider("Body size", 40, 80, 54)
        bible_size = st.slider("Bible size", 40, 70, 50)

        text_case = st.selectbox("Text case", ["Original", "UPPERCASE", "lowercase", "Title Case"])
        include_bible = st.checkbox("Include Bible slide", value=True)

# ── Centered Generate Button (no scroll needed) ─────────────────────────────
st.markdown('<div class="generate-container">', unsafe_allow_html=True)
if st.button("🚀 Generate & Download PPTX", key="generate"):
    if 'uploaded_files' not in st.session_state or not st.session_state.uploaded_files:
        st.error("Upload PDFs first.")
    else:
        with st.spinner("Generating..."):
            prs = Presentation()
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)

            def set_bg(slide):
                fill = slide.background.fill
                fill.solid()
                fill.fore_color.rgb = RGBColor(*bg_rgb)

            def add_centered(slide, l, t, w, h, text, size, color_hex, bold=False):
                tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
                tf = tb.text_frame
                tf.word_wrap = True
                tf.clear()
                p = tf.add_paragraph()
                p.text = text or ""
                p.alignment = PP_ALIGN.CENTER
                run = p.runs[0]
                run.font.size = Pt(size)
                r, g, b = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))
                run.font.color.rgb = RGBColor(r, g, b)
                run.font.bold = bold

            for idx, file in enumerate(st.session_state.uploaded_files):
                doc = fitz.open(stream=file.getvalue(), filetype="pdf")
                text = "".join(page.get_text("text") for page in doc)

                lines = [l.strip() for l in text.split("\n") if l.strip()]

                title = file.name.replace(".pdf", "")
                if "FRIDAY" in text.upper():
                    title = "Friday Prayer Session"
                elif "SATURDAY" in text.upper():
                    title = "Saturday Prayer Session"

                abbr = re.search(r"(IJN=[\s\S]*?ITNJCN=[\s\S]*?Nazareth)", text, re.I)
                abbr_text = abbr.group(0).strip().replace("\n", " • ") if abbr else ""

                bible_ref, bible_text = "", ""
                ref = re.search(r"((Genesis|Hebrews)[\s\S]*?\(KJV\))", text, re.I)
                if ref:
                    bible_ref = ref.group(1).strip()
                    start = text.find(bible_ref) + len(bible_ref)
                    end = text.find("1.", start)
                    bible_text = text[start:end].strip() if end > start else ""

                prayers = []
                current = ""
                for line in lines:
                    if re.match(r"^\d+\.", line):
                        if current:
                            prayers.append(current.strip())
                        current = line
                    elif current and not line.startswith(("Page", "Dunamis Bible Church")):
                        current += " " + line
                if current:
                    prayers.append(current.strip())

                if idx > 0:
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    add_centered(slide, 0.8, 3.0, 11.7, 2.0, f"--- Next Session ---\n{title}", 60, header_color, True)

                slide = prs.slides.add_slide(prs.slide_layouts[6])
                set_bg(slide)
                add_centered(slide, 0.8, 0.5, 11.7, 1.8, f"Dunamis Bible Church", 56, header_color, True)
                add_centered(slide, 1.2, 5.5, 11.0, 1.0, "PRAYER POINTS", 50, "#CCCCCC")

                if include_bible and bible_ref:
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    add_centered(slide, 0.8, 0.8, 11.7, 1.4, bible_ref, header_size + 4, header_color, True)
                    add_centered(slide, 1.0, 2.4, 11.3, 4.6, bible_text, bible_size, body_color)

                for prayer in prayers:
                    m = re.match(r"^(\d+)\.\s*(.*)", prayer, re.DOTALL)
                    if m:
                        num, text = m.groups()
                        if text_case == "UPPERCASE":
                            text = text.upper()
                        elif text_case == "lowercase":
                            text = text.lower()
                        elif text_case == "Title Case":
                            text = text.title()

                        slide = prs.slides.add_slide(prs.slide_layouts[6])
                        set_bg(slide)
                        add_centered(slide, 0.8, 0.6, 11.7, 1.6, f"Prayer Point {num}", header_size, header_color, True)
                        add_centered(slide, 1.0, 2.4, 11.3, 4.5, text.strip(), body_size, body_color)

            bio = BytesIO()
            prs.save(bio)
            bio.seek(0)

            st.success("✅ Ready!")
            st.download_button(
                label="⬇ Download PPTX",
                data=bio,
                file_name="Dunamis_Prayer_Sessions.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True
            )

st.markdown('</div>', unsafe_allow_html=True)