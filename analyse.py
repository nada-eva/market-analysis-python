import pandas as pd
from pymongo import MongoClient
from collections import Counter
import os

client = MongoClient("mongodb://localhost:27017/")
db = client["emploi_maroc"]

data = list(db["offres_propres"].find({}, {"_id": 0}))
df = pd.DataFrame(data)
print(f"✅ {len(df)} offres chargées depuis offres_propres")

os.makedirs("exports", exist_ok=True)

# KPIs
print("\n📊 Calcul des KPIs globaux...")

kpis = {
    "Total_Offres":              len(df),
    "Entreprises_Actives":       df["Entreprise"].nunique(),
    "Metiers_Distincts":         df["Titre_Poste"].nunique(),
    "Villes_Representees":       df["Ville"].nunique(),
    "Salaire_Median_DH":         int(df["Salaire_Mensuel_DH"].median()),
    "Salaire_Moyen_DH":          int(df["Salaire_Mensuel_DH"].mean()),
    "Salaire_Min_DH":            int(df["Salaire_Mensuel_DH"].min()),
    "Salaire_Max_DH":            int(df["Salaire_Mensuel_DH"].max()),
    "Delai_Moyen_Recrutement":   round(df["Delai_Recrutement_Jours"].mean(), 1),
    "Pct_CDI":                   round(len(df[df["Type_Contrat"]=="CDI"]) / len(df) * 100, 1),
    "Pct_Teletravail":           round(len(df[df["Modalite_Travail"]=="Télétravail complet"]) / len(df) * 100, 1),
    "Pct_Hybride":               round(len(df[df["Modalite_Travail"]=="Hybride"]) / len(df) * 100, 1),
    "Pct_IT_Tech":               round(len(df[df["Secteur"]=="It & Tech"]) / len(df) * 100, 1),
}

df_kpis = pd.DataFrame(list(kpis.items()), columns=["Indicateur", "Valeur"])
df_kpis.to_csv("exports/kpis_globaux.csv", index=False, encoding="utf-8-sig")

print(f"   Total offres          : {kpis['Total_Offres']}")
print(f"   Salaire médian        : {kpis['Salaire_Median_DH']} DH")
print(f"   % CDI                 : {kpis['Pct_CDI']}%")
print(f"   Délai moyen           : {kpis['Delai_Moyen_Recrutement']} jours")
print(f"✅ kpis_globaux.csv sauvegardé")

# ANALYSE 2 — PAR SECTEUR
print("\n📊 Analyse par secteur...")

secteur = df.groupby("Secteur").agg(
    Nb_Offres   = ("ID_Offre", "count"),
    Salaire_Moyen  = ("Salaire_Mensuel_DH",  "mean"),
    Salaire_Median  = ("Salaire_Mensuel_DH",  "median"),
    Delai_Moyen   = ("Delai_Recrutement_Jours","mean"),
    Nb_Entreprises  = ("Entreprise", "nunique"),
    Pct_CDI  = ("Type_Contrat",  lambda x: round((x=="CDI").mean()*100, 1)),
    Pct_Teletravail = ("Modalite_Travail",  lambda x: round((x=="Télétravail complet").mean()*100, 1)),
).reset_index()

secteur["Salaire_Moyen"]  = secteur["Salaire_Moyen"].round(0).astype(int)
secteur["Salaire_Median"] = secteur["Salaire_Median"].round(0).astype(int)
secteur["Delai_Moyen"]  = secteur["Delai_Moyen"].round(1)
secteur["Pct_Offres"]  = (secteur["Nb_Offres"] / len(df) * 100).round(1)
secteur = secteur.sort_values("Nb_Offres", ascending=False)

secteur.to_csv("exports/analyse_secteurs.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_secteurs.csv — {len(secteur)} secteurs")

# ANALYSE 3 — PAR MÉTIER
print("\n📊 Analyse par métier...")

