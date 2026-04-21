import pandas as pd
from pymongo import MongoClient

df = pd.read_csv("data/offres_emploi_BRUT.csv", encoding="utf-8-sig")

print(f"{len(df)} lignes chargées")
print(f"Colonnes : {list(df.columns)}")
print(df.head())

client = MongoClient("mongodb://localhost:27017/")
db = client["emploi_maroc"]
collection = db["offres_propres"]

# Insertion
collection.drop() 
data = df.to_dict(orient="records")
collection.insert_many(data)

print(f"{len(data)} documents insérés dans MongoDB")
print(f"Base : emploi_maroc | Collection : offres_brutes")



