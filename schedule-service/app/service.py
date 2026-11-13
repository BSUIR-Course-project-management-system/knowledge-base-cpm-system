from fastapi import HTTPException, status
from app.clients import TableClient
from datetime import timedelta, datetime
from typing import List, Optional
from app.config import settings
from app.utils import is_work_day, parse_from_json
from app.schemas import ScheduleGenerateSchema, ScheduleResponseSchema


class Service:
    def __init__(self, table_client: TableClient) -> None:
        self.table_client = table_client

    async def _generate_candidate_starts(
        self,
        schema: ScheduleGenerateSchema,
    ) -> List[datetime]:
        """Метод для получения потенциальных дат со временем для опроцентовок

        Args:
            start_dt (datetime): Дата принятия проекта
            end_dt (datetime): Дата защиты проекта
            duration_minutes (int): Продолжительность опроцентовки

        Returns:
            List[datetime]: Потенциальные datetime объекты для опроцентовок
        """
        occupied_intervals = parse_from_json(
            await self.table_client.get_milestones(schema.examiner, schema.year)
        )

        candidates = []
        current_day = schema.start_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        while current_day <= schema.end_date:
            day_start = current_day.replace(hour=settings.WORK_START_HOUR, minute=0)
            day_end = current_day.replace(hour=settings.WORK_END_HOUR, minute=0)
            slot_start = max(day_start, schema.start_date)
            minutes_since_midnight = slot_start.hour * 60 + slot_start.minute
            remainder = minutes_since_midnight % settings.STEP_MINUTES
            if remainder != 0:
                slot_start += timedelta(minutes=settings.STEP_MINUTES - remainder)
            while slot_start + timedelta(minutes=schema.duration_minutes) <= min(
                day_end, schema.end_date
            ):
                slot_end = slot_start + timedelta(minutes=schema.duration_minutes)
                conflict = False
                for occ_start, occ_end in occupied_intervals:
                    if slot_start < occ_end and slot_end > occ_start:
                        conflict = True
                        break
                slot_date = slot_start.date()
                if not conflict and is_work_day(slot_date):  # type: ignore
                    candidates.append(slot_start)
                slot_start += timedelta(minutes=settings.STEP_MINUTES)
            current_day += timedelta(days=1)

        return candidates

    async def _select_slots(
        self,
        candidates: List[datetime],
        start_dt: datetime,
        end_dt: datetime,
        num_points: int = 3,
    ) -> Optional[List[datetime]]:
        """Метод для получения 3 дат и времени для проведения опроцентовок по проекту

        Args:
            candidates (List[datetime]): Потенциальные даты для проведения опроцентовок
            start_dt (datetime): Дата принятия проекта
            end_dt (datetime): Дата
            num_points (int, optional): Количество опроцентовок в семестре. По умолчанию 3.

        Returns:
            Optional[List[datetime]]: Список с датами опроцентовок и временем их проведения
        """
        if len(candidates) < num_points:
            return None

        total_secs = (end_dt - start_dt).total_seconds()
        ideal_offsets = [
            total_secs * (i + 1) / (num_points + 1) for i in range(num_points)
        ]

        selected = []
        used_indices = set()

        for ideal_sec in ideal_offsets:
            target = start_dt + timedelta(seconds=ideal_sec)
            best_idx = -1
            best_dist = float("inf")
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

    async def generate_schedule(
        self, schema: ScheduleGenerateSchema
    ) -> ScheduleResponseSchema:
        candidates = await self._generate_candidate_starts(schema)
        best = await self._select_slots(candidates, schema.start_date, schema.end_date)

        if not best:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cannot find free intervals for milestones",
            )

        return ScheduleResponseSchema(schedule=best)
