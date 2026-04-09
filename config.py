import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "doubler.db")

SECRET_KEY = "dev-secret-key"  