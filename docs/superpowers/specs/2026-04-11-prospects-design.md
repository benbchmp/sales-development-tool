# Prospects (Favoris par groupes) — Design Spec

## Overview

Ajouter un système de favoris/watchlist par groupes à LeadFinder. Depuis les résultats de recherche, on peut sauvegarder des entreprises dans des groupes nommés. Une page dédiée "Prospects" permet de gérer les groupes et les prospects sauvegardés.

## Bouton "+" dans le tableau LeadFinder

- Nouvelle première colonne dans le tableau de résultats : un bouton icône `+` (`bi-plus-circle`) par ligne
- Au clic : un **modal** s'ouvre avec :
  - Le nom de l'entreprise en titre
  - La liste des groupes existants, chacun comme bouton cliquable — un clic = ajouté et modal fermé
  - Les groupes où l'entreprise est déjà présente sont grisés avec "(déjà ajouté)"
  - Un séparateur
  - Un champ texte + bouton "Créer un groupe" pour créer un nouveau groupe à la volée
- Feedback visuel : notification verte "Ajouté à [nom du groupe]" (même pattern que le Call Tracker, `dbc.Alert` avec `duration=2000`)

## Page Prospects (`/prospects`)

Nouvel onglet "Prospects" dans la navbar (à côté de LeadFinder et Call Tracker).

### Barre de gestion des groupes (haut de page)

- **Dropdown** pour choisir le groupe actif
- Bouton **"+ Nouveau groupe"** : input inline pour nommer et créer
- Bouton **"Renommer"** : le nom du groupe devient un champ éditable
- Bouton **"Supprimer le groupe"** : confirmation avant suppression (supprime le groupe et ses prospects)

### Tableau du groupe sélectionné

Colonnes :
- Nom
- Localisation
- Téléphone
- Note
- Avis
- Site web
- Google Maps (lien cliquable)
- Notes (champ éditable)
- Actions (déplacer, supprimer)

Chaque ligne a :
- Bouton **crayon** (`bi-pencil`) : les notes deviennent un champ input, sauvegarde sur Entrée ou blur
- Bouton **flèche** (`bi-arrow-right-circle`) : dropdown avec la liste des autres groupes pour déplacer le prospect
- Bouton **corbeille** (`bi-trash`) : supprime le prospect du groupe

Compteur en bas : "X prospects dans ce groupe"

## Données & Persistance

**Fichier** : `prospects_data.json` à la racine du projet (créé automatiquement).

**Format** :
```json
{
  "groups": [
    {
      "id": "uuid-string",
      "name": "Plombiers Lyon",
      "prospects": [
        {
          "Nom": "Plomberie Martin",
          "Localisation": "LYON, 69007",
          "Téléphone": "04 78 12 34 56",
          "Note": "4.2",
          "Avis": "38",
          "Site web": "",
          "Google Maps": "https://...",
          "notes": "Rappeler lundi",
          "added_at": "2026-04-11T10:30:00"
        }
      ]
    }
  ]
}
```

- Les prospects conservent toutes les colonnes du tableau LeadFinder + `notes` (string libre) + `added_at` (date d'ajout)
- Les IDs de groupe sont des UUID pour éviter les conflits
- Le fichier est lu/écrit à chaque action (même pattern que `cold_calls_data.json`)
- La détection de doublons se fait par le champ `Nom` + `Localisation` (une même entreprise ne peut pas être deux fois dans le même groupe)

## Structure des fichiers

```
pages/prospects.py      — nouvelle page (groupes + tableau + gestion)
prospects_data.json     — données (créé automatiquement)
app.py                  — ajouter l'onglet Prospects dans la navbar + routing
pages/leadfinder.py     — ajouter le bouton "+" par ligne + le modal d'ajout
```

## Stack

- Dash + Dash Bootstrap Components (thème DARKLY, cohérent avec l'existant)
- Bootstrap Icons (déjà chargé)
- JSON fichier local pour la persistance
- UUID pour les IDs de groupe (`uuid.uuid4()`)
- Pas de nouvelle dépendance

## Contraintes

- Thème sombre cohérent avec l'app existante
- UX rapide : un clic pour ajouter un prospect depuis les résultats
- Modal non bloquant : on reste sur la page de recherche
- Les données des deux pages persistent entre les onglets (même pattern display:none/block)
- Les notes sont éditables inline, pas besoin d'ouvrir un formulaire
