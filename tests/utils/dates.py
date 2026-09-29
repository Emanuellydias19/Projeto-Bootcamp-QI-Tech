from datetime import date, datetime
from zoneinfo import ZoneInfo

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def today_in_sao_paulo() -> date:
    return datetime.now(SAO_PAULO).date()
