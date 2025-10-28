from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore, auth

BASE_DIR = Path(__file__).resolve().parent
myfile = credentials.Certificate(BASE_DIR/"education.json")
firebase_admin.initialize_app(myfile)
db = firestore.client()