from django import template
from decimal import Decimal
import locale

register = template.Library()

@register.filter
def currency(value):
    """
    Formatea un número como moneda con separadores de miles y símbolo de peso
    """
    if value is None:
        return "$0"
    
    try:
        # Convertir a Decimal si no lo es
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        # Formatear con separadores de miles
        formatted = "{:,.0f}".format(value)
        
        # Agregar símbolo de peso
        return f"${formatted}"
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return "$0"

@register.filter
def currency_detailed(value):
    """
    Formatea un número como moneda con decimales cuando es necesario
    """
    if value is None:
        return "$0.00"
    
    try:
        # Convertir a Decimal si no lo es
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        # Si es un número entero, mostrar sin decimales
        if value == value.to_integral_value():
            formatted = "{:,.0f}".format(value)
            return f"${formatted}"
        else:
            # Mostrar con 2 decimales
            formatted = "{:,.2f}".format(value)
            return f"${formatted}"
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return "$0.00"

@register.filter
def percentage(value):
    """
    Formatea un número como porcentaje
    """
    if value is None:
        return "0%"
    
    try:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        formatted = "{:.1f}".format(value * 100)
        return f"{formatted}%"
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return "0%"
