import pandas as pd
from pymongo import MongoClient
from rapidfuzz import process
import re

client_mongo = MongoClient("mongodb://localhost:27017/")
db = client_mongo["emploi_maroc"]

data = list(db["offres_brutes"].find({}, {"_id": 0}))
df = pd.DataFrame(data)
print(f"✅ {len(df)} documents chargés depuis MongoDB")
print(f" Valeurs manquantes : {df.isnull().sum().sum()}")
print(f" Doublons : {df.duplicated().sum()}")

df.dropna(how="all", inplace=True)
df.drop_duplicates(inplace=True)
print(f"\n✅ Après suppression doublons/vides : {len(df)} lignes")

def normaliser_fuzzy(valeur, valeurs_valides, seuil=80):
    """
    Normalise une valeur en la comparant à une liste de valeurs valides.
    
    Args:
        valeur         : valeur brute à normaliser
        valeurs_valides: liste des valeurs correctes attendues
        seuil          : score minimum de similarité (0-100)
                         80 = assez strict, 70 = plus permissif
    
    Returns:
        str : valeur normalisée si score >= seuil, sinon valeur originale
    
    Exemples :
        "Data Sientist"  → score 92 → "Data Scientist"  ✅
        "Data Engineeer" → score 95 → "Data Engineer"   ✅
        "Casaablanca"    → score 96 → "Casablanca"      ✅
        "Chef Cuisine"   → score 45 → "Chef Cuisine"    (gardé tel quel)
    """
    if pd.isna(valeur):
        return None
    
    valeur_str = str(valeur).strip()
    match, score, _ = process.extractOne(valeur_str, valeurs_valides)

    if score >= seuil:
        return match
    return valeur_str.title()

def appliquer_fuzzy_colonne(serie, valeurs_valides, seuil=80):
    """ sur toute colonne panda"""
    return serie.apply(
        lambda x: normaliser_fuzzy(x, valeurs_valides, seuil)
    )

print("\n Normalisation Titre_Poste avec Fuzzy Matching...")

titres_valides = [
    "Développeur Full Stack", "Développeur Frontend", "Développeur Backend",
    "Data Scientist", "Data Engineer", "ML Engineer",
    "DevOps Engineer", "Ingénieur Réseau", "Cybersécurité Analyst",
    "UX/UI Designer", "Product Manager", "Analyste BI / Power BI",
    "Chef de Projet IT", "Administrateur Système",
    
    "Analyste Financier", "Auditeur Financier", "Comptable",
    "Contrôleur de Gestion", "Responsable RH", "Gestionnaire de Paie",
    
    "Commercial B2B", "Responsable Commercial",
    "Chargé Marketing Digital", "Community Manager",
    
    "Ingénieur Production", "Responsable Qualité", "Technicien Maintenance",
    
    "Ingénieur Génie Civil", "Conducteur de Travaux",
    
    "Médecin Généraliste", "Infirmier(ère)", "Pharmacien",
    
    "Guide Touristique", "Réceptionniste Hôtel",
]

avant = df["Titre_Poste"].nunique()
df["Titre_Poste"] = appliquer_fuzzy_colonne(df["Titre_Poste"], titres_valides, seuil=80)
apres = df["Titre_Poste"].nunique()
print(f"✅ Titres : {avant} → {apres} métiers distincts")

print("\n Normalisation Ville avec Fuzzy Matching...")

villes_valides = [
    "Casablanca", "Rabat", "Tanger", "Marrakech",
    "Agadir", "Fès", "Oujda", "Meknès", "Tétouan", "Kénitra",
]

df["Ville"] = appliquer_fuzzy_colonne(df["Ville"], villes_valides, seuil=75)

# Reconstruire la Région depuis la Ville normalisée
region_map = {
    "Casablanca": "Casablanca-Settat",
    "Rabat":      "Rabat-Salé-Kénitra",
    "Tanger":     "Tanger-Tétouan-Al Hoceïma",
    "Marrakech":  "Marrakech-Safi",
    "Agadir":     "Souss-Massa",
    "Fès":        "Fès-Meknès",
    "Oujda":      "Oriental",
    "Meknès":     "Fès-Meknès",
    "Tétouan":    "Tanger-Tétouan-Al Hoceïma",
    "Kénitra":    "Rabat-Salé-Kénitra",
}
df["Region"] = df["Ville"].map(region_map)
print(f"✅ Villes normalisées : {df['Ville'].nunique()} villes")

# 5. NORMALISER Type_Contrat
print("\n🔍 Normalisation Type_Contrat avec Fuzzy Matching...")

contrats_valides = ["CDI", "CDD", "Freelance", "Stage", "Alternance"]

df["Type_Contrat"] = appliquer_fuzzy_colonne( df["Type_Contrat"], contrats_valides, seuil=70)
print(f"✅ Contrats normalisés : {df['Type_Contrat'].nunique()} types")

# 6. NORMALISER Experience_Requise
print("\n🔍 Normalisation Experience_Requise avec Fuzzy Matching...")

exp_valides = ["0-2 ans", "2-5 ans", "5-8 ans", "8+ ans"]

