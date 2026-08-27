"""
Script to generate the polished, publication-grade master architecture PDF:
VERA_Master_Architecture_and_Build_Guide.pdf

Engineered with ReportLab, NumberedCanvas, custom color tokens, zebra-striped tables,
and perfectly balanced page layouts (12 structured pages, zero trailing overflows).
"""

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

OUTPUT_PDF_PATH = "c:/projects/magicpin/VERA_Master_Architecture_and_Build_Guide.pdf"


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page count: 'Page X of Y'.
    Draws professional running headers and footers on all pages except the cover.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress headers and footers on cover page
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header
        self.drawString(54, 752, "VERA — MASTER ARCHITECTURE & BUILD GUIDE")
        self.setFont("Helvetica", 7.5)
        self.drawRightString(558, 752, "magicpin AI Challenge | Autonomous Message Engine")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, 744, 558, 744)

        # Running Footer
        self.line(54, 42, 558, 42)
        self.drawString(54, 30, "CONFIDENTIAL & PROPRIETARY — STRICT CONTEXT GROUNDING SPECIFICATION")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 30, page_str)

        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PDF_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=58,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    # Color Palette Tokens
    PRIMARY = colors.HexColor("#0F172A")    # Deep Slate
    ACCENT = colors.HexColor("#EA580C")     # magicpin Orange
    BLUE_ACCENT = colors.HexColor("#2563EB")# Royal Blue
    GREEN_ACC = colors.HexColor("#16A34A")  # Success Green
    BG_LIGHT = colors.HexColor("#F8FAFC")   # Slate Light BG
    BORDER_COL = colors.HexColor("#E2E8F0") # Border Gray
    TEXT_MUTED = colors.HexColor("#475569") # Muted Text

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=ACCENT,
    )
    meta_style = ParagraphStyle(
        "CoverMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=12,
        textColor=TEXT_MUTED,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=11,
        textColor=PRIMARY,
        spaceAfter=3,
    )
    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=11,
        textColor=PRIMARY,
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=9.5,
        textColor=PRIMARY,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
    )

    story = []

    def make_callout(text, bg_color="#F1F5F9", border_color="#CBD5E1", title=""):
        content = []
        if title:
            content.append(Paragraph(f"<b><font color='{PRIMARY}'>{title}</font></b>", ParagraphStyle("h_call", fontName="Helvetica-Bold", fontSize=8.5, leading=11, spaceAfter=2)))
        content.append(Paragraph(text, callout_style))
        t = Table([[content]], colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg_color)),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(border_color)),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    def make_badge(text, bg_hex, fg_hex="#FFFFFF"):
        p = Paragraph(f"<font color='{fg_hex}'><b>{text}</b></font>", ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=6.5, alignment=1))
        t = Table([[p]], colWidths=[65], rowHeights=[12])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg_hex)),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 1),
        ]))
        return t

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=3.5, color=ACCENT, spaceBefore=0, spaceAfter=12))
    story.append(Paragraph("VERA — AUTONOMOUS MESSAGE ENGINE", subtitle_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Master Architecture, Build Guide & Adversarial Defence Manual", title_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COL, spaceBefore=4, spaceAfter=12))

    cover_box_text = """
    <b>CORE PROJECT DIRECTIVE & PHILOSOPHY:</b><br/>
    <i>"Build one strong flow. Start small and deterministic. Ground every output in received context.<br/>
    Make Vera hard to break before making Vera fancy. Never hardcode the visible examples.<br/>
    Assume the real judge will try to break the system with unseen inputs."</i>
    """
    story.append(make_callout(cover_box_text, bg_color="#FFF7ED", border_color="#FDBA74", title="ENGINEERING CREED"))
    story.append(Spacer(1, 10))

    meta_table_data = [
        [Paragraph("<b>Document Version:</b>", meta_style), Paragraph("2.2 (Post Phase 2B.2 Hardening & Gate)", meta_style)],
        [Paragraph("<b>Target System:</b>", meta_style), Paragraph("magicpin Vera AI Challenge Backend Service", meta_style)],
        [Paragraph("<b>Status:</b>", meta_style), Paragraph("<font color='#16A34A'><b>PHASE 2B.2 GATE COMPLETE (34/34 AUTOMATED TESTS PASSING)</b></font>", meta_style)],
        [Paragraph("<b>Core Framework:</b>", meta_style), Paragraph("Deterministic 4-Context Synthesis Engine + SQLite State Layer (FastAPI)", meta_style)],
        [Paragraph("<b>Source Repository:</b>", meta_style), Paragraph("c:/projects/magicpin (Production logic in app/)", meta_style)],
        [Paragraph("<b>Generated:</b>", meta_style), Paragraph("August 2026", meta_style)],
    ]
    meta_t = Table(meta_table_data, colWidths=[120, 384])
    meta_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 12))

    toc_data = [
        [Paragraph("<b>TABLE OF CONTENTS</b>", table_header), Paragraph("", table_header)],
        [Paragraph("1. Executive Overview & 4-Context Model", table_cell), Paragraph("11. Adversarial Resilience & Break Matrix", table_cell)],
        [Paragraph("2. Official Challenge Requirements & Contracts", table_cell), Paragraph("12. Test Audit & Verification Architecture", table_cell)],
        [Paragraph("3. Non-Negotiable Vera Operating Rules (30 Rules)", table_cell), Paragraph("13. Real Judge Simulation Lifecycle", table_cell)],
        [Paragraph("4. Technology Stack & Design Boundaries", table_cell), Paragraph("14. Status Matrix: Complete vs Future", table_cell)],
        [Paragraph("5. Actual Repository File Tree & Component Audit", table_cell), Paragraph("15. Future LLM Integration Boundaries", table_cell)],
        [Paragraph("6. End-to-End System Architecture", table_cell), Paragraph("16. Future Multi-Turn Conversation Engine", table_cell)],
        [Paragraph("7. Context Ingestion & Versioning Protocol", table_cell), Paragraph("17. Customer-Facing Engagement Flow", table_cell)],
        [Paragraph("8. Deterministic research_digest Flowchart", table_cell), Paragraph("18. Project Roadmap (Phases 1 to 6)", table_cell)],
        [Paragraph("9. Separation of Decision & Message Strategy", table_cell), Paragraph("19. 'Where We Are Right Now' Summary", table_cell)],
        [Paragraph("10. Multi-Merchant Suppression Architecture", table_cell), Paragraph("20. Master Principle & Vera Glossary", table_cell)],
    ]
    toc_t = Table(toc_data, colWidths=[252, 252])
    toc_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
    ]))
    story.append(toc_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: SECTIONS 1 & 2
    # =========================================================================
    story.append(Paragraph("1. Executive Overview & 4-Context Model", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        "<b>Vera</b> is magicpin's autonomous engagement intelligence. Unlike generic conversational chatbots that hallucinate plausible answers from prompt memory, Vera is a <b>deterministic, context-grounded message engine</b>. Vera determines the exact next message, actionable Call-to-Action (CTA), send-as identity, suppression key, and clinical/business rationale for local merchants and customers.",
        body_style
    ))

    context_desc_data = [
        [Paragraph("<b>CONTEXT SCOPE</b>", table_header), Paragraph("<b>CONTENTS & ROLE IN COMPOSITION</b>", table_header), Paragraph("<b>PRIMARY USE</b>", table_header)],
        [Paragraph("<b>Category Context</b><br/>(Macro Vertical)", table_cell_bold), Paragraph("Industry vertical voice profile, tone (peer_clinical / warm_practical), register, allowed & taboo vocabulary, dynamic salutation templates, curated research digest items, and patient/customer content library.", table_cell), Paragraph("Sets communication register and supplies authoritative facts.", table_cell)],
        [Paragraph("<b>Merchant Context</b><br/>(Business Account)", table_cell_bold), Paragraph("Business name, owner first name, city, locality, verification status, languages, active subscription tier, CTR/views performance metrics, customer aggregates, active offers, cohort signals, and conversation history.", table_cell), Paragraph("Anchors relevance to merchant identity and audience signals.", table_cell)],
        [Paragraph("<b>Trigger Context</b><br/>(Event Signal)", table_cell_bold), Paragraph("Event kind (research_digest, churn_risk, festival, new_offer, view_spike), urgency (1-5), target item IDs, category slug, expiration timestamp, and vertical/merchant suppression key.", table_cell), Paragraph("Dictates timing, trigger reason, and suppression identity.", table_cell)],
        [Paragraph("<b>Customer Context</b><br/>(Optional Consumer)", table_cell_bold), Paragraph("Customer identity, preferences, visit cadence, spend aggregate, lifetime value, and consent records.", table_cell), Paragraph("Enables personalized customer outreach in Phase 4.", table_cell)],
    ]
    ctx_t = Table(context_desc_data, colWidths=[105, 275, 124])
    ctx_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(ctx_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Official Challenge Requirements & Contracts", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    req_data = [
        [Paragraph("<b>DIMENSION</b>", table_header), Paragraph("<b>OFFICIAL CHALLENGE SPECIFICATION</b>", table_header)],
        [Paragraph("<b>Hard Requirements</b>", table_cell_bold), Paragraph("Implement standard HTTP REST endpoints on FastAPI. Enforce strict ACID SQLite context storage with version conflict detection (409 on stale version, 200 on duplicate idempotent). Enforce multi-tenant suppression deduplication. Respect trigger expiration.", table_cell)],
        [Paragraph("<b>Scoring Dimensions (50 pts)</b>", table_cell_bold), Paragraph("<b>1. Specificity (10):</b> Verifiable numbers, trial sizes, citations.<br/><b>2. Category Fit (10):</b> True vertical voice, zero taboo words.<br/><b>3. Merchant Fit (10):</b> Owner name, cohort signals, language.<br/><b>4. Decision Quality (10):</b> Correct trigger routing, suppression.<br/><b>5. Engagement (10):</b> Compelling, low-friction, single CTA.", table_cell)],
        [Paragraph("<b>Required Endpoints</b>", table_cell_bold), Paragraph("<code>GET /v1/healthz</code> — Diagnostic status and exact counts of loaded contexts.<br/><code>GET /v1/metadata</code> — Team name, architecture summary, operational model.<br/><code>POST /v1/context</code> — Ingestion of category, merchant, customer, trigger contexts.<br/><code>POST /v1/tick</code> — Periodic wake-up evaluation emitting up to 20 actions.<br/><code>POST /v1/reply</code> — Multi-turn conversation reply handler.", table_cell)],
        [Paragraph("<b>Operational Caps</b>", table_cell_bold), Paragraph("Max 20 actions per tick. Max timeout: 5s for healthz/metadata, 10s for context, 15s for tick/reply. Latencies must remain &lt;100ms.", table_cell)],
    ]
    req_t = Table(req_data, colWidths=[120, 384])
    req_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#1E293B")),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(req_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: SECTION 3 (30 OPERATING RULES)
    # =========================================================================
    story.append(Paragraph("3. Non-Negotiable Vera Operating Rules (30 Rules)", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=6))

    rules_p1 = [
        "1. Ground everything strictly in received context.",
        "2. Never invent numbers, sample sizes, or stats.",
        "3. Never invent offers, discounts, or vouchers.",
        "4. Never invent dates, deadlines, or schedules.",
        "5. Never invent customer facts or preferences.",
        "6. Never invent business metrics or claim counts.",
        "7. Never invent clinical claims or medical advice.",
        "8. Handle Category + Merchant + Trigger correctly.",
        "9. Decide before writing — logic dictates copy.",
        "10. Specificity > generic marketing fluff.",
        "11. Merchant fit > superficial personalization.",
        "12. One strong, low-friction CTA per message.",
        "13. Sometimes WAIT is the optimal answer.",
        "14. Sometimes SUPPRESS is the optimal answer.",
        "15. Sometimes END is the optimal answer.",
    ]
    rules_p2 = [
        "16. Never repeat messages due to state bugs.",
        "17. Respect merchant-scoped suppression keys.",
        "18. Respect merchant opt-outs and unsubscribe history.",
        "19. YES / GO AHEAD leads directly to execution.",
        "20. Repeated auto-replies must back off and end.",
        "21. Customer outreach requires explicit consent context.",
        "22. Higher context versions atomically replace stale ones.",
        "23. Same input + same state = identical deterministic behavior.",
        "24. Keep API responses sub-10ms (fast & lightweight).",
        "25. Never hardcode visible sample strings in logic.",
        "26. Never test-fit to pass the local judge simulator.",
        "27. Real judge injects unseen merchants and verticals.",
        "28. Passing unit tests does not equal judge immunity.",
        "29. Build small & deterministic before adding complexity.",
        "30. Make Vera hard to break before making Vera fancy.",
    ]

    rule_rows = []
    for r1, r2 in zip(rules_p1, rules_p2):
        rule_rows.append([Paragraph(r1, body_style), Paragraph(r2, body_style)])

    rules_table = Table(rule_rows, colWidths=[252, 252])
    rules_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('PADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(rules_table)
    story.append(Spacer(1, 8))

    flow_box = """
    <b>THE CORE VERA DECISION PIPELINE:</b><br/>
    <b>GROUND</b> (Verify 4 Contexts) → <b>DECIDE</b> (Gating & Eligibility) → <b>SELECT FACTS</b> (Digest & Signals) → <b>COMPOSE</b> (Rule-Based Synthesis) → <b>VALIDATE</b> (Word-Boundary Taboo Filter) → <b>RESPOND SAFELY</b> (Record Suppression & Emit)
    """
    story.append(make_callout(flow_box, bg_color="#EFF6FF", border_color="#93C5FD", title="EXECUTION PIPELINE"))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: SECTIONS 4 & 5
    # =========================================================================
    story.append(Paragraph("4. Technology Stack & Design Boundaries", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    stack_data = [
        [Paragraph("<b>LAYER / COMPONENT</b>", table_header), Paragraph("<b>TECHNOLOGY USED</b>", table_header), Paragraph("<b>RATIONALE & CONSTRAINTS</b>", table_header)],
        [Paragraph("<b>Runtime & API</b>", table_cell_bold), Paragraph("Python 3.11 + FastAPI + Uvicorn", table_cell), Paragraph("Asynchronous, high-performance, strictly typed REST endpoints with automatic OpenAPI schema generation.", table_cell)],
        [Paragraph("<b>Data Validation</b>", table_cell_bold), Paragraph("Pydantic v2", table_cell), Paragraph("Contract validation enforcing non-nullable scopes, ISO dates, integer versions, and strict action models.", table_cell)],
        [Paragraph("<b>Persistent Storage</b>", table_cell_bold), Paragraph("SQLite (WAL Mode + Thread Lock)", table_cell), Paragraph("Zero-dependency ACID persistence, composite primary key deduplication, atomic version transitions, and sub-millisecond lookups.", table_cell)],
        [Paragraph("<b>Testing Framework</b>", table_cell_bold), Paragraph("pytest + FastAPI TestClient", table_cell), Paragraph("34 automated tests spanning unit contracts, flow gating, adversarial edge cases, and judge simulator adapters.", table_cell)],
        [Paragraph("<b>Containerization</b>", table_cell_bold), Paragraph("Docker (Multi-stage build)", table_cell), Paragraph("Production-ready, portable image running on configured PORT with clean SQLite volume binding.", table_cell)],
        [Paragraph("<b>Intentionally Excluded</b>", table_cell_bold), Paragraph("Vector DBs, Redis, LangChain, Multi-Agent Bloat", table_cell), Paragraph("Unnecessary operational complexity. Deterministic routing and factual extraction do not require vector search.", table_cell)],
    ]
    stack_t = Table(stack_data, colWidths=[115, 155, 234])
    stack_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(stack_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("5. Actual Repository File Tree & Component Audit", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    file_tree_data = [
        [Paragraph("<b>FILE PATH</b>", table_header), Paragraph("<b>PURPOSE & SCOPE</b>", table_header), Paragraph("<b>STATUS</b>", table_header)],
        [Paragraph("<code>app/main.py</code>", table_cell_bold), Paragraph("FastAPI app entrypoint, lifespan startup (DB init), global error handlers, route inclusion.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/config.py</code>", table_cell_bold), Paragraph("App constants, server port configuration, and Vera operating principles.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/models/context.py</code>", table_cell_bold), Paragraph("Pydantic models for <code>/v1/context</code> push and response payloads.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/models/health.py</code>", table_cell_bold), Paragraph("Pydantic models for <code>/v1/healthz</code> and <code>/v1/metadata</code>.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/models/interaction.py</code>", table_cell_bold), Paragraph("Pydantic models for <code>/v1/tick</code> (TickAction) and <code>/v1/reply</code>.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/store/context_store.py</code>", table_cell_bold), Paragraph("SQLite engine: atomic versioning, composite suppression tracking, legacy schema migration.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/engine/salutation.py</code>", table_cell_bold), Paragraph("Dynamic greeting resolver driven by <code>CategoryContext.voice</code> and merchant identity.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/engine/composer.py</code>", table_cell_bold), Paragraph("Deterministic composer for research_digest: factual extraction, cohort linking, taboo filters.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/routes/health.py</code>", table_cell_bold), Paragraph("Route handlers for health status, context counts, and metadata inspection.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/routes/context.py</code>", table_cell_bold), Paragraph("Route handler for <code>POST /v1/context</code> with 409 stale version rejection.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<code>app/routes/interaction.py</code>", table_cell_bold), Paragraph("Route handler for <code>/v1/tick</code> (active composer) and <code>/v1/reply</code> (Phase 1/2 stub).", table_cell), make_badge("PARTIAL", "#D97706")],
        [Paragraph("<code>app/engine/conversation.py</code>", table_cell_bold), Paragraph("Multi-turn conversation engine and intent state machine for replies.", table_cell), make_badge("FUTURE", "#64748B")],
    ]
    ft_t = Table(file_tree_data, colWidths=[150, 279, 75])
    ft_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(ft_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: SECTIONS 6 & 7
    # =========================================================================
    story.append(Paragraph("6. End-to-End System Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    arch_box_data = [
        [Paragraph("<b>COMPONENT</b>", table_header), Paragraph("<b>TYPE</b>", table_header), Paragraph("<b>INPUTS & OUTPUTS</b>", table_header), Paragraph("<b>STATUS</b>", table_header)],
        [Paragraph("<b>HTTP Gateway</b><br/>(FastAPI / Uvicorn)", table_cell_bold), Paragraph("REST Ingress", table_cell), Paragraph("Receives Judge HTTP calls on /v1/context, /v1/tick, /v1/reply, /v1/healthz, /v1/metadata.", table_cell), make_badge("ACTIVE", "#16A34A")],
        [Paragraph("<b>Context Store</b><br/>(SQLite Engine)", table_cell_bold), Paragraph("State Layer", table_cell), Paragraph("Stores scopes (category, merchant, customer, trigger). Manages version conflicts and suppression pairs.", table_cell), make_badge("ACTIVE", "#16A34A")],
        [Paragraph("<b>Decision & Gating</b><br/>(Rules Engine)", table_cell_bold), Paragraph("Deterministic Logic", table_cell), Paragraph("Evaluates trigger expiry, vertical consistency, merchant subscription, opt-out history, and suppression.", table_cell), make_badge("ACTIVE", "#16A34A")],
        [Paragraph("<b>Factual Composer</b><br/>(Language Synthesizer)", table_cell_bold), Paragraph("Fact Synthesizer", table_cell), Paragraph("Synthesizes lead hook, cohort relevance, trial facts (N=...), and topic-aware CTA without hallucinations.", table_cell), make_badge("ACTIVE", "#16A34A")],
        [Paragraph("<b>Safety Validator</b><br/>(Word Boundary Filter)", table_cell_bold), Paragraph("Taboo Scrubber", table_cell), Paragraph("Filters category-specific taboo terms using \\b word boundaries without corrupting legitimate words.", table_cell), make_badge("ACTIVE", "#16A34A")],
        [Paragraph("<b>Conversation Engine</b><br/>(Multi-Turn Reply)", table_cell_bold), Paragraph("State Machine", table_cell), Paragraph("Handles merchant replies (YES/GO AHEAD, questions, auto-replies, hostile opt-outs).", table_cell), make_badge("PHASE 3", "#64748B")],
    ]
    arch_t = Table(arch_box_data, colWidths=[115, 85, 229, 75])
    arch_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#1E3A8A")),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(arch_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("7. Context Ingestion & Versioning Protocol", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        "Context arrives via <code>POST /v1/context</code>. The system stores the latest valid state per <code>(scope, context_id)</code> and rejects stale updates with HTTP 409 Conflict.",
        body_style
    ))

    version_rules_data = [
        [Paragraph("<b>VERSION SCENARIO</b>", table_header), Paragraph("<b>STORE STATE</b>", table_header), Paragraph("<b>INCOMING VERSION</b>", table_header), Paragraph("<b>HTTP STATUS & ACTION</b>", table_header)],
        [Paragraph("<b>Initial Ingestion</b>", table_cell_bold), Paragraph("Empty (no record)", table_cell), Paragraph("Version 1", table_cell), Paragraph("<font color='#16A34A'><b>200 OK</b></font> — Stored atomically into SQLite contexts table.", table_cell)],
        [Paragraph("<b>Idempotent Resend</b>", table_cell_bold), Paragraph("Stored Version 1", table_cell), Paragraph("Version 1", table_cell), Paragraph("<font color='#16A34A'><b>200 OK</b></font> — Idempotent no-op. Returns accepted=true.", table_cell)],
        [Paragraph("<b>Context Update</b>", table_cell_bold), Paragraph("Stored Version 1", table_cell), Paragraph("Version 2 (or higher)", table_cell), Paragraph("<font color='#16A34A'><b>200 OK</b></font> — Atomically overwrites payload and updates version.", table_cell)],
        [Paragraph("<b>Stale / Out-of-Order</b>", table_cell_bold), Paragraph("Stored Version 2", table_cell), Paragraph("Version 1 (lower)", table_cell), Paragraph("<font color='#DC2626'><b>409 Conflict</b></font> — Rejected. Body contains error='stale_version'.", table_cell)],
        [Paragraph("<b>Invalid Scope</b>", table_cell_bold), Paragraph("Any", table_cell), Paragraph("scope='unknown'", table_cell), Paragraph("<font color='#DC2626'><b>400 Bad Request</b></font> — Rejected. Must be category/merchant/customer/trigger.", table_cell)],
    ]
    ver_t = Table(version_rules_data, colWidths=[105, 95, 95, 209])
    ver_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(ver_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: SECTIONS 8 & 9
    # =========================================================================
    story.append(Paragraph("8. Deterministic research_digest Flowchart", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    flow_steps_data = [
        [Paragraph("<b>STEP / GATING STAGE</b>", table_header), Paragraph("<b>DETERMINISTIC EVALUATION LOGIC</b>", table_header), Paragraph("<b>FAILURE OUTCOME</b>", table_header)],
        [Paragraph("<b>1. Trigger Validation</b>", table_cell_bold), Paragraph("Verify trigger scope == 'merchant' and kind == 'research_digest'.", table_cell), Paragraph("SUPPRESS (No-op)", table_cell)],
        [Paragraph("<b>2. Expiry Check</b>", table_cell_bold), Paragraph("Compare ISO timestamp <code>body.now > trigger.expires_at</code>.", table_cell), Paragraph("SUPPRESS (Stale Trigger)", table_cell)],
        [Paragraph("<b>3. Entity Resolution</b>", table_cell_bold), Paragraph("Fetch MerchantContext by merchant_id and CategoryContext by category_slug.", table_cell), Paragraph("SUPPRESS (Missing Context)", table_cell)],
        [Paragraph("<b>4. Category Match</b>", table_cell_bold), Paragraph("Verify trigger.payload.category == merchant.category_slug.", table_cell), Paragraph("SUPPRESS (Vertical Mismatch)", table_cell)],
        [Paragraph("<b>5. Subscription & Opt-Out</b>", table_cell_bold), Paragraph("Check active plan and inspect conversation_history for unsubscribe / stop signals.", table_cell), Paragraph("SUPPRESS (Opted Out / Inactive)", table_cell)],
        [Paragraph("<b>6. Multi-Tenant Suppression</b>", table_cell_bold), Paragraph("Query SQLite for <code>(suppression_key, merchant_id)</code>.", table_cell), Paragraph("SUPPRESS (Already Sent)", table_cell)],
        [Paragraph("<b>7. Fact & Cohort Linking</b>", table_cell_bold), Paragraph("Match top_item_id in category.digest; link patient_segment to merchant signals.", table_cell), Paragraph("SAFE FALLBACK (General Practice)", table_cell)],
        [Paragraph("<b>8. Salutation & Hook</b>", table_cell_bold), Paragraph("Resolve greeting from category voice examples; extract journal/issue from source.", table_cell), Paragraph("SAFE FALLBACK ('Doc' / 'Hi team')", table_cell)],
        [Paragraph("<b>9. Fact Synthesis</b>", table_cell_bold), Paragraph("Format core finding with sample size (N=...) without double verbs.", table_cell), Paragraph("SUPPRESS (Missing summary/title)", table_cell)],
        [Paragraph("<b>10. Topic-Aware CTA</b>", table_cell_bold), Paragraph("Route CTA based on digest kind (compliance, tech, cde, trend, clinical).", table_cell), Paragraph("Standard Low-Friction Ask", table_cell)],
        [Paragraph("<b>11. Word-Boundary Taboo</b>", table_cell_bold), Paragraph("Clean taboo list; scrub standalone taboo terms with \\b word boundaries.", table_cell), Paragraph("Preserves legitimate words", table_cell)],
        [Paragraph("<b>12. Action Emission</b>", table_cell_bold), Paragraph("Record (suppression_key, merchant_id); return structured TickAction in actions[].", table_cell), Paragraph("Max 20 actions per tick", table_cell)],
    ]
    flow_t = Table(flow_steps_data, colWidths=[115, 279, 110])
    flow_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#065F46")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#065F46")),
        ('PADDING', (0, 0), (-1, -1), 2.2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(flow_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("9. Separation of Decision & Message Strategy", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        "A foundational design principle of Vera is the strict separation between <b>Deterministic Decision Making</b> and <b>Language Synthesis</b>. The decision engine evaluates eligibility and selects factual anchors; the composer transforms structured facts into natural prose. This guarantees zero hallucinations.",
        body_style
    ))

    strategy_code = """{
  "merchant_id": "m_opt_kavita_pune",
  "salutation": "Dr. Kavita",
  "source_lead": "Optometry Vision Science's Nov issue landed.",
  "cohort_anchor": "One item relevant to pediatric myopia patients — ",
  "finding_fact": "Randomized 2-year trial demonstrated 59% reduction in axial elongation (N=1,560).",
  "cta_text": "Worth a look (2-min abstract). Want me to pull the key takeaways for your team?",
  "citation_footer": " — Optometry Vision Science Nov 2026, p.50",
  "suppression_key": "research:optometry:2026-W45",
  "rationale": "External research digest with pediatric cohort anchor. Source citation at end maintains clinical credibility."
}"""
    t_code = Table([[Paragraph(f"<pre>{strategy_code}</pre>", code_style)]], colWidths=[504])
    t_code.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_code)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: SECTIONS 10 & 11
    # =========================================================================
    story.append(Paragraph("10. Multi-Merchant Suppression Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        "In weekly digests and external announcements, triggers carry vertical-level suppression keys (e.g. <code>research:dentists:2026-W17</code>). If suppression were globally keyed on <code>suppression_key</code> alone, the first merchant would receive the message and all other merchants in that vertical would be silently dropped. Vera enforces <b>Merchant-Scoped Suppression</b>.",
        body_style
    ))

    supp_compare_data = [
        [Paragraph("<b>GLOBAL KEYING (VULNERABLE)</b>", table_header), Paragraph("<b>MERCHANT-SCOPED KEYING (VERA ARCHITECTURE)</b>", table_header)],
        [
            Paragraph("<code>PRIMARY KEY (suppression_key)</code><br/>• Merchant A evaluates key X → <b>SENT</b><br/>• Key X is recorded globally.<br/>• Merchant B evaluates key X → <font color='#DC2626'><b>BLOCKED</b></font><br/><b>Outcome:</b> 49/50 merchants silently dropped.", table_cell),
            Paragraph("<code>PRIMARY KEY (suppression_key, merchant_id)</code><br/>• Merchant A evaluates key X → <b>SENT</b> (X, A)<br/>• Merchant B evaluates key X → <b>SENT</b> (X, B)<br/>• Merchant A receives tick 2 → <font color='#16A34A'><b>SUPPRESSED</b></font><br/><b>Outcome:</b> Perfect multi-tenant isolation.", table_cell)
        ],
    ]
    supp_t = Table(supp_compare_data, colWidths=[252, 252])
    supp_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#991B1B")),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#166534")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(supp_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("11. Adversarial Resilience & Break Matrix", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    break_matrix_data = [
        [Paragraph("<b>FAILURE VECTOR</b>", table_header), Paragraph("<b>JUDGE INJECTION</b>", table_header), Paragraph("<b>VERA DETERMINISTIC DEFENCE</b>", table_header), Paragraph("<b>STATUS</b>", table_header)],
        [Paragraph("<b>Expired Trigger</b>", table_cell_bold), Paragraph("now=2026-05-04, expires=2026-05-03", table_cell), Paragraph("Timestamp comparison detects staleness; yields no-op.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Category Mismatch</b>", table_cell_bold), Paragraph("Salon trigger to dentist merchant", table_cell), Paragraph("Category consistency check rejects action.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Opt-Out History</b>", table_cell_bold), Paragraph("Merchant previously sent 'stop'", table_cell), Paragraph("Conversation history scanner flags opt-out; suppresses.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Missing Owner Name</b>", table_cell_bold), Paragraph("owner_first_name=null (doctor)", table_cell), Paragraph("Resolves to category fallback 'Doc' (never 'Dr. None').", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Missing Trial Size</b>", table_cell_bold), Paragraph("trial_n=null in digest item", table_cell), Paragraph("Grounds in summary text without fabricating trial size.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Missing Summary</b>", table_cell_bold), Paragraph("trial_n=2100 but summary=''", table_cell), Paragraph("Suppresses action; never fabricates clinical claims.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Unseen Journals</b>", table_cell_bold), Paragraph("Source='The Lancet Nov 2026'", table_cell), Paragraph("Dynamic parser handles publication/issue without whitelist.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Taboo Substrings</b>", table_cell_bold), Paragraph("Text with 'secure', 'accurate'", table_cell), Paragraph("Word-boundary regex (\\b) preserves legitimate words.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Trigger Flood (21+)</b>", table_cell_bold), Paragraph("30 candidate triggers in /v1/tick", table_cell), Paragraph("Prioritizes by urgency descending; caps strictly at 20.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Duplicate Triggers</b>", table_cell_bold), Paragraph("available_triggers=['trg_1','trg_1']", table_cell), Paragraph("First trigger records suppression; second is deduplicated.", table_cell), make_badge("PASS", "#16A34A")],
        [Paragraph("<b>Stale Version Resend</b>", table_cell_bold), Paragraph("Pushing v1 after v2 stored", table_cell), Paragraph("Rejects with HTTP 409 Conflict (stale_version error).", table_cell), make_badge("PASS", "#16A34A")],
    ]
    bm_t = Table(break_matrix_data, colWidths=[105, 135, 199, 65])
    bm_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 2.2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(bm_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: SECTIONS 12 & 13
    # =========================================================================
    story.append(Paragraph("12. Test Audit & Verification Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    test_audit_data = [
        [Paragraph("<b>TEST SUITE FILE</b>", table_header), Paragraph("<b>TEST TYPE & PURPOSE</b>", table_header), Paragraph("<b>COUNT</b>", table_header), Paragraph("<b>STATUS</b>", table_header)],
        [Paragraph("<code>tests/test_context.py</code>", table_cell_bold), Paragraph("Contract tests for context scopes, atomic updates, version replacement, stale rejection.", table_cell), Paragraph("7 tests", table_cell), make_badge("7/7 PASS", "#16A34A")],
        [Paragraph("<code>tests/test_health.py</code>", table_cell_bold), Paragraph("Diagnostic tests for /v1/healthz counts, metadata team details, and root endpoint.", table_cell), Paragraph("4 tests", table_cell), make_badge("4/4 PASS", "#16A34A")],
        [Paragraph("<code>tests/test_interaction.py</code>", table_cell_bold), Paragraph("API contract stubs for /v1/tick and /v1/reply interaction lifecycle.", table_cell), Paragraph("2 tests", table_cell), make_badge("2/2 PASS", "#16A34A")],
        [Paragraph("<code>tests/test_flow_research_digest.py</code>", table_cell_bold), Paragraph("Adversarial flow tests: factual synthesis, word-boundary taboos, multi-vertical salutations.", table_cell), Paragraph("12 tests", table_cell), make_badge("12/12 PASS", "#16A34A")],
        [Paragraph("<code>tests/test_judge_simulation_gate.py</code>", table_cell_bold), Paragraph("Integration gate tests: full 355 context warmup, persistence, multi-merchant isolation.", table_cell), Paragraph("8 tests", table_cell), make_badge("8/8 PASS", "#16A34A")],
        [Paragraph("<code>tests/test_judge_sim_runner.py</code>", table_cell_bold), Paragraph("Judge simulator runner executing warmup and phase2_short scenarios against backend.", table_cell), Paragraph("1 test", table_cell), make_badge("1/1 PASS", "#16A34A")],
        [Paragraph("<b>TOTAL VERIFICATION</b>", table_cell_bold), Paragraph("<b>Comprehensive regression & judge gate suite executing in ~12.2s.</b>", table_cell_bold), Paragraph("<b>34 tests</b>", table_cell_bold), make_badge("34/34 PASS", "#16A34A")],
    ]
    t_aud = Table(test_audit_data, colWidths=[150, 219, 65, 70])
    t_aud.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0, 1), (-1, -2), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#1E293B")),
        ('PADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_aud)
    story.append(Spacer(1, 4))
    story.append(Paragraph("<i>CRITICAL PRINCIPLE: 'Tests written by us are necessary, but they are not the same thing as the real judge. True robustness requires zero hardcoding and complete generalizability across unseen contexts.'</i>", meta_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("13. Real Judge Simulation Lifecycle", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    judge_stages_data = [
        [Paragraph("<b>STAGE</b>", table_header), Paragraph("<b>JUDGE ACTIONS & PROTOCOL</b>", table_header), Paragraph("<b>KEY SCORING CRITERIA</b>", table_header)],
        [Paragraph("<b>1. Warmup</b>", table_cell_bold), Paragraph("Calls <code>GET /v1/healthz</code> and <code>GET /v1/metadata</code>. Pushes initial batch of categories and merchants via <code>POST /v1/context</code>.", table_cell), Paragraph("Sub-100ms latency, exact reflection of loaded context counts in healthz.", table_cell)],
        [Paragraph("<b>2. Ingestion</b>", table_cell_bold), Paragraph("Pushes 50 merchants, 200 customers, 100 triggers. Injects updated versions (v2) and stale versions (v1).", table_cell), Paragraph("Strict 200 on valid versions, 409 Conflict on stale versions.", table_cell)],
        [Paragraph("<b>3. Tick</b>", table_cell_bold), Paragraph("Calls <code>POST /v1/tick</code> with simulated timestamp advances and batches of available trigger IDs.", table_cell), Paragraph("Grounded specificity, correct salutation, taboo scrubbing, max 20 action cap.", table_cell)],
        [Paragraph("<b>4. Reply Flow</b>", table_cell_bold), Paragraph("Sends merchant responses (positive YES, clarification questions, repeated auto-replies, hostile opt-outs).", table_cell), Paragraph("Auto-reply backoff detection, opt-out suppression, actionable flow completion.", table_cell)],
        [Paragraph("<b>5. Scoring</b>", table_cell_bold), Paragraph("LLM Judge evaluates 5 dimensions (0-10 each). Imposes heavy penalties for hallucinations, spam, or broken state.", table_cell), Paragraph("50 points maximum. Target score: >80% (Excellent).", table_cell)],
    ]
    judge_t = Table(judge_stages_data, colWidths=[105, 235, 164])
    judge_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(judge_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: SECTIONS 14 & 15
    # =========================================================================
    story.append(Paragraph("14. Status Matrix: Complete vs Future", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    status_matrix_data = [
        [Paragraph("<b>COMPLETE & HARDENED (PHASE 1 - 2B.2)</b>", table_header), Paragraph("<b>SCHEDULED FOR FUTURE PHASES (PHASE 3 - 6)</b>", table_header)],
        [
            Paragraph("• Typed Pydantic models for all 5 endpoints<br/>"
                      "• ACID SQLite store with atomic versioning<br/>"
                      "• 409 Conflict on stale context versions<br/>"
                      "• Multi-tenant (suppression_key, merchant_id) store<br/>"
                      "• Diagnostic /healthz & /metadata endpoints<br/>"
                      "• Deterministic research_digest composition<br/>"
                      "• Dynamic Category voice salutation engine<br/>"
                      "• Generic journal hook parser (no whitelist)<br/>"
                      "• Robust fact synthesis with (N=...) integration<br/>"
                      "• Word-boundary taboo filter (\\b)<br/>"
                      "• Topic-aware CTA router across 5 kinds<br/>"
                      "• Strict 20-action cap with urgency ranking<br/>"
                      "• 34 automated unit, flow & gate tests passing", table_cell),
            Paragraph("• Phase 3: Multi-turn /v1/reply conversation engine<br/>"
                      "• Phase 3: YES / GO AHEAD execution state machine<br/>"
                      "• Phase 3: Auto-reply backoff & loop termination<br/>"
                      "• Phase 3: Merchant hostile opt-out state tracking<br/>"
                      "• Phase 4: Churn risk trigger family (m_churn)<br/>"
                      "• Phase 4: Festival & holiday triggers (trg_festival)<br/>"
                      "• Phase 4: Offer drop & view spike triggers<br/>"
                      "• Phase 4: Customer-facing outreach flows<br/>"
                      "• Phase 5: Live LLM provider integration & validator<br/>"
                      "• Phase 5: Replay testing against full challenge suite<br/>"
                      "• Phase 6: Production Docker deployment & submission", table_cell)
        ],
    ]
    status_t = Table(status_matrix_data, colWidths=[252, 252])
    status_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#15803D")),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#1D4ED8")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(status_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("15. Future LLM Integration Boundaries", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        "When an LLM provider is introduced in Phase 5, it will operate inside strict deterministic boundaries. The LLM is <b>never trusted with state, suppression, or factual grounding</b>.",
        body_style
    ))

    llm_boundary_data = [
        [Paragraph("<b>WHAT THE LLM IS NEVER TRUSTED TO DECIDE</b>", table_header), Paragraph("<b>WHAT THE LLM IS USED FOR</b>", table_header)],
        [
            Paragraph("• Context existence or validity<br/>"
                      "• Version conflict resolution (409 Conflict)<br/>"
                      "• Suppression eligibility or duplicate checks<br/>"
                      "• Category consistency or merchant verification<br/>"
                      "• Selecting trial numbers, metrics, or offers<br/>"
                      "• API contract adherence or action limits", table_cell),
            Paragraph("• Natural phrasing and conversational transitions<br/>"
                      "• Code-mixing (Hindi + English natural phrasing)<br/>"
                      "• Polite clarification questions on ambiguous merchant replies<br/>"
                      "• Dynamic rephrasing within strict MessageStrategy tokens<br/>"
                      "• Empathy adjustments matching Category tone", table_cell)
        ],
    ]
    llm_t = Table(llm_boundary_data, colWidths=[252, 252])
    llm_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#991B1B")),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#1E3A8A")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(llm_t)
    story.append(Spacer(1, 4))

    llm_arch_box = """
    <b>FUTURE LLM SANDWICH ARCHITECTURE:</b><br/>
    <b>Raw Context</b> → <b>Deterministic Gating</b> → <b>MessageStrategy Struct</b> → <b>LLM Paraphrase</b> → <b>Deterministic Taboo & Fact Validator</b> → <b>Action Emission</b>
    """
    story.append(make_callout(llm_arch_box, bg_color="#F5F3FF", border_color="#DDD6FE", title="SANDWICH PATTERN"))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 10: SECTIONS 16 & 17
    # =========================================================================
    story.append(Paragraph("16. Future Reply & Conversation Engine (Phase 3)", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    reply_state_data = [
        [Paragraph("<b>CONVERSATION STATE</b>", table_header), Paragraph("<b>TRIGGER / INPUT</b>", table_header), Paragraph("<b>TRANSITION & BOT ACTION</b>", table_header)],
        [Paragraph("<b>OUTBOUND_SENT</b>", table_cell_bold), Paragraph("Proactive tick message emitted", table_cell), Paragraph("State set to WAITING_REPLY; turn_number=1.", table_cell)],
        [Paragraph("<b>POSITIVE_AFFIRMATION</b>", table_cell_bold), Paragraph("Merchant replies 'Yes', 'Sure', 'Send it'", table_cell), Paragraph("Transition to ACTION_EXECUTION; deliver draft artifact; set status=COMPLETED.", table_cell)],
        [Paragraph("<b>CLARIFICATION_ASK</b>", table_cell_bold), Paragraph("Merchant asks 'What is the dosage?'", table_cell), Paragraph("Extract factual detail from digest; answer concisely; repeat low-friction CTA.", table_cell)],
        [Paragraph("<b>AUTO_REPLY_DETECTED</b>", table_cell_bold), Paragraph("Simulated automated greeting received", table_cell), Paragraph("Increment auto_reply_count; back off (no response or gentle 1-time acknowledgment); terminate after 2 turns.", table_cell)],
        [Paragraph("<b>HOSTILE_OPT_OUT</b>", table_cell_bold), Paragraph("Merchant replies 'Stop messaging me'", table_cell), Paragraph("Acknowledge respectfully; record suppression in DB; terminate conversation.", table_cell)],
    ]
    rep_t = Table(reply_state_data, colWidths=[115, 135, 254])
    rep_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(rep_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("17. Customer-Facing Engagement Flow (Phase 4)", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))
    story.append(Paragraph(
        "In Phase 4, Vera expands to consumer-facing engagement. While merchant messaging focuses on business enablement and clinical insights, customer messaging focuses on <b>personalized offers, loyalty rewards, re-engagement, and service reminders</b> grounded in CustomerContext preferences.",
        body_style
    ))

    cust_diff_data = [
        [Paragraph("<b>ATTRIBUTE</b>", table_header), Paragraph("<b>MERCHANT-FACING VERA</b>", table_header), Paragraph("<b>CUSTOMER-FACING VERA</b>", table_header)],
        [Paragraph("<b>Audience & Persona</b>", table_cell_bold), Paragraph("Business owners, clinic directors, salon founders.", table_cell), Paragraph("End consumers, patients, diners, gym members.", table_cell)],
        [Paragraph("<b>Tone & Voice</b>", table_cell_bold), Paragraph("Peer-clinical, collegial, ROI-focused, respectful.", table_cell), Paragraph("Warm, inviting, concise, value-oriented.", table_cell)],
        [Paragraph("<b>Primary Triggers</b>", table_cell_bold), Paragraph("research_digest, churn_risk, ctr_drop, view_spike.", table_cell), Paragraph("visit_lapse, birthday, festival_offer, voucher_drop.", table_cell)],
        [Paragraph("<b>CTA Goal</b>", table_cell_bold), Paragraph("Approve draft campaign, audit protocol, update offer.", table_cell), Paragraph("Book appointment, claim voucher, order now.", table_cell)],
    ]
    cust_t = Table(cust_diff_data, colWidths=[110, 197, 197])
    cust_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4338CA")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#4338CA")),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(cust_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 11: SECTIONS 18 & 19
    # =========================================================================
    story.append(Paragraph("18. Project Roadmap (Phases 1 to 6)", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    roadmap_data = [
        [Paragraph("<b>PHASE</b>", table_header), Paragraph("<b>GOAL & KEY DELIVERABLES</b>", table_header), Paragraph("<b>STATUS</b>", table_header)],
        [Paragraph("<b>Phase 1: Foundation</b>", table_cell_bold), Paragraph("FastAPI app scaffolding, Pydantic contracts, SQLite context store with 409 stale version rejection, healthz and metadata endpoints.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<b>Phase 2A: Analysis</b>", table_cell_bold), Paragraph("Deep-dive specification analysis of research_digest trigger, failure modes, and 10 adversarial variations.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<b>Phase 2B: Initial Flow</b>", table_cell_bold), Paragraph("First end-to-end research_digest flow connected to /v1/tick and SQLite suppression tracking.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<b>Phase 2B.1: Hardening</b>", table_cell_bold), Paragraph("Eliminated all hardcoding, multi-tenant suppression, word-boundary taboos, generic journal hooks, dynamic category salutations, 20-action cap.", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<b>Phase 2B.2: Integration Gate</b>", table_cell_bold), Paragraph("Full 355 context warmup, simulator compatibility, persistence restart checks, latency profiling (34/34 tests passing).", table_cell), make_badge("COMPLETE", "#16A34A")],
        [Paragraph("<b>Phase 3: Reply Engine</b>", table_cell_bold), Paragraph("Intelligent multi-turn /v1/reply handler, auto-reply backoff, YES action execution, hostile opt-out recording.", table_cell), make_badge("READY TO START", "#2563EB")],
        [Paragraph("<b>Phase 4: Remaining Triggers</b>", table_cell_bold), Paragraph("Churn risk, view spike, festival offers, customer-facing outreach flows.", table_cell), make_badge("PLANNED", "#64748B")],
        [Paragraph("<b>Phase 5: LLM Integration</b>", table_cell_bold), Paragraph("Sandwich LLM paraphrase layer, replay validation against full test pairs.", table_cell), make_badge("PLANNED", "#64748B")],
        [Paragraph("<b>Phase 6: Submission</b>", table_cell_bold), Paragraph("Final Docker build, container validation, submission package delivery.", table_cell), make_badge("PLANNED", "#64748B")],
    ]
    road_t = Table(roadmap_data, colWidths=[115, 299, 90])
    road_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 2.2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(road_t)
    story.append(Spacer(1, 6))

    story.append(Paragraph("19. 'Where We Are Right Now' Executive Snapshot", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    snap_box_data = [
        [Paragraph("<b>QUESTION</b>", table_header), Paragraph("<b>EXACT CURRENT STATE (VERIFIED AGAINST REPOSITORY)</b>", table_header)],
        [Paragraph("<b>What Exists?</b>", table_cell_bold), Paragraph("A fully operational, lightweight FastAPI service with ACID SQLite storage, typed Pydantic models, deterministic salutation and composition engines, and 34 automated unit and integration tests.", table_cell)],
        [Paragraph("<b>What Works?</b>", table_cell_bold), Paragraph("Context ingestion (all 4 scopes), version conflict handling (409 on stale version), multi-merchant suppression deduplication, research_digest tick message synthesis, topic-aware CTAs, and sub-10ms response times.", table_cell)],
        [Paragraph("<b>What Are We Testing?</b>", table_cell_bold), Paragraph("Full warmup with 355 contexts, adversarial edge cases (expired triggers, category mismatches, opt-out history, missing owner names, taboo boundary safety, action caps), and official judge simulator compatibility.", table_cell)],
        [Paragraph("<b>What Is Still A Stub?</b>", table_cell_bold), Paragraph("<code>POST /v1/reply</code> currently returns a compliant stub (action='end'). Intelligent multi-turn conversational replies and auto-reply backoff are intentionally scheduled for Phase 3.", table_cell)],
        [Paragraph("<b>What Are We NOT Building Yet?</b>", table_cell_bold), Paragraph("We are intentionally NOT adding vector databases, Redis, multi-agent frameworks, or ungrounded LLM prompts. We keep the core engine deterministic, robust, and fast first.", table_cell)],
        [Paragraph("<b>What Comes Next?</b>", table_cell_bold), Paragraph("<b>Phase 3: Multi-turn Reply Engine</b> — implementing the conversation state machine, positive execution transitions, and auto-reply loop termination.", table_cell)],
        [Paragraph("<b>What Must NEVER Be Forgotten?</b>", table_cell_bold), Paragraph("<b>Ground every response strictly in received context. Never hardcode sample data. Make Vera hard to break before making Vera fancy.</b>", table_cell_bold)],
    ]
    snap_t = Table(snap_box_data, colWidths=[130, 374])
    snap_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(snap_t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 12: SECTION 20 (MASTER PRINCIPLE & GLOSSARY)
    # =========================================================================
    story.append(Paragraph("20. Final Master Rule & Glossary of Vera Terms", h1_style))
    story.append(HRFlowable(width="100%", thickness=0.75, color=PRIMARY, spaceBefore=1, spaceAfter=5))

    glossary_data = [
        [Paragraph("<b>TERM</b>", table_header), Paragraph("<b>DEFINITION IN THE VERA ENGINE</b>", table_header)],
        [Paragraph("<b>CategoryContext</b>", table_cell_bold), Paragraph("Vertical-level context setting the communication voice, vocabulary rules, allowed/taboo terms, and research digest library.", table_cell)],
        [Paragraph("<b>MerchantContext</b>", table_cell_bold), Paragraph("Account-level context capturing identity, owner name, locality, subscription status, performance metrics, and cohort signals.", table_cell)],
        [Paragraph("<b>TriggerContext</b>", table_cell_bold), Paragraph("Event signal specifying trigger kind, urgency, expiration, and suppression key.", table_cell)],
        [Paragraph("<b>Suppression Key</b>", table_cell_bold), Paragraph("Unique deduplication key scoped per merchant <code>(suppression_key, merchant_id)</code> to prevent repeat messages.", table_cell)],
        [Paragraph("<b>Gating</b>", table_cell_bold), Paragraph("Deterministic pre-composition checks (expiry, category match, opt-out, subscription, suppression) returning safe no-ops on failure.", table_cell)],
        [Paragraph("<b>Factual Grounding</b>", table_cell_bold), Paragraph("Strict rule that every number, statistic, journal name, and claim in the message body must originate from provided context.", table_cell)],
        [Paragraph("<b>Topic-Aware CTA</b>", table_cell_bold), Paragraph("Call-to-action tailored to the digest item kind (compliance checklist, tech workflow, cde credits, or patient education WhatsApp).", table_cell)],
    ]
    glo_t = Table(glossary_data, colWidths=[120, 384])
    glo_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('BACKGROUND', (0, 1), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COL),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#1E293B")),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(glo_t)
    story.append(Spacer(1, 10))

    master_rule_box = """
    <div align="center">
    <b>THE VERA MASTER PRINCIPLE</b><br/>
    <i>"Do not build Vera to answer the visible examples.<br/>
    Build Vera so that the visible examples are merely natural consequences of correct, generalized rules."</i>
    </div>
    """
    story.append(make_callout(master_rule_box, bg_color="#FEF3C7", border_color="#F59E0B", title="FINAL ARCHITECTURAL LAW"))

    # Build Document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF Successfully Generated at: {OUTPUT_PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
