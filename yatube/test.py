from datetime import datetime


def year():
    """Добавляет переменную с текущим годом."""
    y = datetime.today().year
    return {
        'year': y,
    }


print(year())
