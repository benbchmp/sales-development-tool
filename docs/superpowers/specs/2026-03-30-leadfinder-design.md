# LeadFinder – Design Spec
**Date :** 2026-03-30
**Statut :** Approuvé

---

## Contexte

Outil interne de prospection B2B pour une activité de création/vente de sites web à des professionnels français qui n'en ont pas encore (artisans, photographes, professions libérales, etc.).

---

## Périmètre V1

- Recherche de leads via Google Places API
- Filtrage des entreprises sans site web
- Interface web locale avec Dash
- Export Excel
- Cache local SQLite (base pour le mini-CRM futur)

**Hors périmètre V1 :** emailing automatisé, mini-CRM, enrichissement via Pappers ou autres APIs tierces.

---

## Architecture

3 couches distinctes :

1. **Interface (Dash)** — filtres, tableau, export
2. **Logique métier** — orchestration des appels API, filtrage, mise en forme
3. **Connecteurs données** — Google Places (V1), extensible pour d'autres sources

### Structure des fichiers

```
websites/
├── app.py                  # Point d'entrée Dash
├── layout.py               # Composants UI (filtres, tableau)
├── callbacks.py            # Logique réactive (recherche, export)
├── connectors/
│   └── google_places.py    # Appels Google Places + Geocoding API
├── utils/
│   └── export.py           # Génération fichier Excel (openpyxl)
├── cache.db                # SQLite (cache des fiches + base CRM future)
├── .env                    # GOOGLE_API_KEY (jamais committé)
├── .gitignore
└── requirements.txt
```

---

## Interface utilisateur

### Panneau gauche – Filtres
- Champ texte : **Ville** (ex : "Lyon")
- Champ texte : **Type de commerce** (catégorie Google Places, ex : "plumber", "photographer")
- Checkbox **"Sans site web uniquement"** — cochée par défaut
- Bouton **"Rechercher"**

### Zone principale – Tableau de résultats
- Colonnes : Nom | Type | Téléphone | Adresse | Note Google | Nombre d'avis | Lien Google Maps
- Tri par colonne activé
- Nombre total de résultats affiché
- Bouton **"Exporter en Excel"**
- Indicateur de consommation API (nb d'appels utilisés dans la session)

---

## Flux de données

```
1. Saisie ville + type → clic "Rechercher"
2. Geocoding : ville → coordonnées GPS (Google Geocoding API, gratuit)
3. Nearby Search : recherche des commerces dans un rayon de 15km autour des coordonnées (configurable)
4. Pagination : jusqu'à 3 pages (60 résultats max)
5. Place Details : pour chaque résultat, appel détaillé (site web, tel, adresse)
6. Filtre : suppression des résultats avec site web renseigné
7. Cache SQLite : stockage des fiches (évite re-appels à l'API)
8. Affichage dans le tableau Dash
```

---

## Cache & base de données (SQLite)

Table `places` :
| Colonne | Type | Description |
|---------|------|-------------|
| `place_id` | TEXT PK | Identifiant unique Google |
| `name` | TEXT | Nom du commerce |
| `type` | TEXT | Catégorie Google Places |
| `phone` | TEXT | Numéro de téléphone |
| `address` | TEXT | Adresse postale complète |
| `rating` | REAL | Note Google |
| `user_ratings_total` | INTEGER | Nombre d'avis |
| `has_website` | BOOLEAN | True si site web présent |
| `maps_url` | TEXT | Lien Google Maps |
| `fetched_at` | DATETIME | Date du dernier appel API |
| `status` | TEXT | NULL en V1, "contacté" etc. en V2 |

Le champ `status` est prévu dès la V1 pour faciliter l'ajout du mini-CRM en V2 sans migration de schéma.

---

## API Google utilisées

| API | Usage | Coût |
|-----|-------|------|
| Geocoding API | Ville → GPS | Gratuit |
| Places Nearby Search | Lister les commerces | ~$0.032 / appel |
| Place Details | Détails (site, tel, adresse) | ~$0.017 / appel |

Budget estimé pour 100 recherches complètes (60 résultats) : ~$120 sur $200 de crédits gratuits/mois.

---

## Stack technique

| Composant | Outil |
|-----------|-------|
| Interface | Dash + Dash Bootstrap Components (DARKLY) |
| Appels API | `requests` |
| Base de données | SQLite via `sqlite3` (stdlib Python) |
| Export Excel | `openpyxl` |
| Config / secrets | `python-dotenv` |

---

## Ce qui vient après (V2)

- Mini-CRM : gérer le statut de chaque lead (contacté, intéressé, relancé) — le champ `status` en SQLite est déjà prévu
- Enrichissement : brancher Pappers, Hunter.io ou Dropcontact pour trouver les emails manquants
- Emailing automatisé : cold emails personnalisés par agent IA (Claude API), envoi via Brevo ou Instantly.ai
