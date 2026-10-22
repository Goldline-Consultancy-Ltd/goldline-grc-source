"""Goldline GRC house style for exported reports.

Company details, colours and rating words used by every PDF, Word, slide and
spreadsheet export. Change them here (or with the environment variables below)
and every report picks them up.
"""

import os

COMPANY = os.getenv("GOLDLINE_REPORT_COMPANY", "Goldline Consultancy Ltd")
ADDRESS = os.getenv("GOLDLINE_REPORT_ADDRESS", "124 City Road, London EC1V 2NX")
COMPANY_NUMBER = os.getenv("GOLDLINE_REPORT_COMPANY_NUMBER", "10901798")
DEFAULT_ASSESSOR = os.getenv(
    "GOLDLINE_REPORT_ASSESSOR",
    "Alfred Obeng, Goldline Consultancy Ltd. ISO/IEC 27001 Lead Auditor",
)
JURISDICTION = os.getenv("GOLDLINE_REPORT_JURISDICTION", "England and Wales")

# Colours (hex without '#', as Office XML uses them).
NAVY = "0A1628"  # headings, table header rows
BODY = "5B6470"  # body text
TEXT = "1B1F26"  # table text, lead-ins
GOLD = "B8892B"  # eyebrow labels, rules
BORDER = "D9D3C4"  # table borders, 0.5 pt
CREAM = "F6F3EB"  # label cells
WHITE = "FFFFFF"

# Rating fills, keyed by the GRC's own result values.
RATING_FILL = {
    "compliant": "C6EFCE",
    "partially_compliant": "FFEB9C",
    "non_compliant": "FFC7CE",
    "not_assessed": "E7E6E6",
    "not_applicable": "E7E6E6",
    "low": "C6EFCE",
    "medium": "FFEB9C",
    "high": "FFC7CE",
    "critical": "FFC7CE",
}

RESULT_LABEL = {
    "en": {
        "compliant": "Met",
        "partially_compliant": "Partially met",
        "non_compliant": "Not met",
        "not_assessed": "Not assessed",
        "not_applicable": "Not applicable",
    },
    "fr": {
        "compliant": "Satisfait",
        "partially_compliant": "Partiellement satisfait",
        "non_compliant": "Non satisfait",
        "not_assessed": "Non évalué",
        "not_applicable": "Non applicable",
    },
}

# Spreadsheet cell values (any language the GRC exports) that get a rating fill.
RATING_WORDS = {
    "C6EFCE": {"met", "compliant", "low", "conforme", "satisfait", "faible"},
    "FFEB9C": {
        "partially met",
        "partially compliant",
        "partially_compliant",
        "medium",
        "partiellement conforme",
        "partiellement satisfait",
        "moyen",
    },
    "FFC7CE": {
        "not met",
        "non compliant",
        "non-compliant",
        "non_compliant",
        "high",
        "critical",
        "non conforme",
        "non satisfait",
        "élevé",
        "critique",
    },
    "E7E6E6": {
        "not evidenced",
        "not assessed",
        "not_assessed",
        "not applicable",
        "not_applicable",
        "non évalué",
        "non applicable",
    },
}


def footer_text(lang: str = "en") -> str:
    lead = "Confidentiel." if lang == "fr" else "Confidential."
    number = "Numéro d'entreprise" if lang == "fr" else "Company number"
    return f"{lead} {COMPANY}, {ADDRESS}. {number} {COMPANY_NUMBER}."


def brand_payload(lang: str = "en") -> dict:
    """Everything the shared Typst style needs, as plain data."""
    return {
        "company": COMPANY,
        "address": ADDRESS,
        "company_number": COMPANY_NUMBER,
        "default_assessor": DEFAULT_ASSESSOR,
        "jurisdiction": JURISDICTION,
        "footer": footer_text(lang),
        "lang": lang,
        "colours": {
            "navy": NAVY,
            "body": BODY,
            "text": TEXT,
            "gold": GOLD,
            "border": BORDER,
            "cream": CREAM,
        },
        "rating_fill": RATING_FILL,
        "result_label": RESULT_LABEL.get(lang, RESULT_LABEL["en"]),
    }


def domain_name(obj) -> str:
    """Name of the client domain an object sits in, or '' if none."""
    folder = getattr(obj, "folder", None)
    seen = 0
    while folder is not None and seen < 20:
        if getattr(folder, "content_type", None) == "DO":
            return folder.name
        folder = getattr(folder, "parent_folder", None)
        seen += 1
    return ""


