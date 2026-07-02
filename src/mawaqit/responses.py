"""Response models for endpoints whose swagger schema is defined inline.

Model generation only lifts the reusable ``definitions`` from each spec, so an
endpoint that declares its 200 body inline (rather than via ``$ref``) has no
generated model. The v3 ``/mosque/{uuid}/announcements`` endpoint is the only
such case; we compose it here from the generated ``Announcement`` / ``Event``
models so the field types still come straight from the swagger and cannot
diverge. Kept top-level (shared) so the sync client reuses it unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._generated.v3 import Announcement, Event


class AnnouncementsAndEvents(BaseModel):
    """The ``{announcements, events}`` payload of the v3 announcements endpoint."""

    announcements: list[Announcement] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
