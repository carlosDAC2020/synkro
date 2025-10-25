from django import forms
from .models import Cliente, Producto, Categoria, Venta, VentaDetalle, Proveedor, PedidoProveedor, PedidoDetalle, PagoProveedor, Sucursal, Repartidor, RutaEntrega, DetalleRuta, NotaEntregaVenta, DetalleNotaEntrega

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono', 'email', 'razon_social', 'direccion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del cliente'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'razon_social': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razón social (opcional)'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección (opcional)'
            }),
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la categoría'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción opcional'
            }),
        }

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'sku', 'categoria', 'descripcion', 'stock_actual', 'stock_minimo', 'costo_unitario', 'precio_venta']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código único del producto'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del producto'
            }),
            'stock_actual': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'costo_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'precio_venta': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
        }

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = [
            'cliente', 
            'estado', 
            'requiere_domicilio', 
            'direccion_entrega',
            'prioridad_entrega',
            'ventana_tiempo_inicio',
            'ventana_tiempo_fin',
        ]
        
        widgets = {
             'cliente': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
            'direccion_entrega': forms.Textarea(attrs={'rows': 3}),
            # --- WIDGETS PARA LOS CAMPOS DE HORA ---
            'ventana_tiempo_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'ventana_tiempo_fin': forms.TimeInput(attrs={'type': 'time'}),
        }
        
        labels = {
            'requiere_domicilio': '¿Requiere entrega a domicilio?',
            'direccion_entrega': 'Dirección de Entrega',
            'prioridad_entrega': 'Prioridad de la Entrega',
            'ventana_tiempo_inicio': 'Inicio de Horario de Entrega',
            'ventana_tiempo_fin': 'Fin de Horario de Entrega',
        }
        
        help_texts = {
            'ventana_tiempo_inicio': 'Opcional. Hora preferida para iniciar la entrega.',
            'ventana_tiempo_fin': 'Opcional. Hora límite para realizar la entrega.',
        }

class VentaDomicilioForm(forms.ModelForm):
    """
    Formulario específico para editar los detalles de domicilio de una venta existente.
    """
    class Meta:
        model = Venta
        fields = [
            'requiere_domicilio', 
            'direccion_entrega',
            'latitud_entrega',
            'longitud_entrega',
            'prioridad_entrega',
            'ventana_tiempo_inicio',
            'ventana_tiempo_fin'
        ]
        widgets = {
            'requiere_domicilio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'direccion_entrega': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'latitud_entrega': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitud_entrega': forms.NumberInput(attrs={'class': 'form-control'}),
            'prioridad_entrega': forms.Select(attrs={'class': 'form-select'}),
            'ventana_tiempo_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'ventana_tiempo_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

class VentaDetalleForm(forms.ModelForm):
    class Meta:
        model = VentaDetalle
        fields = ['producto', 'cantidad', 'precio_unitario_venta']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select producto-select'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control cantidad-input',
                'min': '1',
                'value': '1'
            }),
            'precio_unitario_venta': forms.NumberInput(attrs={
                'class': 'form-control precio-input',
                'step': '0.01',
                'min': '0',
                'readonly': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar productos con stock disponible
        self.fields['producto'].queryset = Producto.objects.filter(stock_actual__gt=0)

# Formset para manejar múltiples detalles de venta
VentaDetalleFormSet = forms.inlineformset_factory(
    Venta, 
    VentaDetalle, 
    form=VentaDetalleForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True
)

# === FORMULARIOS PARA PROVEEDORES ===

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'contacto', 'razon_social', 'direccion', 'telefono', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa proveedora'
            }),
            'contacto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del contacto principal'
            }),
            'razon_social': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razón social (opcional)'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección (opcional)'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@proveedor.com'
            }),
        }

class PagoProveedorForm(forms.ModelForm):
    class Meta:
        model = PagoProveedor
        fields = ['monto', 'metodo_pago', 'referencia', 'documento_soporte', 'notas']
        widgets = {
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'metodo_pago': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Efectivo, Transferencia, etc.'
            }),
            'referencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Referencia/comprobante'
            }),
            'documento_soporte': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales'
            }),
        }

# === FORMULARIOS PARA PEDIDOS ===

class PedidoProveedorForm(forms.ModelForm):
    class Meta:
        model = PedidoProveedor
        fields = ['proveedor']
        widgets = {
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

class PedidoDetalleForm(forms.ModelForm):
    class Meta:
        model = PedidoDetalle
        fields = ['producto', 'cantidad', 'costo_unitario_compra']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select producto-select'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control cantidad-input',
                'min': '1',
                'value': '1'
            }),
            'costo_unitario_compra': forms.NumberInput(attrs={
                'class': 'form-control costo-input',
                'step': '0.01',
                'min': '0'
            }),
        }

