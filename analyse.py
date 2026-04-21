import pandas as pd
from pymongo import MongoClient
from collections import Counter
import os
import numpy as np
import re

# ── Connexion MongoDB ────────────────────────────────────────
client = MongoClient("mongodb://localhost:27017/")
db = client["emploi_maroc"]

data = list(db["offres_propres"].find({}, {"_id": 0}))
df = pd.DataFrame(data)
print(f"✅ {len(df)} offres chargées depuis offres_propres")

os.makedirs("exports", exist_ok=True)

# ════════════════════════════════════════════════════════════
# NETTOYAGE COMPLET
# ════════════════════════════════════════════════════════════

# ── 1. Salaire ───────────────────────────────────────────────
def clean_salary(val):
    if pd.isna(val) or str(val).strip() in ['Non Renseigné', 'nan', '']:
        return np.nan
    if isinstance(val, str):
        val = val.replace('DH','').replace(' ','').replace('\xa0','').strip()
        if '-' in val:
            try:
                parts = val.split('-')
                return (float(parts[0]) + float(parts[1])) / 2
            except:
                return np.nan
    try:
        f = float(val)
        return f if 1500 <= f <= 100000 else np.nan
    except:
        return np.nan

df["Salaire_Mensuel_DH"] = df["Salaire_Mensuel_DH"].apply(clean_salary)

# ── 2. Délai ─────────────────────────────────────────────────
df["Delai_Recrutement_Jours"] = pd.to_numeric(
    df["Delai_Recrutement_Jours"], errors='coerce'
)
df["Delai_Recrutement_Jours"] = df["Delai_Recrutement_Jours"].clip(lower=1, upper=60)

# ── 3. Type_Contrat ──────────────────────────────────────────
def norm_contrat(v):
    if pd.isna(v): return "CDI"
    v = str(v).strip().lower()
    if re.search(r"c\.?d\.?i|^cdi$|contrat.?cdi", v): return "CDI"
    if re.search(r"c\.?d\.?d|^cdd$|contrat.?cdd", v): return "CDD"
    if re.search(r"free|lance|ind[eé]pendant", v):     return "Freelance"
    if re.search(r"stage|stagiai|pfe|fin.?[eé]tude",v):return "Stage"
    if re.search(r"altern", v):                         return "Alternance"
    return "CDI"

df["Type_Contrat"] = df["Type_Contrat"].apply(norm_contrat)

# ── 4. Experience_Requise ────────────────────────────────────
def norm_exp(v):
    if pd.isna(v): return "Non renseigné"
    v = str(v).strip().lower()
    if re.search(r"d[eé]butant|junior|^0|0.?[àa].?2|0-2|moins.?2", v):
        return "0-2 ans"
    if re.search(r"confirm|2.?[àa].?5|2-5|entre.?2|3.?ans|4.?ans", v):
        return "2-5 ans"
    if re.search(r"exp[eé]rim|senior|5.?[àa].?8|5-8|entre.?5|6.?ans|7.?ans", v):
        return "5-8 ans"
    if re.search(r"expert|8.?\+|\+.?8|8.?ans.?et|10.?ans|9.?ans", v):
        return "8+ ans"
    return "Non renseigné"

df["Experience_Requise"] = df["Experience_Requise"].apply(norm_exp)

# ── 5. Modalite_Travail ──────────────────────────────────────
def norm_modalite(v):
    if pd.isna(v): return "Présentiel"
    v = str(v).strip().lower()
    if re.search(r"t[eé]l[eé]travail|remote|work.?from|full.?remote", v):
        return "Télétravail complet"
    if re.search(r"hybride|hybrid|mixte|partiel", v):
        return "Hybride"
    return "Présentiel"

df["Modalite_Travail"] = df["Modalite_Travail"].apply(norm_modalite)

