// Rapport d'audit, français. Charte Goldline (voir goldline.typ).
// Payload: `core.generators.audit_context_for_typst` via sys.inputs.data.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)
#let shown(key) = key not in d.hidden_fields
#let chart(name) = if name + ".png" in d.charts { image(name + ".png", width: 100%) }
#let has(value) = value != none and value != "" and value != "-"

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: d.audit.name, client: client)

// ------------------------------------------------------------- front matter

#let party = d.at("counterparty", default: none)
#gl-front-matter()

// ------------------------------------------------------------------- summary

#let r = d.at("req", default: none)
#let total = if r != none { field(r, "total", fallback: 0) } else { 0 }

= Synthèse

#gl-details((
  ("Référentiel", d.audit.framework.name),
  ("Référence", field(d.audit, "ref_id")),
  ("Groupes d'implémentation", if d.igs != "" { d.igs } else { "Tous" }),
  ("Contributeurs", d.contributors.replace("\n", ", ")),
  ..if party != none {
    (
      ("Entité évaluée", [#party.entity#if party.ref_id != "" [ (#party.ref_id)]]),
      ..if party.address != "" { (("Adresse", party.address.replace("\n", ", ")),) } else { () },
      ..if party.legal_identifiers.len() > 0 {
        (("Identifiants légaux", party.legal_identifiers.map(p => [#p.label: #p.value]).join("; ")),)
      } else { () },
      ..if party.expiry_date != "-" { (("Date d'expiration", party.expiry_date),) } else { () },
    )
  } else { () },
))

#if r != none [
  == Vue d'ensemble des résultats
  #gl-table(
    columns: (1fr,) * 5,
    align: center,
    header: (
      rating-label("compliant"),
      rating-label("partially_compliant"),
      rating-label("non_compliant"),
      rating-label("not_applicable"),
      rating-label("not_assessed"),
    ),
    rating-cell("compliant", label: [#r.compliant]),
    rating-cell("partially_compliant", label: [#r.partially_compliant]),
    rating-cell("non_compliant", label: [#r.non_compliant]),
    rating-cell("not_applicable", label: [#r.not_applicable]),
    rating-cell("not_assessed", label: [#r.not_assessed]),
  )
]
#if r != none and total > 0 [
  #gl-label("Position globale :")[exigences satisfaites à #str(calc.round(100 * r.compliant / total, digits: 1)).replace(".", ",") % sur #total exigences évaluées. #field(d, "ac_count", fallback: 0) mesures appliquées sont liées à cette évaluation.]
]
#v(0.6em)
#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  chart("compliance_donut"), chart("compliance_radar"),
)

#if has(d.audit.description) [
  == Périmètre
  #d.audit.description
]

#let drifts = field(d, "drifts_per_domain", fallback: ())
#if drifts.len() > 0 [
  == Écarts par domaine
  #gl-table(
    columns: (1fr, auto),
    header: ("Domaine", "Écarts"),
    ..drifts.map(x => (field(x, "name"), align(right)[#x.drift_count])).flatten(),
  )
]

// -------------------------------------------------------------- category view

#let categories = field(d, "category_scores", fallback: (:))
#if shown("score") and categories.len() > 0 [
  = Scores par catégorie

  #gl-table(
    columns: (1fr, auto, auto, auto),
    header: ("Catégorie", "Moyenne", "Évalués", "Éléments"),
    ..categories
      .values()
      .map(c => (
        field(c, "name"),
        align(right)[#field(c, "average_score", fallback: 0)],
        align(right)[#field(c, "scored_count", fallback: 0)],
        align(right)[#field(c, "item_count", fallback: 0)],
      ))
      .flatten(),
  )

  #v(0.8em)
  #chart("category_radar")
]

// ------------------------------------------------------------------ controls

#let p1 = field(d, "p1_controls", fallback: ())
#if p1.len() > 0 [
  = Mesures prioritaires

  #chart("chart_controls")
  #v(0.8em)

  #gl-table(
    columns: (1fr, auto, auto),
    header: ("Mesure", "Statut", "Catégorie"),
    ..p1.map(c => (field(c, "name"), field(c, "status"), field(c, "category"))).flatten(),
  )
]

// ------------------------------------------------------- detailed assessment

#pagebreak(weak: true)
= Résultats détaillés

#let ras = field(d, "requirement_assessments", fallback: ())
#gl-label("Contenu :")[#ras.len() exigences évaluables, avec l'évaluation, les preuves examinées et les mesures liées.]
#v(0.4em)

#let detail(ra) = {
  let lines = ()
  if has(field(ra, "description")) { lines.push(ra.description) }
  if "status" in ra { lines.push(gl-label("Progression :", ra.status)) }
  if "extended_result" in ra and has(ra.extended_result) {
    lines.push(gl-label("Précision du résultat :", ra.extended_result))
  }
  if "score" in ra and ra.score != none {
    lines.push(gl-label("Score :")[#ra.score#if field(ra, "max_score", fallback: none) != none [\/#ra.max_score]])
  }
  for qa in ra.at("answers", default: ()) { lines.push(gl-label(qa.question, qa.answer)) }
  if has(field(ra, "observation")) { lines.push(gl-label("Observation :", ra.observation)) }
  let tasks = ra.at("task_templates", default: ())
  if tasks.len() > 0 { lines.push(gl-label("Tâches :", tasks.join(", "))) }
  let ev = ra.at("evidences", default: ())
  if ev.len() > 0 { lines.push(gl-label("Preuves :", ev.join(", "))) }
  if has(field(ra, "applied_controls")) { lines.push(gl-label("Mesures appliquées :", ra.applied_controls)) }
  [#text(fill: dark, weight: "bold")[#field(ra, "name")]#if lines.len() > 0 [ \ #text(fill: body-grey)[#lines.join(linebreak())]]]
}

#gl-table(
  columns: (13%, 1fr, 17%),
  header: ("Référence ISO", "Exigence et preuves", "Évaluation"),
  ..ras
    .map(ra => (
      field(ra, "ref_id"),
      detail(ra),
      if "result" in ra {
        rating-cell(ra.at("result_key", default: ""), label: rating-label(ra.at("result_key", default: ""), fallback: ra.result))
      } else { [] },
    ))
    .flatten(),
)

// ------------------------------------------------- commitments and tasks

#let undertaking-table(rows) = gl-table(
  columns: (1fr, auto, auto, auto),
  header: ("Engagement", "Statut", "Date d'engagement", "Date actuelle"),
  ..rows
    .map(row => (
      [
        #field(row, "name")
        #if field(row, "notes", fallback: "") != "" [
          \ #gl-label("Notes :", row.notes)
        ]
      ],
      field(row, "state"),
      align(right)[#field(row, "committedDate", fallback: field(row, "committed_eta"))],
      align(right)[
        #field(row, "current_date")
        #if row.at("has_slipped", default: false) [
          #text(fill: rgb("#9C0006"))[(reporté)]
        ]
      ],
    ))
    .flatten(),
)

#let commitments = field(d, "commitments", fallback: ())
#pagebreak(weak: true)
= Engagements

#if commitments.len() > 0 [
  #undertaking-table(commitments)
] else [
  Aucun engagement consigné.
]
#let tasks = field(d, "tasks", fallback: ())
#if tasks.len() > 0 [
  = Tâches
  #undertaking-table(tasks)
]

#v(1.5em)
#text(8pt)[#gl-label("Généré le :", d.generated_at) #h(1em) #gl-label("Identifiant du document :", d.audit.id)]
