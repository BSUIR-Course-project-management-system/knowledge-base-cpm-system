import requests
from datetime import datetime, timedelta
from itertools import combinations
from typing import List, Tuple, Optional

API_URL_GET_OCCUPIED = "http://api.example.com/get_occupied_slots"

def parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))

def generate_candidate_starts(start_dt: datetime,
                              end_dt: datetime,
                              step_minutes: int,
                              duration_minutes: int,
                              occupied_intervals: List[Tuple[datetime, datetime]]) -> List[datetime]:
    candidates = []
    current = start_dt
    # Округление до шага вверх
    minutes_since_midnight = current.hour * 60 + current.minute
    remainder = minutes_since_midnight % step_minutes
    if remainder != 0:
        current += timedelta(minutes=step_minutes - remainder)
    while current + timedelta(minutes=duration_minutes) <= end_dt:
        slot_end = current + timedelta(minutes=duration_minutes)
        conflict = False
        for occ_start, occ_end in occupied_intervals:
            if current < occ_end and slot_end > occ_start:
                conflict = True
                break
        if not conflict:
            candidates.append(current)
        current += timedelta(minutes=step_minutes)
    return candidates

def score_combination(starts: Tuple[datetime, ...],
                      start_dt: datetime,
                      end_dt: datetime) -> float:
    total_secs = (end_dt - start_dt).total_seconds()
    ideal_offsets = [total_secs * (i + 1) / 4 for i in range(3)]
    start_sec = start_dt.timestamp()
    sorted_starts = sorted(starts)
    score = 0.0
    for i, s in enumerate(sorted_starts):
        offset = s.timestamp() - start_sec
        score += (offset - ideal_offsets[i]) ** 2
    return score

def select_best_slots(candidates: List[datetime],
                      start_dt: datetime,
                      end_dt: datetime) -> Optional[List[datetime]]:
    if len(candidates) < 3:
        return None
    best_combo = None
    best_score = float('inf')
    for combo in combinations(candidates, 3):
        s = score_combination(combo, start_dt, end_dt)
        if s < best_score:
            best_score = s
            best_combo = combo
    return sorted(best_combo) if best_combo else None

def get_occupied_slots(reviewer_name: str) -> List[Tuple[datetime, datetime]]:
    try:
        resp = requests.get(API_URL_GET_OCCUPIED, params={"reviewer": reviewer_name}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        occupied = []
        for slot in data.get("occupied_slots", []):
            start = parse_iso(slot["start"])
            end = parse_iso(slot["end"])
            occupied.append((start, end))
        return occupied
    except Exception as e:
        print(f"Ошибка получения занятых слотов: {e}")
        return []

def main():
    print("=== Планирование опроцентовок ===")
    
    project_name = input("Название проекта: ").strip()
    reviewer_name = input("Имя проверяющего: ").strip()
    start_date_str = input("Дата принятия темы (YYYY-MM-DD): ").strip()
    end_date_str = input("Конечная дата (защита) (YYYY-MM-DD): ").strip()
    duration_str = input("Длительность опроцентовки (минуты, по умолчанию 30): ").strip()
    step_minutes = 30
    if duration_str == "":
        duration_minutes = 30
    else:
        duration_minutes = int(duration_str)
    
    work_start_hour = 9
    work_end_hour = 17
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=work_start_hour, minute=0)
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=work_end_hour, minute=0)
    if end_dt <= start_dt:
        print("Ошибка: конечная дата должна быть позже начальной.")
        return
    
    occupied = get_occupied_slots(reviewer_name)
    
    candidates = generate_candidate_starts(start_dt, end_dt, step_minutes, duration_minutes, occupied)
    best = select_best_slots(candidates, start_dt, end_dt)
    
    if best is None:
        print("Не удалось найти три свободных интервала для опроцентовок.")
        return
    
    print("\n=== Результат ===")
    print(f"Проект: {project_name}")
    print(f"Проверяющий: {reviewer_name}")
    for i, start in enumerate(best, start=1):
        end = start + timedelta(minutes=duration_minutes)
        print(f"  Опроцентовка {i}: {start.strftime('%Y-%m-%d %H:%M')} – {end.strftime('%H:%M')}")
    

if __name__ == "__main__":
    main()