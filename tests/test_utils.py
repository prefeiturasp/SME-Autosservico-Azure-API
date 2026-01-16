from utils.helpers import get_first_and_last_day_of_month, format_date, generate_work_item_url

def test_get_first_and_last_day_of_month():
    first, last = get_first_and_last_day_of_month(2024, 2)
    assert first == "2024-02-01"
    assert last == "2024-02-29"

def test_format_date_valid():
    assert format_date("2024-06-01T12:00:00Z") == "01/06/2024"

def test_format_date_invalid():
    assert format_date("data-invalida") is None

def test_generate_work_item_url():
    url = generate_work_item_url("123", "minha-org", "meu-projeto")
    assert url == "https://dev.azure.com/minha-org/meu-projeto/_workitems/edit/123"
