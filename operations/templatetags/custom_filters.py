from django import template

register = template.Library()

@register.filter
def format_gs(value):
    """
    Formatea un número con separador de miles usando puntos.
    Ejemplo: 45000 -> 45.000
    """
    try:
        value = int(float(value))
        return f"{value:,}".replace(",", ".")
    except (ValueError, TypeError):
        return value
