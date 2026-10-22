// Action plan, English. Goldline house style (see goldline.typ).
// Payload: `core.generators.action_plan_context` via sys.inputs.data.
// Used for both audit and risk assessment action plans.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)

#let status-label = (
  to_do: "To do",
  in_progress: "In progress",
  on_hold: "On hold",
  active: "Active",
  degraded: "Degraded",
  deprecated: "Deprecated",
)
#let category-label = (
  policy: "Policy",
  process: "Process",
  technical: "Technical",
  physical: "Physical",
  procedure: "Procedure",
)

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: "Action plan: " + d.subject.name, client: client)

// ------------------------------------------------------------- front matter

#gl-front-matter()

// ------------------------------------------------------------------- summary

= Summary

#gl-details((
  ("Domain", d.subject.domain),
  ("Perimeter", d.subject.perimeter),
  ("Assessment", [#d.subject.name, version #d.subject.version]),
  ..if d.subject.framework != "" { (("Framework", d.subject.framework),) } else { () },
  ("Applied controls", [#d.total]),
))

#gl-label("What this covers:")[the applied controls linked to this assessment, grouped by status and sorted by due date.]

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
      #status-label.at(group.status_key, default: "No status")
      (#group.controls.len())
    ]
  ]
  #gl-table(
    columns: columns-spec,
    align: left + top,
    header: ("Name", "Description", "Category", "Owner", "Due date", "Linked items"),
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
#text(8pt)[#gl-label("Generated at:", d.generated_at) #h(1em) #gl-label("Document ID:", d.id)]
