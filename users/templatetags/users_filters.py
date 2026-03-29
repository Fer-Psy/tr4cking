"""
Template filters personalizados para la app users.
"""
from django import template

register = template.Library()


@register.filter
def dot_decimal(value):
    """
    Convierte un valor decimal a string usando punto como separador decimal.
    Útil para URLs de Google Maps y coordenadas GPS que requieren punto.
    Uso: {{ localidad.latitud|dot_decimal }}
    """
    if value is None:
        return ''
    return str(value).replace(',', '.')