# ── 6. Niveau_Etudes ─────────────────────────────────────────
def norm_niveau(v):
    if pd.isna(v): return "Non Renseigné"
    v = str(v).strip().lower()
    if re.search(r"bac\+?8|doctorat|ph.?d", v):             return "Bac+8 / Doctorat"
    if re.search(r"bac\+?5|master|ing[eé]nieur|grande", v): return "Bac+5 / Master"
    if re.search(r"bac\+?3|licence|bachelor", v):            return "Bac+3"
    if re.search(r"bac\+?2|bts|dut|deug", v):               return "Bac+2"
    if re.search(r"sans|aucun|non.?requis|non.?renseign", v):return "Sans Diplôme Requis"
    return "Non Renseigné"

df["Niveau_Etudes"] = df["Niveau_Etudes"].apply(norm_niveau)

# ── 7. Ville ─────────────────────────────────────────────────
df["Ville"] = df["Ville"].astype(str).str.strip().str.title()

ville_corrections = {
    "Caza":                  "Casablanca",
    "Casa":                  "Casablanca",
    "Casaablanca":           "Casablanca",
    "Casablanca-Mohammedia": "Casablanca",
    "Tanjah":                "Tanger",
    "Tanger-Med":            "Tanger",
    "Tanger Med":            "Tanger",
    "Marrakch":              "Marrakech",
    "Marrakesh":             "Marrakech",
    "Fes":                   "Fès",
    "Fez":                   "Fès",
    "Meknes":                "Meknès",
    "Tetouan":               "Tétouan",
    "Kenitra":               "Kénitra",
    "Casablanca-Settat":     "Casablanca",
}
df["Ville"] = df["Ville"].replace(ville_corrections)

# ── 8. Region ────────────────────────────────────────────────
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
df["Region"] = df["Ville"].map(region_map).fillna("Autres")

# ── 9. Secteur ───────────────────────────────────────────────
df["Secteur"] = df["Secteur"].astype(str).str.strip().str.title()
df.loc[df["Secteur"].isin(["Nan","None","nan",""]), "Secteur"] = "Autres"

# ── 10. Dates et Trimestre ───────────────────────────────────
df["Date_Publication_DT"] = pd.to_datetime(
    df["Date_Publication"], errors="coerce"
)
df["Trimestre"] = (
    "T" + df["Date_Publication_DT"].dt.quarter.astype(str)
    + " " + df["Date_Publication_DT"].dt.year.astype(str)
)
df["Trimestre"] = df["Trimestre"].str.replace(r"\.0", "", regex=True)
df["Trimestre"] = df["Trimestre"].where(df["Date_Publication_DT"].notna(), "Non renseigné")
df["Mois"] = df["Date_Publication_DT"].dt.strftime("%B %Y").fillna("Non renseigné")

# ── 11. Entreprise ───────────────────────────────────────────
df["Entreprise"] = df["Entreprise"].astype(str).str.strip().str.title()

# ── 12. Remplir valeurs manquantes par médiane secteur ───────
df["Salaire_Mensuel_DH"] = df.groupby("Secteur")[
    "Salaire_Mensuel_DH"
].transform(lambda x: x.fillna(x.median()))

df["Delai_Recrutement_Jours"] = df.groupby("Secteur")[
    "Delai_Recrutement_Jours"
].transform(lambda x: x.fillna(x.median()))

print(f"   Villes uniques        : {df['Ville'].nunique()}")
print(f"   Secteurs uniques      : {df['Secteur'].nunique()}")
print(f"   Contrats uniques      : {df['Type_Contrat'].nunique()}")
print(f"   Salaire médian        : {int(df['Salaire_Mensuel_DH'].median())} DH")
print(f"   Délai moyen           : {round(df['Delai_Recrutement_Jours'].mean(),1)} jours")

# ════════════════════════════════════════════════════════════
# KPIs GLOBAUX
# ════════════════════════════════════════════════════════════
print("\n📊 Calcul des KPIs globaux...")

