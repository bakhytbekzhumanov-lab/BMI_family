from datetime import datetime, timedelta
from typing import Any
import pytz
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from app.core.config import settings
import json
import os

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_service = None


def _get_service():
    global _service
    if _service:
        return _service

    creds = None
    token_path = settings.google_token_json
    creds_path = settings.google_credentials_json

    if os.path.exists(token_path):
        with open(token_path) as f:
            creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    _service = build("calendar", "v3", credentials=creds)
    return _service


def _calendar_id(target: str) -> str:
    mapping = {
        "owner": settings.owner_calendar_id,
        "wife": settings.wife_calendar_id,
        "family": settings.family_calendar_id,
    }
    return mapping.get(target, settings.owner_calendar_id)


def _format_event(event: dict, calendar_label: str) -> dict:
    start = event["start"].get("dateTime", event["start"].get("date", ""))
    if "T" in start:
        dt = datetime.fromisoformat(start)
        time_str = dt.strftime("%H:%M")
    else:
        time_str = "весь день"

    return {
        "id": event["id"],
        "title": event.get("summary", "Без названия"),
        "time": time_str,
        "start_raw": start,
        "location": event.get("location"),
        "description": event.get("description"),
        "calendar": calendar_label,
    }


def _fetch_events(time_min: datetime, time_max: datetime) -> list[dict]:
    service = _get_service()
    tz = pytz.timezone(settings.timezone)

    t_min = time_min.astimezone(pytz.utc).isoformat()
    t_max = time_max.astimezone(pytz.utc).isoformat()

    all_events = []
    calendars = [
        ("owner", settings.owner_calendar_id),
        ("wife", settings.wife_calendar_id),
        ("family", settings.family_calendar_id),
    ]

    for label, cal_id in calendars:
        if not cal_id:
            continue
        result = service.events().list(
            calendarId=cal_id,
            timeMin=t_min,
            timeMax=t_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        for e in result.get("items", []):
            all_events.append(_format_event(e, label))

    all_events.sort(key=lambda x: x["start_raw"])
    return all_events


def _today_range() -> tuple[datetime, datetime]:
    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


async def get_today_events() -> list[dict]:
    start, end = _today_range()
    return _fetch_events(start, end)


async def get_tomorrow_events() -> list[dict]:
    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    end = start + timedelta(days=1)
    return _fetch_events(start, end)


async def get_week_events() -> list[dict]:
    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return _fetch_events(start, end)


async def create_event(title: str, start_dt: datetime, calendar_target: str = "family",
                       duration_minutes: int = 60, description: str = "") -> dict:
    service = _get_service()
    cal_id = _calendar_id(calendar_target)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": settings.timezone},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": settings.timezone},
    }

    created = service.events().insert(calendarId=cal_id, body=event_body).execute()
    return _format_event(created, calendar_target)
