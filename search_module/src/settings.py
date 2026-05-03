from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PATH_TO_TEST_JSON = BASE_DIR / "data.json"
PATH_TO_MODEL = BASE_DIR / "models" / "all-MiniLM-L6-v2"
PATH_TO_CHROMA_DB = BASE_DIR / "chroma_db"
MAIN_LOG_FILE = BASE_DIR / "logs" / "search_module_main.log"
THEME_FINDER_LOG_FILE = BASE_DIR / "logs" / "theme_finder.log"
THEME_FINDER_MANAGER_LOG_FILE = BASE_DIR / "logs" / "theme_finder_manager.log"
MAX_DISTANCE = 0.75
