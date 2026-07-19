"""
AMAZON AI - Document Generator
Generates structured academic/professional documents (assignments, research proposals, reports).
"""
import os
import re
import random
from pathlib import Path
from datetime import datetime, timedelta

try:
    import docx
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


def _sanitize_filename(name):
    """Convert any string to a valid filename."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized[:50].strip('_')


def _add_heading(doc, text, level=1):
    """Add a heading to a Word document."""
    if level == 1:
        heading = doc.add_heading(text, level=1)
    elif level == 2:
        heading = doc.add_heading(text, level=2)
    else:
        heading = doc.add_heading(text, level=3)
    return heading


def _add_paragraph(doc, text, bold=False, italic=False):
    """Add a paragraph with optional styling."""
    p = doc.add_paragraph(text)
    if p.runs:
        run = p.runs[0]
        run.font.size = Pt(12)
        run.font.bold = bold
        run.font.italic = italic
    return p


def _add_page_break(doc):
    """Add a page break to the document."""
    doc.add_page_break()


def _add_source_material_section(doc, source_material=None):
    """Append externally provided source material when available."""
    if not source_material:
        return
    snippet = str(source_material).strip()
    if not snippet:
        return
    _add_heading(doc, "Source-Grounded Notes")
    _add_paragraph(
        doc,
        "The following notes were extracted from user-provided references and used to strengthen this document."
    )
    max_chars = 7000
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars] + " ..."
    # Make long scraped text readable by chunking and preserving key labels.
    normalized = re.sub(r"\s+", " ", snippet).strip()
    for label in ["Source ", "URL:", "About", "Vision", "Mission", "Core Values", "Services"]:
        normalized = normalized.replace(label, f"\n{label}")

    for block in normalized.split("\n"):
        text = block.strip(" -•\t")
        if not text:
            continue
        if len(text) <= 420:
            _add_paragraph(doc, text)
            continue
        # Soft-wrap very long lines into digestible chunks.
        words = text.split()
        chunk = []
        chunk_len = 0
        for w in words:
            if chunk_len + len(w) + 1 > 380:
                _add_paragraph(doc, " ".join(chunk))
                chunk = [w]
                chunk_len = len(w)
            else:
                chunk.append(w)
                chunk_len += len(w) + 1
        if chunk:
            _add_paragraph(doc, " ".join(chunk))


def _extract_source_highlights(source_material, max_points=8):
    """Extract concise highlights from scraped source text."""
    if not source_material:
        return []
    text = re.sub(r"\s+", " ", str(source_material)).strip()
    if not text:
        return []

    points = []

    # Keyword-window extraction (works even when source has poor punctuation)
    lowered = text.lower()
    markers = ["about us", "our vision", "our mission", "our core values", "services"]
    words = text.split()
    for marker in markers:
        idx = lowered.find(marker)
        if idx == -1:
            continue
        prefix_words = len(text[:idx].split())
        window = words[prefix_words:prefix_words + 32]
        candidate = " ".join(window).strip(" :;,-")
        if candidate and candidate not in points:
            points.append(candidate)
        if len(points) >= max_points:
            break

    if len(points) < max_points:
        sentences = re.split(r"(?<=[\.!?])\s+", text)
        for s in sentences:
            s = s.strip()
            if 60 <= len(s) <= 220 and s not in points:
                points.append(s)
            if len(points) >= max_points:
                break

    # Last fallback: fixed-size chunks from source body
    if len(points) < max_points:
        chunks = []
        chunk = []
        for w in words:
            chunk.append(w)
            if len(chunk) >= 26:
                chunks.append(" ".join(chunk))
                chunk = []
            if len(chunks) >= max_points:
                break
        for c in chunks:
            if c not in points:
                points.append(c)
            if len(points) >= max_points:
                break

    return points[:max_points]


def generate_assignment(topic, source_material=None):
    """Generate a complete assignment document with cover page, introduction, questions, and conclusion."""
    if not DOCX_AVAILABLE:
        return {
            "status": "failed",
            "message": "python-docx is not installed. Install it to create Word documents."
        }

    doc = docx.Document()

    # Cover Page
    doc.add_heading(f"Assignment: {topic.title()}", level=0)
    _add_paragraph(doc, f"Generated by AMAZON AI Assistant", italic=True)
    _add_paragraph(doc, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    _add_page_break(doc)

    # Introduction
    _add_heading(doc, "Introduction")
    intro_text = (
        f"This assignment explores the topic of {topic}. "
        f"The subject matter encompasses various aspects of {topic} that are "
        f"crucial for understanding its significance and application in modern contexts. "
        f"Through this assignment, we will examine key concepts, analyze relevant data, "
        f"and develop comprehensive insights into {topic}."
    )
    _add_paragraph(doc, intro_text)

    # Main Questions/Exercises
    _add_heading(doc, "Questions and Exercises")

    questions = [
        f"1. Define and explain the core principles of {topic}.",
        f"2. Analyze the impact of {topic} on contemporary practices.",
        f"3. Compare and contrast different approaches to {topic}.",
        f"4. Provide real-world examples of {topic} in action.",
        f"5. Evaluate the future implications of {topic}."
    ]
    for q in questions:
        _add_paragraph(doc, q, bold=True)
        _add_paragraph(doc, f"   Discussion: This question requires a detailed examination of {topic} "
                        f"considering theoretical foundations and practical applications. "
                        f"The answer should demonstrate understanding of key concepts and provide "
                        f"evidence-based analysis.")
        doc.add_paragraph()

    # Conclusion
    _add_heading(doc, "Conclusion")
    conclusion_text = (
        f"In conclusion, this assignment has examined {topic} from multiple perspectives. "
        f"The analysis reveals that {topic} represents a significant area of study with "
        f"far-reaching implications. Through careful consideration of the questions presented, "
        f"we have gained valuable insights into the fundamental nature of this subject and "
        f"its relevance in today's context."
    )
    _add_paragraph(doc, conclusion_text)

    _add_source_material_section(doc, source_material)
    return doc


def generate_research_proposal(topic, source_material=None):
    """Generate a detailed, dynamic research proposal document."""
    if not DOCX_AVAILABLE:
        return {
            "status": "failed",
            "message": "python-docx is not installed. Install it to create Word documents."
        }

    topic_text = (topic or "Research Topic").strip()
    topic_title = topic_text.title()
    topic_words = [w for w in re.findall(r"[A-Za-z0-9]+", topic_text) if len(w) > 2]
    primary_focus = topic_words[0].lower() if topic_words else "subject"
    current_year = datetime.now().year

    business_terms = {"brand", "market", "consumer", "sales", "product", "retail", "company", "cocacola", "coca", "cola"}
    health_terms = {"health", "nutrition", "sugar", "obesity", "diet", "wellness", "disease"}
    tech_terms = {"ai", "data", "digital", "technology", "automation", "platform", "system"}
    environment_terms = {"climate", "carbon", "water", "waste", "sustainability", "environment"}

    lower_topic = topic_text.lower()
    if any(t in lower_topic for t in business_terms):
        lens = "market and consumer behavior"
        methods = ["consumer survey", "retail trend analysis", "brand sentiment coding", "comparative market mapping"]
        indicators = ["brand preference score", "purchase frequency", "price-sensitivity index", "campaign recall rate"]
    elif any(t in lower_topic for t in health_terms):
        lens = "public health outcomes"
        methods = ["cross-sectional survey", "nutritional profile analysis", "policy review", "risk-factor modeling"]
        indicators = ["intake frequency", "risk exposure index", "awareness score", "behavior-change rate"]
    elif any(t in lower_topic for t in tech_terms):
        lens = "technology adoption and impact"
        methods = ["systematic mapping", "usage telemetry analysis", "stakeholder interviews", "prototype evaluation"]
        indicators = ["adoption rate", "efficiency gain", "error reduction", "user satisfaction"]
    elif any(t in lower_topic for t in environment_terms):
        lens = "environmental sustainability"
        methods = ["life-cycle review", "resource-use analysis", "policy compliance audit", "impact benchmarking"]
        indicators = ["emission intensity", "water-use efficiency", "waste diversion rate", "compliance score"]
    else:
        lens = "multi-dimensional socio-economic impact"
        methods = ["mixed-method survey", "document analysis", "key-informant interviews", "cross-case comparison"]
        indicators = ["effect size", "stakeholder confidence", "implementation readiness", "sustainability index"]

    doc = docx.Document()

    # Cover Page
    _add_heading(doc, "Research Proposal", level=0)
    _add_paragraph(doc, f"Title: {topic_title}")
    _add_paragraph(doc, "Generated by AMAZON AI Assistant", italic=True)
    _add_paragraph(doc, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    _add_page_break(doc)

    # Abstract
    _add_heading(doc, "Abstract")
    abstract_text = (
        f"This proposal examines {topic_text} using a {lens} lens. "
        f"It addresses current evidence gaps, identifies measurable determinants of performance, "
        f"and builds a practical framework for decision-making in {current_year}. "
        f"The project combines quantitative and qualitative methods to produce valid, actionable findings "
        f"for researchers, practitioners, and policy stakeholders."
    )
    _add_paragraph(doc, abstract_text)

    # Introduction
    _add_heading(doc, "1. Introduction")
    intro_text = (
        f"{topic_title} is a relevant and timely domain of inquiry due to shifting stakeholder expectations, "
        f"competitive pressures, and policy changes. This study investigates how {primary_focus} affects outcomes "
        f"across operational, social, and strategic dimensions. The proposal is designed to support both theory "
        f"building and practical interventions."
    )
    _add_paragraph(doc, intro_text)
    _add_paragraph(doc, "Problem Statement", bold=True)
    _add_paragraph(
        doc,
        f"Despite growing attention to {topic_text}, there is limited integrated evidence linking drivers, "
        f"mechanisms, and outcomes in a single analytical model. This gap reduces the quality of planning, "
        f"resource allocation, and long-term strategy."
    )
    _add_paragraph(doc, "Aim and Objectives", bold=True)
    objectives = [
        f"To map the major determinants shaping {topic_text}.",
        f"To quantify relationships between key indicators and observed outcomes.",
        f"To compare patterns across relevant contexts and stakeholder groups.",
        f"To recommend an evidence-based implementation framework."
    ]
    for obj in objectives:
        _add_paragraph(doc, f"• {obj}")

    # Literature Review
    _add_heading(doc, "2. Literature Review")
    lit_text = (
        f"Existing scholarship on {topic_text} reports meaningful progress in defining concepts and "
        f"measurement approaches. However, evidence is often fragmented by sector, geography, or method. "
        f"Prior studies typically emphasize either descriptive trends or isolated interventions, leaving a gap "
        f"in integrative explanations that connect context, mechanism, and impact."
    )
    _add_paragraph(doc, lit_text)
    _add_paragraph(doc, "Identified Knowledge Gaps", bold=True)
    for gap in [
        f"Limited longitudinal evidence on {topic_text} outcomes.",
        "Insufficient triangulation between survey, observational, and documentary data.",
        "Weak translation of findings into deployable strategy and policy guidance."
    ]:
        _add_paragraph(doc, f"• {gap}")

    # Research Questions
    _add_heading(doc, "3. Research Questions")
    questions = [
        f"RQ1: Which structural and behavioral factors most strongly influence {topic_text}?",
        f"RQ2: How do variations in context change outcomes related to {topic_text}?",
        f"RQ3: Which intervention or management approaches produce the highest effect size?",
        f"RQ4: What implementation model best supports sustainable improvement?"
    ]
    for q in questions:
        _add_paragraph(doc, q, bold=True)

    # Methodology
    _add_heading(doc, "4. Methodology")
    _add_paragraph(
        doc,
        f"A convergent mixed-method design will be used to investigate {topic_text}. "
        f"Quantitative and qualitative strands will be executed in parallel and integrated during interpretation."
    )
    _add_paragraph(doc, "Data Collection Methods", bold=True)
    for m in methods:
        _add_paragraph(doc, f"• {m.title()}")
    _add_paragraph(doc, "Key Variables / Indicators", bold=True)
    for kpi in indicators:
        _add_paragraph(doc, f"• {kpi.title()}")
    _add_paragraph(doc, "Sampling and Analysis", bold=True)
    _add_paragraph(
        doc,
        "Participants and data sources will be selected using purposive and stratified criteria to maximize representativeness. "
        "Analysis will include descriptive statistics, correlation/regression checks where appropriate, and thematic coding for interview data."
    )
    _add_paragraph(doc, "Ethical Considerations", bold=True)
    _add_paragraph(
        doc,
        "The study will follow informed consent, privacy protection, secure data handling, and non-maleficence principles. "
        "Sensitive data will be anonymized before analysis and reporting."
    )

    # Timeline
    _add_heading(doc, "5. Timeline")
    start_date = datetime.now()
    timeline_items = [
        ("Phase 1: Scoping, protocol design, and literature synthesis", 0, 14),
        (f"Phase 2: Instrument setup and data collection on {topic_text}", 15, 35),
        ("Phase 3: Data cleaning, analysis, and validation", 36, 56),
        ("Phase 4: Drafting results, discussion, and recommendations", 57, 70),
        ("Phase 5: Final revision, quality check, and submission", 71, 84),
    ]
    for item, start_offset, end_offset in timeline_items:
        phase_start = (start_date + timedelta(days=start_offset)).strftime('%b %d, %Y')
        phase_end = (start_date + timedelta(days=end_offset)).strftime('%b %d, %Y')
        _add_paragraph(doc, f"• {item} ({phase_start} - {phase_end})")

    _add_heading(doc, "6. Expected Outcomes and Impact")
    for outcome in [
        f"A validated evidence map of key drivers affecting {topic_text}.",
        "A practical decision framework for implementation and monitoring.",
        "Clear stakeholder guidance with measurable indicators for follow-up evaluation.",
        "Recommendations that can inform operations, policy, and future research."
    ]:
        _add_paragraph(doc, f"• {outcome}")

    # References
    _add_heading(doc, "7. References")
    ref_items = [
        f"Author, A. (2021). Contemporary perspectives on {topic_title}. Journal of Applied Inquiry, 14(2), 101-126.",
        f"Author, B., & Author, C. (2022). Measurement frameworks for {topic_title}. Research Methods Review, 9(4), 55-79.",
        f"Author, D. (2023). Comparative evidence and implementation pathways in {topic_title}. Policy and Practice Quarterly, 18(1), 1-24.",
        f"Author, E. (2024). Integrated models for strategic decision-making in {topic_title}. Academic Insight Press."
    ]
    for ref in ref_items:
        _add_paragraph(doc, ref)

    _add_source_material_section(doc, source_material)
    return doc


def generate_report(topic, source_material=None):
    """Generate a structured report with executive summary, introduction, findings, analysis, conclusion, and recommendations."""
    if not DOCX_AVAILABLE:
        return {
            "status": "failed",
            "message": "python-docx is not installed. Install it to create Word documents."
        }

    doc = docx.Document()

    # Cover Page
    _add_heading(doc, f"Report: {topic.title()}", level=0)
    _add_paragraph(doc, "Generated by AMAZON AI Assistant", italic=True)
    _add_paragraph(doc, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    _add_page_break(doc)

    # Executive Summary
    _add_heading(doc, "Executive Summary")
    exec_summary = (
        f"This report provides a comprehensive analysis of {topic}. Key findings indicate "
        f"significant trends and patterns that are shaping the current landscape. "
        f"The report examines critical data points, evaluates performance metrics, "
        f"and presents actionable insights for stakeholders. Based on this analysis, "
        f"strategic recommendations are proposed to optimize outcomes and address identified challenges."
    )
    _add_paragraph(doc, exec_summary)
    doc.add_paragraph()

    # Introduction
    _add_heading(doc, "1. Introduction")
    intro_text = (
        f"The purpose of this report is to analyze and present findings on {topic}. "
        f"In an era where understanding {topic} is increasingly important, this report "
        f"serves as a comprehensive resource for decision-makers and stakeholders. "
        f"The scope of this analysis covers multiple dimensions of {topic}, providing "
        f"a holistic view of the current situation and future prospects."
    )
    _add_paragraph(doc, intro_text)

    # Background
    _add_heading(doc, "2. Background")
    bg_text = (
        f"{topic.title()} has emerged as a significant area of focus due to recent developments "
        f"and changing market conditions. Understanding the background and context of {topic} "
        f"is essential for making informed decisions. This section provides the necessary "
        f"contextual information to frame the subsequent analysis and findings."
    )
    _add_paragraph(doc, bg_text)

    # Findings
    _add_heading(doc, "3. Findings")
    findings = [
        f"Finding 1: {topic} demonstrates measurable impact on key performance indicators.",
        f"Finding 2: Trends in {topic} indicate progressive changes over time.",
        f"Finding 3: Comparative analysis reveals insights when {topic} is benchmarked against standards.",
        f"Finding 4: Stakeholder feedback on {topic} shows overall positive reception with areas for improvement."
    ]
    for f in findings:
        _add_paragraph(doc, f, bold=True)
        _add_paragraph(doc, f"   Analysis: This finding suggests that {topic} plays a crucial role "
                        f"in determining outcomes and should be carefully monitored and managed.")
        doc.add_paragraph()

    # Analysis
    _add_heading(doc, "4. Analysis")
    analysis_text = (
        f"The analysis of {topic} reveals several key insights. First, there is a strong "
        f"correlation between {topic} and desired outcomes. Second, implementation challenges "
        f"can be addressed through strategic planning and resource allocation. "
        f"Third, the data suggests potential for optimization and scaling. "
        f"These findings are supported by empirical evidence and stakeholder input."
    )
    _add_paragraph(doc, analysis_text)

    # Conclusion
    _add_heading(doc, "5. Conclusion")
    conclusion_text = (
        f"This report has provided a thorough examination of {topic}. The analysis confirms "
        f"that {topic} remains a critical factor in achieving desired outcomes. "
        f"The findings demonstrate both opportunities and challenges that must be addressed. "
        f"Moving forward, continued attention to {topic} will be essential for sustained success "
        f"and improvement in this area."
    )
    _add_paragraph(doc, conclusion_text)

    # Recommendations
    _add_heading(doc, "6. Recommendations")
    rec_items = [
        f"1. Implement systematic monitoring of {topic} metrics to track progress and identify issues early.",
        f"2. Develop standardized protocols for managing {topic} to ensure consistency.",
        f"3. Invest in training and resources to enhance capabilities related to {topic}.",
        f"4. Establish regular review cycles to evaluate effectiveness of {topic} initiatives.",
        f"5. Create feedback mechanisms to continuously improve approaches to {topic}."
    ]
    for rec in rec_items:
        _add_paragraph(doc, rec)

    # Appendices
    _add_heading(doc, "7. Appendices")
    _add_paragraph(doc, f"Appendix A: Additional data on {topic}")
    _add_paragraph(doc, f"Appendix B: Detailed methodology and sources")
    _add_paragraph(doc, f"Appendix C: Supplementary charts and graphs")

    _add_source_material_section(doc, source_material)
    return doc


def generate_schedule(topic, person_name=None):
    """Generate a training/work schedule document."""
    if not DOCX_AVAILABLE:
        return {
            "status": "failed",
            "message": "python-docx is not installed. Install it to create Word documents."
        }

    doc = docx.Document()
    
    # Determine schedule title
    if person_name:
        schedule_title = f"{person_name}'s {topic}"
    else:
        schedule_title = topic

    # Cover Page
    _add_heading(doc, f"Training Schedule: {schedule_title.title()}", level=0)
    _add_paragraph(doc, "Generated by AMAZON AI Assistant", italic=True)
    _add_paragraph(doc, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    _add_page_break(doc)

    # Overview
    _add_heading(doc, "Schedule Overview")
    overview_text = (
        f"This document outlines the training schedule for {schedule_title}. "
        f"The schedule is designed to provide comprehensive coverage of all necessary topics "
        f"and ensure effective learning outcomes. Each session is structured to build upon "
        f"previous knowledge and provide practical application opportunities."
    )
    _add_paragraph(doc, overview_text)
    doc.add_paragraph()

    # Training Schedule Table
    _add_heading(doc, "Training Sessions")
    
    sessions = [
        {
            "session": "Session 1: Introduction & Fundamentals",
            "duration": "2 hours",
            "topics": [
                "Overview of key concepts and terminology",
                "Understanding the foundational principles",
                "Setting up the work environment",
                "Q&A and discussion"
            ]
        },
        {
            "session": "Session 2: Core Skills Development",
            "duration": "3 hours",
            "topics": [
                "Hands-on practice with core tools",
                "Step-by-step guided exercises",
                "Common challenges and solutions",
                "Progress assessment"
            ]
        },
        {
            "session": "Session 3: Advanced Techniques",
            "duration": "3 hours",
            "topics": [
                "Advanced features and capabilities",
                "Best practices and optimization",
                "Real-world case studies",
                "Problem-solving scenarios"
            ]
        },
        {
            "session": "Session 4: Practical Application",
            "duration": "4 hours",
            "topics": [
                "Project-based learning exercise",
                "Independent work with guidance",
                "Peer collaboration and review",
                "Feedback and improvement"
            ]
        },
        {
            "session": "Session 5: Assessment & Certification",
            "duration": "2 hours",
            "topics": [
                "Final assessment and evaluation",
                "Review of key learnings",
                "Certification and next steps",
                "Resources for continued learning"
            ]
        },
    ]
    
    for session in sessions:
        _add_heading(doc, session["session"], level=2)
        _add_paragraph(doc, f"Duration: {session['duration']}", bold=True)
        _add_paragraph(doc, "Topics Covered:")
        for topic_item in session["topics"]:
            _add_paragraph(doc, f"• {topic_item}")
        doc.add_paragraph()

    # Learning Objectives
    _add_heading(doc, "Learning Objectives")
    objectives = [
        f"Understand the fundamental concepts and principles of {topic}",
        f"Develop practical skills through hands-on exercises",
        f"Apply knowledge to real-world scenarios",
        f"Demonstrate proficiency through assessment",
        f"Identify resources for continued learning and growth"
    ]
    for obj in objectives:
        _add_paragraph(doc, f"✓ {obj}")

    # Prerequisites
    _add_heading(doc, "Prerequisites")
    prerequisites = [
        "Basic computer literacy",
        "Willingness to learn and practice",
        "Commitment to complete all scheduled sessions",
        "Access to required tools and materials"
    ]
    for prereq in prerequisites:
        _add_paragraph(doc, f"• {prereq}")

    # Notes
    _add_heading(doc, "Additional Notes")
    notes_text = (
        f"This schedule is flexible and can be adjusted based on the learner's pace and needs. "
        f"Regular breaks are recommended between sessions. "
        f"Additional support and resources are available upon request. "
        f"For questions or concerns, please reach out to the training coordinator."
    )
    _add_paragraph(doc, notes_text)

    return doc


def generate_dynamic_document(topic, instruction=None, source_material=None):
    """Generate a universal blueprint document from topic + instruction + optional sources."""
    if not DOCX_AVAILABLE:
        return {
            "status": "failed",
            "message": "python-docx is not installed. Install it to create Word documents."
        }

    topic_text = (topic or "General Topic").strip()
    instruction_text = (instruction or "").strip()
    blob = f"{topic_text} {instruction_text}".lower()

    # Infer blueprint family and label dynamically
    families = {
        "proposal": ["proposal", "pitch", "concept note"],
        "case_study": ["case study", "case-study"],
        "profile": ["profile", "company profile", "organization profile"],
        "plan": ["plan", "strategy", "roadmap", "implementation"],
        "policy": ["policy", "framework", "guideline"],
        "sop": ["sop", "procedure", "manual"],
        "feasibility": ["feasibility", "viability", "business case"],
        "whitepaper": ["whitepaper", "position paper", "brief"],
        "report": ["report", "analysis", "assessment"],
    }
    family = "report"
    for fam, keys in families.items():
        if any(k in blob for k in keys):
            family = fam
            break

    labels = {
        "proposal": "Proposal",
        "case_study": "Case Study",
        "profile": "Business Profile",
        "plan": "Strategic Plan",
        "policy": "Policy Framework",
        "sop": "Standard Operating Procedure",
        "feasibility": "Feasibility Study",
        "whitepaper": "Whitepaper",
        "report": "Report",
    }
    label = labels.get(family, "Report")

    base_sections = {
        "proposal": [
            "Executive Summary", "Problem Statement", "Objectives", "Proposed Solution",
            "Methodology", "Implementation Plan", "Budget Considerations", "Risks and Mitigation", "Conclusion"
        ],
        "case_study": [
            "Executive Summary", "Background", "Case Context", "Observed Challenges",
            "Interventions", "Results", "Lessons Learned", "Recommendations", "Conclusion"
        ],
        "profile": [
            "Executive Summary", "Company Overview", "Vision, Mission, and Values", "Products and Services",
            "Operational Strengths", "Market Position", "Strategic Opportunities", "Recommendations", "Conclusion"
        ],
        "plan": [
            "Executive Summary", "Current State", "Strategic Objectives", "Action Plan",
            "Timeline and Milestones", "Resource Requirements", "Risks and Mitigation", "KPIs and Monitoring", "Conclusion"
        ],
        "policy": [
            "Executive Summary", "Policy Context", "Policy Objectives", "Scope and Applicability",
            "Governance and Compliance", "Implementation Guidance", "Monitoring and Evaluation", "Review Cycle", "Conclusion"
        ],
        "sop": [
            "Purpose", "Scope", "Roles and Responsibilities", "Procedure Steps",
            "Quality Controls", "Exception Handling", "Documentation and Records", "Review and Updates"
        ],
        "feasibility": [
            "Executive Summary", "Project Context", "Technical Feasibility", "Operational Feasibility",
            "Financial Feasibility", "Risk Analysis", "Recommendation", "Conclusion"
        ],
        "whitepaper": [
            "Abstract", "Context", "Key Arguments", "Evidence and Analysis",
            "Implications", "Recommendations", "Conclusion"
        ],
        "report": [
            "Executive Summary", "Background and Context", "Core Analysis", "Insights and Findings",
            "Recommendations", "Implementation Roadmap", "Risk and Mitigation", "Conclusion"
        ],
    }
    ordered_sections = list(base_sections.get(family, base_sections["report"]))

    # Inject additional sections from instruction keywords
    keyword_sections = {
        "method": "Methodology",
        "objective": "Objectives",
        "scope": "Scope",
        "stakeholder": "Stakeholder Analysis",
        "financial": "Financial Considerations",
        "market": "Market Positioning",
        "technology": "Technology Stack and Capabilities",
        "governance": "Governance and Compliance",
        "timeline": "Timeline and Milestones",
        "kpi": "KPIs and Monitoring",
        "risk": "Risk and Mitigation",
        "budget": "Budget Considerations",
    }
    for key, sec in keyword_sections.items():
        if key in blob and sec not in ordered_sections:
            ordered_sections.insert(min(4, len(ordered_sections)), sec)

    # De-duplicate while preserving order
    seen = set()
    ordered_sections = [s for s in ordered_sections if not (s in seen or seen.add(s))]

    # Level of detail
    depth = 2
    if any(k in blob for k in ["very detailed", "comprehensive", "deep", "full"]):
        depth = 3
    elif any(k in blob for k in ["short", "brief", "summary only"]):
        depth = 1

    highlights = _extract_source_highlights(source_material, max_points=10)
    source_urls = re.findall(r"URL:\s*(https?://\S+)", str(source_material or ""), flags=re.I)
    source_urls = list(dict.fromkeys(source_urls))

    doc = docx.Document()
    _add_heading(doc, f"{label}: {topic_text.title()}", level=0)
    _add_paragraph(doc, "Generated by AMAZON AI Assistant", italic=True)
    _add_paragraph(doc, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    if instruction_text:
        _add_paragraph(doc, f"Instruction Context: {instruction_text}")
    doc.add_paragraph()

    if highlights:
        _add_heading(doc, "Source Highlights")
        for h in highlights[:8]:
            _add_paragraph(doc, f"• {h}")
        doc.add_paragraph()

    for idx, section in enumerate(ordered_sections, 1):
        _add_heading(doc, f"{idx}. {section}")
        intro_pool = [
            f"This section examines {topic_text} through the lens of {section.lower()}, aligning with your instruction context.",
            f"Focus here is on {section.lower()} for {topic_text}, emphasizing practical execution and measurable value.",
            f"The analysis below addresses {section.lower()} in relation to {topic_text} using evidence-informed reasoning.",
        ]
        point_pool = [
            f"• Strategic relevance of {topic_text} in current operating conditions",
            "• Current-state snapshot, constraints, and leverage points",
            "• Recommended actions, ownership model, and expected outcomes",
            "• Dependencies, assumptions, and implementation trade-offs",
            "• Monitoring plan with review checkpoints and adjustment triggers",
        ]

        _add_paragraph(doc, random.choice(intro_pool))

        # Always include 3 core bullets, then expand by detail depth.
        core_points = point_pool[:3]
        for pt in core_points:
            _add_paragraph(doc, pt)
        if depth >= 2:
            _add_paragraph(doc, point_pool[3])
        if depth >= 3:
            _add_paragraph(doc, point_pool[4])

        # Inject one source-informed highlight when available.
        if highlights:
            _add_paragraph(doc, f"Source insight: {highlights[(idx - 1) % len(highlights)]}")

    if source_urls:
        _add_heading(doc, "Reference URLs")
        for u in source_urls:
            _add_paragraph(doc, f"• {u}")

    _add_source_material_section(doc, source_material)
    return doc


def generate_exam_document(topic, instruction=None, source_material=None):
    """Generate a structured final exam paper dynamically from instruction context."""
    if not DOCX_AVAILABLE:
        return {
            "status": "failed",
            "message": "python-docx is not installed. Install it to create Word documents."
        }

    topic_text = (topic or "IT").strip()
    instruction_text = (instruction or "").strip()
    blob = f"{topic_text} {instruction_text}".lower()

    # Parse configurable values from instruction
    duration = "3 Hours"
    m = re.search(r'\b(\d+)\s*(hours?|hrs?)\b', blob, re.I)
    if m:
        duration = f"{m.group(1)} Hours"

    total_marks = "100"
    mm = re.search(r'\b(\d{2,3})\s*(marks?|points?)\b', blob, re.I)
    if mm:
        total_marks = mm.group(1)

    level = "Final Year"
    if "year 4" in blob or "fourth year" in blob:
        level = "Year 4"
    elif "year 3" in blob or "third year" in blob:
        level = "Year 3"

    institution = "KIUT"
    inst = re.search(r'\b(at|for)\s+([A-Za-z][A-Za-z\s&.-]{2,})$', instruction_text, re.I)
    if inst:
        institution = inst.group(2).strip()

    # Parse section styles/counts dynamically
    sec_a_mcq = "multiple choice" in blob or "mcq" in blob
    sec_b_essay = "essay" in blob or "long" in blob

    a_count = 10 if sec_a_mcq else 6
    b_count = 5 if sec_b_essay else 4
    ma = re.search(r'section\s*a.*?(\d{1,2})', blob, re.I)
    mb = re.search(r'section\s*b.*?(\d{1,2})', blob, re.I)
    if ma:
        a_count = max(3, min(20, int(ma.group(1))))
    if mb:
        b_count = max(2, min(12, int(mb.group(1))))

    # Derive exam domains from topic + source highlights
    highlights = _extract_source_highlights(source_material, max_points=12)
    keyword_candidates = re.findall(r"[A-Za-z]{4,}", f"{topic_text} {' '.join(highlights[:4])}")
    stop = {"about", "with", "from", "that", "this", "their", "there", "which", "technology", "limited"}
    domains = []
    for w in keyword_candidates:
        wl = w.lower()
        if wl not in stop and wl not in domains:
            domains.append(wl)
        if len(domains) >= 8:
            break
    if not domains:
        domains = ["software", "security", "database", "network", "systems", "project"]

    doc = docx.Document()
    _add_heading(doc, f"Final Examination: {topic_text.title()}", level=0)
    _add_paragraph(doc, f"Institution: {institution}")
    _add_paragraph(doc, f"Level: {level}")
    _add_paragraph(doc, f"Duration: {duration}")
    _add_paragraph(doc, f"Total Marks: {total_marks}")
    _add_paragraph(doc, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    doc.add_paragraph()

    _add_heading(doc, "General Instructions")
    choose_b = min(3, b_count)
    instructions = [
        f"Answer all questions in Section A and any {choose_b} questions from Section B.",
        "Show all workings where applicable.",
        "Read each question carefully before answering.",
        "Use clear, concise, and technically accurate language.",
    ]
    for line in instructions:
        _add_paragraph(doc, f"• {line}")

    section_a_title = "Section A: Multiple Choice Questions" if sec_a_mcq else "Section A: Short Questions"
    _add_heading(doc, f"{section_a_title} (40 Marks)")
    verbs_a = ["Define", "Identify", "Differentiate", "Explain", "State", "Outline"]
    marks_a = max(2, 40 // max(1, a_count))
    for i in range(1, a_count + 1):
        dom = domains[(i - 1) % len(domains)]
        verb = random.choice(verbs_a)
        if sec_a_mcq:
            _add_paragraph(doc, f"A{i}. {verb} the best description of {dom} in modern IT environments. ({marks_a} Marks)")
            _add_paragraph(doc, "   A) Option 1    B) Option 2    C) Option 3    D) Option 4")
        else:
            _add_paragraph(doc, f"A{i}. {verb} the role of {dom} in enterprise or academic systems. ({marks_a} Marks)")

    _add_heading(doc, "Section B: Essay / Problem Solving (60 Marks)")
    verbs_b = ["Design", "Analyze", "Evaluate", "Develop", "Propose", "Critique"]
    marks_b = max(8, 60 // max(1, b_count))
    for i in range(1, b_count + 1):
        dom = domains[(i + 2) % len(domains)]
        verb = random.choice(verbs_b)
        _add_paragraph(
            doc,
            f"B{i}. {verb} a practical solution focused on {dom}, including assumptions, implementation steps, and evaluation criteria. ({marks_b} Marks)"
        )

    _add_heading(doc, "Marking Scheme (Summary)")
    _add_paragraph(doc, "Section A: Accuracy, concept mastery, and concise expression.")
    _add_paragraph(doc, "Section B: Analytical depth, feasibility, structure, and technical justification.")

    # If user provides an example in the instruction, keep it as guideline
    example_match = re.search(r'(?:example|mfano)\s*:\s*(.+)$', instruction_text, re.I)
    if example_match:
        _add_heading(doc, "Exam Style Reference (User Example)")
        _add_paragraph(doc, example_match.group(1).strip())

    _add_source_material_section(doc, source_material)
    return doc


def save_document(doc, filename, base_dir=None):
    """Save a Word document to the specified location."""
    if base_dir is None:
        base_dir = Path(os.path.expanduser("~")) / "Desktop"
    else:
        base_dir = Path(base_dir)

    base_dir.mkdir(parents=True, exist_ok=True)

    # Ensure .docx extension
    if not filename.endswith('.docx'):
        filename = filename + '.docx'

    full_path = base_dir / filename

    try:
        doc.save(str(full_path))
        return {
            "status": "success",
            "message": f"Document created: {full_path}",
            "path": str(full_path),
            "name": filename
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e)
        }