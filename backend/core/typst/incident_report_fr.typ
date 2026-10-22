// Rapport d'incident, français. Charte Goldline (voir goldline.typ).
// Payload: `core.generators.incident_context` via sys.inputs.data.

#import "goldline.typ": *

#let d = json(bytes(sys.inputs.data))
#let inc = d.incident
#let has(value) = value != none and value != "" and value != "-"

#let severity-label = (
  "1": "Critique",
  "2": "Majeure",
  "3": "Modérée",
  "4": "Mineure",
  "5": "Faible",
  "6": "Inconnue",
)
// Gravité vers couleur : critique et majeure en rose, modérée en ambre,
// mineure et faible en vert, inconnue en gris.
#let severity-rating = (
  "1": "high",
  "2": "high",
  "3": "medium",
  "4": "low",
  "5": "low",
  "6": "not_assessed",
)
#let incident-status-label = (
  "new": "Nouveau",
  "ongoing": "En cours",
  "resolved": "Résolu",
  "closed": "Clos",
  "dismissed": "Écarté",
)
#let detection-label = (
  "internally_detected": "Interne",
  "externally_detected": "Externe",
)
#let entry-label = (
  detection: "Détection",
  mitigation: "Atténuation",
  observation: "Observation",
  severity_changed: "Gravité modifiée",
  status_changed: "Statut modifié",
)

#let severity-cell(key) = table.cell(
  fill: rating-fill(severity-rating.at(key, default: "not_assessed")),
)[#severity-label.at(key, default: "-")]

#let client = if cover != none { cover.at("client", default: "") } else { "" }
#show: gl-setup.with(title: inc.name, client: client)

// ------------------------------------------------------------- front matter

#gl-front-matter()

// ------------------------------------------------------------------- summary

= Détails de l'incident

#{
  set text(9pt, fill: dark)
  table(
    columns: (38%, 1fr),
    stroke: border-stroke,
    inset: 4pt,
    fill: (x, _) => if x == 0 { cream } else { white },
    [*Référence*], [#if inc.ref_id != "" [#inc.ref_id] else [-]],
    [*Incident*], [#inc.name],
    [*Gravité*], severity-cell(inc.severity_key),
    [*Statut*], [#incident-status-label.at(inc.status_key, default: "-")],
    [*Détection*], [#detection-label.at(inc.detection_key, default: "-")],
    [*Domaine*], [#inc.folder],
    [*Responsables*], [#inc.owners],
    [*Survenu le*], [#inc.occurred_at],
    [*Signalé le*], [#inc.reported_at],
    [*Résolu le*], [#inc.resolved_at],
    [*PCA activé*], [#if inc.is_bcp_activated [Oui] else [Non]],
  )
}

#if has(inc.description) [
  == Description
  #inc.description
]

#if has(inc.resolution) [
  == Résolution
  #inc.resolution
]

// --------------------------------------------------------------------- scope

#let scope = (
  ("Qualifications", inc.qualifications),
  ("Entités concernées", inc.entities),
  ("Actifs affectés", inc.assets),
  ("Menaces associées", inc.threats),
).filter(((label, items)) => items.len() > 0)

#if scope.len() > 0 [
  = Périmètre
  #gl-table(
    columns: (38%, 1fr),
    header: ("Domaine", "Éléments"),
    ..scope.map(((label, items)) => (label, items.join(", "))).flatten(),
  )
]

// ------------------------------------------------------------------ timeline

#pagebreak(weak: true)
= Chronologie

#gl-label("Contenu :")[#d.counts.total entrées par ordre chronologique, heures en UTC : #d.counts.detection détection et #d.counts.mitigation atténuation.]
#v(0.4em)

#let entry-detail(entry) = {
  let lines = ()
  if has(entry.observation) { lines.push(entry.observation) }
  if entry.evidences.len() > 0 { lines.push(gl-label("Preuves :", entry.evidences.join(", "))) }
  [#text(fill: dark, weight: "bold")[#entry.entry]#if lines.len() > 0 [ \ #text(fill: body-grey)[#lines.join(linebreak())]]]
}

#if d.timeline.len() > 0 [
  #gl-table(
    columns: (17%, 20%, 1fr, 18%),
    header: ("Type d'entrée", "Heure", "Entrée et observation", "Auteur"),
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
  Aucune entrée dans la chronologie.
]

#v(1.5em)
#text(8pt)[#gl-label("Généré le :", d.generated_at) #h(1em) #gl-label("Identifiant du document :", d.id)]
