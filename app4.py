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
        padding: 90px 0 40px 0;
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
        margin: 40px 0 40px 0;
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
        <p class="subtitle">PDF to PPTX Dashboard</p>
    </div>
""", unsafe_allow_html=True)

# Initialize counter states cleanly
if 'parsed_prayers_count' not in st.session_state:
    st.session_state.parsed_prayers_count = "-"
if 'parsed_sessions_count' not in st.session_state:
    st.session_state.parsed_sessions_count = "-"

# ── Metrics Row ─────────────────────────────────────────────────────────────
cols = st.columns(3)
with cols[0]:
    num_pdfs = len(st.session_state.get('uploaded_files', []))
    st.markdown(f"<div class='metric-card'><h3>{num_pdfs}</h3><p>Total PDFs</p></div>", unsafe_allow_html=True)
with cols[1]:
    st.markdown(f"<div class='metric-card'><h3>{st.session_state.parsed_prayers_count}</h3><p>Total Prayers</p></div>", unsafe_allow_html=True)
with cols[2]:
    st.markdown(f"<div class='metric-card'><h3>{st.session_state.parsed_sessions_count}</h3><p>Total Sessions</p></div>", unsafe_allow_html=True)

# ── Configuration Tabs ──────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📁 Upload", "🎨 Customise"])

with tab1:
    uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        st.success(f"Uploaded {len(uploaded_files)} PDF(s)")
        
        # Calculate dynamic metrics on document submission
        total_prayers_found = 0
        for f in uploaded_files:
            try:
                d = fitz.open(stream=f.getvalue(), filetype="pdf")
                t = "".join(p.get_text("text") for p in d)
                total_prayers_found += len(re.findall(r"^\d+\.", t, re.M))
            except:
                pass
        st.session_state.parsed_prayers_count = total_prayers_found if total_prayers_found > 0 else "-"
        st.session_state.parsed_sessions_count = len(uploaded_files)

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
        header_size = st.slider("Header size", 40, 90, 64)
        body_size = st.slider("Body size", 32, 70, 46)
        bible_size = st.slider("Bible size", 32, 70, 42)

        text_case = st.selectbox("Text case", ["Original", "UPPERCASE", "lowercase", "Title Case"])
        include_bible = st.checkbox("Include Bible slide", value=True)

# ── Generation Engine ───────────────────────────────────────────────────────
st.markdown('<div class="generate-container">', unsafe_allow_html=True)
if st.button("🚀 Generate & Download PPTX", key="generate"):
    if 'uploaded_files' not in st.session_state or not st.session_state.uploaded_files:
        st.error("Upload PDFs first.")
    else:
        with st.spinner("Generating Presentation Layouts..."):
            prs = Presentation()
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)

            def set_bg(slide):
                fill = slide.background.fill
                fill.solid()
                fill.fore_color.rgb = RGBColor(*bg_rgb)

            def clean_system_artifacts(txt):
                if not txt:
                    return ""
                # Strip variable spacing page markers: "P a g e  1 | 2", "Page 2", etc.
                txt = re.sub(r"P\s*a\s*g\s*e\s*\d+\s*\|\s*\d+", "", txt, flags=re.I)
                txt = re.sub(r"Page\s*\d+", "", txt, flags=re.I)
                # Eliminate standard repeated running document footers/headers
                txt = re.sub(r"Dunamis Bible Church", "", txt, flags=re.I)
                return txt.strip()

            def get_adaptive_font_size(text, base_size):
                length = len(text)
                # Scaled font logic to fit within widescreen bounding parameters
                if length > 300:
                    return max(24, int(base_size * 0.55))
                elif length > 180:
                    return max(28, int(base_size * 0.72))
                elif length > 120:
                    return max(34, int(base_size * 0.85))
                return base_size

            def add_centered(slide, l, t, w, h, text, size, color_hex, bold=False):
                tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
                tf = tb.text_frame
                tf.word_wrap = True
                tf.clear()
                
                # Zero out internal margins so text has extra vertical breathing room
                tf.margin_left = Inches(0.1)
                tf.margin_right = Inches(0.1)
                tf.margin_top = Inches(0.1)
                tf.margin_bottom = Inches(0.1)
                
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                
                run = p.add_run()
                run.text = text or ""
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

                # Intermission slide between multiple uploaded files
                if idx > 0:
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    add_centered(slide, 0.8, 2.5, 11.7, 2.5, f"--- Next Session ---\n{title}", 54, header_color, True)

                # Welcome Cover Slide
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                set_bg(slide)
                add_centered(slide, 0.8, 1.2, 11.7, 1.8, f"Dunamis Bible Church", 56, header_color, True)
                add_centered(slide, 1.2, 4.5, 11.0, 1.5, "PRAYER POINTS", 48, "#CCCCCC")

                # Parse Scripture metadata details
                bible_ref, bible_text = "", ""
                ref = re.search(r"(([1-3]?\s?[A-Za-z]+)[\s\S]*?\(KJV\))", text, re.I)
                if ref:
                    bible_ref = ref.group(1).strip()
                    start = text.find(bible_ref) + len(bible_ref)
                    end = text.find("1.", start)
                    if end > start:
                        raw_bible_text = text[start:end]
                        bible_text = clean_system_artifacts(raw_bible_text)

                if include_bible and bible_ref and bible_text:
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    
                    # Prevent long book name reference overflows
                    ref_size = header_size if len(bible_ref) < 40 else header_size - 12
                    add_centered(slide, 0.8, 0.5, 11.7, 1.2, bible_ref, ref_size, header_color, True)
                    
                    # Dynamically compute safety size for scripture bodies
                    computed_bible_size = get_adaptive_font_size(bible_text, bible_size)
                    add_centered(slide, 0.8, 2.0, 11.7, 5.0, bible_text, computed_bible_size, body_color)

                # Parse and group Prayer Points cleanly
                prayers = []
                current = ""
                for line in lines:
                    if re.match(r"^\d+\.", line):
                        if current:
                            prayers.append(current.strip())
                        current = line
                    elif current:
                        # Prevent appending running headers/footers into text body streams
                        cleaned_line = clean_system_artifacts(line)
                        if cleaned_line:
                            current += " " + cleaned_line
                if current:
                    prayers.append(current.strip())

                # Generate clean scaled slides for each parsed point
                for prayer in prayers:
                    m = re.match(r"^(\d+)\.\s*(.*)", prayer, re.DOTALL)
                    if m:
                        num, text_content = m.groups()
                        text_content = clean_system_artifacts(text_content)

                        if text_case == "UPPERCASE":
                            text_content = text_content.upper()
                        elif text_case == "lowercase":
                            text_content = text_content.lower()
                        elif text_case == "Title Case":
                            text_content = text_content.title()

                        slide = prs.slides.add_slide(prs.slide_layouts[6])
                        set_bg(slide)
                        
                        # Primary Title Header Block
                        add_centered(slide, 0.8, 0.6, 11.7, 1.4, f"Prayer Point {num}", header_size, header_color, True)
                        
                        # Calculate adaptive font size for the prayer content body
                        computed_body_size = get_adaptive_font_size(text_content, body_size)
                        
                        # Position body with expanded vertical allotment (y=2.2, h=4.8) to maximize visual safe areas
                        add_centered(slide, 0.8, 2.2, 11.7, 4.8, text_content, computed_body_size, body_color)

            bio = BytesIO()
            prs.save(bio)
            bio.seek(0)

            st.success("✅ Presentation layouts generated successfully!")
            st.download_button(
                label="⬇ Download PPTX",
                data=bio,
                file_name="Dunamis_Prayer_Sessions.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True
            )

st.markdown('</div>', unsafe_allow_html=True)