kpis = {
    "Total_Offres":            len(df),
    "Entreprises_Actives":     df["Entreprise"].nunique(),
    "Metiers_Distincts":       df["Titre_Poste"].nunique(),
    "Villes_Representees":     df["Ville"].nunique(),
    "Salaire_Median_DH":       int(df["Salaire_Mensuel_DH"].median()),
    "Salaire_Moyen_DH":        int(df["Salaire_Mensuel_DH"].mean()),
    "Salaire_Min_DH":          int(df["Salaire_Mensuel_DH"].min()),
    "Salaire_Max_DH":          int(df["Salaire_Mensuel_DH"].max()),
    "Delai_Moyen_Recrutement": round(df["Delai_Recrutement_Jours"].mean(), 1),
    "Pct_CDI":                 round((df["Type_Contrat"]=="CDI").mean()*100, 1),
    "Pct_Teletravail":         round((df["Modalite_Travail"]=="Télétravail complet").mean()*100, 1),
    "Pct_Hybride":             round((df["Modalite_Travail"]=="Hybride").mean()*100, 1),
    "Pct_IT_Tech":             round((df["Secteur"]=="It & Tech").mean()*100, 1),
}

df_kpis = pd.DataFrame(list(kpis.items()), columns=["Indicateur","Valeur"])
df_kpis.to_csv("exports/kpis_globaux.csv", index=False, encoding="utf-8-sig")
print(f"   Total offres          : {kpis['Total_Offres']}")
print(f"   Salaire médian        : {kpis['Salaire_Median_DH']} DH")
print(f"   % CDI                 : {kpis['Pct_CDI']}%")
print(f"   Délai moyen           : {kpis['Delai_Moyen_Recrutement']} jours")
print(f"✅ kpis_globaux.csv sauvegardé")

# ════════════════════════════════════════════════════════════
# ANALYSE PAR SECTEUR
# ════════════════════════════════════════════════════════════
print("\n📊 Analyse par secteur...")

secteur_agg = df.groupby("Secteur").agg(
    Nb_Offres      = ("ID_Offre",               "count"),
    Salaire_Moyen  = ("Salaire_Mensuel_DH",     "mean"),
    Salaire_Median = ("Salaire_Mensuel_DH",     "median"),
    Delai_Moyen    = ("Delai_Recrutement_Jours","mean"),
    Nb_Entreprises = ("Entreprise",             "nunique"),
    Pct_CDI        = ("Type_Contrat",           lambda x: round((x=="CDI").mean()*100,1)),
    Pct_Teletravail= ("Modalite_Travail",       lambda x: round((x=="Télétravail complet").mean()*100,1)),
).reset_index().fillna(0)

secteur_agg["Salaire_Moyen"]  = secteur_agg["Salaire_Moyen"].round(0).astype(int)
secteur_agg["Salaire_Median"] = secteur_agg["Salaire_Median"].round(0).astype(int)
secteur_agg["Delai_Moyen"]    = secteur_agg["Delai_Moyen"].round(1)
secteur_agg["Pct_Offres"]     = (secteur_agg["Nb_Offres"]/len(df)*100).round(1)
secteur_agg = secteur_agg.sort_values("Nb_Offres", ascending=False)

secteur_agg.to_csv("exports/analyse_secteurs.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_secteurs.csv — {len(secteur_agg)} secteurs")

# ════════════════════════════════════════════════════════════
# ANALYSE PAR MÉTIER
# ════════════════════════════════════════════════════════════
print("\n📊 Analyse par métier...")

metiers = df.groupby(["Titre_Poste","Secteur"]).agg(
    Nb_Offres      = ("ID_Offre",               "count"),
    Salaire_Moyen  = ("Salaire_Mensuel_DH",     "mean"),
    Salaire_Median = ("Salaire_Mensuel_DH",     "median"),
    Salaire_Min    = ("Salaire_Mensuel_DH",     "min"),
    Salaire_Max    = ("Salaire_Mensuel_DH",     "max"),
    Delai_Moyen    = ("Delai_Recrutement_Jours","mean"),
    Nb_Entreprises = ("Entreprise",             "nunique"),
).reset_index().fillna(0)

