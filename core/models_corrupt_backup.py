# core/models.py

from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError

# --- Modelos existentes (con mejoras) ---

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = "Categorías"

class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, help_text="Código de Referencia Único")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField(blank=True)
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5, help_text="Umbral para alertas de stock bajo")
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} ({self.sku})"
    
    def ganancia(self):
        return self.precio_venta - self.costo_unitario
    
    # Propiedad para el sistema de alertas
    @property
    def necesita_reposicion(self):
        return self.stock_actual <= self.stock_minimo

class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    razon_social = models.CharField(max_length=200, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return self.nombre

class Venta(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('PENDIENTE_PAGO', 'Pendiente de Pago'),
        ('PAGADA_PENDIENTE_ENTREGA', 'Pagada y Pendiente de Entrega'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
        ('COTIZACION', 'Cotizacion'),
    ]
    
    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="Usuario que realizó la venta")
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='COMPLETADA')
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False) # Editable=False para que no se cambie a mano
    _estado_anterior = None 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estado_anterior = self.estado

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.strftime('%d/%m/%Y')}"
    
    # NUEVO: Lógica para calcular total y actualizar stock
    def save(self, *args, **kwargs):
        # Calcular el monto total basado en los detalles antes de guardar
        # Esta parte se ejecutará al crear los detalles en el admin.
        # Para un cálculo robusto, lo ideal es recalcularlo con una señal o en la vista.
        
        # Lógica de actualización de stock
        if self.pk is not None:
            # Usamos transaction.atomic para asegurar que todas las operaciones de BD se completen o ninguna lo haga.
            with transaction.atomic():
                # Si la venta se marca como COMPLETADA (y antes no lo era)
                if self.estado == 'COMPLETADA' and self._estado_anterior != 'COMPLETADA':
                    for detalle in self.detalles.all():
                        if detalle.producto.stock_actual < detalle.cantidad:
                            raise ValidationError(f"No hay stock suficiente para el producto: {detalle.producto.nombre}")
                        detalle.producto.stock_actual -= detalle.cantidad
                        detalle.producto.save()
                
                elif self.estado != 'COMPLETADA' and self._estado_anterior == 'COMPLETADA':
                     for detalle in self.detalles.all():
                        detalle.producto.stock_actual += detalle.cantidad
                        detalle.producto.save()

        super().save(*args, **kwargs)
        self._estado_anterior = self.estado

    @property
    def total_pagado(self):
        """Suma de pagos registrados al pedido."""
        total = self.pagos.aggregate(models.Sum('monto')).get('monto__sum') if hasattr(self, 'pagos') else None
        return total or 0

    @property
    def saldo_pendiente(self):
        """Saldo pendiente segun costo_total y total_pagado."""
        return (self.costo_total or 0) - self.total_pagado

class VentaDetalle(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
{{ ... }}
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class PedidoProveedor(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('RECIBIDO', 'Recibido'),
        ('CANCELADO', 'Cancelado'),
        ('PAGANDO', 'Pagando'),
    ]
    
    proveedor = models.ForeignKey('Proveedor', on_delete=models.PROTECT)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    _estado_anterior = None # Campo temporal para rastrear cambios

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estado_anterior = self.estado
    
    def __str__(self):
        return f"Pedido a {self.proveedor.nombre} - {self.fecha_pedido.strftime('%d/%m/%Y')}"

    # NUEVO: Lógica para actualizar stock al recibir pedido
    def save(self, *args, **kwargs):
        if self.pk is not None:
            with transaction.atomic():
                # Si el pedido se marca como RECIBIDO (y antes no lo era)
                if self.estado == 'RECIBIDO' and self._estado_anterior != 'RECIBIDO':
                    for detalle in self.detalles_pedido.all():
                        pass
        
        super().save(*args, **kwargs)
        self._estado_anterior = self.estado

class OrdenDetalle(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='detalles_orden')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    costo_unitario_compra = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario_compra
    
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Orden #{self.orden.id}"


class PagoProveedor(models.Model):
    """Trazabilidad de pagos periódicos a proveedores."""
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2, help_text="Monto abonado")
    metodo_pago = models.CharField(max_length=50, blank=True, help_text="Efectivo, Transferencia, etc.")
    referencia = models.CharField(max_length=100, blank=True, help_text="Referencia o comprobante")
    documento_soporte = models.FileField(upload_to='pagos_proveedores/', blank=True, null=True)
    notas = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-fecha_pago']
        verbose_name = 'Pago a Proveedor'
        verbose_name_plural = 'Pagos a Proveedores'

    def __str__(self):
        return f"Pago {self.monto} - Orden #{self.orden_id}"