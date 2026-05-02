from datetime import datetime, timedelta
from .datetime_parser import DatetimeParser
from .config_parser import YamlParser
from .schedule_generator import SheduleGenerator
from table_api.storage import Storage
from .date_checker import DateChecker
import json


def main():
    config_parser = YamlParser()
    storage = Storage()
    dc = DateChecker()
    sg = SheduleGenerator(config_parser, dc)

    print("=== Планирование опроцентовок ===")

    project_name = input("Название проекта: ").strip()
    reviewer_name = input("Имя проверяющего: ").strip()
    start_date_str = input("Дата принятия темы (YYYY-MM-DD): ").strip()
    end_date_str = input("Конечная дата (защита) (YYYY-MM-DD): ").strip()
    duration_str = input(
        "Длительность опроцентовки (минуты, по умолчанию 30): "
    ).strip()
    duration_minutes = 30 if duration_str == "" else int(duration_str)

    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
        hour=sg.WORK_START_HOUR, minute=0
    )
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
        hour=sg.WORK_END_HOUR, minute=0
    )

    if end_dt <= start_dt:
        print("Ошибка: конечная дата должна быть позже начальной.")
        return

    data = json.loads(storage.get_examiner_schedule(reviewer_name))
    occupied_dict_list = data["Milestone_1"] + data["Milestone_2"] + data["Milestone_3"]
    occupied_intervals = []
    for item in occupied_dict_list:
        occ_start = DatetimeParser.parse_iso(item["start"])
        occ_end = DatetimeParser.parse_iso(item["end"])
        occupied_intervals.append((occ_start, occ_end))

    candidates = sg.generate_candidate_starts(
        start_dt, end_dt, duration_minutes, occupied_intervals
    )

    best = sg.select_slots(candidates, start_dt, end_dt, num_points=3)

    if best is None:
        print("Не удалось найти три свободных интервала для опроцентовок.")
        return

    print("\n=== Результат ===")
    print(f"Проект: {project_name}")
    print(f"Проверяющий: {reviewer_name}")
    for i, start in enumerate(best, start=1):
        end = start + timedelta(minutes=duration_minutes)
        print(
            f"  Опроцентовка {i}: {start.strftime('%Y-%m-%d %H:%M')} – {end.strftime('%H:%M')}"
        )


if __name__ == "__main__":
    main()
