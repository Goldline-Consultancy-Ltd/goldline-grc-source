// Incident report, English. Goldline house style (see goldline.typ).
// Payload: `core.generators.incident_context` via sys.inputs.data.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let inc = d.incident
#let has(value) = value != none and value != "" and value != "-"

#let severity-label = (
  "1": "Critical",
  "2": "Major",
  "3": "Moderate",
  "4": "Minor",
  "5": "Low",
  "6": "Unknown",
)
// Severity to rating fill: critical and major pink, moderate amber,
// minor and low green, unknown grey.
#let severity-rating = (
  "1": "high",
  "2": "high",
  "3": "medium",
  "4": "low",
  "5": "low",
  "6": "not_assessed",
)
#let incident-status-label = (
  "new": "New",
  "ongoing": "Ongoing",
  "resolved": "Resolved",
  "closed": "Closed",
  "dismissed": "Dismissed",
)
#let detection-label = (
  "internally_detected": "Internal",
  "externally_detected": "External",
)
#let entry-label = (
  detection: "Detection",
  mitigation: "Mitigation",
  observation: "Observation",
  severity_changed: "Severity changed",
  status_changed: "Status changed",
)

#let severity-cell(key) = table.cell(
  fill: rating-fill(severity-rating.at(key, default: "not_assessed")),
)[#severity-label.at(key, default: "-")]

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: inc.name, client: client)

// ------------------------------------------------------------- front matter

#gl-front-matter()

// ------------------------------------------------------------------- summary

= Incident details

#{
  set text(9pt, fill: dark)
  table(
    columns: (38%, 1fr),
    stroke: border-stroke,
    inset: 4pt,
    fill: (x, _) => if x == 0 { cream } else { white },
    [*Reference*], [#if inc.ref_id != "" [#inc.ref_id] else [-]],
    [*Incident*], [#inc.name],
    [*Severity*], severity-cell(inc.severity_key),
    [*Status*], [#incident-status-label.at(inc.status_key, default: "-")],
    [*Detection*], [#detection-label.at(inc.detection_key, default: "-")],
    [*Domain*], [#inc.folder],
    [*Owners*], [#inc.owners],
    [*Occurred at*], [#inc.occurred_at],
    [*Reported at*], [#inc.reported_at],
    [*Resolved at*], [#inc.resolved_at],
    [*BCP activated*], [#if inc.is_bcp_activated [Yes] else [No]],
  )
}

#if has(inc.description) [
  == Description
  #inc.description
]

#if has(inc.resolution) [
  == Resolution
  #inc.resolution
]

// --------------------------------------------------------------------- scope

#let scope = (
  ("Qualifications", inc.qualifications),
  ("Related entities", inc.entities),
  ("Affected assets", inc.assets),
  ("Related threats", inc.threats),
).filter(((label, items)) => items.len() > 0)

#if scope.len() > 0 [
  = Scope
  #gl-table(
    columns: (38%, 1fr),
    header: ("Area", "Items"),
    ..scope.map(((label, items)) => (label, items.join(", "))).flatten(),
  )
]

// ------------------------------------------------------------------ timeline

#pagebreak(weak: true)
= Timeline

#gl-label("What this covers:")[#d.counts.total entries in chronological order, times in UTC: #d.counts.detection detection and #d.counts.mitigation mitigation.]
#v(0.4em)

#let entry-detail(entry) = {
  let lines = ()
  if has(entry.observation) { lines.push(entry.observation) }
  if entry.evidences.len() > 0 { lines.push(gl-label("Evidence:", entry.evidences.join(", "))) }
  [#text(fill: dark, weight: "bold")[#entry.entry]#if lines.len() > 0 [ \ #text(fill: body-grey)[#lines.join(linebreak())]]]
}

#if d.timeline.len() > 0 [
  #gl-table(
    columns: (17%, 20%, 1fr, 18%),
    header: ("Entry type", "Time", "Entry and observation", "Author"),
    ..d
      .timeline
      .map(entry => (
        entry-label.at(entry.type_key, default: entry.type_key),
        entry.timestamp,
        entry-detail(entry),
        if has(entry.author) { entry.author } else { "-" },
      ))
      .flatten(),
  )
] else [
  No timeline entries recorded.
]

#v(1.5em)
#text(8pt)[#gl-label("Generated at:", d.generated_at) #h(1em) #gl-label("Document ID:", d.id)]
