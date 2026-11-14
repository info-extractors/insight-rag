import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable


class HRule(Flowable):
    """Guaranteed vector horizontal rule that never gets swallowed by adjacent tables."""
    def __init__(self, width=548, thickness=0.8, color=colors.HexColor("#1F2937"), space_after=3.5):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color
        self.space_after = space_after

    def wrap(self, availWidth, availHeight):
        return self.width, self.thickness + self.space_after

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.space_after, self.width, self.space_after)
        self.canv.restoreState()


def build_pdf(output_path: str):
    margin_lr = 32
    margin_tb = 24
    usable_width = 612 - (2 * margin_lr)  # 548 pt

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=margin_lr,
        rightMargin=margin_lr,
        topMargin=margin_tb,
        bottomMargin=margin_tb
    )

    PRIMARY = colors.HexColor("#000000")
    TEXT_DARK = colors.HexColor("#111827")
    TEXT_MUTED = colors.HexColor("#374151")
    LINK_BLUE = colors.HexColor("#0969DA")

    # Typography styles
    name_style = ParagraphStyle(
        "Name",
        fontName="Times-Bold",
        fontSize=21.5,
        leading=23,
        alignment=1,
        textColor=PRIMARY
    )

    contact_style = ParagraphStyle(
        "Contact",
        fontName="Times-Roman",
        fontSize=9.2,
        leading=12.5,
        alignment=1,
        textColor=TEXT_MUTED
    )

    section_title_style = ParagraphStyle(
        "SectionTitle",
        fontName="Times-Bold",
        fontSize=10.8,
        leading=12.5,
        textColor=PRIMARY
    )

    item_title_style = ParagraphStyle(
        "ItemTitle",
        fontName="Times-Bold",
        fontSize=9.6,
        leading=11.8,
        textColor=PRIMARY
    )

    item_meta_style = ParagraphStyle(
        "ItemMeta",
        fontName="Times-Bold",
        fontSize=9.2,
        leading=11.8,
        alignment=2,
        textColor=PRIMARY
    )

    item_sub_style = ParagraphStyle(
        "ItemSub",
        fontName="Times-Italic",
        fontSize=9.2,
        leading=11.5,
        textColor=TEXT_DARK
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        fontName="Times-Roman",
        fontSize=9.05,
        leading=11.5,
        textColor=TEXT_DARK,
        leftIndent=11,
        firstLineIndent=-11,
        alignment=4
    )

    skills_style = ParagraphStyle(
        "Skills",
        fontName="Times-Roman",
        fontSize=9.1,
        leading=12.2,
        textColor=TEXT_DARK
    )

    def section_header(title: str):
        return [
            Paragraph(f"<b>{title.upper()}</b>", section_title_style),
            HRule(width=usable_width, thickness=0.8, color=colors.HexColor("#0F172A"), space_after=3)
        ]

    story = []

    # 1. Header
    story.append(Paragraph("RESHAB SHARMA", name_style))
    story.append(Spacer(1, 2.5))
    
    contacts = (
        'Greater Noida, Delhi NCR, India &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="tel:+919103380852">+91-9103380852</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="mailto:reshabsharma2345@gmail.com">reshabsharma2345@gmail.com</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://linkedin.com/in/reshab-sharma-1198a8335/">LinkedIn</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://github.com/info-extractors">GitHub</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://leetcode.com/u/ReshabSharma/">LeetCode</a></font> &nbsp;|&nbsp; '
        '<font color="#0969DA"><a href="https://codeforces.com/profile/alwaysAnewbie">Codeforces</a></font>'
    )
    story.append(Paragraph(contacts, contact_style))
    story.append(Spacer(1, 4))

    # 2. Education
    story.extend(section_header("Education"))
    edu_data = [
        [
            Paragraph("<b>Sharda University</b>", item_title_style),
            Paragraph("Greater Noida, UP &nbsp;|&nbsp; 2023 – 2027 (Expected)", item_meta_style)
        ],
        [
            Paragraph("Bachelor of Technology in Computer Science and Engineering &nbsp;|&nbsp; <b>CGPA: 9.2 / 10.0</b>", item_sub_style),
            Paragraph("", item_meta_style)
        ]
    ]
    t_edu = Table(edu_data, colWidths=[360, 188])
    t_edu.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_edu)
    story.append(Spacer(1, 4.5))

    # 3. Technical Skills
    story.extend(section_header("Technical Skills"))
    skills_text = (
        "<b>Languages:</b> Python, C++, SQL, JavaScript, C<br/>"
        "<b>Machine Learning &amp; GenAI:</b> PyTorch, Hugging Face, Transformers, LightGBM, Scikit-Learn, ChromaDB, Okapi BM25, Cross-Encoders, Causal Elasticity, TreeSHAP<br/>"
        "<b>Backend &amp; Cloud/MLOps:</b> FastAPI, Streamlit, Docker, REST APIs, PostgreSQL, MongoDB, Git, GitHub Actions, Linux, ONNX Runtime<br/>"
        "<b>Data Engineering &amp; Math:</b> Pandas, NumPy, SciPy, Statistical Hypothesis Testing, Constrained Optimization, Feature Engineering"
    )
    story.append(Paragraph(skills_text, skills_style))
    story.append(Spacer(1, 4.5))

    # 4. Experience
    story.extend(section_header("Experience"))
    exp_data = [
        [
            Paragraph("<b>Freelance Backend Developer</b> &nbsp;|&nbsp; <i>Contract Client Solutions</i>", item_title_style),
            Paragraph("Remote, India &nbsp;|&nbsp; March 2025 – Sept 2025", item_meta_style)
        ]
    ]
    t_exp = Table(exp_data, colWidths=[360, 188])
    t_exp.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_exp)
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("• Architected and deployed scalable RESTful backend services using Node.js, Express, and PostgreSQL for client web platforms.", bullet_style))
    story.append(Paragraph("• Implemented relational database schemas, secure authentication workflows, and high-throughput API endpoints to serve real-time requests.", bullet_style))
    story.append(Paragraph("• Collaborated directly with frontend teams to integrate APIs with responsive web interfaces, improving system maintainability and uptime.", bullet_style))
    story.append(Spacer(1, 4.5))

    # 5. Projects
    story.extend(section_header("Projects"))

    def project_header_table(title_bold: str, tech_italic: str, year: str, repo_url: str):
        left_p = Paragraph(f"<b>{title_bold}</b> &nbsp;|&nbsp; <i>{tech_italic}</i>", item_title_style)
        right_p = Paragraph(f'{year} &nbsp;|&nbsp; <font color="#0969DA"><a href="{repo_url}">GitHub</a></font>', item_meta_style)
        t = Table([[left_p, right_p]], colWidths=[452, 96])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return t

    # Project 1: InsightRAG
    story.append(project_header_table(
        "InsightRAG — Multimodal RAG & Document Intelligence Platform",
        "ChromaDB, BM25, Qwen 2.5, Streamlit",
        "2026",
        "https://github.com/info-extractors/insight-rag"
    ))
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("• Architected a layout-aware Multimodal RAG platform preserving tabular Markdown and SEC 10-K financial reports without context fragmentation.", bullet_style))
    story.append(Paragraph("• Engineered a hybrid retrieval engine fusing Dense ChromaDB vector search with Okapi BM25 keyword search via Reciprocal Rank Fusion (k=60) and Cross-Encoder neural reranking.", bullet_style))
    story.append(Paragraph("• Integrated local CPU-optimized Qwen 2.5 0.5B inference for an 8GB RAM footprint, backed by automated citation auditing and numerical hallucination guardrails.", bullet_style))
    story.append(Spacer(1, 4))

    # Project 2: PriceOptima
    story.append(project_header_table(
        "PriceOptima — Dynamic Pricing & Demand Elasticity Engine",
        "LightGBM, SciPy, FastAPI, Streamlit",
        "2026",
        "https://github.com/info-extractors/PriceOptima"
    ))
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("• Formulated an econometric log-log causal estimator extracting price elasticity of demand and 95% confidence intervals across multi-SKU retail catalogs.", bullet_style))
    story.append(Paragraph("• Trained a LightGBM non-linear demand regressor achieving R² = 0.942 and WAPE = 9.68% on an out-of-sample temporal holdout test set.", bullet_style))
    story.append(Paragraph("• Built a prescriptive profit optimizer with margin floors (&ge; 15%) and inventory caps, driving a +24.8% net portfolio gross profit uplift.", bullet_style))
    story.append(Spacer(1, 4))

    # Project 3: Customer Intent Prediction
    story.append(project_header_table(
        "Customer Intent Prediction Engine",
        "Scikit-Learn, XGBoost, Pandas, Imbalanced Learning",
        "2024",
        "https://github.com/info-extractors/Customer-Intent-prediction-using-machine-learning"
    ))
    story.append(Spacer(1, 1.5))
    story.append(Paragraph("• Developed an end-to-end predictive classification pipeline forecasting e-commerce purchase intent from behavioral and demographic signals.", bullet_style))
    story.append(Paragraph("• Engineered interaction features, addressed extreme class imbalance using cost-sensitive learning, and conducted cross-validation hyperparameter tuning.", bullet_style))
    story.append(Paragraph("• Analyzed feature importances and decision boundaries using SHAP attribution metrics to provide interpretable marketing decision insights.", bullet_style))
    story.append(Spacer(1, 4.5))

    # 6. Certifications & Problem Solving
    story.extend(section_header("Certifications & Problem Solving"))
    story.append(Paragraph("• <b>Competitive Programming:</b> Active problem solver across LeetCode, Codeforces, and GeeksforGeeks; solid foundations in algorithms and data structures.", bullet_style))
    story.append(Paragraph('• <b>Mastering Data Structures &amp; Algorithms</b> — Udemy Verified Certification (<font color="#0969DA"><a href="https://www.udemy.com/certificate/UC-c0e8dc21-8e8b-4f6e-9d05-5d109a9523cd/">Credential Link</a></font>)', bullet_style))
    story.append(Paragraph('• <b>C++ Advanced Programming</b> — Udemy Verified Certification (<font color="#0969DA"><a href="https://www.udemy.com/certificate/UC-b732c216-80d9-448c-b5fd-42b4aa7ca0ee/">Credential Link</a></font>)', bullet_style))

    doc.build(story)
    print(f"Compiled clean single-page PDF resume to {output_path}")

if __name__ == "__main__":
    out_pdf = Path(r"C:\Users\resha\Downloads\Machine Learning Project 1\Reshab_Sharma_Resume.pdf")
    build_pdf(str(out_pdf))
