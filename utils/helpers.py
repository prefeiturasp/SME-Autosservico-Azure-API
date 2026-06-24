import base64
from datetime import datetime, date
import calendar
from typing import Optional, Dict

from dateutil import parser
from fastapi import HTTPException

def format_date(iso_date: str) -> Optional[str]:
    if iso_date:
        try:
            return parser.isoparse(iso_date).strftime("%d/%m/%Y")
        except Exception:
            return None
    return None

def parse_iso_datetime(iso_date: Optional[str]) -> Optional[datetime]:
    if iso_date:
        try:
            return parser.isoparse(iso_date)
        except Exception:
            return None
    return None

def humanize_duration_hours(total_hours: float) -> tuple[float, str]:
    """Escolhe a unidade mais natural para uma duração em horas.

    Retorna (valor, unidade) onde unidade ∈
    {"minutes", "hours", "days", "months", "years"}.
    Aproxima 1 mês = 30 dias e 1 ano = 365 dias.
    """
    total_days = total_hours / 24

    if total_hours < 1:
        return round(total_hours * 60, 1), "minutes"
    if total_hours < 24:
        return round(total_hours, 1), "hours"
    if total_days < 30:
        return round(total_days, 1), "days"
    if total_days < 365:
        return round(total_days / 30, 1), "months"
    return round(total_days / 365, 1), "years"

def format_duration_label(value: float, unit: str) -> str:
    """Monta o rótulo em pt-br do tempo de atendimento (ex.: '2d', '5h', '1,5 meses')."""
    if value == int(value):
        number = str(int(value))
    else:
        number = f"{value:.1f}".replace(".", ",")

    if unit == "minutes":
        return f"{number}min"
    if unit == "hours":
        return f"{number}h"
    if unit == "days":
        return f"{number}d"
    if unit == "months":
        return f"{number} {'mês' if value == 1 else 'meses'}"
    return f"{number} {'ano' if value == 1 else 'anos'}"

def get_first_and_last_day_of_month(year: int, month: int) -> tuple[str, str]:
    first_day = date(year, month, 1)
    _, last_day_num = calendar.monthrange(year, month)
    last_day = date(year, month, last_day_num)
    return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")

def generate_work_item_url(work_item_id: str, organization: str, project: str) -> str:
    return f'https://dev.azure.com/{organization}/{project}/_workitems/edit/{work_item_id}'

def create_auth_headers(pat: str) -> Dict[str, str]:
    encoded_pat = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {encoded_pat}",
        "Content-Type": "application/json"
    }

def get_env_or_param(param_value: Optional[str], env_value: str, param_name: str) -> str:
    if param_value:
        return param_value
    if env_value:
        return env_value
    raise HTTPException(
        status_code=400,
        detail=f"{param_name} deve ser fornecido no request ou definido no .env"
    )