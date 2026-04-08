# Cold Calls Analytics — Design Spec

## Overview

Ajouter une page d'analyse des cold calls à l'application LeadFinder. L'objectif : un outil rapide à utiliser pendant les appels pour tracker les résultats, avec une vision claire de la performance et des patterns.

## Navigation

- Barre de navigation en haut des deux pages avec 2 liens : "LeadFinder" (`/`) et "Cold Calls" (`/cold-calls`)
- Le logo eagle reste au-dessus de la navbar
- La page active est visuellement mise en avant (bouton plein vs outline)

## Page `/cold-calls` — Deux sections

### Section 1 : KPI & Analytics

**Filtre de période** en haut à droite : boutons radio `1J | 3J | 7J | 1M | All`

**Bloc KPI** — rangée de cartes :
- Total appels
- Succès (vert)
- Échecs / recalé au pitch (rouge)
- Objections (orange)
- Taux de conversion = succès / total (%)

Chaque carte : chiffre en gros, label en dessous, couleur distincte.

**Graphiques (côte à côte) :**
- Gauche : courbe du nombre d'appels par jour (filtrée par période)
- Droite : camembert (pie chart) de la répartition des résultats

### Section 2 : Call Tracker

**Boutons d'action** — 3 gros boutons :
- "Recalé au pitch" (rouge) — clic direct, enregistre immédiatement
- "Objection" (orange) — ouvre un sous-menu avec 7 sous-catégories :
  - Redirigé vers email
  - Pas d'intérêt
  - Pas de budget
  - Pas le temps
  - Pas le bon moment
  - Déjà équipé
  - Pas le décideur
- "Succès — RDV booké" (vert) — clic direct, enregistre immédiatement

**Bouton "Annuler dernier appel"** — petit, discret, sous les boutons principaux. Supprime le dernier enregistrement.

**Mini-stats de session** sous les boutons :
- Appels aujourd'hui
- Dernier résultat (avec l'heure)
- Taux de succès du jour
- Objection la plus fréquente du jour

## Données & Persistance

**Fichier** : `cold_calls_data.json` à la racine du projet.

**Format** — liste d'objets :
```json
{
  "timestamp": "2026-04-08T14:32:05",
  "result": "objection",
  "detail": "pas de budget"
}
```

**Valeurs de `result`** :
- `"pitch_fail"` — recalé au pitch
- `"objection"` — objection (avec `detail` renseigné)
- `"success"` — RDV booké

**`detail`** : sous-catégorie pour les objections, chaîne vide sinon.

Le fichier est lu/écrit à chaque action. Le bouton "Annuler" supprime la dernière entrée.

## Structure des fichiers

```
app.py                  — routing + navbar (allégé)
pages/
  leadfinder.py         — contenu actuel de app.py (recherche de leads)
  cold_calls.py         — nouvelle page (tracker + analytics)
cold_calls_data.json    — données des appels (créé automatiquement)
```

## Stack

- Dash + Dash Bootstrap Components (thème DARKLY, cohérent avec l'existant)
- Plotly pour les graphiques (courbe + camembert)
- JSON fichier local pour la persistance
- Pas de nouvelle dépendance

## Contraintes

- Thème sombre cohérent avec l'app existante
- Interface simple et rapide à utiliser pendant les appels
- Un clic = un appel enregistré
- Bouton annuler pour corriger les misclicks
- Compteur global (pas lié à un lead spécifique)