metiers["Salaire_Moyen"]  = metiers["Salaire_Moyen"].round(0).astype(int)
metiers["Salaire_Median"] = metiers["Salaire_Median"].round(0).astype(int)
metiers["Delai_Moyen"]    = metiers["Delai_Moyen"].round(1)

sal_min = metiers["Salaire_Moyen"].min()
sal_max = metiers["Salaire_Moyen"].max()
del_min = metiers["Delai_Moyen"].min()
del_max = metiers["Delai_Moyen"].max()

metiers["Score_Attractivite"] = (
    (metiers["Salaire_Moyen"] - sal_min) / (sal_max - sal_min + 1) * 60 +
    (1 - (metiers["Delai_Moyen"] - del_min) / (del_max - del_min + 1)) * 40
).round(1)

metiers = metiers.sort_values("Nb_Offres", ascending=False)
metiers.to_csv("exports/analyse_metiers.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_metiers.csv — {len(metiers)} métiers")

# ════════════════════════════════════════════════════════════
# ANALYSE GÉOGRAPHIQUE
# ════════════════════════════════════════════════════════════
print("\n📊 Analyse géographique...")

geo = df.groupby(["Ville","Region"]).agg(
    Nb_Offres      = ("ID_Offre",               "count"),
    Salaire_Moyen  = ("Salaire_Mensuel_DH",     "mean"),
    Salaire_Median = ("Salaire_Mensuel_DH",     "median"),
    Delai_Moyen    = ("Delai_Recrutement_Jours","mean"),
    Nb_Entreprises = ("Entreprise",             "nunique"),
    Pct_CDI        = ("Type_Contrat",           lambda x: round((x=="CDI").mean()*100,1)),
    Pct_Teletravail= ("Modalite_Travail",       lambda x: round((x=="Télétravail complet").mean()*100,1)),
    Pct_Hybride    = ("Modalite_Travail",       lambda x: round((x=="Hybride").mean()*100,1)),
).reset_index().fillna(0)

geo["Salaire_Moyen"]  = geo["Salaire_Moyen"].round(0).astype(int)
geo["Salaire_Median"] = geo["Salaire_Median"].round(0).astype(int)
geo["Delai_Moyen"]    = geo["Delai_Moyen"].round(1)
geo["Pct_Offres"]     = (geo["Nb_Offres"]/len(df)*100).round(1)
geo = geo.sort_values("Nb_Offres", ascending=False)

geo.to_csv("exports/analyse_geo.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_geo.csv — {len(geo)} villes")

# ════════════════════════════════════════════════════════════
# ANALYSE COMPÉTENCES
# ════════════════════════════════════════════════════════════
print("\n📊 Analyse des compétences...")

all_skills = []
for val in df["Competences_Cles"].dropna():
    for skill in str(val).split(";"):
        s = skill.strip()
        if s:
            all_skills.append(s)

skill_counts = Counter(all_skills)
df_skills = pd.DataFrame(
    skill_counts.most_common(50), columns=["Competence","Frequence"]
)
df_skills["Pct_Offres"] = (df_skills["Frequence"]/len(df)*100).round(1)
df_skills.to_csv("exports/analyse_competences.csv", index=False, encoding="utf-8-sig")
print(f"✅ analyse_competences.csv — Top {len(df_skills)} compétences")

# ════════════════════════════════════════════════════════════
# CONTRATS & SALAIRES
# ════════════════════════════════════════════════════════════
print("\n📊 Analyse contrats & salaires...")

