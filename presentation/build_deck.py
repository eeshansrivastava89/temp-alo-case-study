from __future__ import annotations

from pathlib import Path

import qrcode
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "presentation"
ASSET_DIR = OUT_DIR / "assets"
OUT_PATH = OUT_DIR / "ALO_AI_Business_Analyst_Case_Study.pptx"

APP_URL = "https://temp-alo-case-study-clyugcdbazahif33twk2ss.streamlit.app/"
REPO_URL = "https://github.com/eeshansrivastava89/temp-alo-case-study"
VIDEO_URL = f"{REPO_URL}/blob/main/demo/alo_business_analyst_demo.mp4"

NAVY = "112B3C"
BLUE = "2F6690"
SKY = "DCEAF4"
TEAL = "2A7F72"
GREEN = "1E8E5A"
GREEN_LIGHT = "E8F4EE"
RED = "C74646"
RED_LIGHT = "F8EAEA"
INK = "17212B"
MID = "5F6B75"
LIGHT = "EEF2F5"
LINE = "D6DDE2"
WHITE = "FFFFFF"
BLACK = "000000"
AMBER = "D89432"

SLIDE_W = 13.333
SLIDE_H = 7.5
FONT = "Arial"


def rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color)


def set_fill(shape, color: str) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)


def set_line(shape, color: str | None = None, width: float = 0.8) -> None:
    if color is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = rgb(color)
        shape.line.width = Pt(width)


def add_rect(slide, x, y, w, h, fill=WHITE, line=None, radius=False):
    kind = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    set_fill(shape, fill)
    set_line(shape, line)
    if radius:
        shape.adjustments[0] = 0.08
    return shape


def add_text(
    slide,
    text,
    x,
    y,
    w,
    h,
    *,
    size=12,
    color=INK,
    bold=False,
    font=FONT,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    margin=0,
    line_spacing=1.0,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line_spacing
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)
    return box


