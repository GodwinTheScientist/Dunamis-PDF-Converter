import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import fitz  # PyMuPDF
import re
from io import BytesIO
from collections import Counter

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
        padding: 6px !important;
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
    /* Match the metric-card row's width/centering to the tab panel below it,
       since they otherwise inherit different widths from the block-container. */
    [data-testid="stHorizontalBlock"] {{
        max-width: 600px !important;
        margin: 0 auto 20px auto !important;
    }}
    /* st.button/st.download_button live in their own DOM node, not inside
       whatever <div> a nearby st.markdown call opens - centering them needs
       to target their actual container directly. */
    [data-testid="stButton"], [data-testid="stDownloadButton"] {{
        display: flex !important;
        justify-content: center !important;
    }}
    [data-testid="stButton"] {{
        margin-top: 40px !important;
    }}
    [data-testid="stDownloadButton"] {{
        margin-bottom: 40px !important;
    }}
    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {{
        width: 100%;
        max-width: 600px;
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

# ── Shared helpers ───────────────────────────────────────────────────────────
def hex_to_rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def is_church_template(text):
    """Detect the church's own prayer-point template by its hallmark phrases,
    rather than by generic numbered lines (which false-positive on almost any
    document that contains a date, verse reference, or numbered list)."""
    t = text.lower()
    return t.count("prayer point") >= 2 or "dunamis bible church" in t


def derive_title(filename, text):
    t = text.upper()
    if "FRIDAY" in t:
        return "Friday Prayer Session"
    if "SATURDAY" in t:
        return "Saturday Prayer Session"
    return filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip().title()


# ── Metrics Syncing ─────────────────────────────────────────────────────────
if 'total_prayers_count' not in st.session_state:
    st.session_state.total_prayers_count = "-"
if 'total_sessions_count' not in st.session_state:
    st.session_state.total_sessions_count = "-"

cols = st.columns(3)
with cols[0]:
    num_pdfs = len(st.session_state.get('uploaded_files', []))
    st.markdown(f"<div class='metric-card'><h3>{num_pdfs}</h3><p>Total PDFs</p></div>", unsafe_allow_html=True)
with cols[1]:
    st.markdown(f"<div class='metric-card'><h3>{st.session_state.total_prayers_count}</h3><p>Prayers</p></div>", unsafe_allow_html=True)
with cols[2]:
    st.markdown(f"<div class='metric-card'><h3>{st.session_state.total_sessions_count}</h3><p>Sessions</p></div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📁 Upload", "🎨 Customise"])

with tab1:
    doc_type_choice = st.selectbox(
        "Document type",
        ["Auto-detect", "Church Prayer Points", "General Document"],
        help="Auto-detect looks for the church template's own markers (e.g. 'Prayer Point'). "
             "Anything else is treated as a general document and split by headings/paragraphs instead."
    )

    uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        st.success(f"Uploaded {len(uploaded_files)} PDF(s)")

        prayers_found = 0
        sections_found = 0
        previews = []
        for f in uploaded_files:
            try:
                doc = fitz.open(stream=f.getvalue(), filetype="pdf")
                full_text = "".join(p.get_text("text") for p in doc)
                if not full_text.strip():
                    previews.append((f.name, "⚠️ No extractable text — looks like a scanned/image-only PDF"))
                    continue
                detected_church = is_church_template(full_text)
                if doc_type_choice == "Church Prayer Points" or (doc_type_choice == "Auto-detect" and detected_church):
                    prayers_found += len(re.findall(r"^\s*(?:Prayer Point\s*\d+|\(?\d+\)?[\.\s])", full_text, re.M | re.I))
                    previews.append((f.name, "Church Prayer Template"))
                else:
                    previews.append((f.name, "General Document"))
                    sections_found += 1
            except Exception as e:
                previews.append((f.name, f"⚠️ Could not read file: {e}"))

        st.session_state.total_prayers_count = prayers_found if prayers_found > 0 else "-"
        st.session_state.total_sessions_count = len(uploaded_files)

        with st.expander("Detected file types"):
            for name, label in previews:
                st.caption(f"**{name}** — {label}")

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
            bg_rgb = hex_to_rgb(bg_hex)

        header_color = st.color_picker("Header", "#FFD700")
        body_color = st.color_picker("Body", "#FFFFFF")

    with col_right:
        header_size = st.slider("Header size", 40, 100, 68)
        body_size = st.slider("Maximum Body size", 40, 100, 60)
        text_case = st.selectbox("Text case", ["Original", "UPPERCASE", "lowercase", "Title Case"])


def apply_case(text_case, value):
    if not value:
        return value
    if text_case == "UPPERCASE":
        return value.upper()
    if text_case == "lowercase":
        return value.lower()
    if text_case == "Title Case":
        return value.title()
    return value


# ── PowerPoint Generation Engine ────────────────────────────────────────────
if st.button("🚀 Generate & Download PPTX", key="generate"):
    if 'uploaded_files' not in st.session_state or not st.session_state.uploaded_files:
        st.error("Upload PDFs first.")
    else:
        with st.spinner("Processing Presentation Slides..."):
            prs = Presentation()
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)

            def set_bg(slide):
                fill = slide.background.fill
                fill.solid()
                fill.fore_color.rgb = RGBColor(*bg_rgb)

            def clean_text_block(txt):
                if not txt:
                    return ""
                txt = re.sub(r"P\s*a\s*g\s*e\s*\d+\s*\|\s*\d+", "", txt, flags=re.I)
                txt = re.sub(r"Page\s*\d+", "", txt, flags=re.I)
                txt = re.sub(r"Dunamis Bible Church.*", "", txt, flags=re.I)
                txt = re.sub(r"\(AKA.* Charity.*", "", txt, flags=re.I)
                return txt.strip()

            def add_cover_centered(slide, l, t, w, h, text, size, color_hex, bold=False):
                tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
                tf = tb.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                run = p.add_run()
                run.text = text
                run.font.size = Pt(size)
                r, g, b = hex_to_rgb(color_hex)
                run.font.color.rgb = RGBColor(r, g, b)
                run.font.bold = bold

            # ── Unified fluid text-fit engine (title optional) ──────────────
            def add_fluid_text_slide(slide, title, body_text, max_b_size, h_size, h_color, b_color):
                left = Inches(0.8)
                top = Inches(0.6)
                width = Inches(11.733)
                height = Inches(6.3)

                tb = slide.shapes.add_textbox(left, top, width, height)
                tf = tb.text_frame
                tf.word_wrap = True
                tf.margin_top = Inches(0)
                tf.margin_bottom = Inches(0)
                tf.margin_left = Inches(0)
                tf.margin_right = Inches(0)

                current_size = max_b_size
                char_len = len(body_text)

                if char_len > 300:
                    current_size = min(current_size, 38)
                elif char_len > 180:
                    current_size = min(current_size, 46)

                title_allowance = (h_size + 24) if title else 0

                while current_size >= 20:
                    tf.clear()

                    if title:
                        p1 = tf.paragraphs[0]
                        p1.alignment = PP_ALIGN.CENTER
                        p1.space_after = Pt(24)
                        run1 = p1.add_run()
                        run1.text = title
                        run1.font.size = Pt(h_size)
                        r, g, b = hex_to_rgb(h_color)
                        run1.font.color.rgb = RGBColor(r, g, b)
                        run1.font.bold = True
                        p2 = tf.add_paragraph()
                    else:
                        p2 = tf.paragraphs[0]

                    p2.alignment = PP_ALIGN.CENTER
                    p2.line_spacing = 1.15

                    run2 = p2.add_run()
                    run2.text = body_text
                    run2.font.size = Pt(current_size)
                    br, bg, bb = hex_to_rgb(b_color)
                    run2.font.color.rgb = RGBColor(br, bg, bb)
                    run2.font.bold = True

                    estimated_lines = (char_len * (current_size * 0.55)) / (11.733 * 72)
                    estimated_height = (title_allowance + (estimated_lines * current_size * 1.2)) / 72

                    if estimated_height <= 6.0:
                        break
                    current_size -= 4

            # ── Bullet-list slide for general documents ─────────────────────
            def add_bullet_slide(slide, title, bullets, h_size, max_b_size, h_color, b_color):
                left = Inches(0.9)
                top = Inches(0.6)
                width = Inches(11.5)
                height = Inches(6.3)

                tb = slide.shapes.add_textbox(left, top, width, height)
                tf = tb.text_frame
                tf.word_wrap = True
                tf.margin_top = Inches(0)
                tf.margin_bottom = Inches(0)

                current_size = min(max_b_size, 32)
                title_allowance = (h_size + 20) if title else 0

                while current_size >= 18:
                    tf.clear()

                    if title:
                        p1 = tf.paragraphs[0]
                        p1.alignment = PP_ALIGN.CENTER
                        p1.space_after = Pt(20)
                        run1 = p1.add_run()
                        run1.text = title
                        run1.font.size = Pt(h_size)
                        r, g, b = hex_to_rgb(h_color)
                        run1.font.color.rgb = RGBColor(r, g, b)
                        run1.font.bold = True
                        first_bullet_target = None
                    else:
                        first_bullet_target = tf.paragraphs[0]

                    for i, bullet in enumerate(bullets):
                        p = first_bullet_target if (i == 0 and first_bullet_target is not None) else tf.add_paragraph()
                        p.alignment = PP_ALIGN.LEFT
                        p.space_after = Pt(14)
                        p.line_spacing = 1.1
                        run = p.add_run()
                        run.text = f"•  {bullet}"
                        run.font.size = Pt(current_size)
                        br, bg, bb = hex_to_rgb(b_color)
                        run.font.color.rgb = RGBColor(br, bg, bb)
                        run.font.bold = False

                    total_chars = sum(len(b) for b in bullets)
                    estimated_height = (title_allowance + len(bullets) * (current_size * 1.5)
                                         + total_chars * current_size * 0.012) / 72
                    if estimated_height <= 6.2:
                        break
                    current_size -= 3

            # ── Church-template parsing (existing behaviour, bug-fixed) ─────
            def process_church_pdf(lines, header_color, body_color, header_size, body_size, text_case):
                is_prayer_start = lambda line: bool(
                    re.match(r"^\(?\d+\)?[\.\s]", line) or re.match(r"^Prayer Point\s*\d+", line, re.I)
                )

                prayers = []
                current = ""
                for line in lines:
                    if any(m in line.lower() for m in
                           ["charity no", "dunamis centre", "northmoor", "manchester m12", "info@", "+44", "prayer session"]):
                        continue
                    if re.match(r"^P\s*a\s*g\s*e\s*\d+", line, re.I) or line.strip() == "Dunamis Bible Church" or "PRAYER POINTS" in line:
                        continue
                    if any(x in line for x in ["IJN=", "ITNJ=", "ITMNJ=", "ITNJCN=", "(KJV)"]):
                        continue
                    if not current and not is_prayer_start(line):
                        continue

                    if is_prayer_start(line):
                        if current:
                            prayers.append(current.strip())
                        current = line
                    elif current:
                        current += " " + line
                if current:
                    prayers.append(current.strip())

                point_counter = 0
                for prayer in prayers:
                    point_counter += 1
                    m = re.match(r"^(?:Prayer Point\s*)?\(?(\d+)\)?[\.\s]*(.*)", prayer, re.DOTALL | re.I)
                    # Fall back to a running counter instead of silently dropping
                    # any prayer whose text doesn't match the expected pattern.
                    if m and m.group(1):
                        num, text_content = m.group(1), m.group(2)
                    else:
                        num, text_content = str(point_counter), prayer

                    text_content = clean_text_block(text_content)
                    if not text_content:
                        continue
                    text_content = apply_case(text_case, text_content)

                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    add_fluid_text_slide(slide, f"Prayer Point {num}", text_content, body_size, header_size, header_color, body_color)

            # ── General-document parsing ─────────────────────────────────────
            NOISE_LINE_RE = re.compile(r"^(page\s*\d+(\s*(of|\|)\s*\d+)?|\d{1,3})$", re.I)
            BULLET_RE = re.compile(r"^\s*(?:[-•*▪◦‣]|\(?\d+\)?[\.\)]|\(?[a-zA-Z]\)?[\.\)])\s+")

            def is_noise_line(line):
                return bool(NOISE_LINE_RE.match(line.strip()))

            def get_body_font_size(doc):
                counter = Counter()
                for page in doc:
                    d = page.get_text("dict")
                    for block in d.get("blocks", []):
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                size = round(span["size"], 1)
                                counter[size] += max(len(span["text"]), 1)
                if not counter:
                    return 11.0
                return counter.most_common(1)[0][0]

            def extract_sections(doc):
                body_size_pt = get_body_font_size(doc)
                sections = []
                current = {"title": None, "lines": []}

                for page in doc:
                    d = page.get_text("dict")
                    for block in d.get("blocks", []):
                        for line in block.get("lines", []):
                            spans = line.get("spans", [])
                            if not spans:
                                continue
                            line_text = "".join(s["text"] for s in spans).strip()
                            if not line_text or is_noise_line(line_text):
                                continue

                            max_size = max(s["size"] for s in spans)
                            is_bold = any(s["flags"] & 16 for s in spans)
                            is_heading = (
                                len(line_text) <= 90
                                and not BULLET_RE.match(line_text)
                                and (max_size >= body_size_pt * 1.15 or (is_bold and max_size >= body_size_pt * 0.98))
                            )

                            if is_heading:
                                if current["title"] or current["lines"]:
                                    sections.append(current)
                                current = {"title": line_text, "lines": []}
                            else:
                                current["lines"].append(line_text)

                if current["title"] or current["lines"]:
                    sections.append(current)
                return sections

            def chunk_text(text, max_chars):
                if len(text) <= max_chars:
                    return [text]
                sentences = re.split(r"(?<=[.!?])\s+", text)
                chunks, cur = [], ""
                for s in sentences:
                    if cur and len(cur) + len(s) + 1 > max_chars:
                        chunks.append(cur.strip())
                        cur = s
                    else:
                        cur = (cur + " " + s).strip()
                if cur:
                    chunks.append(cur.strip())
                return chunks

            def split_section_slides(section, max_chars_per_slide=550):
                title = section["title"]
                lines = section["lines"]
                if not lines:
                    return [{"title": title, "type": "paragraph", "content": ""}] if title else []

                bullet_lines = [l for l in lines if BULLET_RE.match(l)]
                is_bullet_section = len(bullet_lines) >= max(2, len(lines) * 0.5)

                slides = []
                if is_bullet_section:
                    items, cur = [], None
                    for l in lines:
                        if BULLET_RE.match(l):
                            if cur:
                                items.append(cur.strip())
                            cur = BULLET_RE.sub("", l)
                        elif cur is not None:
                            cur += " " + l
                    if cur:
                        items.append(cur.strip())

                    avg_len = sum(len(i) for i in items) / max(len(items), 1)
                    if avg_len <= 140:
                        chunk, chunk_len = [], 0
                        for item in items:
                            if chunk and chunk_len + len(item) > max_chars_per_slide:
                                slides.append({"title": title, "type": "bullets", "content": chunk})
                                chunk, chunk_len = [], 0
                            chunk.append(item)
                            chunk_len += len(item)
                        if chunk:
                            slides.append({"title": title, "type": "bullets", "content": chunk})
                    else:
                        for item in items:
                            slides.append({"title": title, "type": "paragraph", "content": item})
                else:
                    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
                    for chunk in chunk_text(text, max_chars_per_slide):
                        slides.append({"title": title, "type": "paragraph", "content": chunk})
                return slides

            def process_general_pdf(doc, header_color, body_color, header_size, body_size, text_case):
                sections = extract_sections(doc)
                if not sections:
                    full_text = "".join(p.get_text("text") for p in doc)
                    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]
                    sections = [{"title": None, "lines": [p]} for p in paragraphs]

                for section in sections:
                    for payload in split_section_slides(section):
                        title = apply_case(text_case, payload["title"])
                        slide = prs.slides.add_slide(prs.slide_layouts[6])
                        set_bg(slide)

                        if payload["type"] == "bullets":
                            bullets = [apply_case(text_case, b) for b in payload["content"]]
                            add_bullet_slide(slide, title, bullets, header_size, body_size, header_color, body_color)
                        else:
                            body_text = apply_case(text_case, payload["content"])
                            if not body_text:
                                continue
                            add_fluid_text_slide(slide, title, body_text, body_size, header_size, header_color, body_color)

            # ── Main per-file loop ────────────────────────────────────────────
            skipped = []
            for idx, file in enumerate(st.session_state.uploaded_files):
                try:
                    doc = fitz.open(stream=file.getvalue(), filetype="pdf")
                    text = "".join(page.get_text("text") for page in doc)

                    if not text.strip():
                        skipped.append(f"{file.name} (no extractable text — likely a scanned PDF)")
                        continue

                    if doc_type_choice == "Church Prayer Points":
                        file_mode = "church"
                    elif doc_type_choice == "General Document":
                        file_mode = "general"
                    else:
                        file_mode = "church" if is_church_template(text) else "general"

                    title = derive_title(file.name, text)

                    if idx > 0:
                        slide = prs.slides.add_slide(prs.slide_layouts[6])
                        set_bg(slide)
                        divider_label = "Next Session" if file_mode == "church" else "Next Document"
                        add_cover_centered(slide, 0.8, 2.8, 11.7, 2.0, f"--- {divider_label} ---\n{title}", 56, header_color, True)

                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    if file_mode == "church":
                        add_cover_centered(slide, 0.8, 1.2, 11.7, 1.8, "Dunamis Bible Church", 56, header_color, True)
                        add_cover_centered(slide, 1.2, 4.8, 11.0, 1.2, "PRAYER POINTS", 50, "#CCCCCC")
                    else:
                        add_cover_centered(slide, 0.8, 2.8, 11.7, 2.0, title, 56, header_color, True)

                    if file_mode == "church":
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        process_church_pdf(lines, header_color, body_color, header_size, body_size, text_case)
                    else:
                        process_general_pdf(doc, header_color, body_color, header_size, body_size, text_case)

                except Exception as e:
                    skipped.append(f"{file.name} (error: {e})")
                    continue

            bio = BytesIO()
            prs.save(bio)
            bio.seek(0)

            st.success(f"✅ Generated {len(prs.slides)} slides!")
            if skipped:
                st.warning("Skipped:\n" + "\n".join(f"- {s}" for s in skipped))

            st.download_button(
                label="⬇ Download PPTX",
                data=bio,
                file_name="Dunamis_Prayer_Points.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True
            )
