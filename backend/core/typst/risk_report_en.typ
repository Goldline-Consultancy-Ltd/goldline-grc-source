// Risk assessment report, English. Goldline house style (see goldline.typ).
// Payload: `core.generators.risk_assessment_context` via sys.inputs.data.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let ra = d.assessment
#let has(value) = value != none and value != "" and value != "-"

#let assessment-status-label = (
  "planned": "Planned",
  "in_progress": "In progress",
  "in_review": "In review",
  "done": "Done",
  "deprecated": "Deprecated",
)

#let view-label = (
  inherent: "Inherent risk",
  current: "Current risk",
  residual: "Residual risk",
)

#let axis-title = (
  probabilityISO: "Likelihood",
  probabilityEBIOS: "Likelihood",
  impactISO: "Impact",
  impactEBIOS: "Severity",
)
#let axis-name(kind) = axis-title.at(kind + d.label_standard)
#let qualification-label = if d.use_risk_category_label { "Risk categories" } else { "Qualifications" }

#let treatment-label = (
  open: "Open",
  mitigate: "Mitigate",
  accept: "Accept",
  avoid: "Avoid",
  transfer: "Transfer",
  cancelled: "Cancelled",
)

// Risk level as a filled rating cell: Low green, Medium amber, High pink.
// Level names come from the client's matrix; unknown names keep the matrix colour.
#let level-words = (
  low: ("very low", "low", "limited", "negligible", "minor", "très faible", "faible", "limité", "négligeable", "mineur"),
  medium: ("medium", "moderate", "significant", "moyen", "modéré", "significatif"),
  high: ("high", "very high", "critical", "severe", "major", "fort", "élevé", "très élevé", "critique", "grave", "majeur"),
)
#let level-fill(level) = {
  let name = lower(level.name)
  for (key, words) in level-words.pairs() {
    if name in words { return rating-fill(key) }
  }
  if has(level.at("hexcolor", default: "")) { rgb(level.hexcolor) } else { rating-fill("not_assessed") }
}
#let level-cell(level) = table.cell(fill: level-fill(level))[#level.name]

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: ra.name, client: client)

// ------------------------------------------------------------- front matter

#gl-front-matter()

// ------------------------------------------------------------------- summary

= Summary

#gl-details((
  ("Domain", ra.folder),
  ("Perimeter", ra.perimeter),
  ("Risk matrix", ra.matrix),
  ("Status", assessment-status-label.at(ra.status_key, default: "-")),
  ("Authors", ra.authors),
  ("Reviewers", ra.reviewers),
  ("Target date", ra.eta),
  ("Due date", ra.due_date),
))

#if has(ra.description) [
  == Scope
  #ra.description
]

// -------------------------------------------------------------- matrix views

= Risk matrix

#gl-label("What this covers:")[where each scenario sits on the client's risk matrix. Colours are those of the matrix.]

#for view in d.matrix_views [
  #block(breakable: false, above: 1.2em)[
    == #view-label.at(view.key)
    #grid(
      columns: (0.9cm, 1fr),
      align: center + horizon,
      rotate(-90deg, reflow: true)[#text(9pt, fill: body-grey)[#axis-name(view.y_type)]],
      table(
        columns: (2.4cm,) + view.x_axis.map(_ => 1fr),
        rows: (auto,) * view.cells.len() + (auto,),
        stroke: 2pt + white,
        align: center + horizon,
        inset: (x: 5pt, y: 12pt),
        ..view
          .cells
          .enumerate()
          .map(((index, row)) => (
            table.cell(fill: cream)[#text(8pt, fill: dark, weight: "bold")[#view.y_axis.at(index).name]],
          ) + row.map(cell => table.cell(fill: rgb(cell.hexcolor))[
            #text(7.5pt, fill: dark)[#cell.refs.join(", ")]
          ]))
          .flatten(),
        table.cell(fill: white)[],
        ..view.x_axis.map(axis => table.cell(fill: cream)[#text(8pt, fill: dark, weight: "bold")[#axis.name]]),
      ),
    )
    #align(center)[#text(9pt, fill: body-grey)[#axis-name(view.x_type)]]
  ]
]

// ---------------------------------------------------------- scenario summary

#pagebreak(weak: true)
= Scenario summary

#let with-inherent = d.include_inherent
#gl-table(
  columns: if with-inherent { (1.6cm, 3fr, 4fr, auto, auto, auto, auto) } else {
    (1.6cm, 3fr, 4fr, auto, auto, auto)
  },
  header: (
    "Ref.",
    "Name",
    "Description",
    ..if with-inherent { ("Inherent",) } else { () },
    "Current",
    "Residual",
    "Treatment",
  ),
  ..d
    .scenarios
    .enumerate()
    .map(((index, scenario)) => (
      // Jumps to the matching entry under "Risk scenarios".
      [#link(label("scn-" + str(index)))[#scenario.ref_id]],
      scenario.name,
      scenario.description,
    ) + (if with-inherent { (level-cell(scenario.inherent),) } else { () }) + (
      level-cell(scenario.current),
      level-cell(scenario.residual),
      treatment-label.at(scenario.treatment_key, default: scenario.treatment_key),
    ))
    .flatten(),
)

// ----------------------------------------------------------------- scenarios

#pagebreak(weak: true)
= Risk scenarios

#gl-label("What this covers:")[#d.scenarios.len() scenarios, with their assets, threats, controls and treatment.]

#for (index, scenario) in d.scenarios.enumerate() [
  #block(breakable: true, width: 100%, above: 1.2em)[
    #text(11pt, weight: "bold", fill: navy)[#if has(scenario.ref_id) [#scenario.ref_id: ]#scenario.name] #label("scn-" + str(index))
    #v(2pt)
    #let row(name, body) = ((name, body),)
    #gl-details(
      (
        if has(scenario.description) { row("Description", scenario.description) } else { () }
          + if scenario.qualifications.len() > 0 { row(qualification-label, scenario.qualifications.join(", ")) } else { () }
          + if scenario.assets.len() > 0 { row("Assets", scenario.assets.join(", ")) } else { () }
          + if scenario.threats.len() > 0 { row("Threats", scenario.threats.join(", ")) } else { () }
          + if "inherent" in scenario { ((["Inherent level"], level-cell(scenario.inherent)),) } else { () }
          + if scenario.existing_controls.len() > 0 { row("Existing controls", scenario.existing_controls.join(", ")) } else { () }
          + (("Current level", level-cell(scenario.current)),)
          + if scenario.controls.len() > 0 { row("Additional controls", scenario.controls.join(", ")) } else { () }
          + (("Residual level", level-cell(scenario.residual)),)
          + row("Strength of knowledge", scenario.strength_of_knowledge)
          + row("Treatment", treatment-label.at(scenario.treatment_key, default: scenario.treatment_key))
          + if has(scenario.justification) { row("Justification", scenario.justification) } else { () }
      ),
    )
  ]
]

#v(1.5em)
#text(8pt)[#gl-label("Generated at:", d.generated_at) #h(1em) #gl-label("Document ID:", d.id)]
