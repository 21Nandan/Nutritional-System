"""
EATGOOD — Per-request user profile.

The profile lives only in the visitor's browser (localStorage). The frontend sends it
with each request in the X-Eatgood-Profile header as URI-encoded JSON. The server
validates it, uses it for that one request, and never stores it. This keeps one
visitor's allergens from ever being applied to another visitor.
"""

import json
from typing import Literal
from urllib.parse import unquote

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, ValidationError, field_validator

PROFILE_HEADER = "x-eatgood-profile"

GOALS = {"Reduce Sugar", "Reduce Sodium", "Increase Fibre", "Increase Protein", "Balanced Choices"}


class UserProfile(BaseModel):
    """Only the fields scoring needs. Name, age and activity level never leave the browser."""

    goal: str = Field(default="Balanced Choices", max_length=200)
    dietary_preference: Literal["No preference", "Vegetarian", "Vegan", "Lactose avoidance"] = "No preference"
    allergens_to_avoid: str = Field(default="", max_length=500)

    @field_validator("goal")
    @classmethod
    def _known_goals(cls, value: str) -> str:
        goals = [g.strip() for g in value.split(",") if g.strip()]
        unknown = [g for g in goals if g not in GOALS]
        if unknown:
            raise ValueError(f"Unknown goal(s): {', '.join(unknown)}")
        return ", ".join(goals) or "Balanced Choices"


def get_request_profile(request: Request) -> dict:
    """Returns the validated profile sent by the browser, or an anonymous default profile.

    The returned dict carries profile_source = "browser" | "default" so responses can
    tell the user whether their own preferences were applied.
    """
    raw = request.headers.get(PROFILE_HEADER)
    if not raw:
        profile = UserProfile().model_dump()
        profile["profile_source"] = "default"
        return profile
    try:
        profile = UserProfile.model_validate(json.loads(unquote(raw))).model_dump()
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "PROFILE_INVALID",
                "message": "Your saved profile could not be read. Please open your profile and save it again.",
            },
        ) from exc
    profile["profile_source"] = "browser"
    return profile