contrats = df.groupby(["Type_Contrat","Experience_Requise","Secteur"]).agg(
    Nb_Offres      = ("ID_Offre",           "count"),
    Salaire_Min    = ("Salaire_Mensuel_DH", "min"),
    Salaire_Moyen  = ("Salaire_Mensuel_DH", "mean"),
    Salaire_Max    = ("Salaire_Mensuel_DH", "max"),
    Salaire_Median = ("Salaire_Mensuel_DH", "median"),
).reset_index().fillna(0)

for col in ["Salaire_Moyen","Salaire_Median","Salaire_Min","Salaire_Max"]:
    contrats[col] = contrats[col].round(0).astype(int)
contrats = contrats.sort_values("Nb_Offres", ascending=False)

contrats.to_csv("exports/contrats_salaires.csv", index=False, encoding="utf-8-sig")
print(f"✅ contrats_salaires.csv — {len(contrats)} combinaisons")

# ════════════════════════════════════════════════════════════
# TENDANCES MENSUELLES
# ════════════════════════════════════════════════════════════
print("\n📊 Analyse des tendances...")

df_dates = df.dropna(subset=["Date_Publication_DT"]).copy()
df_dates["Mois_Annee"] = df_dates["Date_Publication_DT"].dt.to_period("M").astype(str)

tendances = df_dates.groupby(["Mois_Annee","Secteur"]).agg(
    Nb_Offres     = ("ID_Offre",           "count"),
    Salaire_Moyen = ("Salaire_Mensuel_DH", "mean"),
).reset_index().fillna(0)

tendances["Salaire_Moyen"] = tendances["Salaire_Moyen"].round(0).astype(int)
tendances = tendances.sort_values(["Mois_Annee","Nb_Offres"], ascending=[True,False])
tendances.to_csv("exports/tendances_mensuelles.csv", index=False, encoding="utf-8-sig")
print(f"✅ tendances_mensuelles.csv — {len(tendances)} lignes")

# ════════════════════════════════════════════════════════════
# OFFRES PROPRES COMPLÈTES
# ════════════════════════════════════════════════════════════
def tranche(s):
    if pd.isna(s): return "Non renseigné"
    try:
        s = int(s)
        if s < 4000:    return "1. < 4 000 DH"
        elif s < 6000:  return "2. 4 000 – 6 000 DH"
        elif s < 8000:  return "3. 6 000 – 8 000 DH"
        elif s < 10000: return "4. 8 000 – 10 000 DH"
        elif s < 12000: return "5. 10 000 – 12 000 DH"
        elif s < 15000: return "6. 12 000 – 15 000 DH"
        elif s < 20000: return "7. 15 000 – 20 000 DH"
        else:           return "8. > 20 000 DH"
    except:
        return "Non renseigné"

df["Tranche_Salaire"] = df["Salaire_Mensuel_DH"].apply(tranche)
df["Date_Publication"] = df["Date_Publication_DT"].dt.strftime("%Y-%m-%d")
df.drop(columns=["Date_Publication_DT"], inplace=True, errors="ignore")

df.to_csv("exports/offres_propres.csv", index=False, encoding="utf-8-sig")
print(f"\n✅ offres_propres.csv — {len(df)} lignes exportées")

# Table compétences détail
rows = []
for _, row in df.iterrows():
    if pd.notna(row.get("Competences_Cles")):
        for skill in str(row["Competences_Cles"]).split(";"):
            s = skill.strip()
            if s:
                rows.append({
                    "ID_Offre":    row["ID_Offre"],
                    "Competence":  s,
                    "Secteur":     row["Secteur"],
                    "Titre_Poste": row["Titre_Poste"],
                    "Ville":       row["Ville"],
                })

df_comp = pd.DataFrame(rows)
df_comp.to_csv("exports/competences_detail.csv", index=False, encoding="utf-8-sig")
print(f"✅ competences_detail.csv — {len(df_comp)} lignes")

print(f"\n{'='*55}")
print(f"  ✅ ANALYSE TERMINÉE — fichiers dans exports/")
print(f"{'='*55}")