metiers = df.groupby(["Titre_Poste", "Secteur"]).agg(
    Nb_Offres       = ("ID_Offre",               "count"),
    Salaire_Moyen   = ("Salaire_Mensuel_DH",     "mean"),
    Salaire_Median  = ("Salaire_Mensuel_DH",     "median"),
    Salaire_Min     = ("Salaire_Mensuel_DH",     "min"),
    Salaire_Max     = ("Salaire_Mensuel_DH",     "max"),
    Delai_Moyen     = ("Delai_Recrutement_Jours","mean"),
    Nb_Entreprises  = ("Entreprise",             "nunique"),
).reset_index()

metiers["Salaire_Moyen"]  = metiers["Salaire_Moyen"].round(0).astype(int)
metiers["Salaire_Median"] = metiers["Salaire_Median"].round(0).astype(int)
metiers["Delai_Moyen"]    = metiers["Delai_Moyen"].round(1)

# Score attractivité (0-100)
sal_min = metiers["Salaire_Moyen"].min()
sal_max = metiers["Salaire_Moyen"].max()
del_min = metiers["Delai_Moyen"].min()
del_max = metiers["Delai_Moyen"].max()

metiers["Score_Attractivite"] = (
    (metiers["Salaire_Moyen"] - sal_min) / (sal_max - sal_min) * 60 +
    (1 - (metiers["Delai_Moyen"] - del_min) / (del_max - del_min)) * 40
).round(1)

metiers = metiers.sort_values("Nb_Offres", ascending=False)
metiers.to_csv("exports/analyse_metiers.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_metiers.csv — {len(metiers)} métiers")

# ANALYSE 4 — PAR VILLE / RÉGION
print("\n📊 Analyse géographique...")

geo = df.groupby(["Ville", "Region"]).agg(
    Nb_Offres       = ("ID_Offre",               "count"),
    Salaire_Moyen   = ("Salaire_Mensuel_DH",     "mean"),
    Salaire_Median  = ("Salaire_Mensuel_DH",     "median"),
    Delai_Moyen     = ("Delai_Recrutement_Jours","mean"),
    Nb_Entreprises  = ("Entreprise",             "nunique"),
    Pct_CDI         = ("Type_Contrat",           lambda x: round((x=="CDI").mean()*100, 1)),
    Pct_Teletravail = ("Modalite_Travail",       lambda x: round((x=="Télétravail complet").mean()*100, 1)),
    Pct_Hybride     = ("Modalite_Travail",       lambda x: round((x=="Hybride").mean()*100, 1)),
).reset_index()

geo["Salaire_Moyen"]  = geo["Salaire_Moyen"].round(0).astype(int)
geo["Salaire_Median"] = geo["Salaire_Median"].round(0).astype(int)
geo["Delai_Moyen"]    = geo["Delai_Moyen"].round(1)
geo["Pct_Offres"]     = (geo["Nb_Offres"] / len(df) * 100).round(1)
geo = geo.sort_values("Nb_Offres", ascending=False)

geo.to_csv("exports/analyse_geo.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_geo.csv — {len(geo)} villes")

# ANALYSE 5 — COMPÉTENCES
print("\n📊 Analyse des compétences...")

all_skills = []
for val in df["Competences_Cles"].dropna():
    for skill in str(val).split(";"):
        s = skill.strip()
        if s:
            all_skills.append(s)

skill_counts = Counter(all_skills)
df_skills = pd.DataFrame(
    skill_counts.most_common(50),
    columns=["Competence", "Frequence"]
)
df_skills["Pct_Offres"] = (df_skills["Frequence"] / len(df) * 100).round(1)

df_skills.to_csv("exports/analyse_competences.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_competences.csv — Top {len(df_skills)} compétences")
print(f"   Top 5 : {list(df_skills['Competence'].head())}")

# ANALYSE 6 — CONTRATS & SALAIRES
print("\n📊 Analyse contrats & salaires...")

contrats = df.groupby(["Type_Contrat", "Experience_Requise", "Secteur"]).agg(
    Nb_Offres      = ("ID_Offre",            "count"),
    Salaire_Min    = ("Salaire_Mensuel_DH",  "min"),
    Salaire_Moyen  = ("Salaire_Mensuel_DH",  "mean"),
    Salaire_Max    = ("Salaire_Mensuel_DH",  "max"),
    Salaire_Median = ("Salaire_Mensuel_DH",  "median"),
).reset_index()

