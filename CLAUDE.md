# LeadFinder – Instructions

## Projet
Outil interne de prospection B2B pour une activité de création/vente de sites web à des professionnels qui n'en ont pas encore.

## Rôles
- **L'utilisateur (Benjamin) n'est PAS développeur.** Il est le manager/product owner et décide de la direction du produit. Claude est le développeur. Toujours expliquer les choix techniques de manière accessible, proposer les meilleurs outils/intermédiaires possibles, et guider pas à pas pour tout ce qui touche au code, déploiement, infrastructure.

## Modèle par défaut
- Utiliser **Sonnet** (`sonnet`) par défaut pour toutes les tâches courantes (édition de code, debug, ajout de features, questions).
- Utiliser **Opus** (`opus`) uniquement pour la planification de tâches complexes (architecture, refactoring majeur, nouveaux modules importants).

## Stack (à confirmer après brainstorm)
- Python
- Interface : à définir (Dash, Streamlit, ou autre)
- Scraping leads : API Google Maps / Places
- Emailing : à définir
- Agents IA : à définir

## Fonctionnalités cibles
1. **Recherche de leads** – Scraper Google Maps par ville + type de commerce, filtrer ceux sans site web. Afficher : nom, téléphone, email, adresse. Export Excel.
2. **Cold emailing automatisé** – Template adapté par type de commerce, personnalisé par agent IA qui analyse la fiche Google Maps du prospect.

## Lancer l'app
```
cd C:/Users/benjb/python/websites && python app.py
```
