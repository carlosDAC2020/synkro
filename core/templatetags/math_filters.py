from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplica dos valores"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract_total(detalle):
    """Calcula el subtotal de un detalle de venta"""
    try:
        return float(detalle.cantidad) * float(detalle.precio_unitario_venta)
    except (ValueError, TypeError):
        return 0
