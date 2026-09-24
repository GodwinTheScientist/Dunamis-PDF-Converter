import streamlit as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import fitz  # PyMuPDF
import re
from io import BytesIO
from collections import Counter
import zipfile

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
    .block-container {{
        max-width: 700px !important;
        margin: 0 auto !important;
        padding: 0 20px !important;
    }}
    .section-heading {{
        color: #FFD700;
        font-size: 1.1rem;
        font-weight: 700;
        margin: 34px 0 10px 0;
    }}
    /* Cards: st.container(border=True) and st.expander both render as real
       nested Streamlit containers (unlike raw HTML divs split across separate
       st.markdown calls, which don't actually wrap anything placed between
       them). Styling these testids gives every step the same glass-card look.
       Note: internal testids can change between Streamlit versions - if this
       doesn't pick up styling after an upgrade, re-check via browser devtools. */
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] {{
        background: rgba(255,255,255,0.08) !important;
        backdrop-filter: blur(16px) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
    }}
    [data-testid="stExpander"] summary {{
        color: #FFD700 !important;
        font-weight: 600 !important;
    }}
    .stats-strip {{
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 22px;
        padding: 4px 0 2px 0;
        color: #CBD5E1;
        font-size: 0.95rem;
    }}
    .stats-strip b {{
        color: #FFD700;
    }}
    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {{
        background: linear-gradient(135deg, #FFD700, #E8B923) !important;
        color: #14172B !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 14px !important;
        font-size: 1.05rem !important;
        margin-top: 6px !important;
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


SCRIPTURE_REF_RE = re.compile(
    r"^\(?(?:[1-3]\s)?[A-Za-z]+(?:\s[A-Za-z]+){0,2}\.?\s+\d{1,3}:\d{1,3}(?:-\d{1,3})?\)?\.?"
    r"\s*(?:\([A-Za-z]{2,6}\))?$"
)


def looks_like_scripture_ref(line):
    """True for standalone Bible-reference lines like '2 Corinthians 5:17' or
    'John 3:16 (NIV)' - these share a 'digit + space + word' shape with the
    template's own '1 Give thanks for...' numbering, but a scripture reference
    is short and centers on a chapter:verse pattern, which a real prayer line
    never has. Used to stop such lines from being misread as a new prayer
    point boundary."""
    line = line.strip()
    return len(line) <= 60 and bool(SCRIPTURE_REF_RE.match(line))


def safe_filename(name):
    name = re.sub(r"[^\w\-]+", "_", name).strip("_")
    return name or "presentation"


CHURCH_NOISE_SUBSTRINGS = [
    "charity no", "dunamis centre", "northmoor", "manchester m12",
    "info@", "+44", "prayer session", "(aka",
]

# Catches header lines like "Friday 18th September 2026" wherever they sit in
# a line (e.g. "(AKA Dunamis Ministries) SOS Friday 18th September 2026") -
# matched generally on the day-of-week + ordinal date + month + year shape, so
# next week's date is caught automatically without hardcoding this one.
DAY_DATE_RE = re.compile(
    r"\b(?:Mon|Tue(?:s)?|Wed(?:nes)?|Thu(?:rs)?|Fri|Sat|Sun)(?:day)?\s+\d{1,2}(?:st|nd|rd|th)?\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep(?:t)?|Oct|Nov|Dec)\w*\s+\d{4}\b",
    re.I,
)


def is_church_noise_line(line):
    """True for church letterhead/boilerplate lines - address, charity number,
    contact details, session-date stamps, alias tags - that should never end
    up on a slide, in either the passage or the prayer points."""
    stripped = line.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    if any(m in lower for m in CHURCH_NOISE_SUBSTRINGS):
        return True
    if re.match(r"^P\s*a\s*g\s*e\s*\d+", stripped, re.I) or stripped == "Dunamis Bible Church":
        return True
    if any(x in stripped for x in ["IJN=", "ITNJ=", "ITMNJ=", "ITNJCN="]):
        return True
    if DAY_DATE_RE.search(stripped):
        return True
    return False


def extract_passage(lines):
    """Pull a reference (e.g. '2 Thessalonians 2:3') and the passage body text
    out of the preamble lines that sit above a template's 'PRAYER POINTS'
    heading. The reference is usually its own short line; everything else
    that isn't known noise is treated as the passage body."""
    reference = None
    body_lines = []
    for line in lines:
        stripped = line.strip()
        if is_church_noise_line(stripped):
            continue
        if looks_like_scripture_ref(stripped):
            reference = stripped
            continue
        body_lines.append(stripped)
    body_text = " ".join(body_lines).strip()
    return reference, body_text


VERSE_NUM_RE = re.compile(r"(?:^|[:.]\s+)(\d{1,3})(?=[\.\s])")


def find_point_list_start(lines, uses_explicit_label):
    """Locate where the real numbered prayer list begins, for documents with
    no literal 'PRAYER POINTS' heading to anchor on. A quoted Bible passage's
    own inline verse numbers (1, 2, 3...) look identical to bare prayer-point
    numbering - but verse numbers only ever increase within a passage, so the
    first place the numbering resets back down is the clearest sign the real
    list has begun. Falls back to the first numbered line found if no reset
    is ever seen, which correctly handles both 'no passage present' and 'a
    single, unnumbered verse' - cases where the first number really is point 1."""
    if uses_explicit_label:
        for i, line in enumerate(lines):
            if re.match(r"^Prayer Point\s*1\b", line, re.I) and not looks_like_scripture_ref(line):
                return i
        return None

    last_num = 0
    first_leading_idx = None
    for i, line in enumerate(lines):
        if looks_like_scripture_ref(line):
            continue
        if first_leading_idx is None and re.match(r"^\(?\d+\)?[\.\s]", line):
            first_leading_idx = i
        for n in (int(n) for n in VERSE_NUM_RE.findall(line)):
            if last_num > 0 and n <= last_num:
                return i
            last_num = max(last_num, n)
    return first_leading_idx


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

# ── Step 1: Upload ────────────────────────────────────────────────────────────
st.markdown('<p class="section-heading">📁 1. Upload your PDFs</p>', unsafe_allow_html=True)
with st.container(border=True):
    doc_type_choice = st.selectbox(
        "Document type",
        ["Auto-detect", "Church Prayer Points", "General Document"],
        help="Auto-detect looks for the church template's own markers (e.g. 'Prayer Point'). "
             "Anything else is treated as a general document and split by headings/paragraphs instead."
    )

    uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files

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

# Slim stats strip - only takes up space once there's something to report.
if st.session_state.get('uploaded_files'):
    st.markdown(
        f"<div class='stats-strip'>"
        f"📄 <b>{len(st.session_state.uploaded_files)}</b> PDFs&nbsp;&nbsp;•&nbsp;&nbsp;"
        f"🙏 <b>{st.session_state.total_prayers_count}</b> prayers&nbsp;&nbsp;•&nbsp;&nbsp;"
        f"📚 <b>{st.session_state.total_sessions_count}</b> sessions"
        f"</div>",
        unsafe_allow_html=True
    )

# ── Step 2: Customize (optional, collapsed by default) ───────────────────────
with st.expander("🎨 2. Customize appearance (optional)", expanded=False):
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

# ── Step 3: Generate ──────────────────────────────────────────────────────────
st.markdown('<p class="section-heading">🚀 3. Generate your presentation</p>', unsafe_allow_html=True)


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
if st.button("Generate & Download PPTX", key="generate", use_container_width=True):
    if 'uploaded_files' not in st.session_state or not st.session_state.uploaded_files:
        st.error("Upload PDFs first.")
    else:
        with st.spinner("Processing Presentation Slides..."):
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

            # ── Bible Passage slide: title, italic reference, then body ─────
            def add_passage_slide(slide, reference, body_text, header_size, max_b_size, header_color, body_color,
                                   title_text="Bible Passage", min_size=28):
                left = Inches(0.8)
                top = Inches(0.5)
                width = Inches(11.733)
                height = Inches(6.5)

                tb = slide.shapes.add_textbox(left, top, width, height)
                tf = tb.text_frame
                tf.word_wrap = True
                tf.margin_top = Inches(0)
                tf.margin_bottom = Inches(0)
                tf.margin_left = Inches(0)
                tf.margin_right = Inches(0)

                title_size = min(int(header_size * 0.6), 36)
                ref_size = max(min(int(header_size * 0.35), 24), 16)
                current_size = max_b_size
                char_len = len(body_text)

                if char_len > 300:
                    current_size = min(current_size, 38)
                elif char_len > 180:
                    current_size = min(current_size, 46)

                while current_size >= min_size:
                    tf.clear()

                    p_title = tf.paragraphs[0]
                    p_title.alignment = PP_ALIGN.CENTER
                    p_title.space_after = Pt(2)
                    run_title = p_title.add_run()
                    run_title.text = title_text
                    run_title.font.size = Pt(title_size)
                    r, g, b = hex_to_rgb(header_color)
                    run_title.font.color.rgb = RGBColor(r, g, b)
                    run_title.font.bold = True

                    ref_allowance = 0
                    if reference:
                        p_ref = tf.add_paragraph()
                        p_ref.alignment = PP_ALIGN.CENTER
                        p_ref.space_after = Pt(14)
                        run_ref = p_ref.add_run()
                        run_ref.text = reference
                        run_ref.font.size = Pt(ref_size)
                        run_ref.font.color.rgb = RGBColor(r, g, b)
                        run_ref.font.italic = True
                        run_ref.font.bold = False
                        ref_allowance = ref_size + 14

                    p_body = tf.add_paragraph()
                    p_body.alignment = PP_ALIGN.CENTER
                    p_body.line_spacing = 1.15
                    run_body = p_body.add_run()
                    run_body.text = body_text
                    run_body.font.size = Pt(current_size)
                    br, bg, bb = hex_to_rgb(body_color)
                    run_body.font.color.rgb = RGBColor(br, bg, bb)
                    run_body.font.bold = True

                    title_allowance = title_size + 2 + ref_allowance
                    estimated_lines = (char_len * (current_size * 0.55)) / (11.733 * 72)
                    estimated_height = (title_allowance + (estimated_lines * current_size * 1.2)) / 72

                    if estimated_height <= 6.3:
                        break
                    current_size -= 4

            # ── Split a passage into slide-sized pages instead of shrinking ──
            # its font indefinitely: pack sentences onto a page as long as the
            # page would still fit at min_size or larger; once it wouldn't,
            # start a new page. add_passage_slide then picks the best size for
            # each page (up to max_b_size), so short pages render large and
            # only genuinely long passages spill onto a second slide.
            def paginate_passage(body_text, header_size, max_b_size, has_reference, min_size=28):
                title_size = min(int(header_size * 0.6), 36)
                ref_size = max(min(int(header_size * 0.35), 24), 16)
                ref_allowance = (ref_size + 14) if has_reference else 0
                title_allowance = title_size + 2 + ref_allowance

                def fits_at_min(char_len):
                    estimated_lines = (char_len * (min_size * 0.55)) / (11.733 * 72)
                    estimated_height = (title_allowance + estimated_lines * min_size * 1.2) / 72
                    return estimated_height <= 6.3

                sentences = re.split(r"(?<=[.!?])\s+", body_text)
                pages, current = [], ""
                for sentence in sentences:
                    candidate = (current + " " + sentence).strip() if current else sentence
                    if current and not fits_at_min(len(candidate)):
                        pages.append(current.strip())
                        current = sentence
                    else:
                        current = candidate
                if current:
                    pages.append(current.strip())
                return pages if pages else [body_text]

            # ── Church-template parsing (existing behaviour, bug-fixed) ─────
            def process_church_pdf(prs, lines, header_color, body_color, header_size, body_size, text_case):
                # If the document explicitly labels points as "Prayer Point N"
                # anywhere, that's a reliable signal - a quoted Bible passage
                # almost always carries its own inline verse numbers (1, 2,
                # 3...) which are indistinguishable from bare "1."/"2."
                # numbering and would otherwise get mistaken for the list.
                uses_explicit_label = any(re.match(r"^Prayer Point\s*\d+", l, re.I) for l in lines)

                def is_prayer_start(line):
                    if uses_explicit_label:
                        looks_numbered = bool(re.match(r"^Prayer Point\s*\d+", line, re.I))
                    else:
                        looks_numbered = bool(
                            re.match(r"^\(?\d+\)?[\.\s]", line) or re.match(r"^Prayer Point\s*\d+", line, re.I)
                        )
                    return looks_numbered and not looks_like_scripture_ref(line)

                # The template's own PDFs sometimes carry a literal "PRAYER
                # POINTS" heading marking exactly where the passage-of-the-week
                # ends and the real list begins - when present, that's the
                # most reliable anchor. Use the LAST such heading, in case the
                # passage text itself happens to mention the phrase.
                heading_idx = None
                for i, line in enumerate(lines):
                    if "PRAYER POINTS" in line.upper():
                        heading_idx = i

                if heading_idx is not None:
                    start_idx = heading_idx + 1
                else:
                    # No literal heading - fall back to detecting where the
                    # numbering resets, since a passage's own inline verse
                    # numbers only ever increase (see find_point_list_start).
                    start_idx = find_point_list_start(lines, uses_explicit_label)

                # If neither signal is found, treat the whole document as
                # points (no passage to extract) rather than producing nothing.
                preamble_end = heading_idx if heading_idx is not None else start_idx
                preamble_lines = lines[:preamble_end] if preamble_end is not None else []
                point_lines = lines[start_idx:] if start_idx is not None else lines

                # ── Bible Passage slide, built from what used to be discarded ──
                reference, passage_body = extract_passage(preamble_lines)
                if passage_body:
                    ref_display = apply_case(text_case, reference) if reference else None
                    body_display = apply_case(text_case, passage_body)
                    passage_pages = paginate_passage(body_display, header_size, body_size, bool(ref_display))
                    for page_idx, page_text in enumerate(passage_pages):
                        slide = prs.slides.add_slide(prs.slide_layouts[6])
                        set_bg(slide)
                        page_title = "Bible Passage" if page_idx == 0 else "Bible Passage (cont'd)"
                        add_passage_slide(slide, ref_display, page_text, header_size, body_size, header_color, body_color,
                                           title_text=page_title)

                # ── "Prayer Points" section divider ─────────────────────────
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                set_bg(slide)
                add_cover_centered(slide, 1.2, 3.1, 11.0, 1.3, "PRAYER POINTS", 60, header_color, True)

                prayers = []
                current = ""
                for line in point_lines:
                    if is_church_noise_line(line) or "PRAYER POINTS" in line.upper():
                        continue
                    if any(x in line for x in ["(KJV)"]):
                        continue
                    if looks_like_scripture_ref(line):
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

            def process_general_pdf(prs, doc, header_color, body_color, header_size, body_size, text_case):
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

            # ── Main per-file loop - one separate deck per PDF ────────────────
            skipped = []
            generated_decks = []  # (title, out_filename, pptx_bytes, slide_count)
            used_names = set()

            for file in st.session_state.uploaded_files:
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

                    prs = Presentation()
                    prs.slide_width = Inches(13.333)
                    prs.slide_height = Inches(7.5)

                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    set_bg(slide)
                    if file_mode == "church":
                        add_cover_centered(slide, 0.8, 2.8, 11.7, 2.0, "Dunamis Bible Church", 56, header_color, True)
                    else:
                        add_cover_centered(slide, 0.8, 2.8, 11.7, 2.0, title, 56, header_color, True)

                    if file_mode == "church":
                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        process_church_pdf(prs, lines, header_color, body_color, header_size, body_size, text_case)
                    else:
                        process_general_pdf(prs, doc, header_color, body_color, header_size, body_size, text_case)

                    if len(prs.slides) <= 1:
                        skipped.append(f"{file.name} (no content could be extracted into slides)")
                        continue

                    deck_bytes = BytesIO()
                    prs.save(deck_bytes)
                    deck_bytes.seek(0)

                    base_name = safe_filename(title)
                    out_name = f"{base_name}.pptx"
                    n = 2
                    while out_name in used_names:
                        out_name = f"{base_name}_{n}.pptx"
                        n += 1
                    used_names.add(out_name)

                    generated_decks.append((title, out_name, deck_bytes.getvalue(), len(prs.slides)))

                except Exception as e:
                    skipped.append(f"{file.name} (error: {e})")
                    continue

            if not generated_decks:
                st.error("No slides could be generated from the uploaded file(s).")
            elif len(generated_decks) == 1:
                title, out_name, data, slide_count = generated_decks[0]
                st.success(f"✅ Generated {slide_count} slides!")
                st.download_button(
                    label="⬇ Download PPTX",
                    data=data,
                    file_name=out_name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            else:
                total_slides = sum(d[3] for d in generated_decks)
                st.success(f"✅ Generated {len(generated_decks)} separate presentations ({total_slides} slides total)!")

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for _, out_name, data, _ in generated_decks:
                        zf.writestr(out_name, data)
                zip_buffer.seek(0)

                st.download_button(
                    label="⬇ Download all as ZIP",
                    data=zip_buffer,
                    file_name="Dunamis_Prayer_Points_Batch.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                with st.expander("Or download each presentation separately"):
                    for title, out_name, data, slide_count in generated_decks:
                        st.download_button(
                            label=f"⬇ {title} ({slide_count} slides)",
                            data=data,
                            file_name=out_name,
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            key=f"dl_{out_name}",
                            use_container_width=True
                        )

            if skipped:
                st.warning("Skipped:\n" + "\n".join(f"- {s}" for s in skipped))
