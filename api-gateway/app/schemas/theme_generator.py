from pydantic import BaseModel, Field, field_validator


class GenerateIdeasRequest(BaseModel):
    subject_area: str = Field(
        min_length=2,
        max_length=160,
        description="Предметная область, например «Экология».",
        examples=["Экология"],
    )

    @field_validator("subject_area")
    @classmethod
    def subject_area_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Предметная область не должна быть пустой.")
        return value


class ProjectIdea(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=20, max_length=900)
    goal: str = Field(min_length=10, max_length=400)
    recommended_functionality: list[str] = Field(min_length=3, max_length=7)


class GenerateIdeasResponse(BaseModel):
    subject_area: str
    ideas: list[ProjectIdea] = Field(min_length=5, max_length=5)
