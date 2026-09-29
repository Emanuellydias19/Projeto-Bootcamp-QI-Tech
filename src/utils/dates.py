from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def is_valid_competencia(competencia: str) -> bool:
    return parse_date(f"{competencia}-01") is not None


def today_in_sao_paulo() -> date:
    return datetime.now(SAO_PAULO).date()


def date_in_sao_paulo(moment: datetime) -> date:
    return moment.astimezone(SAO_PAULO).date()


def format_moment(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
