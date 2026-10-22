// Goldline GRC house style, shared by every PDF report.
// Company details and colours come from core/report_brand.py through
// sys.inputs.brand; per-report cover fields come through sys.inputs.cover.

#let brand = json(bytes(sys.inputs.brand))
#let cover = if "cover" in sys.inputs { json(bytes(sys.inputs.cover)) } else { none }
#let lang = brand.lang

#let navy = rgb("#" + brand.colours.navy)
#let body-grey = rgb("#" + brand.colours.body)
#let dark = rgb("#" + brand.colours.text)
#let gold = rgb("#" + brand.colours.gold)
#let border = rgb("#" + brand.colours.border)
#let cream = rgb("#" + brand.colours.cream)
#let border-stroke = 0.5pt + border

#let i18n = (
  en: (
    contents: "Contents",
    doc-control: "Document control",
    version: "Version",
    date: "Date",
    author: "Author",
    change: "Change",
    first-issue: "First issue",
    page: "Page",
    company-assessed: "Company assessed",
    prepared-for: "Prepared for",
    engagement: "Engagement",
    report-date: "Report date",
    assessor: "Assessor",
    to-complete: "To be completed",
    conf-lead: "Confidential working document.",
    conf-body: client => [Prepared for #client and intended only for its management and auditors. Do not share it with third parties without written agreement from #brand.company. Governed by the law of #brand.jurisdiction.],
  ),
  fr: (
    contents: "Sommaire",
    doc-control: "Suivi du document",
    version: "Version",
    date: "Date",
    author: "Auteur",
    change: "Modification",
    first-issue: "Première émission",
    page: "Page",
    company-assessed: "Entreprise évaluée",
    prepared-for: "Préparé pour",
    engagement: "Mission",
    report-date: "Date du rapport",
    assessor: "Évaluateur",
    to-complete: "À compléter",
    conf-lead: "Document de travail confidentiel.",
    conf-body: client => [Préparé pour #client et destiné uniquement à sa direction et à ses auditeurs. Ne pas le communiquer à des tiers sans l'accord écrit de #brand.company. Régi par le droit de l'Angleterre et du pays de Galles.],
  ),
)
#let t = i18n.at(lang, default: i18n.en)

// Value, or a clearly marked gap when the GRC has no data for it.
#let filled(value) = if value == none or value == "" or value == "-" {
  text(fill: gold, style: "italic")[\[#t.to-complete\]]
} else { value }

#let gl-mark(height) = image("goldline-mark.svg", height: height)

// ------------------------------------------------------------------ ratings

#let rating-fill(key) = {
  let hex = brand.rating_fill.at(key, default: none)
  if hex == none { none } else { rgb("#" + hex) }
}
#let rating-label(key, fallback: none) = brand.result_label.at(
  key,
  default: if fallback == none { key } else { fallback },
)
// A table cell filled by rating: Met green, Partially met amber, Not met pink,
// Not assessed grey.
#let rating-cell(key, label: none) = table.cell(fill: rating-fill(key))[
  #if label == none { rating-label(key) } else { label }
]

// ------------------------------------------------------------------- tables

