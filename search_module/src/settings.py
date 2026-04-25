from pathlib import Path

BASE_DIR = Path(__file__).parent.parent 
PATH_TO_TEST_JSON = BASE_DIR / 'data.json'               
PATH_TO_MODEL = BASE_DIR / 'models' / 'all-MiniLM-L6-v2'  
PATH_TO_CHROMA_DB = BASE_DIR / 'chroma_db'                