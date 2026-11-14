import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
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
            # Only 1 page expected
            super().showPage()
        super().save()


def build_pdf(output_path: str):
    # Standard 1-page resume dimensions (letter size with 32pt / ~0.44in margins)
    margin = 32
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=26,
        bottomMargin=26
    )

    styles = getSampleStyleSheet()

    # Color palette
    PRIMARY_COLOR = colors.HexColor("#0F172A")    # Deep slate
    ACCENT_COLOR = colors.HexColor("#1E293B")     # Dark slate
    MUTED_COLOR = colors.HexColor("#475569")      # Muted gray
    LINK_COLOR = colors.HexColor("#0969DA")       # GitHub blue

    # Typography styles
    name_style = ParagraphStyle(
        "Name",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=22,
        alignment=1, # Center
        textColor=PRIMARY_COLOR
    )

    contact_style = ParagraphStyle(
        "Contact",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        alignment=1, # Center
        textColor=MUTED_COLOR
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=12.5,
        textColor=PRIMARY_COLOR,
        spaceBefore=0,
        spaceAfter=0
    )

    subhead_title_style = ParagraphStyle(
        "SubheadTitle",
        fontName="Helvetica-Bold",
        fontSize=9.2,
        leading=11.5,
        textColor=ACCENT_COLOR
    )

    subhead_right_style = ParagraphStyle(
        "SubheadRight",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        alignment=2, # Right
        textColor=MUTED_COLOR
    )

    subhead_subtitle_style = ParagraphStyle(
        "SubheadSubtitle",
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11,
        textColor=ACCENT_COLOR
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.8,
        textColor=ACCENT_COLOR,
        leftIndent=12,
        firstLineIndent=-12
    )

    skills_style = ParagraphStyle(
        "Skills",
        fontName="Helvetica",
        fontSize=8.3,
        leading=11.2,
        textColor=ACCENT_COLOR
    )

    story = []

    # 1. Header (Name & Contact Details)
    story.append(Paragraph("RESHAB SHARMA", name_style))
    story.append(Spacer(1, 3))
    
    contact_line = (
        'Greater Noida, Delhi NCR, India &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="tel:+919103380852">+91-9103380852</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="mailto:reshabsharma2345@gmail.com">reshabsharma2345@gmail.com</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://linkedin.com/in/reshab-sharma-1198a8335/">LinkedIn</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://github.com/info-extractors">GitHub</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://leetcode.com/u/ReshabSharma/">LeetCode</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://codeforces.com/profile/alwaysAnewbie">Codeforces</a></font>'
    )
    story.append(Paragraph(contact_line, contact_style))
    story.append(Spacer(1, 5))

    def make_section(title: str):
        return [
            Paragraph(title.upper(), section_header_style),
            Spacer(1, 1),
            HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=4)
        ]

    # 2. Education
    story.extend(make_section("Education"))
    edu_table_data = [
        [
            Paragraph("<b>Sharda University</b>", subhead_title_style),
            Paragraph("Greater Noida, UP | 2023 – 2027 (Expected)", subhead_right_style)
        ],
        [
            Paragraph("Bachelor of Technology in Computer Science and Engineering &nbsp;|&nbsp; <b>CGPA: 9.2 / 10.0</b>", subhead_subtitle_style),
            Paragraph("", subhead_right_style)
        ]
    ]
    t_edu = Table(edu_table_data, colWidths=[380, 168])
    t_edu.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_edu)
    story.append(Spacer(1, 5))

    # 3. Technical Skills
    story.extend(make_section("Technical Skills"))
    skills_text = (
        "<b>Languages:</b> Python, C++, SQL, JavaScript, C<br/>"
        "<b>Machine Learning & GenAI:</b> PyTorch, Hugging Face, Transformers, LightGBM, Scikit-Learn, ChromaDB, Okapi BM25, Cross-Encoder Reranking, Causal Elasticity, TreeSHAP<br/>"
        "<b>Backend & Cloud/MLOps:</b> FastAPI, Streamlit, Docker, REST APIs, PostgreSQL, MongoDB, Git, GitHub Actions, Linux, ONNX Runtime<br/>"
        "<b>Data Engineering & Math:</b> Pandas, NumPy, SciPy, Statistical Inference, Hypothesis Testing, Prescriptive Optimization, Feature Engineering"
    )
    story.append(Paragraph(skills_text, skills_style))
    story.append(Spacer(1, 5))

    # 4. Work Experience
    story.extend(make_section("Experience"))
    exp_table_data = [
        [
            Paragraph("<b>Freelance Backend Developer</b> &nbsp;|&nbsp; <i>Contract Solutions</i>", subhead_title_style),
            Paragraph("Remote, India | March 2025 – Sept 2025", subhead_right_style)
        ]
    ]
    t_exp = Table(exp_table_data, colWidths=[370, 178])
    t_exp.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_exp)
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("• Architected and deployed scalable RESTful backend services using Node.js, Express, and PostgreSQL for client applications.", bullet_style))
    story.append(Paragraph("• Implemented database schemas, secure token-based authentication, and optimized API queries to handle concurrent requests.", bullet_style))
    story.append(Paragraph("• Collaborated directly with frontend teams to integrate dynamic APIs and ensure end-to-end performance and reliable uptime.", bullet_style))
    story.append(Spacer(1, 5))

    # 5. Projects
    story.extend(make_section("Projects"))

    # Project 1: InsightRAG
    p1_head = [
        [
            Paragraph('<b>InsightRAG — Enterprise Multimodal RAG Platform</b> &nbsp;|&nbsp; <i>Python, ChromaDB, BM25, Qwen 2.5, Streamlit</i>', subhead_title_style),
            Paragraph('2026 &nbsp;|&nbsp; <font color="#0969DA"><a href="https://github.com/info-extractors/insight-rag">GitHub</a></font>', subhead_right_style)
        ]
    ]
    t_p1 = Table(p1_head, colWidths=[420, 128])
    t_p1.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_p1)
    story.append(Spacer(1, 1))
    story.append(Paragraph("• Architected a layout-aware Multimodal RAG platform preserving multi-column Markdown tables and SEC 10-K financial reports.", bullet_style))
    story.append(Paragraph("• Engineered a hybrid retrieval engine fusing Dense ChromaDB vector search with Okapi BM25 keyword search via Reciprocal Rank Fusion (k=60) and Cross-Encoder neural reranking.", bullet_style))
    story.append(Paragraph("• Integrated local CPU-optimized Qwen 2.5 0.5B inference for an 8GB RAM footprint, backed by automated citation auditing and numerical hallucination guardrails.", bullet_style))
    story.append(Spacer(1, 4))

    # Project 2: PriceOptima
    p2_head = [
        [
            Paragraph('<b>PriceOptima — Dynamic Pricing & Demand Elasticity Engine</b> &nbsp;|&nbsp; <i>Python, LightGBM, SciPy, FastAPI, Streamlit</i>', subhead_title_style),
            Paragraph('2026 &nbsp;|&nbsp; <font color="#0969DA"><a href="https://github.com/info-extractors/PriceOptima">GitHub</a></font>', subhead_right_style)
        ]
    ]
    t_p2 = Table(p2_head, colWidths=[420, 128])
    t_p2.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_p2)
    story.append(Spacer(1, 1))
    story.append(Paragraph("• Formulated an econometric log-log causal estimator extracting price elasticity of demand and 95% confidence intervals across multi-SKU catalogs.", bullet_style))
    story.append(Paragraph("• Trained a LightGBM non-linear demand regressor achieving R² = 0.942 and WAPE = 9.68% on out-of-sample temporal holdout test data.", bullet_style))
    story.append(Paragraph("• Built a prescriptive profit optimizer with margin floors (&ge; 15%) and inventory caps, driving a +24.8% net portfolio gross profit uplift.", bullet_style))
    story.append(Spacer(1, 4))

    # Project 3: Customer Intent Prediction
    p3_head = [
        [
            Paragraph('<b>Customer Intent Prediction Engine</b> &nbsp;|&nbsp; <i>Python, Scikit-Learn, XGBoost, Pandas, Imbalanced Learning</i>', subhead_title_style),
            Paragraph('2024 &nbsp;|&nbsp; <font color="#0969DA"><a href="https://github.com/info-extractors/Customer-Intent-prediction-using-machine-learning">GitHub</a></font>', subhead_right_style)
        ]
    ]
    t_p3 = Table(p3_head, colWidths=[420, 128])
    t_p3.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_p3)
    story.append(Spacer(1, 1))
    story.append(Paragraph("• Developed an end-to-end predictive classification pipeline forecasting e-commerce purchase intent from behavioral and demographic signals.", bullet_style))
    story.append(Paragraph("• Engineered interaction features, addressed extreme class imbalance using cost-sensitive learning, and conducted cross-validation hyperparameter tuning.", bullet_style))
    story.append(Paragraph("• Analyzed feature importances and decision boundaries using SHAP attribution metrics to provide interpretable marketing decision insights.", bullet_style))
    story.append(Spacer(1, 5))

    # 6. Certifications & Achievements
    story.extend(make_section("Certifications & Problem Solving"))
    story.append(Paragraph("• <b>Competitive Programming:</b> Active problem solver across LeetCode, Codeforces, and GeeksforGeeks; solid foundations in data structures and algorithmic complexity.", bullet_style))
    story.append(Paragraph('• <b>Mastering Data Structures & Algorithms</b> — Udemy Verified Certification (<font color="#0969DA"><a href="https://www.udemy.com/certificate/UC-c0e8dc21-8e8b-4f6e-9d05-5d109a9523cd/">Credential</a></font>)', bullet_style))
    story.append(Paragraph('• <b>C++ Advanced Programming</b> — Udemy Verified Certification (<font color="#0969DA"><a href="https://www.udemy.com/certificate/UC-b732c216-80d9-448c-b5fd-42b4aa7ca0ee/">Credential</a></font>)', bullet_style))

    doc.build(story)
    print(f"Successfully generated ATS-compliant PDF resume at: {output_path}")

if __name__ == "__main__":
    out_file = Path(r"C:\Users\resha\Downloads\Machine Learning Project 1\Reshab_Sharma_Resume.pdf")
    build_pdf(str(out_file))