// Navy header row (repeats on every page), white body, 0.5 pt borders.
#let gl-table(columns: auto, header: (), align: left, ..cells) = {
  set text(9pt, fill: dark)
  set par(justify: false, leading: 0.45em)
  table(
    columns: columns,
    align: align,
    stroke: border-stroke,
    inset: 4pt,
    fill: (_, y) => if y == 0 and header.len() > 0 { navy } else { white },
    ..if header.len() > 0 {
      (
        table.header(
          repeat: true,
          ..header.map(h => text(fill: white, weight: "bold")[#h]),
        ),
      )
    } else { () },
    ..cells,
  )
}

// Two-column label/value table: labels bold on cream.
#let gl-details(rows) = {
  set text(9pt, fill: dark)
  set par(justify: false, leading: 0.45em)
  table(
    columns: (38%, 1fr),
    stroke: border-stroke,
    inset: 4pt,
    fill: (x, _) => if x == 0 { cream } else { white },
    ..rows.map(r => ([*#r.at(0)*], r.at(1))).flatten(),
  )
}

// Bold dark lead-in followed by grey text.
#let gl-label(lead, body) = [#text(fill: dark, weight: "bold")[#lead] #body]

// --------------------------------------------------------------- page setup

#let gl-setup(title: "", client: "", flipped: false, doc) = {
  let client-name = if client == none or client == "" { brand.company } else { client }
  set document(author: brand.company, title: title)
  set page(
    paper: "a4",
    flipped: flipped,
    margin: (x: 20mm, top: 24mm, bottom: 22mm),
    header: {
      set text(7.5pt, fill: body-grey)
      align(right)[#client-name#h(0.6em)|#h(0.6em)#title]
      v(-0.55em)
      line(length: 100%, stroke: 0.75pt + gold)
    },
    footer: context {
      set text(7.5pt, fill: body-grey)
      align(center)[
        #brand.footer#h(1.2em)#t.page #text(9.5pt, fill: dark)[#counter(page).display("1")]
      ]
    },
  )
  set text(font: "Carlito", size: 10.5pt, fill: body-grey, lang: lang)
  set par(justify: false, leading: 0.62em, spacing: 0.9em)
  // H1 numbered "1.", lower levels unnumbered.
  set heading(numbering: "1.")
  show heading.where(level: 2): set heading(numbering: none)
  show heading.where(level: 3): set heading(numbering: none)
  show heading: set text(fill: navy, weight: "bold")
  show heading.where(level: 1): it => {
    set text(15pt)
    block(above: 1.4em, below: 0.8em, it)
  }
  show heading.where(level: 2): it => {
    set text(12.5pt)
    block(above: 1.1em, below: 0.6em, it)
  }
  show heading.where(level: 3): it => {
    set text(10.5pt)
    block(above: 0.9em, below: 0.5em, it)
  }
  show strong: set text(fill: dark)
  doc
}

// -------------------------------------------------------------- front matter

// Cover page, contents page and document control page.
#let gl-front-matter(
  eyebrow: none,
  title: none,
  subtitle: none,
  report-line: none,
  details: none,
  control: none,
) = {
  let c = if cover == none { (:) } else { cover }
  let get(key, given) = if given != none { given } else { c.at(key, default: "") }
  let client = c.at("client", default: "")

  // Cover.
  block(height: 20mm, gl-mark(20mm))
  v(16mm)
  text(10pt, weight: "bold", fill: gold, tracking: 0.06em)[#upper(get("eyebrow", eyebrow))]
  v(3mm)
  block(text(22pt, weight: "bold", fill: navy)[#get("title", title)])
  let sub = get("subtitle", subtitle)
  if sub != "" {
    v(1mm)
    block(text(15pt, fill: navy)[#sub])
  }
  let line-text = get("report_line", report-line)
  if line-text != "" {
    v(3mm)
    block(text(12.5pt, weight: "bold", fill: dark)[#line-text])
  }
  v(5mm)
  line(length: 100%, stroke: 2pt + gold)
  v(5mm)
  gl-details(
    if details != none { details } else {
      (
        (t.company-assessed, filled(c.at("company_assessed", default: ""))),
        (t.prepared-for, filled(c.at("prepared_for", default: ""))),
        (t.engagement, filled(c.at("engagement", default: ""))),
        (t.report-date, filled(c.at("date", default: ""))),
        (t.version, filled(c.at("version", default: ""))),
        (t.assessor, filled(c.at("assessor", default: brand.default_assessor))),
      )
    },
  )
  v(5mm)
  block({
    set text(9pt)
    set par(justify: false)
    [#text(fill: dark, weight: "bold")[#t.conf-lead] #(t.conf-body)(if client == "" { brand.company } else { client })]
  })
  pagebreak()

  // Contents.
  block(below: 1em, text(15pt, weight: "bold", fill: navy)[#t.contents])
  {
    set text(10.5pt, fill: dark)
    show outline.entry.where(level: 1): it => {
      v(0.5em, weak: true)
      strong(it)
    }
    outline(title: none, depth: 2, indent: 1.2em)
  }
  pagebreak()

  // Document control.
  block(below: 1em, text(15pt, weight: "bold", fill: navy)[#t.doc-control])
  let rows = if control != none { control } else {
    (
      (
        filled(c.at("version", default: "")),
        filled(c.at("date", default: "")),
        filled(c.at("assessor", default: brand.default_assessor)),
        t.first-issue,
      ),
    )
  }
  gl-table(
    columns: (16%, 18%, 1fr, 1fr),
    header: (t.version, t.date, t.author, t.change),
    ..rows.flatten(),
  )
  pagebreak()
}