def add_rich_text(slide, segments, x, y, w, h, *, size=12, valign=MSO_ANCHOR.TOP, margin=0, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    for segment in segments:
        run = p.add_run()
        run.text = segment["text"]
        run.font.name = FONT
        run.font.size = Pt(segment.get("size", size))
        run.font.bold = segment.get("bold", False)
        run.font.color.rgb = rgb(segment.get("color", INK))
        if segment.get("url"):
            run.hyperlink.address = segment["url"]
            run.font.underline = True
    return box


def add_title(slide, title: str, number: int, kicker: str | None = None) -> None:
    add_rect(slide, 0, 0, SLIDE_W, 0.08, fill=TEAL)
    if kicker:
        add_text(slide, kicker.upper(), 0.55, 0.25, 8.5, 0.22, size=8.5, color=TEAL, bold=True)
    add_text(slide, title, 0.55, 0.52 if kicker else 0.34, 12.0, 0.72, size=25, color=NAVY, bold=True)
    add_text(slide, f"{number:02d}", 12.35, 0.30, 0.42, 0.25, size=9, color=MID, bold=True, align=PP_ALIGN.RIGHT)


def add_footer(slide, source: str, number: int) -> None:
    y = 7.19
    add_rect(slide, 0.55, y, 12.22, 0.012, fill=LINE)
    add_text(slide, source, 0.55, y + 0.06, 10.8, 0.18, size=7, color=MID)
    add_text(slide, f"AI Business Analyst case study  |  {number}/5", 11.35, y + 0.06, 1.42, 0.18, size=7, color=MID, align=PP_ALIGN.RIGHT)


def add_notes(slide, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = text


def add_chevron(slide, x, y, w=0.28, h=0.30, color=TEAL):
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.CHEVRON, Inches(x), Inches(y), Inches(w), Inches(h))
    set_fill(shape, color)
    set_line(shape, None)
    return shape


def add_stat(slide, x, y, w, value, label, accent=TEAL):
    add_rect(slide, x, y, w, 0.92, fill=WHITE, line=LINE, radius=True)
    add_rect(slide, x, y, 0.08, 0.92, fill=accent)
    add_text(slide, value, x + 0.22, y + 0.13, w - 0.3, 0.34, size=20, color=NAVY, bold=True)
    add_text(slide, label, x + 0.22, y + 0.53, w - 0.3, 0.22, size=8.5, color=MID)


def add_qr(url: str, name: str) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSET_DIR / name
    qr = qrcode.QRCode(version=4, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color=f"#{NAVY}", back_color=f"#{WHITE}").save(path)
    return path


def slide_1(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(WHITE)
    add_title(
        slide,
        "Governed AI turns fragmented Digital + Retail extracts into decision-ready answers—without letting the model invent the numbers",
        1,
        "Executive summary",
    )
    add_text(
        slide,
        "A four-hour prototype focused on the leadership job to be done: understand performance, isolate drivers, decide where to act, and know what must be validated first.",
        0.55,
        1.28,
        11.8,
        0.48,
        size=12.5,
        color=MID,
    )

    add_stat(slide, 0.55, 1.88, 3.85, "293K", "source rows ingested from four workbooks", BLUE)
    add_stat(slide, 4.74, 1.88, 3.85, "5", "governed analytical tools; no arbitrary SQL", TEAL)
    add_stat(slide, 8.92, 1.88, 3.85, "15", "automated contract and presentation tests", GREEN)

    sections = [
        (
            "The problem",
            "Executives receive separate commerce, GA, store, and category extracts with inconsistent grains and definitions.",
            "A generic chatbot would amplify ambiguity rather than resolve it.",
        ),
        (
            "The design choice",
            "Python and SQL calculate every figure; the model chooses validated tools, synthesizes findings, and links each claim to evidence.",
            "Source ownership and blocked metrics are explicit—not hidden fallbacks.",
        ),
        (
            "The outcome",
            "A deployed analyst answers follow-ups with precise periods, TY/LY labels, exhibits, methods, and practical next actions.",
            "The same semantic contract powers an executive dashboard and auditable notebook.",
        ),
    ]
    xs = [0.55, 4.74, 8.92]
    for x, (heading, body, second) in zip(xs, sections, strict=True):
        add_text(slide, heading.upper(), x, 3.08, 3.85, 0.25, size=9, color=TEAL, bold=True)
        add_text(slide, body, x, 3.43, 3.72, 1.02, size=13.2, color=INK, bold=True)
        add_text(slide, second, x, 4.62, 3.72, 0.82, size=10.5, color=MID)

    add_rect(slide, 0.55, 5.82, 12.22, 0.90, fill=NAVY, radius=True)
    add_text(slide, "DESIGN THESIS", 0.82, 6.03, 1.45, 0.22, size=8.5, color="86C8BD", bold=True)
    add_text(
        slide,
        "Govern the calculations and evidence; preserve model freedom in tool selection and executive synthesis.",
        2.25,
        5.99,
        9.95,
        0.35,
        size=15,
        color=WHITE,
        bold=True,
    )
    add_footer(slide, "Source: case-study brief; application repository and validation suite", 1)
    add_notes(
        slide,
        "Open with the core choice: this is not text-to-SQL. The LLM never owns the numbers. Four workbooks and 293K rows were converted into a governed semantic layer; five tools answer executive questions, while the model selects evidence and writes the brief. Emphasize that the prototype is deployed and tested, not just a notebook.",
    )


def slide_2(prs: Presentation, qr_path: Path) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(WHITE)
    add_title(
        slide,
        "An executive asks one question; the agent returns a quantified answer, matched evidence, and a decision—not raw model reasoning",
        2,
        "Product experience + demo",
    )

    # Product frame
    add_rect(slide, 0.55, 1.28, 8.55, 5.55, fill="0E141A", line="27333D", radius=True)
    add_text(slide, "AI BUSINESS ANALYST", 0.83, 1.52, 2.2, 0.20, size=8, color="8B99A5", bold=True)
    add_rect(slide, 0.82, 1.85, 7.98, 0.58, fill="1B232C", line="303A44", radius=True)
    add_text(slide, "What drove Store Revenue last week, and where should we act?", 1.02, 2.02, 7.55, 0.22, size=11, color=WHITE, bold=True)

    add_text(slide, "2026-06-22 to 2026-06-28  |  vs. 2026-06-15 to 2026-06-21", 0.85, 2.62, 7.7, 0.20, size=7.5, color="98A5AF")
    add_text(slide, "Store Revenue fell $132K (0.9%) as conversion outweighed traffic and AOV gains.", 0.85, 2.93, 7.78, 0.50, size=15, color=WHITE, bold=True)

    add_rect(slide, 0.85, 3.56, 7.72, 0.82, fill="141D24", line="2A343D", radius=True)
    add_text(slide, "1", 1.05, 3.78, 0.25, 0.25, size=11, color="86C8BD", bold=True)
    add_rich_text(
        slide,
        [
            {"text": "Store Conversion Rate contributed ", "color": WHITE, "size": 10.5},
            {"text": "−$472K", "color": "FF7777", "size": 10.5, "bold": True},
            {"text": "; AOV and Traffic offset ", "color": WHITE, "size": 10.5},
            {"text": "+$339K", "color": "6FD09D", "size": 10.5, "bold": True},
            {"text": ".", "color": WHITE, "size": 10.5},
        ],
        1.37,
        3.77,
        6.88,
        0.28,
    )
    # mini contribution bars
    center = 4.15
    add_rect(slide, center, 4.52, 0.015, 0.84, fill="65717B")
    contributions = [("Conversion", -472, RED), ("AOV", 286, GREEN), ("Traffic", 53, GREEN)]
    ys = [4.55, 4.85, 5.15]
    scale = 0.0054
    for (label, value, color), y in zip(contributions, ys, strict=True):
        add_text(slide, label, 1.02, y - 0.02, 1.0, 0.17, size=7.5, color="AAB4BC")
        width = abs(value) * scale
        x = center - width if value < 0 else center
        add_rect(slide, x, y, width, 0.13, fill=color)
        add_text(slide, f"{'−' if value < 0 else '+'}${abs(value)}K", x - 0.70 if value < 0 else x + width + 0.07, y - 0.05, 0.65, 0.20, size=7.5, color=WHITE, bold=True, align=PP_ALIGN.RIGHT if value < 0 else PP_ALIGN.LEFT)

    add_rect(slide, 0.85, 5.63, 7.72, 0.78, fill="132A27", line="27534C", radius=True)
    add_text(slide, "ACTION", 1.05, 5.86, 0.60, 0.18, size=8, color="86C8BD", bold=True)
    add_text(slide, "Validate local demand and operations at the ten stores driving $311K of gross Store Revenue decline.", 1.72, 5.79, 6.55, 0.34, size=10.2, color=WHITE, bold=True)
    add_text(slide, "Each finding is linked to a validated tool result; methods and source files remain inspectable.", 0.86, 6.55, 7.55, 0.18, size=7.5, color="8B99A5")

    # Demo panel
    add_rect(slide, 9.40, 1.28, 3.37, 5.55, fill=LIGHT, line=LINE, radius=True)
    add_text(slide, "DEMO PATH", 9.72, 1.58, 1.35, 0.22, size=9, color=TEAL, bold=True)
    steps = [
        ("1", "Ask", "Natural-language question or follow-up"),
        ("2", "Verify", "Exact period, metric definition, and evidence"),
        ("3", "Act", "Recommendation plus material caveat"),
    ]
    for i, (num, head, detail) in enumerate(steps):
        y = 2.02 + i * 0.76
        circle = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.OVAL, Inches(9.72), Inches(y), Inches(0.34), Inches(0.34))
        set_fill(circle, NAVY)
        set_line(circle, None)
        add_text(slide, num, 9.72, y + 0.055, 0.34, 0.18, size=8, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_text(slide, head, 10.18, y - 0.01, 0.80, 0.20, size=10.5, color=NAVY, bold=True)
        add_text(slide, detail, 10.18, y + 0.24, 2.17, 0.31, size=8.2, color=MID)

    slide.shapes.add_picture(str(qr_path), Inches(9.72), Inches(4.38), Inches(1.23), Inches(1.23))
    add_text(slide, "LIVE APP", 11.16, 4.48, 1.12, 0.20, size=8, color=TEAL, bold=True)
    link_box = add_text(slide, "Open deployed prototype", 11.16, 4.76, 1.22, 0.48, size=9.2, color=BLUE, bold=True)
    link_box.text_frame.paragraphs[0].runs[0].hyperlink.address = APP_URL

    play = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(9.72), Inches(5.82), Inches(2.66), Inches(0.52))
    set_fill(play, NAVY)
    set_line(play, None)
    play.click_action.hyperlink.address = VIDEO_URL
    add_text(slide, "▶  OPEN DEMO VIDEO", 9.84, 5.98, 2.42, 0.18, size=8.5, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_rich_text(
        slide,
        [
            {"text": "App", "color": BLUE, "bold": True, "url": APP_URL},
            {"text": "   |   ", "color": MID},
            {"text": "GitHub", "color": BLUE, "bold": True, "url": REPO_URL},
            {"text": "   |   ", "color": MID},
            {"text": "Video", "color": BLUE, "bold": True, "url": VIDEO_URL},
        ],
        9.70,
        6.50,
        2.70,
        0.18,
        size=7.5,
        align=PP_ALIGN.CENTER,
    )
    add_footer(slide, "Prototype: Streamlit Community Cloud | Video fallback path: demo/alo_business_analyst_demo.mp4", 2)
    add_notes(
        slide,
        "Run a 45–60 second demo. Ask: ‘What drove Store Revenue last week, and where should we act?’ Then ask a follow-up such as ‘Which stores explain the decline?’ Point out the exact dates, evidence-linked exhibits, action, and collapsed methods. If the live demo is unavailable, click the demo-video button. Record the video into demo/alo_business_analyst_demo.mp4 before submission.",
    )


def slide_3(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(WHITE)
    add_title(
        slide,
        "A semantic layer—not the LLM—owns calculations, definitions, access, and traceability",
        3,
        "Solution architecture + AI workflow",
    )
    add_text(slide, "The model has analytical freedom inside a deliberately narrow, auditable execution boundary.", 0.55, 1.23, 11.8, 0.30, size=11.5, color=MID)

    nodes = [
        ("01", "Excel sources", "4 workbooks\n293K rows"),
        ("02", "Audit + contract", "grain, quality,\nownership"),
        ("03", "SQLite layer", "4 facts + date\nmetric views"),
        ("04", "Governed tools", "summary, drivers,\nrank, stores, forecast"),
        ("05", "LLM reasoning", "select tools;\nsynthesize"),
        ("06", "Executive UI", "finding ↔ evidence\naction + caveat"),
    ]
    x0, node_w, gap = 0.55, 1.82, 0.21
    for i, (num, head, detail) in enumerate(nodes):
        x = x0 + i * (node_w + gap)
        add_rect(slide, x, 1.83, node_w, 1.55, fill=WHITE, line=LINE, radius=True)
        add_text(slide, num, x + 0.18, 2.03, 0.35, 0.20, size=8, color=TEAL, bold=True)
        add_text(slide, head, x + 0.18, 2.36, node_w - 0.34, 0.28, size=11, color=NAVY, bold=True)
        add_text(slide, detail, x + 0.18, 2.76, node_w - 0.34, 0.45, size=8.2, color=MID)
        if i < len(nodes) - 1:
            add_chevron(slide, x + node_w + 0.025, 2.47, 0.16, 0.26)

    add_text(slide, "CONTROL POINTS", 0.55, 3.79, 2.2, 0.22, size=9, color=TEAL, bold=True)
    controls = [
        ("Metric ownership", "Commerce = Digital top line\nGA = labeled diagnostics\nStore = Retail KPIs"),
        ("Period contract", "Mon–Sun complete weeks\n63-day full window vs supplied LY\nNo invented LY dates"),
        ("Access boundary", "Read-only repository\nValidated dimensions\nNo generated SQL or Python"),
        ("Evidence contract", "Every figure comes from a tool\nFinding selects exact evidence\nNo chain-of-thought or raw JSON"),
    ]
    for i, (head, body) in enumerate(controls):
        x = 0.55 + i * 3.05
        add_rect(slide, x, 4.13, 2.77, 1.37, fill=LIGHT, line=None, radius=True)
        add_text(slide, head, x + 0.20, 4.36, 2.35, 0.22, size=10.5, color=NAVY, bold=True)
        add_text(slide, body, x + 0.20, 4.72, 2.35, 0.55, size=8.4, color=MID)

    add_rect(slide, 0.55, 5.84, 12.22, 0.78, fill=SKY, line=None, radius=True)
    add_text(slide, "PRODUCTION PATH", 0.78, 6.07, 1.45, 0.20, size=8.5, color=BLUE, bold=True)
    add_text(slide, "Replace SQLite with the enterprise warehouse; retain the repository, metric registry, tool contracts, tests, and evidence-linked response schema.", 2.23, 6.01, 10.1, 0.34, size=10.6, color=NAVY, bold=True)
    add_footer(slide, "Source: application architecture and semantic contract in repository", 3)
    add_notes(
        slide,
        "Walk left to right. Excel is ingested once; the audit established source ownership and blocked unsafe combinations. SQLite simulates a warehouse semantic layer. Five deterministic tools expose only governed analyses. DeepSeek selects tools but cannot query SQL directly. The final response is structured: each finding references an evidence index and a supported visual. In production, swap the repository connection for the warehouse without redesigning the agent.",
    )


def slide_4(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(WHITE)
    add_title(
        slide,
        "Store Revenue fell $132K WoW because conversion erased traffic and AOV gains; the risk is concentrated enough to act",
        4,
        "Business insight + recommendation",
    )
    add_text(slide, "Latest complete week: June 22–28, 2026 vs June 15–21, 2026 | Store source", 0.55, 1.22, 11.8, 0.24, size=9, color=MID)

    # Contribution chart
    add_text(slide, "STORE REVENUE CHANGE DECOMPOSITION", 0.55, 1.70, 5.9, 0.22, size=9, color=TEAL, bold=True)
    add_text(slide, "$K contribution to week-over-week Store Revenue change", 0.55, 1.98, 5.9, 0.20, size=8, color=MID)
    chart_x, chart_y, chart_w = 0.70, 2.45, 6.35
    center = chart_x + 3.55
    add_rect(slide, center, chart_y - 0.12, 0.014, 2.05, fill="89949D")
    rows = [("Conversion Rate", -472, RED), ("AOV", 286, GREEN), ("Traffic", 53, GREEN), ("Net change", -132, NAVY)]
    scale = 0.0062
    for i, (label, value, color) in enumerate(rows):
        y = chart_y + i * 0.48
        add_text(slide, label, chart_x, y - 0.01, 1.25, 0.20, size=9, color=INK, bold=(label == "Net change"))
        width = abs(value) * scale
        x = center - width if value < 0 else center
        add_rect(slide, x, y, width, 0.22, fill=color)
        label_x = x - 0.74 if value < 0 else x + width + 0.08
        add_text(slide, f"{'−' if value < 0 else '+'}${abs(value)}K", label_x, y + 0.01, 0.67, 0.18, size=8.5, color=color, bold=True, align=PP_ALIGN.RIGHT if value < 0 else PP_ALIGN.LEFT)
    add_text(slide, "−$472K + $286K + $53K = −$132K", 1.64, 4.49, 4.68, 0.28, size=11.5, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, "Shapley contributions reconcile to the observed Store Revenue change.", 1.52, 4.83, 5.0, 0.22, size=8, color=MID, align=PP_ALIGN.CENTER)

    # Concentration + actions
    add_rect(slide, 7.35, 1.70, 5.42, 3.68, fill=LIGHT, line=None, radius=True)
    add_text(slide, "THE DECLINE IS CONCENTRATED", 7.67, 1.98, 3.20, 0.22, size=9, color=TEAL, bold=True)
    add_rich_text(
        slide,
        [
            {"text": "10 stores", "size": 19, "bold": True, "color": NAVY},
            {"text": " generated ", "size": 11, "color": MID},
            {"text": "−$311K", "size": 19, "bold": True, "color": RED},
            {"text": " of gross decline", "size": 11, "color": MID},
        ],
        7.67,
        2.35,
        4.72,
        0.38,
    )
    add_text(slide, "Other stores offset +$179K, resulting in the −$132K portfolio decline.", 7.67, 2.83, 4.54, 0.33, size=9.5, color=MID)

    headers = ["Store", "Revenue Δ", "Δ %", "Primary driver"]
    widths = [0.75, 1.18, 0.82, 1.65]
    x = 7.67
    for head, width in zip(headers, widths, strict=True):
        add_text(slide, head, x, 3.33, width, 0.20, size=7.5, color=MID, bold=True)
        x += width
    store_rows = [
        ("10072", "−$55K", "−27.9%", "Traffic"),
        ("10083", "−$42K", "−17.3%", "Traffic"),
        ("10058", "−$36K", "−39.9%", "Traffic"),
        ("10174", "−$30K", "−28.5%", "Traffic"),
        ("50122", "−$28K", "−19.2%", "Traffic"),
    ]
    for i, row in enumerate(store_rows):
        y = 3.63 + i * 0.29
        add_rect(slide, 7.62, y - 0.035, 4.64, 0.255, fill=WHITE if i % 2 == 0 else "F5F7F8")
        x = 7.67
        for j, (value, width) in enumerate(zip(row, widths, strict=True)):
            add_text(slide, value, x, y, width, 0.17, size=7.7, color=RED if j in {1, 2} else INK, bold=j in {0, 1})
            x += width

    add_rect(slide, 0.55, 5.72, 12.22, 0.94, fill=NAVY, radius=True)
    add_text(slide, "RECOMMENDED ACTION", 0.82, 5.95, 1.75, 0.20, size=8.5, color="86C8BD", bold=True)
    add_text(slide, "Start with store-manager validation at the ten declining stores; test local demand, operating hours, staffing, service, and availability before committing incremental spend.", 2.55, 5.88, 9.75, 0.42, size=11, color=WHITE, bold=True)
    add_footer(slide, "Source: Retail daily/store workbook; Shapley decomposition; values rounded", 4)
    add_notes(
        slide,
        "This is the anchor business insight. Store Revenue declined $132K, or 0.9%, week over week. Conversion Rate contributed negative $472K, while AOV and Traffic offset $339K. Ten stores account for $311K of gross decline; gains elsewhere offset $179K. The tool identifies traffic as the largest negative operating contribution for the five worst stores, but this is a diagnostic signal—not proof of cause—so validate with store managers and missing operational data.",
    )


def slide_5(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(WHITE)
    add_title(
        slide,
        "The next value step is data reconciliation and operating context—not a more complex model",
        5,
        "Assumptions, requested data + roadmap",
    )
    add_text(slide, "The prototype is decision-support ready within its contract; production decisions require richer inputs and owner sign-off.", 0.55, 1.22, 11.8, 0.30, size=11.5, color=MID)

    # Known boundaries
    add_text(slide, "KNOWN BOUNDARIES", 0.55, 1.74, 3.55, 0.22, size=9, color=TEAL, bold=True)
    boundaries = [
        ("GA ≠ commerce", "GA revenue/orders are lower while GA sessions are higher; treat tracking and traffic quality as hypotheses."),
        ("Category is blocked", "Retail category totals are ~14–19× Store totals; hierarchy, extract, and scaling definitions require reconciliation."),
        ("History is short", "63 daily dates span May 3–July 4; the forecast is a directional weekday baseline, not an operating plan."),
    ]
    for i, (head, body) in enumerate(boundaries):
        y = 2.07 + i * 1.10
        add_rect(slide, 0.55, y, 3.58, 0.91, fill=RED_LIGHT if i < 2 else "FFF6E8", line=None, radius=True)
        add_text(slide, head, 0.78, y + 0.18, 1.15, 0.21, size=9.5, color=RED if i < 2 else AMBER, bold=True)
        add_text(slide, body, 1.90, y + 0.13, 2.00, 0.56, size=7.7, color=INK)

    # Data request
    add_text(slide, "DATA TO REQUEST", 4.51, 1.74, 3.65, 0.22, size=9, color=TEAL, bold=True)
    data_groups = [
        ("Definitions", "Metric dictionary; currency; gross/net; fiscal calendar; store/category hierarchy"),
        ("Demand + customer", "Transactions; customer/cohort IDs; traffic source; geography; loyalty"),
        ("Commercial levers", "Marketing spend; impressions/clicks; promotions; price; inventory/availability"),
        ("Economics + operations", "COGS/margin; returns; labor/hours; service; holidays; weather; market plans"),
    ]
    for i, (head, body) in enumerate(data_groups):
        y = 2.07 + i * 0.82
        add_rect(slide, 4.51, y, 3.67, 0.65, fill=LIGHT, line=None, radius=True)
        add_text(slide, head, 4.72, y + 0.13, 1.25, 0.20, size=8.5, color=NAVY, bold=True)
        add_text(slide, body, 5.96, y + 0.10, 1.97, 0.39, size=7.2, color=MID)

    # Roadmap
    add_text(slide, "PRODUCTION ROADMAP", 8.56, 1.74, 4.21, 0.22, size=9, color=TEAL, bold=True)
    phases = [
        ("0–30 days", "Reconcile", "Approve metric ownership, currency/accounting rules, GA instrumentation, and Retail hierarchy."),
        ("30–60 days", "Connect", "Point the repository at the warehouse; add spend, inventory, promotion, customer, and cost features."),
        ("60–90 days", "Prove", "Pilot with leaders; back-test recommendations; monitor quality, latency, drift, adoption, and business impact."),
    ]
    for i, (timing, head, body) in enumerate(phases):
        y = 2.07 + i * 1.14
        add_rect(slide, 8.56, y, 4.21, 0.94, fill=WHITE, line=LINE, radius=True)
        add_rect(slide, 8.56, y, 0.10, 0.94, fill=TEAL if i < 2 else GREEN)
        add_text(slide, timing, 8.82, y + 0.14, 0.88, 0.18, size=7.5, color=TEAL, bold=True)
        add_text(slide, head, 9.73, y + 0.11, 0.86, 0.22, size=10.5, color=NAVY, bold=True)
        add_text(slide, body, 8.82, y + 0.42, 3.63, 0.38, size=7.8, color=MID)

    add_rect(slide, 0.55, 5.78, 12.22, 0.86, fill=GREEN_LIGHT, line=None, radius=True)
    add_text(slide, "SUCCESS MEASURE", 0.80, 6.01, 1.52, 0.20, size=8.5, color=GREEN, bold=True)
    add_text(slide, "Faster executive decisions with fewer metric disputes—measured through answer accuracy, source traceability, adoption, time-to-insight, and validated action impact.", 2.32, 5.94, 9.95, 0.40, size=10.8, color=NAVY, bold=True)
    add_footer(slide, "Source: notebook data-quality findings and production design recommendations", 5)
    add_notes(
        slide,
        "Close by showing judgment about limitations. The most important next step is not a larger model. First reconcile GA versus commerce and Retail category versus store definitions. Then add the operating levers the current extracts lack: spend, inventory, promotion, price, customer, costs, and labor. Pilot the workflow with leaders and measure both analytical quality and whether recommended actions create value.",
    )


def build() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    qr_path = add_qr(APP_URL, "app_qr.png")
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    slide_1(prs)
    slide_2(prs, qr_path)
    slide_3(prs)
    slide_4(prs)
    slide_5(prs)
    prs.core_properties.title = "AI Business Analyst — Digital & Retail Case Study"
    prs.core_properties.subject = "Five-slide case-study presentation"
    prs.core_properties.author = "Eeshan Srivastava"
    prs.core_properties.keywords = "AI business analyst, digital, retail, semantic layer, Streamlit"
    prs.save(OUT_PATH)
    return OUT_PATH


if __name__ == "__main__":
    print(build())