# Formset para manejar múltiples detalles de pedido
PedidoDetalleFormSet = forms.inlineformset_factory(
    PedidoProveedor, 
    PedidoDetalle, 
    form=PedidoDetalleForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True
)

# === FORMULARIOS PARA DOMICILIOS ===

class SucursalForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ['nombre', 'codigo', 'direccion', 'ciudad', 'departamento', 
                  'latitud', 'longitud', 'telefono', 'email', 'activa', 'es_principal',
                  'radio_cobertura_km', 'horario_apertura', 'horario_cierre', 'notas']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la sucursal'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código único (ej: SUC001)'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección completa'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'departamento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Departamento'
            }),
            'latitud': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001',
                'placeholder': 'Ej: 10.9685'
            }),
            'longitud': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001',
                'placeholder': 'Ej: -74.7813'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@sucursal.com'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'es_principal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'radio_cobertura_km': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0'
            }),
            'horario_apertura': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'horario_cierre': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales (opcional)'
            }),
        }


class RepartidorForm(forms.ModelForm):
    class Meta:
        model = Repartidor
        fields = [
            'nombre', 
            'documento', 
            'telefono', 
            'estado',
            'capacidad_maxima_kg',
            'capacidad_maxima_m3',
        ]
        
        # Define las etiquetas que se mostrarán en el formulario
        labels = {
            'nombre': 'Nombre Completo',
            'documento': 'Documento de Identidad',
            'capacidad_maxima_kg': 'Capacidad Máxima (kg)',
            'capacidad_maxima_m3': 'Capacidad Máxima (m³)',
        }

        # Aquí está la magia: añadimos clases y placeholders a los campos
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre completo del repartidor'
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento (cédula)'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select' # Para los <select> se usa form-select
            }),
            'capacidad_maxima_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1000.0'
            }),
            'capacidad_maxima_m3': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 5.0'
            }),
        }
        
        # Textos de ayuda que aparecerán debajo de los campos
        help_texts = {
            'documento': 'Número de cédula o documento único.',
            'capacidad_maxima_kg': 'Capacidad de carga del vehículo en kilogramos.',
            'capacidad_maxima_m3': 'Capacidad de carga del vehículo en metros cúbicos.',
        }


class RutaEntregaForm(forms.ModelForm):
    class Meta:
        model = RutaEntrega
        fields = ['sucursal_origen', 'repartidor', 'fecha_entrega']
        widgets = {
            'sucursal_origen': forms.Select(attrs={
                'class': 'form-select'
            }),
            'repartidor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha_entrega': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }


# === FORMULARIOS PARA NOTAS DE ENTREGA ===

class NotaEntregaVentaForm(forms.ModelForm):
    """Formulario para crear notas de entrega de ventas"""
    
    class Meta:
        model = NotaEntregaVenta
        fields = ['descripcion', 'observaciones']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ej: Cliente vino hoy y recogió 5 unidades del producto X',
                'required': True
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales (opcional)'
            }),
        }
        labels = {
            'descripcion': 'Descripción de la entrega',
            'observaciones': 'Observaciones adicionales'
        }


class DetalleNotaEntregaForm(forms.ModelForm):
    """Formulario para especificar productos y cantidades entregadas"""
    
    class Meta:
        model = DetalleNotaEntrega
        fields = ['producto', 'cantidad_entregada']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select producto-entrega-select'
            }),
            'cantidad_entregada': forms.NumberInput(attrs={
                'class': 'form-control cantidad-entrega-input',
                'min': '1',
                'value': '1'
            }),
        }
        labels = {
            'producto': 'Producto',
            'cantidad_entregada': 'Cantidad entregada'
        }
    
    def __init__(self, *args, venta=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si se proporciona una venta, filtrar solo los productos de esa venta
        if venta:
            productos_venta = venta.detalles.values_list('producto', flat=True)
            self.fields['producto'].queryset = Producto.objects.filter(id__in=productos_venta)
            
            # Agregar información de cantidades pendientes en el help_text
            self.venta = venta


# Formset para manejar múltiples detalles de nota de entrega
DetalleNotaEntregaFormSet = forms.inlineformset_factory(
    NotaEntregaVenta,
    DetalleNotaEntrega,
    form=DetalleNotaEntregaForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True
)
