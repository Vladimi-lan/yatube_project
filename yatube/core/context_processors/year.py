from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    y = datetime.today().year
    return {
        'year': y,
    }
