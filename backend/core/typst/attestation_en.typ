// Attestation to countersign, English. Goldline house style (see goldline.typ).
// Payload: `core.generators.audit_context_for_typst` via sys.inputs.data.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)
#let shown(key) = key not in d.hidden_fields
#let has(value) = value != none and value != "" and value != "-"

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: d.audit.name, client: client)

// ------------------------------------------------------------- front matter

#let party = d.at("counterparty", default: none)
#gl-front-matter()

// ------------------------------------------------------------------- summary

= Summary

#gl-details((
  ("Framework", d.audit.framework.name),
  ("Reference", field(d.audit, "ref_id")),
  ("Implementation groups", if d.igs != "" { d.igs } else { "All" }),
  ("Contributors", d.contributors.replace("\n", ", ")),
  ..if party != none {
    (
      ("Assessed entity", [#party.entity#if party.ref_id != "" [ (#party.ref_id)]]),
      ..if party.address != "" { (("Address", party.address.replace("\n", ", ")),) } else { () },
      ..if party.legal_identifiers.len() > 0 {
        (("Legal identifiers", party.legal_identifiers.map(p => [#p.label: #p.value]).join("; ")),)
      } else { () },
      ..if party.expiry_date != "-" { (("Expiry date", party.expiry_date),) } else { () },
    )
  } else { () },
))

#if has(d.audit.description) [
  == Scope
  #d.audit.description
]

// ------------------------------------------------------- detailed assessment

#pagebreak(weak: true)
= Detailed results

#let ras = field(d, "requirement_assessments", fallback: ())
#gl-label("What this covers:")[#ras.len() assessable requirements, with the rating, the answers given and the linked controls.]
#v(0.4em)

#let detail(ra) = {
  let lines = ()
  if has(field(ra, "description")) { lines.push(ra.description) }
  if "status" in ra { lines.push(gl-label("Progress:", ra.status)) }
  if "extended_result" in ra and has(ra.extended_result) {
    lines.push(gl-label("Result detail:", ra.extended_result))
  }
  if "score" in ra and ra.score != none {
    lines.push(gl-label("Score:")[#ra.score#if field(ra, "max_score", fallback: none) != none [\/#ra.max_score]])
  }
  for qa in ra.at("answers", default: ()) { lines.push(gl-label(qa.question, qa.answer)) }
  if has(field(ra, "observation")) { lines.push(gl-label("Observation:", ra.observation)) }
  let tasks = ra.at("task_templates", default: ())
  if tasks.len() > 0 { lines.push(gl-label("Tasks:", tasks.join(", "))) }
  let ev = ra.at("evidences", default: ())
  if ev.len() > 0 { lines.push(gl-label("Evidence:", ev.join(", "))) }
  if has(field(ra, "applied_controls")) { lines.push(gl-label("Applied controls:", ra.applied_controls)) }
  [#text(fill: dark, weight: "bold")[#field(ra, "name")]#if lines.len() > 0 [ \ #text(fill: body-grey)[#lines.join(linebreak())]]]
}

#gl-table(
  columns: (13%, 1fr, 17%),
  header: ("ISO reference", "Requirement and evidence", "Rating"),
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
  header: ("Undertaking", "Status", "Committed date", "Current date"),
  ..rows
    .map(row => (
      [
        #field(row, "name")
        #if field(row, "notes", fallback: "") != "" [
          \ #gl-label("Notes:", row.notes)
        ]
      ],
      field(row, "state"),
      align(right)[#field(row, "committedDate", fallback: field(row, "committed_eta"))],
      align(right)[
        #field(row, "current_date")
        #if row.at("has_slipped", default: false) [
          #text(fill: rgb("#9C0006"))[(slipped)]
        ]
      ],
    ))
    .flatten(),
)

#let commitments = field(d, "commitments", fallback: ())
#pagebreak(weak: true)
= Commitments

#if commitments.len() > 0 [
  #undertaking-table(commitments)
] else [
  No commitments recorded.
]
#let tasks = field(d, "tasks", fallback: ())
#if tasks.len() > 0 [
  = Tasks
  #undertaking-table(tasks)
]

// ------------------------------------------------------------ signatures

#pagebreak(weak: true)
= Signatures

By signing below, the parties agree to the compliance status and the commitments recorded in this document.
#v(1.5em)

#grid(
  columns: (1fr, 1fr),
  gutter: 2em,
  ..("For the assessed entity", "For the assessing organisation").map(who => [
    #text(fill: dark, weight: "bold")[#who]
    #v(2.5em)
    #line(length: 100%, stroke: 0.5pt + border)
    #text(8pt)[Name and role]
    #v(2em)
    #line(length: 100%, stroke: 0.5pt + border)
    #text(8pt)[Signature and date]
  ]),
)

#v(1.5em)
#text(8pt)[#gl-label("Generated at:", d.generated_at) #h(1em) #gl-label("Document ID:", d.audit.id)]
