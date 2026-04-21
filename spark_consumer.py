from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType
from rapidfuzz import process
from pymongo import MongoClient
import pandas as pd
from datetime import datetime
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
os.environ['HADOOP_HOME'] = "C:/hadoop"
os.environ['PATH'] = "C:/hadoop/bin;" + os.environ['PATH']

# ════════════════════════════════════════════
# VALEURS VALIDES POUR FUZZY MATCHING
# ════════════════════════════════════════════
TITRES_VALIDES = [
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

CONTRATS_VALIDES = ["CDI", "CDD", "Freelance", "Stage", "Alternance"]

EXP_VALIDES = ["0-2 ans", "2-5 ans", "5-8 ans", "8+ ans"]

NIVEAUX_VALIDES = [
    "Bac+2", "Bac+3", "Bac+5 / Master",
    "Bac+8 / Doctorat", "Sans Diplôme Requis"
]

SECTEURS_VALIDES = [
    "It & Tech", "Finance & Rh", "Commerce",
    "Industrie", "Santé", "Btp", "Tourisme", "Autres"
]

# ── Médiane salaire par secteur (depuis données actuelles)
SALAIRE_MEDIANE_SECTEUR = {
    "It & Tech":    12000,
    "Finance & Rh": 10500,
    "Commerce":     9000,
    "Industrie":    8500,
    "Santé":        11000,
    "Btp":          8000,
    "Tourisme":     6000,
    "Autres":       9000,
}

# ── Délai moyen recrutement par secteur
DELAI_MOYEN_SECTEUR = {
    "It & Tech":    22,
    "Finance & Rh": 25,
    "Commerce":     28,
    "Industrie":    30,
    "Santé":        20,
    "Btp":          32,
    "Tourisme":     35,
    "Autres":       25,
}

# ════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ════════════════════════════════════════════
def fuzzy_normalize(valeur, valides, seuil=75):
    """Normalise une valeur avec Fuzzy Matching"""
    if not valeur or pd.isna(valeur) or str(valeur).strip() == "":
        return None
    match, score, _ = process.extractOne(str(valeur), valides)
    return match if score >= seuil else str(valeur).strip().title()


def normaliser_experience(exp):
    """
    Normalise l'expérience d'emploi.ma vers le format standard.
    Exemple : "Expérience entre 2 ans et 5 ans" → "2-5 ans"
    """
    if not exp or pd.isna(exp):
        return "Non renseigné"

    exp_lower = str(exp).lower()

    if any(k in exp_lower for k in ["débutant", "sans expérience", "0", "junior"]):
        return "0-2 ans"
    elif any(k in exp_lower for k in ["entre 2", "2 ans", "3 ans", "4 ans"]):
        return "2-5 ans"
    elif any(k in exp_lower for k in ["entre 5", "5 ans", "6 ans", "7 ans"]):
        return "5-8 ans"
    elif any(k in exp_lower for k in ["8 ans", "10 ans", "plus de 8", "senior", "confirmé"]):
        return "8+ ans"
    else:
        return fuzzy_normalize(exp, EXP_VALIDES, seuil=70) or "Non renseigné"


def normaliser_niveau(niveau):
    """
    Normalise le niveau d'études d'emploi.ma vers le format standard.
    Exemple : "Bac+5 et plus" → "Bac+5 / Master"
    """
    if not niveau or pd.isna(niveau):
        return "Non Renseigné"

    niveau_lower = str(niveau).lower()

    if "bac+8" in niveau_lower or "doctorat" in niveau_lower:
        return "Bac+8 / Doctorat"
    elif "bac+5" in niveau_lower or "master" in niveau_lower or "ingénieur" in niveau_lower:
        return "Bac+5 / Master"
    elif "bac+3" in niveau_lower or "licence" in niveau_lower:
        return "Bac+3"
    elif "bac+2" in niveau_lower or "bts" in niveau_lower or "dut" in niveau_lower:
        return "Bac+2"
    elif any(k in niveau_lower for k in ["sans", "aucun", "non requis"]):
        return "Sans Diplôme Requis"
    else:
        return fuzzy_normalize(niveau, NIVEAUX_VALIDES, seuil=70) or "Non Renseigné"


def calculer_tranche_salaire(salaire):
    """Calcule la tranche salariale"""
    if not salaire:
        return "Non renseigné"
    s = int(salaire)
    if s < 4000:     return "1. < 4 000 DH"
    elif s < 6000:   return "2. 4 000 – 6 000 DH"
    elif s < 8000:   return "3. 6 000 – 8 000 DH"
    elif s < 10000:  return "4. 8 000 – 10 000 DH"
    elif s < 12000:  return "5. 10 000 – 12 000 DH"
    elif s < 15000:  return "6. 12 000 – 15 000 DH"
    elif s < 20000:  return "7. 15 000 – 20 000 DH"
    else:            return "8. > 20 000 DH"


# ════════════════════════════════════════════
# TRAITEMENT DU BATCH
# ════════════════════════════════════════════
def nettoyer_batch(batch_df, batch_id):
    """
    Appelée pour chaque micro-batch Spark.
    Nettoie, normalise et insère dans MongoDB.
    """
    df = batch_df.toPandas()

    if df.empty:
        print(f"  Batch {batch_id} : vide, ignoré")
        return

    print(f"\n Batch {batch_id} : {len(df)} offres reçues")

    # ── 1. Normaliser Titre_Poste ─────────────
    df["Titre_Poste"] = df["Titre_Poste"].apply(
        lambda x: fuzzy_normalize(x, TITRES_VALIDES, seuil=80)
    )

    # ── 2. Normaliser Type_Contrat ────────────
    df["Type_Contrat"] = df["Type_Contrat"].apply(
        lambda x: fuzzy_normalize(x, CONTRATS_VALIDES, seuil=70)
    )

    # ── 3. Normaliser Experience_Requise ──────
    df["Experience_Requise"] = df["Experience_Requise"].apply(
        normaliser_experience
    )

    # ── 4. Normaliser Niveau_Etudes ───────────
    df["Niveau_Etudes"] = df["Niveau_Etudes"].apply(
        normaliser_niveau
    )

    # ── 5. Normaliser Secteur ─────────────────
    df["Secteur"] = df["Secteur"].apply(
        lambda x: fuzzy_normalize(x, SECTEURS_VALIDES, seuil=75)
    )

    # ── 6. Imputer Salaire manquant ───────────
    df["Salaire_Mensuel_DH"] = df.apply(
        lambda row: SALAIRE_MEDIANE_SECTEUR.get(
            row["Secteur"], 9000
        ) if pd.isna(row.get("Salaire_Mensuel_DH")) else row["Salaire_Mensuel_DH"],
        axis=1
    )

    # ── 7. Imputer Délai manquant ─────────────
    df["Delai_Recrutement_Jours"] = df["Secteur"].apply(
        lambda s: min(DELAI_MOYEN_SECTEUR.get(s, 25), 30)
    )

    # ── 8. Imputer Modalite_Travail ───────────
    df["Modalite_Travail"] = df["Modalite_Travail"].fillna("Présentiel")

    # ── 9. Calculer Tranche_Salaire ───────────
    df["Tranche_Salaire"] = df["Salaire_Mensuel_DH"].apply(
        calculer_tranche_salaire
    )

    # ── 10. Ajouter Mois et Trimestre ─────────
    df["Date_Publication"] = pd.to_datetime(
        df["Date_Publication"], errors="coerce"
    )
    df["Mois"] = df["Date_Publication"].dt.strftime("%B %Y")
    df["Trimestre"] = (
        "T" + df["Date_Publication"].dt.quarter.astype(str)
        + " " + df["Date_Publication"].dt.year.astype(str)
    )
    df["Date_Publication"] = df["Date_Publication"].dt.strftime("%Y-%m-%d")

    # ── 11. Nettoyer Entreprise ───────────────
    df["Entreprise"] = df["Entreprise"].str.strip().str.title()

    # ── 12. Insérer dans MongoDB ──────────────
    client = MongoClient("mongodb://localhost:27017/")
    db = client["emploi_maroc"]

    inseres = 0
    maj = 0

    for row in df.to_dict(orient="records"):
        # Garder seulement les valeurs non nulles
        clean = {k: v for k, v in row.items() if pd.notna(v) and v != ""}

        if not clean or "ID_Offre" not in clean:
            continue

        # Upsert : met à jour si existe, insère sinon
        result = db["offres_propres"].update_one(
            {"ID_Offre": clean["ID_Offre"]},
            {"$set": clean},
            upsert=True
        )

        if result.upserted_id:
            inseres += 1
        else:
            maj += 1

    client.close()
    print(f" {inseres} Insérées | {maj} mises à jour dans MongoDB")


# ════════════════════════════════════════════
# SCHEMA KAFKA — adapté à emploi.ma
# ════════════════════════════════════════════
schema = StructType() \
    .add("ID_Offre",           StringType()) \
    .add("Titre_Poste",        StringType()) \
    .add("Entreprise",         StringType()) \
    .add("Ville",              StringType()) \
    .add("Region",             StringType()) \
    .add("Secteur",            StringType()) \
    .add("Type_Contrat",       StringType()) \
    .add("Experience_Requise", StringType()) \
    .add("Niveau_Etudes",      StringType()) \
    .add("Competences_Cles",   StringType()) \
    .add("Modalite_Travail",   StringType()) \
    .add("Salaire_Mensuel_DH", StringType()) \
    .add("Date_Publication",   StringType()) \
    .add("Source",             StringType()) \
    .add("Timestamp",          StringType())

# ════════════════════════════════════════════
# SESSION SPARK
# ════════════════════════════════════════════
spark = SparkSession.builder \
    .appName("JobMarketStreaming_EmploiMa") \
    .config("spark.sql.streaming.checkpointLocation", "C:/hadoop/checkpoints") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("Parfait! Spark demarre avec le connecteur Kafka")
# ════════════════════════════════════════════
# LIRE DEPUIS KAFKA
# ════════════════════════════════════════════
df_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "offres_emploi") \
    .option("startingOffsets", "earliest") \
    .load()

# ── Parser JSON ──────────────────────────────
df_parsed = df_stream.select(
    from_json(
        col("value").cast("string"), schema
    ).alias("data")
).select("data.*")

# ════════════════════════════════════════════
# LANCER LE STREAMING
# ════════════════════════════════════════════
print("Streaming demarre - en attente des offres de emploi.ma...")

query = df_parsed.writeStream \
    .foreachBatch(nettoyer_batch) \
    .outputMode("append") \
    .start()

query.awaitTermination()
