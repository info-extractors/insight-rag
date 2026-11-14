import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable


class HRule(Flowable):
    """Guaranteed vector horizontal rule that never gets swallowed by adjacent tables."""
    def __init__(self, width=556, thickness=0.7, color=colors.HexColor("#0F172A"), space_after=1.8):
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
    # Dimensions: 612 x 792 pt. Margins: 28 pt left/right, 18 pt top/bottom -> usable width = 556 pt
    margin_lr = 28
    margin_tb = 18
    usable_width = 612 - (2 * margin_lr)  # 556 pt

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

    # Typography styles
    name_style = ParagraphStyle(
        "Name",
        fontName="Times-Bold",
        fontSize=20,
        leading=21.5,
        alignment=1,
        textColor=PRIMARY
    )

    contact_style = ParagraphStyle(
        "Contact",
        fontName="Times-Roman",
        fontSize=8.6,
        leading=11.2,
        alignment=1,
        textColor=TEXT_MUTED
    )

    section_title_style = ParagraphStyle(
        "SectionTitle",
        fontName="Times-Bold",
        fontSize=9.8,
        leading=11.2,
        textColor=PRIMARY
    )

    item_title_style = ParagraphStyle(
        "ItemTitle",
        fontName="Times-Bold",
        fontSize=9.1,
        leading=10.8,
        textColor=PRIMARY
    )

    item_meta_style = ParagraphStyle(
        "ItemMeta",
        fontName="Times-Bold",
        fontSize=8.6,
        leading=10.8,
        alignment=2,
        textColor=PRIMARY
    )

    item_sub_style = ParagraphStyle(
        "ItemSub",
        fontName="Times-Italic",
        fontSize=8.6,
        leading=10.6,
        textColor=TEXT_DARK
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        fontName="Times-Roman",
        fontSize=8.4,
        leading=10.2,
        textColor=TEXT_DARK,
        leftIndent=10,
        firstLineIndent=-10,
        alignment=4
    )

    skills_style = ParagraphStyle(
        "Skills",
        fontName="Times-Roman",
        fontSize=8.45,
        leading=10.7,
        textColor=TEXT_DARK
    )

    def section_header(title: str):
        return [
            Paragraph(f"<b>{title.upper()}</b>", section_title_style),
            HRule(width=usable_width, thickness=0.7, color=colors.HexColor("#0F172A"), space_after=1.8)
        ]

    story = []

    # 1. Header
    story.append(Paragraph("RESHAB SHARMA", name_style))
    story.append(Spacer(1, 1))
    
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
    story.append(Spacer(1, 2.5))

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
    t_edu = Table(edu_data, colWidths=[360, 196])
    t_edu.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_edu)
    story.append(Spacer(1, 2.5))

    # 3. Technical Skills
    story.extend(section_header("Technical Skills"))
    skills_text = (
        "<b>Languages:</b> Python, C++, SQL, JavaScript, C<br/>"
        "<b>Machine Learning &amp; GenAI:</b> PyTorch, Hugging Face, Transformers, LightGBM, Scikit-Learn, ChromaDB, Okapi BM25, Cross-Encoders, RAG, TreeSHAP, Causal Elasticity<br/>"
        "<b>Backend &amp; MLOps:</b> FastAPI, Streamlit, Node.js, Express, REST APIs, Docker, PostgreSQL, MongoDB, Git, GitHub Actions, Linux, ONNX Runtime<br/>"
        "<b>Data Engineering &amp; Coordination:</b> Pandas, NumPy, SciPy, Statistical Inference, Constrained Optimization, Feature Engineering, Agile/Scrum, JIRA"
    )
    story.append(Paragraph(skills_text, skills_style))
    story.append(Spacer(1, 2.5))

    # 4. Experience (At least 4 pointers per role)
    story.extend(section_header("Experience"))

    # Telgoo5 (4 pointers)
    exp1_data = [
        [
            Paragraph("<b>Telgoo5</b> &nbsp;|&nbsp; <i>Project Coordinator</i>", item_title_style),
            Paragraph("Remote / Hybrid &nbsp;|&nbsp; Oct 2024 – Feb 2025", item_meta_style)
        ]
    ]
    t_exp1 = Table(exp1_data, colWidths=[360, 196])
    t_exp1.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_exp1)
    story.append(Spacer(1, 1))
    story.append(Paragraph("• Coordinated sprint roadmaps and cross-functional deliverables between product managers, engineering teams, and client stakeholders.", bullet_style))
    story.append(Paragraph("• Tracked release milestones, managed task backlogs in JIRA, and facilitated daily technical standups ensuring on-time feature deployments.", bullet_style))
    story.append(Paragraph("• Streamlined QA bug tracking and deployment verification cycles, reducing feature integration turnaround time across releases.", bullet_style))
    story.append(Paragraph("• Authored technical workflow documentation and release notes to maintain operational alignment across distributed engineering teams.", bullet_style))
    story.append(Spacer(1, 2))

    # Freelance Backend Developer (4 pointers)
    exp2_data = [
        [
            Paragraph("<b>Freelance Backend Developer</b> &nbsp;|&nbsp; <i>Contract Client Solutions</i>", item_title_style),
            Paragraph("Remote, India &nbsp;|&nbsp; March 2025 – Sept 2025", item_meta_style)
        ]
    ]
    t_exp2 = Table(exp2_data, colWidths=[360, 196])
    t_exp2.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_exp2)
    story.append(Spacer(1, 1))
    story.append(Paragraph("• Architected and deployed scalable RESTful backend services using Node.js, Express, and PostgreSQL for client web platforms.", bullet_style))
    story.append(Paragraph("• Implemented relational database schemas, query optimizations, and connection pooling to ensure low-latency response times under load.", bullet_style))
    story.append(Paragraph("• Built secure JWT authentication, role-based access control (RBAC), and robust input validation guardrails for client APIs.", bullet_style))
    story.append(Paragraph("• Collaborated directly with frontend teams to integrate dynamic APIs and ensure end-to-end performance and reliable uptime.", bullet_style))
    story.append(Spacer(1, 2.5))

    # 5. Projects (4 pointers per project)
    story.extend(section_header("Projects"))

    def project_header_table(title_bold: str, tech_italic: str, year: str, repo_url: str):
        left_p = Paragraph(f"<b>{title_bold}</b> &nbsp;|&nbsp; <i>{tech_italic}</i>", item_title_style)
        right_p = Paragraph(f'{year} &nbsp;|&nbsp; <font color="#0969DA"><a href="{repo_url}">GitHub</a></font>', item_meta_style)
        t = Table([[left_p, right_p]], colWidths=[460, 96])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return t

    # Project 1: InsightRAG (4 bullets)
    story.append(project_header_table(
        "InsightRAG — Multimodal RAG & Document Intelligence Platform",
        "ChromaDB, BM25, Qwen 2.5, Streamlit",
        "2026",
        "https://github.com/info-extractors/insight-rag"
    ))
    story.append(Spacer(1, 0.8))
    story.append(Paragraph("• Architected a layout-aware Multimodal RAG platform preserving tabular Markdown and SEC 10-K financial reports without context fragmentation.", bullet_style))
    story.append(Paragraph("• Engineered a hybrid retrieval engine fusing Dense ChromaDB vector search with Okapi BM25 keyword search via Reciprocal Rank Fusion (k=60) and Cross-Encoder neural reranking.", bullet_style))
    story.append(Paragraph("• Integrated local CPU-optimized Qwen 2.5 0.5B inference for an 8GB RAM footprint with greedy decoding and inference caching.", bullet_style))
    story.append(Paragraph("• Implemented automated citation auditing and numerical hallucination guardrails, benchmarked via automated RAG Triad evaluation metrics.", bullet_style))
    story.append(Spacer(1, 2))

    # Project 2: PriceOptima (4 bullets)
    story.append(project_header_table(
        "PriceOptima — Dynamic Pricing & Demand Elasticity Engine",
        "LightGBM, SciPy, FastAPI, Streamlit",
        "2026",
        "https://github.com/info-extractors/PriceOptima"
    ))
    story.append(Spacer(1, 0.8))
    story.append(Paragraph("• Formulated an econometric log-log causal estimator extracting price elasticity of demand and 95% confidence intervals across multi-SKU retail catalogs.", bullet_style))
    story.append(Paragraph("• Trained a LightGBM non-linear demand regressor achieving R² = 0.942 and WAPE = 9.68% on an out-of-sample temporal holdout test set.", bullet_style))
    story.append(Paragraph("• Built a prescriptive profit optimizer with margin floors (&ge; 15%) and inventory caps, driving a +24.8% net portfolio gross profit uplift.", bullet_style))
    story.append(Paragraph("• Deployed an interactive multi-scenario Streamlit simulator and FastAPI REST service delivering sub-4ms pricing recommendation inferences.", bullet_style))
    story.append(Spacer(1, 2))

    # Project 3: Customer Intent Prediction (4 bullets)
    story.append(project_header_table(
        "Customer Intent Prediction Engine",
        "Scikit-Learn, XGBoost, Pandas, Imbalanced Learning",
        "2024",
        "https://github.com/info-extractors/Customer-Intent-prediction-using-machine-learning"
    ))
    story.append(Spacer(1, 0.8))
    story.append(Paragraph("• Developed an end-to-end predictive classification pipeline forecasting e-commerce purchase intent from behavioral and demographic signals.", bullet_style))
    story.append(Paragraph("• Engineered interaction features, addressed extreme class imbalance using cost-sensitive learning, and conducted cross-validation hyperparameter tuning.", bullet_style))
    story.append(Paragraph("• Conducted Stratified K-Fold validation to guarantee model generalization and stability across diverse customer demographic segments.", bullet_style))
    story.append(Paragraph("• Analyzed feature importances and decision boundaries using SHAP attribution metrics to provide interpretable marketing decision insights.", bullet_style))
    story.append(Spacer(1, 2.5))

    # 6. Achievements
    story.extend(section_header("Achievements & Competitive Programming"))
    story.append(Paragraph("• <b>LeetCode Problem Solving:</b> Solved <b>900+</b> algorithmic problems across data structures, dynamic programming, graphs, and system algorithms.", bullet_style))
    story.append(Paragraph("• <b>Contest Rating:</b> Achieved <b>1600+</b> contest rating on LeetCode; active competitive programmer on Codeforces (Handle: <i>alwaysAnewbie</i>).", bullet_style))

    doc.build(story)
    print(f"Compiled clean single-page PDF resume to {output_path}")

if __name__ == "__main__":
    out_pdf = Path(r"C:\Users\resha\Downloads\Machine Learning Project 1\Reshab_Sharma_Resume_Latest.pdf")
    build_pdf(str(out_pdf))
    # Also attempt updating original if not locked
    orig_pdf = Path(r"C:\Users\resha\Downloads\Machine Learning Project 1\Reshab_Sharma_Resume.pdf")
    try:
        import shutil
        shutil.copy2(out_pdf, orig_pdf)
        print("Updated Reshab_Sharma_Resume.pdf as well.")
    except Exception as e:
        print(f"Note: Original file in use by editor. Reshab_Sharma_Resume_Latest.pdf is ready.")

