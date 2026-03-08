import os
from dotenv import load_dotenv

# Load the variables from .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Folder paths
DATA_DIR = "Data"
FINAL_GRAPH_PATH = os.path.join(DATA_DIR, "final_memory_graph.json")
ENTITY_REGISTRY_PATH = os.path.join(DATA_DIR, "canonicalized_entities.json")