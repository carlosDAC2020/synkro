# core/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Categoria, Producto, Cliente, Venta, VentaDetalle,
    Proveedor, PedidoProveedor, PedidoDetalle,
    NotaEntregaVenta, DetalleNotaEntrega
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

class DetalleNotaEntregaInline(admin.TabularInline):
    model = DetalleNotaEntrega
    extra = 1
    autocomplete_fields = ['producto']
    readonly_fields = ('get_cantidad_pendiente',)
    
    def get_cantidad_pendiente(self, obj):
        """Muestra la cantidad pendiente de entregar del producto"""
        if obj.nota_entrega and obj.producto:
            venta = obj.nota_entrega.venta
            pendiente = venta.cantidad_pendiente_producto(obj.producto)
            return f"{pendiente} unidades pendientes"
        return "-"
    get_cantidad_pendiente.short_description = "Cantidad Pendiente"

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


# --- REGISTROS PARA NOTAS DE ENTREGA ---

@admin.register(NotaEntregaVenta)
class NotaEntregaVentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'fecha_entrega', 'usuario', 'estado_inventario', 'ver_descripcion')
    list_filter = ('descuento_inventario_aplicado', 'fecha_entrega', 'usuario')
    search_fields = ('venta__id', 'descripcion')
    inlines = [DetalleNotaEntregaInline]
    readonly_fields = ('fecha_entrega', 'descuento_inventario_aplicado', 'ver_resumen_venta')
    autocomplete_fields = ['venta', 'usuario']
    
    fieldsets = (
        ('Información General', {
            'fields': ('venta', 'usuario', 'fecha_entrega')
        }),
        ('Detalles de la Entrega', {
            'fields': ('descripcion', 'observaciones')
        }),
        ('Control de Inventario', {
            'fields': ('descuento_inventario_aplicado', 'ver_resumen_venta'),
            'classes': ('collapse',)
        }),
    )
    
    def estado_inventario(self, obj):
        """Muestra si el inventario ya fue descontado"""
        if obj.descuento_inventario_aplicado:
            return format_html('<span style="color: green;">✓ Aplicado</span>')
        return format_html('<span style="color: orange;">⏳ Pendiente</span>')
    estado_inventario.short_description = "Estado Inventario"
    
    def ver_descripcion(self, obj):
        """Muestra un resumen corto de la descripción"""
        if len(obj.descripcion) > 50:
            return obj.descripcion[:50] + "..."
        return obj.descripcion
    ver_descripcion.short_description = "Descripción"
    
    def ver_resumen_venta(self, obj):
        """Muestra un resumen de la venta y sus entregas"""
        if not obj.venta:
            return "-"
        
        venta = obj.venta
        html = f"<strong>Venta #{venta.id}</strong><br>"
        html += f"Estado: {venta.get_estado_display()}<br><br>"
        html += "<table style='border-collapse: collapse; width: 100%;'>"
        html += "<tr style='background: #f0f0f0;'><th style='padding: 5px; border: 1px solid #ddd;'>Producto</th>"
        html += "<th style='padding: 5px; border: 1px solid #ddd;'>Total</th>"
        html += "<th style='padding: 5px; border: 1px solid #ddd;'>Entregado</th>"
        html += "<th style='padding: 5px; border: 1px solid #ddd;'>Pendiente</th></tr>"
        
        for item in venta.resumen_entregas:
            html += f"<tr><td style='padding: 5px; border: 1px solid #ddd;'>{item['producto'].nombre}</td>"
            html += f"<td style='padding: 5px; border: 1px solid #ddd; text-align: center;'>{item['cantidad_total']}</td>"
            html += f"<td style='padding: 5px; border: 1px solid #ddd; text-align: center;'>{item['cantidad_entregada']}</td>"
            html += f"<td style='padding: 5px; border: 1px solid #ddd; text-align: center;'>{item['cantidad_pendiente']}</td></tr>"
        
        html += "</table>"
        return format_html(html)
    ver_resumen_venta.short_description = "Resumen de Entregas"
    
    actions = ['aplicar_descuento_inventario', 'revertir_descuento_inventario']
    
    def aplicar_descuento_inventario(self, request, queryset):
        """Acción para aplicar descuento de inventario a notas seleccionadas"""
        aplicadas = 0
        for nota in queryset:
            try:
                if nota.aplicar_descuento_inventario():
                    aplicadas += 1
            except Exception as e:
                self.message_user(request, f"Error en nota #{nota.id}: {str(e)}", level='error')
        
        if aplicadas > 0:
            self.message_user(request, f"Se aplicó el descuento de inventario a {aplicadas} nota(s)")
    aplicar_descuento_inventario.short_description = "Aplicar descuento de inventario"
    
    def revertir_descuento_inventario(self, request, queryset):
        """Acción para revertir descuento de inventario de notas seleccionadas"""
        revertidas = 0
        for nota in queryset:
            try:
                if nota.revertir_descuento_inventario():
                    revertidas += 1
            except Exception as e:
                self.message_user(request, f"Error en nota #{nota.id}: {str(e)}", level='error')
        
        if revertidas > 0:
            self.message_user(request, f"Se revirtió el descuento de inventario de {revertidas} nota(s)")
    revertir_descuento_inventario.short_description = "Revertir descuento de inventario"