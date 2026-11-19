from typing import Dict, Any


# Переписать на реальное подключение к сервису таблиц
class TableClient:
    async def get_milestones(self, examiner: str, year: int) -> Dict[str, Any]:
        return {"milestone_1": [], "milestone_2": [], "milestone_3": []}
