# 🌿 Job Market Analysis — Morocco 2024–2025

Analyse du marché de l'emploi au Maroc à partir de 482 offres collectées entre Mars 2024 et Janvier 2025.

---

## 📁 Structure du Projet

```
job-market-morocco/
│
├── data/
│   └── offres_emploi_BRUT.csv       # Données brutes (500 offres)
│
├── exports/                          # Fichiers CSV générés pour Power BI
│   ├── kpis_globaux.csv
│   ├── analyse_secteurs.csv
│   ├── analyse_metiers.csv
│   ├── analyse_geo.csv
│   ├── analyse_competences.csv
│   ├── contrats_salaires.csv
│   ├── tendances_mensuelles.csv
│   ├── offres_propres.csv
│   └── competences_detail.csv
│
├── connexion.py                      # Chargement CSV → MongoDB
├── nettoyage.py                      # Nettoyage & normalisation (Fuzzy)
├── analyse.py                        # Agrégations & exports CSV
├── Job Market.pbix                   # Dashboard Power BI (6 pages)
└── README.md
```

---

## ⚙️ Pipeline de Traitement

```
offres_emploi_BRUT.csv
        │
        ▼
  connexion.py          → MongoDB : offres_brutes (500 docs)
        │
        ▼
  nettoyage.py          → MongoDB : offres_propres (482 docs)
        │
        ▼
  analyse.py            → exports/*.csv (9 fichiers)
        │
        ▼
  Job Market.pbix       → Dashboard Power BI (6 pages)
```

---

## 🗃️ Base de Données MongoDB

- **Base** : `emploi_maroc`
- **Collection brute** : `offres_brutes` — 500 documents (données originales)
- **Collection propre** : `offres_propres` — 482 documents (après nettoyage)

---

## 📄 Description des Fichiers

### `connexion.py`
Charge le fichier CSV brut et l'insère dans MongoDB.

```
Entrée  → data/offres_emploi_BRUT.csv
Sortie  → MongoDB : offres_brutes
```

### `nettoyage.py`
Nettoie et normalise les données avec **Fuzzy Matching** (rapidfuzz).

**Opérations effectuées :**
- Suppression des doublons et lignes vides
- Normalisation des titres de postes (fuzzy matching, seuil 80)
- Normalisation des villes + création colonne Région
- Normalisation des types de contrats, expérience, modalités, niveau études
- Nettoyage des salaires (aberrants exclus, manquants → médiane secteur)
- Nettoyage des dates (création colonnes Mois et Trimestre)
- Nettoyage des délais de recrutement

```
Entrée  → MongoDB : offres_brutes
Sortie  → MongoDB : offres_propres
```

### `analyse.py`
Calcule les agrégations et exporte les fichiers CSV pour Power BI.

```
Entrée  → MongoDB : offres_propres
Sortie  → exports/*.csv (9 fichiers)
```

---

## 📊 Dashboard Power BI

6 pages interactives :

| Page | Contenu |
|------|---------|
| **Overview** | KPIs globaux, répartition secteurs, évolution mensuelle |
| **Top Jobs** | Top 15 métiers, salaires, scatter plot, treemap |
| **Skills** | Top compétences, matrice secteur, compétences par ville |
| **Geography** | Carte des offres, top villes, salaires par ville |
| **Contracts** | Distribution salaires, types contrats, détail par expérience |
| **Trends** | Évolution temporelle, tendances sectorielles, attractivité |

---

## 🔑 Colonnes du Dataset

| Colonne | Description | Exemple |
|---------|-------------|---------|
| `ID_Offre` | Identifiant unique | O001 |
| `Titre_Poste` | Intitulé du poste normalisé | Data Scientist |
| `Secteur` | Secteur d'activité | IT & Tech |
| `Entreprise` | Nom de l'entreprise | TechMaroc |
| `Ville` | Ville normalisée | Casablanca |
| `Region` | Région administrative | Casablanca-Settat |
| `Type_Contrat` | CDI / CDD / Freelance / Stage / Alternance | CDI |
| `Experience_Requise` | Tranche d'expérience | 2-5 ans |
| `Niveau_Etudes` | Niveau académique requis | Bac+5 / Master |
| `Salaire_Mensuel_DH` | Salaire mensuel en DH | 12000 |
| `Tranche_Salaire` | Tranche salariale | 5. 10 000 – 12 000 DH |
| `Modalite_Travail` | Présentiel / Hybride / Télétravail complet | Hybride |
| `Competences_Cles` | Compétences requises | Python; AWS; Agile |
| `Date_Publication` | Date de publication | 2024-06-15 |
| `Mois` | Mois de publication | June 2024 |
| `Trimestre` | Trimestre de publication | T2 2024 |
| `Delai_Recrutement_Jours` | Délai moyen en jours | 25 |

---

## 🚀 Installation & Lancement

### Prérequis
```bash
pip install pandas pymongo rapidfuzz
```

### MongoDB
```
MongoDB doit être lancé sur localhost:27017
```

### Ordre d'exécution
```bash
# 1. Charger les données dans MongoDB
python connexion.py

# 2. Nettoyer et normaliser
python nettoyage.py

# 3. Générer les exports CSV
python analyse.py

# 4. Ouvrir Power BI et rafraîchir les données
# Home → Refresh
```

---

## 📈 Résultats Clés

```
📋 482 offres analysées
💰 Salaire médian : 11 000 DH
⏱️  Délai moyen recrutement : 25.7 jours
🏢 37 entreprises actives
🖥️  IT & Tech : secteur dominant (41% des offres)
🎯 Agile & Scrum : compétences les plus demandées
🏙️  Casablanca : 1ère ville (175 offres, 36%)
```

---

## 🛠️ Technologies Utilisées

| Outil | Usage |
|-------|-------|
| Python 3.x | Traitement des données |
| Pandas | Manipulation DataFrame |
| MongoDB | Stockage des données |
| PyMongo | Connexion Python ↔ MongoDB |
| RapidFuzz | Normalisation par fuzzy matching |
| Power BI | Visualisation et dashboard |

---
Projet académique — Analyse du marché de l'emploi au Maroc 2024–2025