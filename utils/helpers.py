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