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

# Initialize session state tracking
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'total_prayers' not in st.session_state:
    st.session_state.total_prayers = 0
if 'total_sessions' not in st.session_state:
    st.session_state.total_sessions = 0

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
        padding: 60px 0 30px 0;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
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
    .block-container {{
        max-width: 900px !important;
        margin: 0 auto !important;
        padding: 0 20px !important;
    }}
    .stTabs > div > div:has(> *) {{
        background: rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(16px) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
        padding: 25px 20px !important;
        margin: 15px auto !important;
    }}
    .generate-container {{
        text-align: center;
        margin: 30px 0;
    }}
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
        <p class="subtitle">Universal PDF to PPTX Dashboard</p>
    </div>
""", unsafe_allow_html=True)

# ── Dynamic Metric Panels ───────────────────────────────────────────────────
cols = st.columns(3)
with cols[0]:
    num_pdfs = len(st.session_state.uploaded_files)
    st.markdown(f"<div class='metric-card'><h3>{num_pdfs}</h3><p>Total PDFs</p></div>", unsafe_allow_html=True)
with cols[1]:
    st.markdown(f"<div class='metric-card'><h3>{st.session_state.total_prayers}</h3><p>Content Blocks</p></div>", unsafe_allow_html=True)
with cols[2]:
    st.markdown(f"<div class='metric-card'><h3>{st.session_state.total_sessions}</h3><p>Total Files</p></div>", unsafe_allow_html=True)

# ── Customizer & Management Tabs ───────────────────────────────────────────
tab1, tab2 = st.tabs(["📁 Upload", "🎨 Customise"])

with tab1:
    uploaded_files = st.file_uploader("Upload PDFs (Template or General)", type=["pdf"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        
        # Calculate metrics directly on the fly without forcing an aggressive st.rerun()
        temp_blocks = 0
        for file in uploaded_files:
            try:
                doc = fitz.open(stream=file.getvalue(), filetype="pdf")
                text = "".join(page.get_text("text") for page in doc)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                
                if any(re.match(r"^\d+\.", l) for l in lines):
                    temp_blocks += sum(1 for l in lines if re.match(r"^\d+\.", l))
                else:
                    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                    temp_blocks += max(1, len(paragraphs) - 1)
            except Exception:
                pass
        st.session_state.total_prayers = temp_blocks
        st.session_state.total_sessions = len(uploaded_files)
        st.rerun()

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

        header_color = st.color_picker("Header Color", "#FFD700")
        body_color = st.color_picker("Body Text Color", "#FFFFFF")

    with col_right:
        header_size = st.slider("Header text size", 30, 100, 60)
        body_size = st.slider("Body text size", 24, 80, 44)
        bible_size = st.slider("Scripture text size", 24, 70, 40)

        text_case = st.selectbox("Text casing adjustment", ["Original", "UPPERCASE", "lowercase", "Title Case"])
        include_bible = st.checkbox("Look for & include Bible slides", value=True)

# ── Processing & Generation Engine ──────────────────────────────────────────
st.markdown('<div class="generate-container">', unsafe_allow_html=True)

if st.button("🚀 Generate & Download PPTX", key="generate", use_container_width=True):
    if 'uploaded_files' not in st.session_state or not st.session_state.uploaded_files:
        st.error("Please upload one or more PDF files before trying to generate presentation files.")
    else:
        # Create a container to give real-time status updates right on the UI
        status_box = st.empty()
        status_box.info("Processing files and applying adaptive layout logic...")
        
        try:
            prs = Presentation()
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)

            def set_bg(slide):
                fill = slide.background.fill
                fill.solid()
                fill.fore_color.rgb = RGBColor(*bg_rgb)

            def apply_casing(txt):
                if text_case == "UPPERCASE":
                    return txt.upper()
                elif text_case == "lowercase":
                    return txt.lower()
                elif text_case == "Title Case":
                    return txt.title()
                return txt

            def add_centered(slide, l, t, w, h, text, size, color_hex, bold=False):
                tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
                tf = tb.text_frame
                tf.word_wrap = True
                tf.clear()
                p = tf.add_paragraph()
                p.text = text or ""
                p.alignment = PP_ALIGN.CENTER
                if p.runs:
                    run = p.runs[0]
                    run.font.size = Pt(size)
                    r, g, b = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))
                    run.font.color.rgb = RGBColor(r, g, b)
                    run.font.bold = bold

            for idx, file in enumerate(st.session_state.uploaded_files):
                doc = fitz.open(stream=file.getvalue(), filetype="pdf")
                raw_text = "".join(page.get_text("text") for page in doc)
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                
                if not lines:
                    continue

                # Auto-detect if it's a template or a normal document
                is_template = any(re.match(r"^\d+\.", l) for l in lines)
                
                doc_title = file.name.replace(".pdf", "").replace("_", " ")
                if "FRIDAY" in raw_text.upper():
                    doc_title = "Friday Prayer Session"
                elif "SATURDAY" in raw_text.upper():
                    doc_title = "Saturday Prayer Session"
                elif not is_template and len(lines) > 0:
                    if len(lines[0]) < 60:
                        doc_title = lines[0]

                # Intermission Slide
                if idx > 0:
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    add_centered(slide, 0.8, 3.0, 11.7, 2.0, f"--- Next Section ---\n{doc_title}", 48, header_color, True)

                # Welcome Cover Slide
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                set_bg(slide)
                add_centered(slide, 0.8, 2.2, 11.7, 1.8, "Dunamis Bible Church" if is_template else "Presentation Deck", 52, header_color, True)
                add_centered(slide, 1.2, 4.2, 11.0, 1.5, doc_title.upper(), 40, "#CCCCCC", False)

                if is_template:
                    # ── TEMPLATE PROCESSING LOGIC ──
                    bible_ref, bible_text = "", ""
                    ref = re.search(r"(([Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|John|Jude|Revelation][\w\s]+)\s\d+:\d+.*\(KJV\))", raw_text, re.I)
                    if ref:
                        bible_ref = ref.group(1).strip()
                        start = raw_text.find(bible_ref) + len(bible_ref)
                        end = raw_text.find("1.", start)
                        if end > start:
                            raw_bible_text = raw_text[start:end].strip()
                            bible_text = re.sub(r"(Dunamis Bible Church|Page\s+\d+)", "", raw_bible_text, flags=re.I).strip()

                    if include_bible and bible_ref and bible_text:
                        slide = prs.slides.add_slide(prs.slide_layouts[6])
                        set_bg(slide)
                        add_centered(slide, 0.8, 0.8, 11.7, 1.2, bible_ref, header_size, header_color, True)
                        add_centered(slide, 1.0, 2.2, 11.3, 4.8, bible_text, bible_size, body_color)

                    items = []
                    current = ""
                    for line in lines:
                        if re.match(r"^\d+\.", line):
                            if current: items.append(current.strip())
                            current = line
                        elif current:
                            if not any(x in line.lower() for x in ["page ", "dunamis bible church", "prayer points"]):
                                current += " " + line
                    if current: items.append(current.strip())

                    for item in items:
                        m = re.match(r"^(\d+)\.\s*(.*)", item, re.DOTALL)
                        if m:
                            num, p_text = m.groups()
                            slide = prs.slides.add_slide(prs.slide_layouts[6])
                            set_bg(slide)
                            add_centered(slide, 0.8, 0.6, 11.7, 1.4, f"Point {num}", header_size, header_color, True)
                            add_centered(slide, 1.0, 2.2, 11.3, 4.8, apply_casing(p_text.strip()), body_size, body_color)
                else:
                    # ── GENERIC / NORMAL PDF PROCESSING LOGIC ──
                    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
                    
                    # Safe fallback if double-newlines don't exist
                    if len(paragraphs) <= 1:
                        paragraphs = []
                        current_chunk = []
                        start_idx = 1 if len(lines[0]) < 60 else 0
                        for line in lines[start_idx:]:
                            current_chunk.append(line)
                            if len(current_chunk) >= 3 or len(" ".join(current_chunk)) > 250:
                                paragraphs.append(" ".join(current_chunk))
                                current_chunk = []
                        if current_chunk:
                            paragraphs.append(" ".join(current_chunk))

                    for i, block in enumerate(paragraphs):
                        if len(block) < 5:
                            continue
                        slide = prs.slides.add_slide(prs.slide_layouts[6])
                        set_bg(slide)
                        add_centered(slide, 0.8, 0.6, 11.7, 1.4, f"Section {i+1}", header_size, header_color, True)
                        add_centered(slide, 1.0, 2.2, 11.3, 4.8, apply_casing(block), max(20, body_size - 6), body_color)

            # Build byte output
            bio = BytesIO()
            prs.save(bio)
            bio.seek(0)

            # Clear the processing message and display success tracking
            status_box.empty()
            st.success("🎉 PowerPoint slideshow generated successfully!")
            
            st.download_button(
                label="⬇ Click Here to Download PPTX Deck",
                data=bio,
                file_name="Converted_Presentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True
            )
        except Exception as e:
            status_box.empty()
            st.error(f"Processing Error: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)