
import pytest

from backend.services.request_service import (
    RequestService,
    RequestValidationError,
)


def test_valid_medical_leave():
    service = RequestService(college=None)

    payload = {
        "type": "medical_leave",
        "from_date": "2026-11-15",
        "to_date": "2026-11-16",
        "reason": "Not feeling well",
    }

    result = service.validate_request(payload)

    assert result["type"] == "medical_leave"
    assert result["half_day"] is False


def test_invalid_request_type():
    service = RequestService(college=None)

    payload = {
        "type": "work_from_home",
        "from_date": "2026-11-15",
        "to_date": "2026-11-15",
        "reason": "Test",
    }

    with pytest.raises(RequestValidationError):
        service.validate_request(payload)


def test_end_date_before_start_date():
    service = RequestService(college=None)

    payload = {
        "type": "personal_leave",
        "from_date": "2026-11-16",
        "to_date": "2026-11-15",
        "reason": "Personal work",
    }

    with pytest.raises(RequestValidationError):
        service.validate_request(payload)


def test_od_requires_event_name():
    service = RequestService(college=None)

    payload = {
        "type": "on_duty",
        "from_date": "2026-11-15",
        "to_date": "2026-11-15",
        "reason": "Participating in an event",
    }

    with pytest.raises(RequestValidationError):
        service.validate_request(payload)