df["Experience_Requise"] = appliquer_fuzzy_colonne( df["Experience_Requise"], exp_valides, seuil=70)
print(f"✅ Expériences normalisées : {df['Experience_Requise'].nunique()} niveaux")

# 7. NORMALISER Modalite_Travail
print("\n🔍 Normalisation Modalite_Travail avec Fuzzy Matching...")

modalites_valides = ["Présentiel", "Hybride", "Télétravail complet"]

df["Modalite_Travail"] = appliquer_fuzzy_colonne( df["Modalite_Travail"], modalites_valides, seuil=70)
print(f"✅ Modalités normalisées : {df['Modalite_Travail'].nunique()} types")

# 8. NORMALISER Niveau_Etudes
print("\n🔍 Normalisation Niveau_Etudes avec Fuzzy Matching...")

niveaux_valides = [
    "Bac+2", "Bac+3", "Bac+5 / Master",
    "Bac+8 / Doctorat", "Sans Diplôme Requis"
]

df["Niveau_Etudes"] = appliquer_fuzzy_colonne(df["Niveau_Etudes"], niveaux_valides, seuil=70)
df["Niveau_Etudes"] = df["Niveau_Etudes"].fillna("Non Renseigné")
print(f"✅ Niveaux études normalisés : {df['Niveau_Etudes'].nunique()} niveaux")

# 9. NETTOYER Salaire_Mensuel_DH
def nettoyer_salaire(val):
    if pd.isna(val): 
        return None
    v = str(val).strip().lower()
    if re.match(r"^\d+k$", v):
        return int(v.replace("k", "")) * 1000
    v = re.sub(r"[^\d\-]", "", v)

    if "-" in v:
        parts = v.split("-")
        try: 
            return int((int(parts[0]) + int(parts[1])) / 2)
        except: 
            return None
    try:
        val_int = int(v)
        if val_int < 1500 or val_int > 100000:
            return None
        return val_int
    except:
        return None

df["Salaire_Mensuel_DH"] = df["Salaire_Mensuel_DH"].apply(nettoyer_salaire)
df["Salaire_Mensuel_DH"] = df.groupby("Secteur")["Salaire_Mensuel_DH"].transform(
    lambda x: x.fillna(x.median())
)
print(f"\n✅ Salaires nettoyés — médiane : {int(df['Salaire_Mensuel_DH'].median())} DH")

# 10. NETTOYER Date_Publication
df["Date_Publication"] = pd.to_datetime(
    df["Date_Publication"], dayfirst=False, errors="coerce"
)
df.loc[df["Date_Publication"].dt.year < 2024, "Date_Publication"] = None
df.loc[df["Date_Publication"].dt.year > 2025, "Date_Publication"] = None

df["Mois"] = df["Date_Publication"].dt.strftime("%B %Y")
df["Trimestre"] = ("T" + df["Date_Publication"].dt.quarter.astype(str)
                   + " " + df["Date_Publication"].dt.year.astype(str))
print(f"✅ Dates nettoyées — {df['Date_Publication'].notna().sum()} valides")

# 11. NETTOYER Delai_Recrutement_Jours
def nettoyer_delai(val):
    if pd.isna(val): 
        return None
    v = re.sub(r"[^\d]", "", str(val))
    try:
        d = int(v)
        return d if 1 <= d <= 90 else None
    except:
        return None

df["Delai_Recrutement_Jours"] = df["Delai_Recrutement_Jours"].apply(nettoyer_delai)
df["Delai_Recrutement_Jours"] = df["Delai_Recrutement_Jours"].fillna(
    df["Delai_Recrutement_Jours"].median()
)

# 12. NETTOYER Competences_Cles
def normaliser_competences(val):
    if pd.isna(val): return None
    v = re.sub(r"\s*[,/\-]\s*", "; ", str(val))
    skills = [s.strip().title() for s in v.split(";") if s.strip()]
    return "; ".join(skills)

df["Competences_Cles"] = df["Competences_Cles"].apply(normaliser_competences)

# 13. NORMALISER Secteur et Entreprise
df["Secteur"] = df["Secteur"].str.strip().str.title()
df["Entreprise"] = df["Entreprise"].str.strip().str.title()

# 14. SAUVEGARDER dans MongoDB
df_clean = df.copy()
df_clean["Date_Publication"] = df_clean["Date_Publication"].dt.strftime("%Y-%m-%d")
df_clean = df_clean.dropna(how="all")

clean_data = []
for row in df_clean.to_dict(orient="records"):
    clean_row = {k: v for k, v in row.items() if pd.notna(v)}
    if clean_row:
        clean_data.append(clean_row)

db["offres_propres"].drop()
db["offres_propres"].insert_many(clean_data)

print(f"\n{'='*55}")
print(f"  ✅ NETTOYAGE FUZZY TERMINÉ")
print(f"{'='*55}")
print(f"  Lignes finales  : {len(df)}")
print(f"  Valeurs manquantes  : {df.isnull().sum().sum()}")
print(f"  Doublons restants   : {df.duplicated().sum()}")
print(f"  Collection MongoDB  : offres_propres ✅")
