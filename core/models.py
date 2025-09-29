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

    def __str__(self):
        return f"{self.nombre} ({self.sku})"
    
    # NUEVO: Propiedad para el sistema de alertas
    @property
    def necesita_reposicion(self):
        return self.stock_actual <= self.stock_minimo

class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)

    def __str__(self):
        return self.nombre

class Venta(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('PENDIENTE_PAGO', 'Pendiente de Pago'),
        ('PAGADA_PENDIENTE_ENTREGA', 'Pagada y Pendiente de Entrega'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="Usuario que realizó la venta")
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='COMPLETADA')
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False) # Editable=False para que no se cambie a mano
    _estado_anterior = None # Campo temporal para rastrear cambios

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
                
                # Opcional: Revertir stock si se cancela una venta que estaba completada
                elif self.estado != 'COMPLETADA' and self._estado_anterior == 'COMPLETADA':
                     for detalle in self.detalles.all():
                        detalle.producto.stock_actual += detalle.cantidad
                        detalle.producto.save()

        super().save(*args, **kwargs)
        self._estado_anterior = self.estado

class VentaDetalle(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario_venta = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio al momento de la venta")

    def save(self, *args, **kwargs):
        # Si el precio no se especifica, tomar el precio actual del producto
        if not self.precio_unitario_venta:
            self.precio_unitario_venta = self.producto.precio_venta
        
        super().save(*args, **kwargs)
        
        # Recalcular el total de la venta padre
        venta = self.venta
        total = sum(d.cantidad * d.precio_unitario_venta for d in venta.detalles.all())
        venta.monto_total = total
        venta.save()

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

# --- NUEVOS MODELOS PARA PROVEEDORES Y COMPRAS ---

class Proveedor(models.Model):
    nombre = models.CharField(max_length=200)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class PedidoProveedor(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('RECIBIDO', 'Recibido'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
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
                        detalle.producto.stock_actual += detalle.cantidad
                        detalle.producto.save()
                
                # Opcional: Revertir stock si se cambia el estado de un pedido que ya estaba recibido
                elif self.estado != 'RECIBIDO' and self._estado_anterior == 'RECIBIDO':
                    for detalle in self.detalles_pedido.all():
                        # Asegurarse de no dejar stock negativo
                        if detalle.producto.stock_actual >= detalle.cantidad:
                            detalle.producto.stock_actual -= detalle.cantidad
                            detalle.producto.save()
                        else:
                            raise ValidationError(f"No se puede revertir el stock para {detalle.producto.nombre}, ya que las unidades fueron vendidas.")
        
        super().save(*args, **kwargs)
        self._estado_anterior = self.estado

class PedidoDetalle(models.Model):
    pedido = models.ForeignKey(PedidoProveedor, related_name='detalles_pedido', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    costo_unitario_compra = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalcular el total del pedido padre
        pedido = self.pedido
        total = sum(d.cantidad * d.costo_unitario_compra for d in pedido.detalles_pedido.all())
        pedido.costo_total = total
        pedido.save()

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Pedido #{self.pedido.id}"