contrats["Salaire_Moyen"]  = contrats["Salaire_Moyen"].round(0).astype(int)
contrats["Salaire_Median"] = contrats["Salaire_Median"].round(0).astype(int)
contrats = contrats.sort_values("Nb_Offres", ascending=False)

contrats.to_csv("exports/contrats_salaires.csv", index=False, encoding="utf-8-sig")
print(f"✅ contrats_salaires.csv — {len(contrats)} combinaisons")

# ANALYSE 7 — TENDANCES MENSUELLES
print("\n📊 Analyse des tendances...")

df["Date_Publication"] = pd.to_datetime(df["Date_Publication"], errors="coerce")
df_dates = df.dropna(subset=["Date_Publication"]).copy()
df_dates["Mois_Annee"] = df_dates["Date_Publication"].dt.to_period("M").astype(str)

tendances = df_dates.groupby(["Mois_Annee", "Secteur"]).agg(
    Nb_Offres      = ("ID_Offre",           "count"),
    Salaire_Moyen  = ("Salaire_Mensuel_DH", "mean"),
).reset_index()

tendances["Salaire_Moyen"] = tendances["Salaire_Moyen"].round(0).astype(int)
tendances = tendances.sort_values(["Mois_Annee", "Nb_Offres"], ascending=[True, False])

tendances.to_csv("exports/tendances_mensuelles.csv", index=False, encoding="utf-8-sig")
print(f"✅ tendances_mensuelles.csv — {len(tendances)} lignes")

# ANALYSE 8 — DONNÉES BRUTES PROPRES (pour Power BI)
df["Date_Publication"] = df["Date_Publication"].dt.strftime("%Y-%m-%d")

# Colonne tranche salaire
def tranche(s):
    if pd.isna(s): return "Non renseigné"
    s = int(s)
    if s < 4000:    return "1. < 4 000 DH"
    elif s < 6000:  return "2. 4 000 – 6 000 DH"
    elif s < 8000:  return "3. 6 000 – 8 000 DH"
    elif s < 10000: return "4. 8 000 – 10 000 DH"
    elif s < 12000: return "5. 10 000 – 12 000 DH"
    elif s < 15000: return "6. 12 000 – 15 000 DH"
    elif s < 20000: return "7. 15 000 – 20 000 DH"
    else:           
        return "8. > 20 000 DH"

df["Tranche_Salaire"] = df["Salaire_Mensuel_DH"].apply(tranche)

df.to_csv("exports/offres_propres.csv", index=False, encoding="utf-8-sig")
print(f"\n✅ offres_propres.csv — {len(df)} lignes (données complètes)")

# Créer une table compétences × offres
rows = []
for _, row in df.iterrows():
    if pd.notna(row["Competences_Cles"]):
        for skill in str(row["Competences_Cles"]).split(";"):
            s = skill.strip()
            if s:
                rows.append({
                    "ID_Offre": row["ID_Offre"],
                    "Competence": s,
                    "Secteur": row["Secteur"],
                    "Titre_Poste": row["Titre_Poste"],
                    "Ville": row["Ville"],
                })

df_comp_detail = pd.DataFrame(rows)
df_comp_detail.to_csv("exports/competences_detail.csv", 
                       index=False, encoding="utf-8-sig")
print(f"✅ competences_detail.csv — {len(df_comp_detail)} lignes")


print(f"\n{'='*55}")
print(f"  ✅ ANALYSE TERMINÉE — fichiers dans exports/")
print(f"{'='*55}")
fichiers = [
    ("kpis_globaux.csv",         "Indicateurs clés"),
    ("analyse_secteurs.csv",     "Stats par secteur"),
    ("analyse_metiers.csv",      "Stats par métier"),
    ("analyse_geo.csv",          "Stats par ville"),
    ("analyse_competences.csv",  "Top 50 compétences"),
    ("contrats_salaires.csv",    "Contrats × salaires"),
    ("tendances_mensuelles.csv", "Évolution mensuelle"),
    ("offres_propres.csv",       "Données complètes"),
]
for f, desc in fichiers:
    print(f"  📄 {f:<30} → {desc}")
