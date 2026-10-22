// Plan d'action, français. Goldline house style (see goldline.typ).
// Payload: `core.generators.action_plan_context` via sys.inputs.data.
// Used for both audit and risk assessment action plans.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)

#let status-label = (
  to_do: "À faire",
  in_progress: "En cours",
  on_hold: "En attente",
  active: "Actif",
  degraded: "Dégradé",
  deprecated: "Déprécié",
)
#let category-label = (
  policy: "Politique",
  process: "Processus",
  technical: "Technique",
  physical: "Physique",
  procedure: "Procédure",
)

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: "Plan d'action : " + d.subject.name, client: client)

// ------------------------------------------------------------- front matter

#gl-front-matter()

// ------------------------------------------------------------------- summary

= Synthèse

#gl-details((
  ("Domaine", d.subject.domain),
  ("Périmètre", d.subject.perimeter),
  ("Évaluation", [#d.subject.name, version #d.subject.version]),
  ..if d.subject.framework != "" { (("Référentiel", d.subject.framework),) } else { () },
  ("Mesures appliquées", [#d.total]),
))

#gl-label("Périmètre du document :")[les mesures appliquées liées à cette évaluation, regroupées par statut et triées par échéance.]

// ------------------------------------------------------------------ actions

= Actions

// Fractions, not auto: auto columns overflow and overlap.
#let columns-spec = (
  2.3fr, // name
  3.6fr, // description, the column actually read
  1.4fr, // category
  1.8fr, // owner
  1.4fr, // due date
  2.8fr, // linked items
)

#for group in d.groups [
  #block(
    width: 100%,
    fill: rgb(group.fill),
    stroke: border-stroke,
    inset: 5pt,
    above: 1.2em,
    below: 0.5em,
    sticky: true,
  )[
    #text(10pt, weight: "bold", fill: navy)[
      #status-label.at(group.status_key, default: "Sans statut")
      (#group.controls.len())
    ]
  ]
  #gl-table(
    columns: columns-spec,
    align: left + top,
    header: ("Nom", "Description", "Catégorie", "Responsable", "Échéance", "Éléments liés"),
    ..group
      .controls
      .map(c => (
        [#c.name],
        [#text(8.5pt)[#c.description]],
        [#category-label.at(c.category_key, default: "-")],
        [#c.owner],
        [#c.eta],
        [#text(8.5pt)[#if c.linked.len() > 0 { c.linked.join(linebreak()) } else { "-" }]],
      ))
      .flatten(),
  )
]

#v(1.5em)
#text(8pt)[#gl-label("Généré le :", d.generated_at) #h(1em) #gl-label("Identifiant du document :", d.id)]
