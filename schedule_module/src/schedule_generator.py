from .config_parser import BaseParser
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


class SheduleGenerator:
    def __init__(self, config_parser: BaseParser) -> None:
        self.config_parser = config_parser
        self._init_variables()
        
    def _init_variables(self):
        data = self.config_parser.parse_config("config/settings.yaml")
        self.WORK_START_HOUR = data["work_start"]
        self.WORK_END_HOUR = data["work_end"]
        self.STEP_MINUTES = data["step"]
        
    def generate_candidate_starts(
    self,
    start_dt: datetime,
    end_dt: datetime,
    duration_minutes: int,
    occupied_intervals: List[Tuple[datetime, datetime]],
) -> List[datetime]:
        candidates = []
        current_day = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        while current_day <= end_dt:
            day_start = current_day.replace(hour=self.WORK_START_HOUR, minute=0)
            day_end = current_day.replace(hour=self.WORK_END_HOUR, minute=0)
            slot_start = max(day_start, start_dt)
            minutes_since_midnight = slot_start.hour * 60 + slot_start.minute
            remainder = minutes_since_midnight % self.STEP_MINUTES
            if remainder != 0:
                slot_start += timedelta(minutes=self.STEP_MINUTES - remainder)
            while slot_start + timedelta(minutes=duration_minutes) <= min(day_end, end_dt):
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                conflict = False
                for occ_start, occ_end in occupied_intervals:
                    if slot_start < occ_end and slot_end > occ_start:
                        conflict = True
                        break
                if not conflict:
                    candidates.append(slot_start)
                slot_start += timedelta(minutes=self.STEP_MINUTES)
            current_day += timedelta(days=1)
        return candidates


    def select_slots(
        self,
        candidates: List[datetime], start_dt: datetime, end_dt: datetime, num_points: int = 3
    ) -> Optional[List[datetime]]:
        if len(candidates) < num_points:
            return None

        total_secs = (end_dt - start_dt).total_seconds()
        ideal_offsets = [total_secs * (i + 1) / (num_points + 1) for i in range(num_points)]

        selected = []
        used_indices = set()

        for ideal_sec in ideal_offsets:
            target = start_dt + timedelta(seconds=ideal_sec)
            best_idx = -1
            best_dist = float('inf')
            for idx, cand in enumerate(candidates):
                if idx in used_indices:
                    continue
                if selected and cand <= selected[-1]:
                    continue
                dist = abs((cand - target).total_seconds())
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx
            if best_idx == -1:
                step = len(candidates) / (num_points + 1)
                indices = [int(step * (i + 1)) for i in range(num_points)]
                return [candidates[i] for i in indices]
            selected.append(candidates[best_idx])
            used_indices.add(best_idx)

        return sorted(selected)