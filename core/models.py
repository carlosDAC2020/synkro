# core/models.py

from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError

# --- Modelos ---

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
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.nombre} ({self.sku})"

    @property
    def necesita_reposicion(self):
        return self.stock_actual <= self.stock_minimo

    @property
    def ganancia_unitaria(self):
        return (self.precio_venta or 0) - (self.costo_unitario or 0)

    @property
    def margen_ganancia(self):
        if self.costo_unitario and self.costo_unitario > 0:
            return (self.ganancia_unitaria / self.costo_unitario) * 100
        return 0


class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    razon_social = models.CharField(max_length=200, blank=True)
    direccion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    nombre = models.CharField(max_length=200)
    contacto = models.CharField(max_length=100, blank=True)
    razon_social = models.CharField(max_length=200, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    ESTADO_CHOICES = [
        ('COTIZACION', 'Cotización'),
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
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    
    # Campos para domicilios
    requiere_domicilio = models.BooleanField(default=False, help_text="Indica si requiere entrega a domicilio")
    direccion_entrega = models.CharField(max_length=300, blank=True, help_text="Dirección de entrega")
    latitud_entrega = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitud_entrega = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    prioridad_entrega = models.CharField(
        max_length=10,
        choices=[('alta', 'Alta'), ('media', 'Media'), ('baja', 'Baja')],
        default='media',
        help_text="Prioridad de entrega"
    )
    
    _estado_anterior = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estado_anterior = self.estado

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.strftime('%d/%m/%Y')}"
    
    @property
    def coordenadas_entrega(self):
        """Retorna coordenadas de entrega como lista [lat, lng]"""
        if self.latitud_entrega and self.longitud_entrega:
            return [float(self.latitud_entrega), float(self.longitud_entrega)]
        return None

    def save(self, *args, **kwargs):
        # Ajustes de stock solo cuando cambia estado respecto a COMPLETADA
        if self.pk is not None:
            with transaction.atomic():
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


class VentaDetalle(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario_venta = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio al momento de la venta")

    def save(self, *args, **kwargs):
        if not self.precio_unitario_venta:
            self.precio_unitario_venta = self.producto.precio_venta
        
        # Si la venta está COMPLETADA y estamos creando el detalle, descontar stock
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        if es_nuevo and self.venta.estado == 'COMPLETADA':
            if self.producto.stock_actual < self.cantidad:
                raise ValidationError(f"No hay stock suficiente para {self.producto.nombre}")
            self.producto.stock_actual -= self.cantidad
            self.producto.save()
        
        # Recalcular total de la venta
        venta = self.venta
        total = sum(d.cantidad * d.precio_unitario_venta for d in venta.detalles.all())
        venta.monto_total = total
        venta.save()

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario_venta

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"


class PedidoProveedor(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('RECIBIDO', 'Recibido'),
        ('CANCELADO', 'Cancelado'),
        ('PAGANDO', 'Pagando'),
    ]

    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    _estado_anterior = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estado_anterior = self.estado

    def __str__(self):
        return f"Pedido a {self.proveedor.nombre} - {self.fecha_pedido.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            with transaction.atomic():
                if self.estado == 'RECIBIDO' and self._estado_anterior != 'RECIBIDO':
                    for detalle in self.detalles_pedido.all():
                        detalle.producto.stock_actual += detalle.cantidad
                        detalle.producto.save()
                elif self.estado != 'RECIBIDO' and self._estado_anterior == 'RECIBIDO':
                    for detalle in self.detalles_pedido.all():
                        if detalle.producto.stock_actual >= detalle.cantidad:
                            detalle.producto.stock_actual -= detalle.cantidad
                            detalle.producto.save()
        super().save(*args, **kwargs)
        self._estado_anterior = self.estado

    @property
    def total_pagado(self):
        from django.db.models import Sum
        total = self.pagos.aggregate(s=Sum('monto')).get('s') if hasattr(self, 'pagos') else None
        return total or 0

    @property
    def saldo_pendiente(self):
        return (self.costo_total or 0) - self.total_pagado


class PedidoDetalle(models.Model):
    pedido = models.ForeignKey(PedidoProveedor, on_delete=models.CASCADE, related_name='detalles_pedido')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    costo_unitario_compra = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # Si el pedido está RECIBIDO y estamos creando el detalle, incrementar stock
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        if es_nuevo and self.pedido.estado == 'RECIBIDO':
            self.producto.stock_actual += self.cantidad
            self.producto.save()
        
        # Recalcular total del pedido
        pedido = self.pedido
        total = sum(d.cantidad * d.costo_unitario_compra for d in pedido.detalles_pedido.all())
        pedido.costo_total = total
        pedido.save()

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario_compra

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Pedido #{self.pedido.id}"


class PagoProveedor(models.Model):
    """Trazabilidad de pagos periódicos a proveedores."""
    pedido = models.ForeignKey(PedidoProveedor, on_delete=models.CASCADE, related_name='pagos')
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
        return f"Pago {self.monto} - Pedido #{self.pedido_id}"


# === MÓDULO DE DOMICILIOS ===

class Sucursal(models.Model):
    """Sucursales/Puntos de origen para envío de domicilios"""
    nombre = models.CharField(max_length=200, unique=True, help_text="Nombre de la sucursal")
    codigo = models.CharField(max_length=20, unique=True, help_text="Código único de la sucursal")
    
    # Ubicación
    direccion = models.CharField(max_length=300)
    ciudad = models.CharField(max_length=100, default='Barranquilla')
    departamento = models.CharField(max_length=100, default='Atlántico')
    latitud = models.DecimalField(max_digits=10, decimal_places=7, help_text="Latitud de la ubicación")
    longitud = models.DecimalField(max_digits=10, decimal_places=7, help_text="Longitud de la ubicación")
    
    # Información de contacto
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)
    
    # Configuración
    activa = models.BooleanField(default=True, help_text="Indica si la sucursal está operativa")
    es_principal = models.BooleanField(default=False, help_text="Sucursal principal por defecto")
    radio_cobertura_km = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.0,
        help_text="Radio de cobertura en kilómetros"
    )
    
    # Horarios (opcional)
    horario_apertura = models.TimeField(null=True, blank=True)
    horario_cierre = models.TimeField(null=True, blank=True)
    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True, help_text="Notas adicionales sobre la sucursal")
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
    
    def save(self, *args, **kwargs):
        # Si se marca como principal, desmarcar las demás
        if self.es_principal:
            Sucursal.objects.filter(es_principal=True).update(es_principal=False)
        super().save(*args, **kwargs)
    
    @property
    def coordenadas(self):
        """Retorna las coordenadas como tupla (lat, lng)"""
        return (float(self.latitud), float(self.longitud))
    
    @property
    def url_google_maps(self):
        """Genera URL de Google Maps para la ubicación"""
        return f"https://www.google.com/maps?q={self.latitud},{self.longitud}"
    
    class Meta:
        verbose_name_plural = "Sucursales"
        ordering = ['-es_principal', 'nombre']


