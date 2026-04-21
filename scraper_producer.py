import time
import json
import requests
import hashlib
from bs4 import BeautifulSoup
from kafka import KafkaProducer
from datetime import datetime

# -- Connexion Kafka
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    api_version=(3, 9, 2),  # <--- AJOUTE CETTE LIGNE ABSOLUMENT
    value_serializer=lambda x: json.dumps(
        x, ensure_ascii=False
    ).encode("utf-8")
)

print("✅ Connecté à Kafka")

# ── IDs déjà scrapés (évite les doublons) ────
ids_scraped = set()

# ── Mapping Région → Ville principale ────────
region_to_ville = {
    "Casablanca-Settat":           "Casablanca",
    "Rabat-Salé-Kénitra":          "Rabat",
    "Tanger-Tétouan-Al Hoceïma":   "Tanger",
    "Marrakech-Safi":              "Marrakech",
    "Souss-Massa":                 "Agadir",
    "Fès-Meknès":                  "Fès",
    "Oriental":                    "Oujda",
    "Drâa-Tafilalet":              "Ouarzazate",
    "Béni Mellal-Khénifra":        "Béni Mellal",
    "Laâyoune-Sakia El Hamra":     "Laâyoune",
}

# ── Mapping Titre → Secteur ───────────────────
def deduire_secteur(titre):
    titre = titre.lower()
    if any(k in titre for k in ["data", "dev", "it", "digital", "web", "réseau", "cyber", "spark", "kafka", "cloud", "sql", "python", "bi", "analyste"]):
        return "It & Tech"
    elif any(k in titre for k in ["financ", "compta", "audit", "trésor", "contrôl", "fiscal"]):
        return "Finance & Rh"
    elif any(k in titre for k in ["rh", "recrutement", "ressources humaines", "paie", "talent"]):
        return "Finance & Rh"
    elif any(k in titre for k in ["commercial", "vente", "marketing", "brand", "cm", "community"]):
        return "Commerce"
    elif any(k in titre for k in ["qualité", "qhse", "production", "maintenance", "logistique", "industriel", "mécanicien"]):
        return "Industrie"
    elif any(k in titre for k in ["médecin", "infirmier", "pharmacien", "santé", "médical"]):
        return "Santé"
    elif any(k in titre for k in ["génie civil", "travaux", "btp", "chantier", "architecture"]):
        return "Btp"
    elif any(k in titre for k in ["tourisme", "hôtel", "guide", "réception"]):
        return "Tourisme"
    else:
        return "Autres"

def generer_id(titre, entreprise, date):
    """Génère un ID unique"""
    cle = f"{titre}{entreprise}{date}".lower()
    return "E" + hashlib.md5(cle.encode()).hexdigest()[:6].upper()

def extraire_li_value(ul, label):
    """
    Extrait la valeur d'un <li> contenant un label spécifique.
    Exemple : "Contrat proposé : " → "CDI"
    """
    if not ul:
        return None
    for li in ul.find_all("li"):
        texte = li.get_text()
        if label.lower() in texte.lower():
            strong = li.find("strong")
            if strong:
                return strong.get_text(strip=True)
    return None

def scraper_emploi_ma(page=1):
    """Scrape une page de emploi.ma"""

    url = f"https://www.emploi.ma/recherche-jobs-maroc?page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")

        # ── Trouver toutes les offres ─────────
        offres = soup.find_all("div", class_="card card-job")
        print(f"  🔍 {len(offres)} offres trouvées sur la page {page}")

        nouvelles = 0

        for offre in offres:
            try:
                # ── Titre ────────────────────
                h3 = offre.find("h3")
                titre = h3.get_text(strip=True) if h3 else None
                if not titre:
                    continue

                # ── Entreprise ───────────────
                entreprise_tag = offre.find("a", class_="card-job-company")
                entreprise = entreprise_tag.get_text(strip=True) if entreprise_tag else "Non renseigné"

                # ── Description (ul) ─────────
                ul = offre.find("ul")

                # ── Niveau Études ─────────────
                niveau = extraire_li_value(ul, "Niveau d'études")
                if not niveau:
                    niveau = "Non Renseigné"

                # ── Expérience ────────────────
                experience = extraire_li_value(ul, "Niveau d'expérience")
                if not experience:
                    experience = "Non renseigné"

                # ── Contrat ───────────────────
                contrat = extraire_li_value(ul, "Contrat proposé")
                if not contrat:
                    contrat = "CDI"

                # ── Région ────────────────────
                region = extraire_li_value(ul, "Région de")
                if not region:
                    region = "Casablanca-Settat"

                # ── Ville (depuis région) ─────
                ville = region_to_ville.get(region, region.split("-")[0].strip())

                # ── Compétences ───────────────
                competences = extraire_li_value(ul, "Compétences clés")
                if not competences:
                    competences = None

                # ── Date ─────────────────────
                time_tag = offre.find("time")
                if time_tag:
                    date_str = time_tag.get("datetime", "")
                    date_pub = date_str if date_str else datetime.now().strftime("%Y-%m-%d")
                else:
                    date_pub = datetime.now().strftime("%Y-%m-%d")

                # ── Secteur (déduit) ──────────
                secteur = deduire_secteur(titre)

                # ── ID unique ─────────────────
                id_offre = generer_id(titre, entreprise, date_pub)

                # ── Éviter les doublons ───────
                if id_offre in ids_scraped:
                    continue
                ids_scraped.add(id_offre)
                nouvelles += 1

                # ── Construire le document ────
                data = {
                    "ID_Offre":           id_offre,
                    "Titre_Poste":        titre,
                    "Entreprise":         entreprise,
                    "Ville":              ville,
                    "Region":             region,
                    "Secteur":            secteur,
                    "Type_Contrat":       contrat,
                    "Experience_Requise": experience,
                    "Niveau_Etudes":      niveau,
                    "Competences_Cles":   competences,
                    "Modalite_Travail":   "Présentiel",  # défaut
                    "Salaire_Mensuel_DH": None,          # imputer après
                    "Date_Publication":   date_pub,
                    "Source":             "emploi.ma",
                    "Timestamp":          datetime.now().isoformat(),
                }

                # ── Envoyer dans Kafka ────────
                producer.send("offres_emploi", value=data)
                print(f"  📤 {titre[:50]} | {ville} | {contrat}")

            except Exception as e:
                print(f"  ⚠️ Erreur offre : {e}")
                continue

        producer.flush()
        print(f"  ✅ Page {page} : {nouvelles} nouvelles offres envoyées")
        return nouvelles

    except Exception as e:
        print(f"❌ Erreur scraping page {page} : {e}")
        return 0

# ════════════════════════════════════════════
# BOUCLE PRINCIPALE
# ════════════════════════════════════════════
print("\n🕷️ Démarrage du scraper emploi.ma...")
print("   Intervalle : toutes les 30 minutes\n")

while True:
    print(f"\n{'='*50}")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} — Scraping en cours...")

    total = 0
    for page in range(1, 11):  # 10 pages × ~10 offres = ~100 offres
        total += scraper_emploi_ma(page)
        time.sleep(3)  # pause entre les pages

    print(f"\n✅ Total : {total} nouvelles offres envoyées dans Kafka")
    print(f"⏳ Prochain passage dans 30 minutes...")
    time.sleep(1800)