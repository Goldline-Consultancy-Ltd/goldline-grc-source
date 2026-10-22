// Findings report, English. Goldline house style (see goldline.typ).
// Payload: `core.generators.findings_assessment_context` via sys.inputs.data.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)
#let has(value) = value != none and value != "" and value != "-"

#let L = (
  summary: "Summary",
  details: "Assessment details",
  reference: "Reference",
  domain: "Domain",
  status: "Status",
  category: "Category",
  authors: "Authors",
  reviewers: "Reviewers",
  date: "Date",
  description: "Description:",
  metrics: "Findings at a glance",
  total: "Total",
  open: "Open",
  closed: "Closed",
  unresolved: "Unresolved important",
  severity: "Severity",
  count: "Findings",
  share: "Share",
  observation: "Observation",
  findings: "Findings",
  covers: "What this covers:",
  covers-text: n => [#n findings, grouped by severity, with the owner, dates, observation and recommendation.],
  ref: "Ref",
  finding: "Finding",
  owner: "Owner:",
  priority: "Priority:",
  eta: "ETA:",
  due: "Due:",
  obs: "Observation:",
  rec: "Recommendation:",
  controls: "Applied controls:",
  evidence: "Evidence:",
  labels: "Labels:",
  generated: "Generated at:",
  doc-id: "Document ID:",
)

#let assessment-status-label = (
  "planned": "Planned",
  "in_progress": "In progress",
  "in_review": "In review",
  "done": "Done",
  "deprecated": "Deprecated",
)
#let category-label = (
  "--": "Undefined",
  "pentest": "Pentest",
  "threat_hunting": "Threat hunting",
  "red_teaming": "Red teaming",
  "audit": "Audit",
  "self_identified": "Self-identified",
  "posture": "Posture follow-up",
  "responsible_disclosure": "Responsible disclosure",
)
#let severity-label = (
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
  undefined: "Undefined",
)
#let status-label = (
  undefined: "Undefined",
  identified: "Identified",
  confirmed: "Confirmed",
  assigned: "Assigned",
  in_progress: "In progress",
  mitigated: "Mitigated",
  resolved: "Resolved",
  dismissed: "Dismissed",
  deprecated: "Deprecated",
  closed: "Closed",
)

// Severity fills: low green, medium amber, high and critical pink, else grey.
#let severity-rating(key) = (
  critical: "high",
  high: "high",
  medium: "medium",
  low: "low",
).at(key, default: "not_assessed")
#let severity-cell(key) = rating-cell(
  severity-rating(key),
  label: severity-label.at(key, default: key),
)

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: d.assessment.name, client: client)

// ------------------------------------------------------------- front matter

#gl-front-matter()

// ------------------------------------------------------------------- summary

= #L.summary

#gl-details((
  (L.reference, field(d.assessment, "ref_id")),
  (L.category, category-label.at(d.assessment.category_key, default: d.assessment.category_key)),
  (L.domain, field(d.assessment, "folder")),
  (L.status, assessment-status-label.at(d.assessment.status_key, default: "-")),
  (L.authors, field(d.assessment, "authors")),
  (L.reviewers, field(d.assessment, "reviewers")),
  (L.date, d.date),
))

#if has(d.assessment.description) [
  #gl-label(L.description, d.assessment.description)
]

#let m = d.metrics
== #L.metrics
#gl-table(
  columns: (1fr,) * 4,
  align: center,
  header: (L.total, L.open, L.closed, L.unresolved),
  [#m.total],
  rating-cell("non_compliant", label: [#m.open]),
  rating-cell("compliant", label: [#m.closed]),
  rating-cell("partially_compliant", label: [#m.unresolved_important]),
)

== #L.severity
#let peak = calc.max(1, ..d.severity_rows.map(r => r.count))
#gl-table(
  columns: (25%, 15%, 1fr),
  header: (L.severity, L.count, L.share),
  ..d
    .severity_rows
    .map(row => (
      severity-cell(row.key),
      align(right)[#row.count],
      box(width: 100%, height: 8pt)[
        #if row.count > 0 {
          place(left + horizon, rect(width: row.count / peak * 100%, height: 8pt, fill: navy))
        }
      ],
    ))
    .flatten(),
)

#if has(d.assessment.observation) [
  == #L.observation
  #d.assessment.observation
]

// ------------------------------------------------------------------ findings

#pagebreak(weak: true)
= #L.findings

#let total-findings = d.groups.map(g => g.findings.len()).sum(default: 0)
#gl-label(L.covers, (L.covers-text)(total-findings))

#let detail(f) = {
  let lines = ()
  if has(field(f, "description", fallback: "")) { lines.push(f.description) }
  let meta = ()
  if has(field(f, "owners", fallback: "")) { meta.push(gl-label(L.owner, f.owners)) }
  if has(field(f, "priority", fallback: "")) { meta.push(gl-label(L.priority, [#f.priority])) }
  if has(field(f, "eta", fallback: "")) { meta.push(gl-label(L.eta, f.eta)) }
  if has(field(f, "due_date", fallback: "")) { meta.push(gl-label(L.due, f.due_date)) }
  if meta.len() > 0 { lines.push(meta.join(h(1em))) }
  if has(field(f, "observation", fallback: "")) { lines.push(gl-label(L.obs, f.observation)) }
  if has(field(f, "recommendation", fallback: "")) { lines.push(gl-label(L.rec, f.recommendation)) }
  let ctl = f.at("controls", default: ())
  if ctl.len() > 0 { lines.push(gl-label(L.controls, ctl.join(", "))) }
  let ev = f.at("evidences", default: ())
  if ev.len() > 0 { lines.push(gl-label(L.evidence, ev.join(", "))) }
  let lb = f.at("labels", default: ())
  if lb.len() > 0 { lines.push(gl-label(L.labels, lb.join(", "))) }
  [#text(fill: dark, weight: "bold")[#f.name]#if lines.len() > 0 [ \ #text(fill: body-grey)[#lines.join(linebreak())]]]
}

#for group in d.groups [
  == #severity-label.at(group.severity_key, default: group.severity_key) (#group.findings.len())
  #gl-table(
    columns: (11%, 1fr, 15%, 15%),
    header: (L.ref, L.finding, L.severity, L.status),
    ..group
      .findings
      .map(f => (
        field(f, "ref_id"),
        detail(f),
        severity-cell(f.severity_key),
        status-label.at(f.status_key, default: f.status_key),
      ))
      .flatten(),
  )
]

#v(1.5em)
#text(8pt)[#gl-label(L.generated, d.generated_at) #h(1em) #gl-label(L.doc-id, d.id)]