class Repartidor(models.Model):
    """Repartidores para entregas a domicilio"""
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
        ('EN_RUTA', 'En Ruta'),
    ]
    
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    documento = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')
    fecha_ingreso = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = "Repartidores"


class RutaEntrega(models.Model):
    """Rutas planificadas para entregas"""
    ESTADO_CHOICES = [
        ('PLANIFICADA', 'Planificada'),
        ('EN_CURSO', 'En Curso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    sucursal_origen = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='rutas')
    repartidor = models.ForeignKey(Repartidor, on_delete=models.SET_NULL, null=True, blank=True, related_name='rutas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateField()
    
    # Datos de la ruta
    distancia_total_km = models.DecimalField(max_digits=6, decimal_places=2)
    tiempo_estimado_min = models.PositiveIntegerField()
    numero_paradas = models.PositiveIntegerField()
    
    # Geometría de la ruta (JSON)
    waypoints = models.JSONField(help_text="Coordenadas de los puntos de la ruta")
    geometria_ruta = models.JSONField(null=True, blank=True, help_text="Geometría completa de la ruta")
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PLANIFICADA')
    
    def __str__(self):
        return f"Ruta #{self.id} - {self.sucursal_origen.nombre} - {self.fecha_entrega}"
    
    class Meta:
        verbose_name_plural = "Rutas de Entrega"
        ordering = ['-fecha_creacion']


class DetalleRuta(models.Model):
    """Ventas incluidas en una ruta"""
    ruta = models.ForeignKey(RutaEntrega, related_name='detalles', on_delete=models.CASCADE)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    orden_entrega = models.PositiveIntegerField(help_text="Orden en la ruta (1, 2, 3...)")
    tiempo_estimado_llegada = models.TimeField(null=True, blank=True)
    entregado = models.BooleanField(default=False)
    hora_entrega_real = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    
    def __str__(self):
        return f"Parada {self.orden_entrega} - Venta #{self.venta.id}"
    
    class Meta:
        verbose_name_plural = "Detalles de Ruta"
        ordering = ['orden_entrega']
