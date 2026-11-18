import pytest
from pydantic import ValidationError
from app.schemas import GenerateIdeasRequest

def test_strips_subject_area():
    assert GenerateIdeasRequest(subject_area="  Экология  ").subject_area == "Экология"

def test_rejects_blank_subject_area():
    with pytest.raises(ValidationError):
        GenerateIdeasRequest(subject_area="   ")
