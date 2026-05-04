from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
LOGS_DIR = BASE_DIR / "logs"

RECOMMENDATION_RANKING_LOG_FILE = LOGS_DIR / "search_ranking.log"
RECOMMENDATION_TOPIC_LOG_FILE = LOGS_DIR / "topic_descriptions.log"
RECOMMENDATION_MAIN_LOG_FILE = LOGS_DIR / "recommendation_main.log"

TOPIC_DATA_FILE = PROJECT_DIR / "table_api" / "data" / "topic_data.json"