def report_cover(
    obj=None,
    *,
    eyebrow: str,
    title: str,
    subtitle: str = "",
    report_line: str = "",
    engagement: str = "",
    version: str = "",
    date: str = "",
    prepared_for: str = "",
) -> dict:
    """Cover page fields. Empty values are shown as 'to be completed' fields."""
    client = domain_name(obj) if obj is not None else ""
    return {
        "eyebrow": eyebrow,
        "title": title,
        "subtitle": subtitle,
        "report_line": report_line,
        "client": client,
        "company_assessed": client,
        "prepared_for": prepared_for or client,
        "engagement": engagement,
        "date": date,
        "version": version or (getattr(obj, "version", "") or ""),
        "assessor": DEFAULT_ASSESSOR,
    }


COVER_TEXT = {
    "en": {
        "audit_report": ("Compliance assessment", "Compliance assessment report"),
        "attestation": ("Attestation", "Attestation report"),
        "risk_report": ("Risk assessment", "Risk assessment report"),
        "action_plan": ("Action plan", "Remediation action plan"),
        "findings_report": ("Findings", "Findings report"),
        "incident_report": ("Incident report", "Incident report"),
        "mapped_to": "Mapped to {}",
        "risk_matrix": "Risk matrix: {}",
    },
    "fr": {
        "audit_report": ("Évaluation de conformité", "Rapport d'évaluation de conformité"),
        "attestation": ("Attestation", "Rapport d'attestation"),
        "risk_report": ("Analyse de risques", "Rapport d'analyse de risques"),
        "action_plan": ("Plan d'action", "Plan d'action de remédiation"),
        "findings_report": ("Constats", "Rapport de constats"),
        "incident_report": ("Rapport d'incident", "Rapport d'incident"),
        "mapped_to": "Selon {}",
        "risk_matrix": "Matrice de risques : {}",
    },
}


def cover_for(obj, kind: str, lang: str, payload: dict | None = None) -> dict:
    """Cover fields for a report on `obj` (an audit, risk assessment, findings
    assessment or incident)."""
    words = COVER_TEXT.get(lang, COVER_TEXT["en"])
    eyebrow, report_line = words.get(kind, ("", ""))
    framework = getattr(obj, "framework", None)
    matrix = getattr(obj, "risk_matrix", None)
    subtitle = ""
    if framework is not None:
        subtitle = words["mapped_to"].format(framework.name)
    elif matrix is not None:
        subtitle = words["risk_matrix"].format(matrix.name)
    elif getattr(obj, "category", None) not in (None, "", "--", "undefined") and hasattr(
        obj, "get_category_display"
    ):
        subtitle = str(obj.get_category_display())
    perimeter = getattr(obj, "perimeter", None)
    engagement = perimeter.name if perimeter is not None else (getattr(obj, "ref_id", "") or "")
    return report_cover(
        obj,
        eyebrow=eyebrow,
        title=getattr(obj, "name", "") or "",
        subtitle=subtitle,
        report_line=report_line,
        engagement=engagement,
        date=(payload or {}).get("date", ""),
    )


TO_COMPLETE = {"en": "[To be completed]", "fr": "[À compléter]"}


def word_context(obj, lang: str, context: dict) -> dict:
    """Extra docxtpl context for the Goldline Word report: cover fields (gaps
    shown as highlighted fields to fill in), brand details and per-row rating
    words and fills."""
    from docxtpl import RichText

    lang = lang if lang in RESULT_LABEL else "en"
    cover = cover_for(obj, "audit_report", lang, context)

    def field(value):
        if value in (None, "", "-"):
            return RichText(TO_COMPLETE[lang], color=GOLD, italic=True, highlight="yellow")
        return RichText(str(value))

    labels = RESULT_LABEL[lang]
    rows = []
    for ra in context.get("requirement_assessments", []):
        key = ra.get("result_key", "")
        rows.append(
            {
                **ra,
                "rating_label": labels.get(key, ra.get("result", "")),
                "rating_fill": RATING_FILL.get(key, WHITE),
            }
        )
    fields = {
        key: field(cover.get(key))
        for key in ("company_assessed", "prepared_for", "engagement", "date", "version", "assessor")
    }
    fields["scope"] = field(cover.get("engagement"))
    fields["description"] = field(getattr(obj, "description", ""))
    fields["observation"] = field(getattr(obj, "observation", ""))
    return {
        "cover": cover,
        "fields": fields,
        "comments": field(""),
        "client": cover["client"] or COMPANY,
        "brand": brand_payload(lang),
        "requirement_assessments": rows,
    }
