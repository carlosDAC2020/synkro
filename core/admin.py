# core/admin.py

from django.contrib import admin
from .models import (
    Categoria, Producto, Cliente, Venta, VentaDetalle,
    Proveedor, PedidoProveedor, PedidoDetalle
)

# --- Inlines para mejorar la experiencia de usuario ---

class VentaDetalleInline(admin.TabularInline):
    model = VentaDetalle
    extra = 1
    autocomplete_fields = ['producto']

class PedidoDetalleInline(admin.TabularInline):
    model = PedidoDetalle
    extra = 1
    autocomplete_fields = ['producto']

# --- Registros de Modelos ---

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ['nombre']

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # NUEVO: 'necesita_reposicion' muestra la alerta
    list_display = ('nombre', 'sku', 'categoria', 'stock_actual', 'precio_venta', 'necesita_reposicion')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'sku')
    # Para que la búsqueda de productos en Ventas y Pedidos sea más rápida
    search_fields = ['nombre', 'sku']

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email')
    search_fields = ('nombre', 'email')

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'cliente', 'estado', 'monto_total', 'usuario')
    list_filter = ('estado', 'fecha', 'usuario')
    search_fields = ('cliente__nombre', 'id')
    inlines = [VentaDetalleInline]
    autocomplete_fields = ['cliente']
    readonly_fields = ('monto_total',) # El total no se debe editar a mano

# --- NUEVOS REGISTROS PARA PROVEEDORES ---

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'contacto', 'telefono', 'email')
    search_fields = ('nombre',)

@admin.register(PedidoProveedor)
class PedidoProveedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'proveedor', 'fecha_pedido', 'estado', 'costo_total')
    list_filter = ('estado', 'proveedor')
    inlines = [PedidoDetalleInline]
    autocomplete_fields = ['proveedor']
    readonly_fields = ('costo_total',)