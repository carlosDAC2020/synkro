from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, F
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from datetime import datetime
import json 
import requests 


from .models import Cliente, Producto, Categoria, Venta, VentaDetalle, Proveedor, PedidoProveedor, PedidoDetalle, PagoProveedor, NotaEntregaVenta, DetalleNotaEntrega, Sucursal, Repartidor, RutaEntrega, DetalleRuta
from .forms import ClienteForm, ProductoForm, VentaForm, VentaDetalleFormSet, ProveedorForm, PedidoProveedorForm, PedidoDetalleFormSet, PagoProveedorForm, NotaEntregaVentaForm, DetalleNotaEntregaFormSet, SucursalForm, RepartidorForm, RutaEntregaForm, VentaDomicilioForm

# Dashboard
@login_required
def dashboard(request):
    from django.db.models import Sum, Count, Avg
    from decimal import Decimal
    
    # Fechas para análisis
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    hace_30_dias = hoy - timedelta(days=30)
    
    # Estadísticas básicas
    total_productos = Producto.objects.count()
    total_clientes = Cliente.objects.count()
    total_proveedores = Proveedor.objects.count()
    
    # Ventas y ganancias
    ventas_hoy_count = Venta.objects.filter(fecha__date=hoy, estado='COMPLETADA').count()
    ventas_hoy_total = Venta.objects.filter(fecha__date=hoy, estado='COMPLETADA').aggregate(
        total=Sum('monto_total')
    )['total'] or Decimal('0')
    
    # Ventas del mes
    ventas_mes_total = Venta.objects.filter(
        fecha__date__gte=inicio_mes, 
        estado='COMPLETADA'
    ).aggregate(total=Sum('monto_total'))['total'] or Decimal('0')
    
    ventas_mes_count = Venta.objects.filter(
        fecha__date__gte=inicio_mes, 
        estado='COMPLETADA'
    ).count()
    
    # Ganancias estimadas (diferencia entre precio venta y costo)
    ganancias_mes = Decimal('0')
    ventas_completadas = Venta.objects.filter(
        fecha__date__gte=inicio_mes, 
        estado='COMPLETADA'
    ).prefetch_related('detalles__producto')
    
    for venta in ventas_completadas:
        for detalle in venta.detalles.all():
            # Calcular ganancia por producto (precio venta - costo estimado)
            precio_venta = detalle.precio_unitario_venta * detalle.cantidad
            # Usar el último costo de compra del producto como referencia
            ultimo_pedido = PedidoDetalle.objects.filter(
                producto=detalle.producto
            ).order_by('-pedido__fecha_pedido').first()
            
            if ultimo_pedido:
                costo_estimado = ultimo_pedido.costo_unitario_compra * detalle.cantidad
                ganancia_producto = precio_venta - costo_estimado
                # Solo sumar si la ganancia es positiva (evitar costos incorrectos)
                if ganancia_producto > 0:
                    ganancias_mes += ganancia_producto
                else:
                    # Si el costo es mayor que el precio, usar margen del 30%
                    ganancias_mes += precio_venta * Decimal('0.3')
            else:
                # Si no hay costo de compra, asumir 40% de ganancia
                ganancias_mes += precio_venta * Decimal('0.4')
    
    # Ticket promedio
    ticket_promedio = Decimal('0')
    if ventas_mes_count > 0:
        ticket_promedio = ventas_mes_total / ventas_mes_count
    
    # Productos más vendidos (últimos 30 días)
    productos_mas_vendidos = VentaDetalle.objects.filter(
        venta__fecha__date__gte=hace_30_dias,
        venta__estado='COMPLETADA'
    ).values(
        'producto__nombre', 'producto__sku'
    ).annotate(
        total_vendido=Sum('cantidad'),
        ingresos=Sum(F('cantidad') * F('precio_unitario_venta'))
    ).order_by('-total_vendido')[:5]
    
    # Clientes más activos
    clientes_activos = Venta.objects.filter(
        fecha__date__gte=hace_30_dias,
        estado='COMPLETADA'
    ).values(
        'cliente__nombre'
    ).annotate(
        total_compras=Count('id'),
        total_gastado=Sum('monto_total')
    ).order_by('-total_gastado')[:5]
    
    # Productos con stock bajo
    productos_stock_bajo = Producto.objects.filter(stock_actual__lte=F('stock_minimo')).count()
    productos_alerta = Producto.objects.filter(stock_actual__lte=F('stock_minimo'))[:5]
    
    # Pedidos pendientes
    pedidos_pendientes = PedidoProveedor.objects.filter(estado='PENDIENTE').count()
    pedidos_alerta = PedidoProveedor.objects.filter(estado='PENDIENTE').select_related('proveedor')[:5]
    
    # Inversión en inventario (pedidos pendientes)
    inversion_pendiente = PedidoProveedor.objects.filter(
        estado='PENDIENTE'
    ).aggregate(total=Sum('costo_total'))['total'] or Decimal('0')
    
    # Ventas recientes
    ventas_recientes = Venta.objects.select_related('cliente').order_by('-fecha')[:5]
    
    context = {
        # Estadísticas básicas
        'total_productos': total_productos,
        'total_clientes': total_clientes,
        'total_proveedores': total_proveedores,
        
        # Ventas y ganancias
        'ventas_hoy_count': ventas_hoy_count,
        'ventas_hoy_total': ventas_hoy_total,
        'ventas_mes_total': ventas_mes_total,
        'ventas_mes_count': ventas_mes_count,
        'ganancias_mes': ganancias_mes,
        'ticket_promedio': ticket_promedio,
        
        # Inventario y pedidos
        'productos_stock_bajo': productos_stock_bajo,
        'productos_alerta': productos_alerta,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_alerta': pedidos_alerta,
        'inversion_pendiente': inversion_pendiente,
        
        # Análisis de ventas
        'productos_mas_vendidos': productos_mas_vendidos,
        'clientes_activos': clientes_activos,
        'ventas_recientes': ventas_recientes,
    }
    return render(request, 'dashboard.html', context)

# Clientes
@login_required
def cliente_list(request):
    search = request.GET.get('search', '')
    clientes = Cliente.objects.all()
    
    if search:
        clientes = clientes.filter(
            Q(nombre__icontains=search) | 
            Q(email__icontains=search) | 
            Q(telefono__icontains=search)
        )
    
    return render(request, 'clientes/list.html', {
        'clientes': clientes,
        'search': search
    })

@login_required
def cliente_add(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente agregado exitosamente.')
            return redirect('cliente_list')
    else:
        form = ClienteForm()
    
    return render(request, 'clientes/form.html', {
        'form': form,
        'title': 'Agregar Cliente'
    })

@login_required
def cliente_edit(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado exitosamente.')
            return redirect('cliente_list')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'clientes/form.html', {
        'form': form,
        'title': 'Editar Cliente',
        'cliente': cliente
    })

@login_required
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente eliminado exitosamente.')
        return redirect('cliente_list')
    
    return render(request, 'clientes/delete.html', {'cliente': cliente})

# Productos
@login_required
def producto_list(request):
    search = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria', '')
    
    productos = Producto.objects.select_related('categoria')
    
    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) | 
            Q(sku__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    
    categorias = Categoria.objects.all()
    
    return render(request, 'productos/list.html', {
        'productos': productos,
        'categorias': categorias,
        'search': search,
        'categoria_selected': categoria_id
    })

@login_required
def producto_add(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto agregado exitosamente.')
            return redirect('producto_list')
    else:
        form = ProductoForm()
    
    return render(request, 'productos/form.html', {
        'form': form,
        'title': 'Agregar Producto'
    })

@login_required
def producto_edit(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('producto_list')
    else:
        form = ProductoForm(instance=producto)
    
    return render(request, 'productos/form.html', {
        'form': form,
        'title': 'Editar Producto',
        'producto': producto
    })

@login_required
def producto_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('producto_list')
    
    return render(request, 'productos/delete.html', {'producto': producto})

# Ventas
@login_required
def venta_list(request):
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    
    ventas = Venta.objects.select_related('cliente', 'usuario').prefetch_related('detalles__producto')
    
    if search:
        ventas = ventas.filter(
            Q(cliente__nombre__icontains=search) |
            Q(id__icontains=search)
        )
    
    if estado:
        ventas = ventas.filter(estado=estado)
    
    ventas = ventas.order_by('-fecha')
    
    return render(request, 'ventas/list.html', {
        'ventas': ventas,
        'search': search,
        'estado_selected': estado,
        'estados': Venta.ESTADO_CHOICES
    })

@login_required
def nueva_venta(request):
    if request.method == 'POST':
        venta_form = VentaForm(request.POST)
        formset = VentaDetalleFormSet(request.POST)
        
        if venta_form.is_valid() and formset.is_valid():
            # Validar stock antes de crear la venta
            stock_errors = []
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    producto = form.cleaned_data.get('producto')
                    cantidad = form.cleaned_data.get('cantidad', 0)
                    
                    if producto and cantidad > 0:
                        if producto.stock_actual < cantidad:
                            stock_errors.append(
                                f"Stock insuficiente para {producto.nombre}. "
                                f"Disponible: {producto.stock_actual}, Solicitado: {cantidad}"
                            )
            
            if stock_errors:
                for error in stock_errors:
                    messages.error(request, error)
            else:
                with transaction.atomic():
                    venta = venta_form.save(commit=False)
                    venta.usuario = request.user
                    venta.save()
                    
                    formset.instance = venta
                    detalles = formset.save()
                    
                    # Actualizar stock de productos
                    for detalle in detalles:
                        producto = detalle.producto
                        producto.stock_actual -= detalle.cantidad
                        producto.save()
                    
                    # Calcular total
                    total = sum(d.cantidad * d.precio_unitario_venta for d in detalles)
                    venta.monto_total = total
                    venta.save()
                    messages.success(request, f'Venta #{venta.id} creada exitosamente.')
                    return redirect('venta_detail', pk=venta.id)
    else:
        venta_form = VentaForm()
        formset = VentaDetalleFormSet()
    
    return render(request, 'ventas/nueva_venta.html', {
        'venta_form': venta_form,
        'formset': formset
    })

@login_required
def venta_detail(request, pk):

    domicilio_form = VentaDomicilioForm(instance=venta)
    venta = get_object_or_404(Venta, pk=pk)
    detalles = venta.detalles.select_related('producto')
    return render(request, 'ventas/detail.html', {
        'venta': venta,
        'detalles': detalles,
        'domicilio_form': domicilio_form,
    })

@login_required
def venta_cambiar_estado(request, pk):
    """
    Gestiona el cambio de estado de una venta a través de un formulario POST.
    """
    venta = get_object_or_404(Venta, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        
        # Validar que el nuevo estado sea una opción válida
        if nuevo_estado in [choice[0] for choice in Venta.ESTADO_CHOICES]:
            
            # Si se va a marcar como pendiente de entrega, asegurar que requiere domicilio
            if nuevo_estado == 'PAGADA_PENDIENTE_ENTREGA':
                if not venta.requiere_domicilio:
                    # Si no lo tiene, lo marcamos automáticamente
                    # En un futuro, podrías hacer esto más complejo si es necesario
                    venta.requiere_domicilio = True
            
            venta.estado = nuevo_estado
            try:
                # El método save() de tu modelo ya tiene la lógica para ajustar el stock
                venta.save()
                messages.success(request, f'El estado de la Venta #{venta.id} se actualizó a "{venta.get_estado_display()}".')
            except Exception as e:
                messages.error(request, f'Hubo un error al cambiar el estado: {e}')
        else:
            messages.error(request, 'El estado seleccionado no es válido.')
            
    return redirect('venta_detail', pk=venta.id)

@login_required
def venta_editar_domicilio(request, pk):
    """
    Procesa la actualización de los datos de domicilio de una venta.
    """
    venta = get_object_or_404(Venta, pk=pk)
    
    if request.method == 'POST':
        form = VentaDomicilioForm(request.POST, instance=venta)
        if form.is_valid():
            # Limpiar coordenadas si no se requiere domicilio
            if not form.cleaned_data.get('requiere_domicilio'):
                venta.latitud_entrega = None
                venta.longitud_entrega = None

            form.save()
            messages.success(request, f'Los datos de domicilio para la Venta #{venta.id} se han actualizado.')
        else:
            # Construir un mensaje de error legible
            error_messages = []
            for field, errors in form.errors.items():
                error_messages.append(f"{field}: {', '.join(errors)}")
            messages.error(request, f"No se pudo actualizar. Errores: {'; '.join(error_messages)}")
            
    return redirect('venta_detail', pk=pk)

# API endpoints para AJAX
@login_required
def get_producto_precio(request, producto_id):
    try:
        producto = Producto.objects.get(id=producto_id)
        return JsonResponse({
            'precio': float(producto.precio_venta),
            'stock': producto.stock_actual
        })
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)

@login_required
def buscar_productos(request):
    query = request.GET.get('q', '')
    if query:
        productos = Producto.objects.filter(
            Q(nombre__icontains=query) | Q(sku__icontains=query),
            stock_actual__gt=0
        )[:10]
        
        results = [{
            'id': p.id,
            'nombre': p.nombre,
            'sku': p.sku,
            'precio': float(p.precio_venta),
            'stock': p.stock_actual
        } for p in productos]
        
        return JsonResponse({'productos': results})
    
    return JsonResponse({'productos': []})

# === PROVEEDORES ===

@login_required
def proveedor_list(request):
    search = request.GET.get('search', '')
    proveedores = Proveedor.objects.all()
    
    if search:
        proveedores = proveedores.filter(
            Q(nombre__icontains=search) | 
            Q(email__icontains=search) | 
            Q(telefono__icontains=search)
        )
    
    return render(request, 'proveedores/list.html', {
        'proveedores': proveedores,
        'search': search
    })

@login_required
def proveedor_add(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor agregado exitosamente.')
            return redirect('proveedor_list')
    else:
        form = ProveedorForm()
    
    return render(request, 'proveedores/form.html', {
        'form': form,
        'title': 'Agregar Proveedor'
    })

@login_required
def proveedor_edit(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor actualizado exitosamente.')
            return redirect('proveedor_list')
    else:
        form = ProveedorForm(instance=proveedor)
    
    return render(request, 'proveedores/form.html', {
        'form': form,
        'title': 'Editar Proveedor',
        'proveedor': proveedor
    })

@login_required
def proveedor_delete(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        proveedor.delete()
        messages.success(request, 'Proveedor eliminado exitosamente.')
        return redirect('proveedor_list')
    
    return render(request, 'proveedores/delete.html', {'proveedor': proveedor})

# === PEDIDOS A PROVEEDORES ===

@login_required
def pedido_list(request):
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    
    pedidos = PedidoProveedor.objects.select_related('proveedor').prefetch_related('detalles_pedido__producto')
    
    if search:
        pedidos = pedidos.filter(
            Q(proveedor__nombre__icontains=search) |
            Q(id__icontains=search)
        )
    
    if estado:
        pedidos = pedidos.filter(estado=estado)
    
    pedidos = pedidos.order_by('-fecha_pedido')
    
    return render(request, 'pedidos/list.html', {
        'pedidos': pedidos,
        'search': search,
        'estado_selected': estado,
        'estados': PedidoProveedor.ESTADO_CHOICES
    })

@login_required
def pedido_add(request):
    if request.method == 'POST':
        pedido_form = PedidoProveedorForm(request.POST)
        formset = PedidoDetalleFormSet(request.POST)

        if pedido_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                pedido = pedido_form.save()
                formset.instance = pedido
                detalles = formset.save()

                # Calcular total
                total = sum(d.cantidad * d.costo_unitario_compra for d in detalles)
                pedido.costo_total = total
                pedido.save()

                messages.success(request, f'Pedido #{pedido.id} creado exitosamente.')
                return redirect('pedido_detail', pk=pedido.id)
        # Si no es válido, caemos a render con errores
    else:
        pedido_form = PedidoProveedorForm()
        formset = PedidoDetalleFormSet()

    return render(request, 'pedidos/form.html', {
        'pedido_form': pedido_form,
        'formset': formset,
        'title': 'Nuevo Pedido'
    })
    
# === PAGOS A PROVEEDORES ===
@login_required
def pedido_pago_add(request, pk):
    pedido = get_object_or_404(PedidoProveedor, pk=pk)
    if request.method == 'POST':
        form = PagoProveedorForm(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.pedido = pedido
            pago.usuario = request.user
            pago.save()
            messages.success(request, f'Pago registrado para el Pedido #{pedido.id}.')
            return redirect('pedido_detail', pk=pedido.id)
    else:
        form = PagoProveedorForm()
    return render(request, 'pedidos/pago_form.html', {
        'form': form,
        'pedido': pedido,
        'title': f'Nuevo Pago - Pedido #{pedido.id}'
    })

@login_required
def pedido_detail(request, pk):
    pedido = get_object_or_404(PedidoProveedor, pk=pk)
    detalles = pedido.detalles_pedido.select_related('producto')
    pagos = pedido.pagos.select_related('usuario').order_by('-fecha_pago') if hasattr(pedido, 'pagos') else []
    return render(request, 'pedidos/detail.html', {
        'pedido': pedido,
        'detalles': detalles,
        'pagos': pagos,
        'total_pagado': pedido.total_pagado,
        'saldo_pendiente': pedido.saldo_pendiente,
    })

@login_required
def pedido_cambiar_estado(request, pk):
    pedido = get_object_or_404(PedidoProveedor, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(PedidoProveedor.ESTADO_CHOICES):
            pedido.estado = nuevo_estado
            pedido.save()
            
            if nuevo_estado == 'RECIBIDO':
                # Actualizar stock de productos
                for detalle in pedido.detalles_pedido.all():
                    detalle.producto.stock_actual += detalle.cantidad
                    detalle.producto.save()
                messages.success(request, f'Pedido #{pedido.id} marcado como recibido. Stock actualizado.')
            else:
                messages.success(request, f'Estado del pedido #{pedido.id} actualizado.')
                
            return redirect('pedido_detail', pk=pedido.id)
    
    return redirect('pedido_detail', pk=pedido.id)

# === NOTAS DE ENTREGA ===

@login_required
def nota_entrega_crear(request, venta_id):
    """Crear una nueva nota de entrega para una venta"""
    venta = get_object_or_404(Venta, pk=venta_id)
    
    # Verificar que la venta permita notas de entrega
    if not venta.permite_notas_entrega:
        messages.error(request, f'No se pueden agregar notas de entrega para ventas en estado "{venta.get_estado_display()}"')
        return redirect('venta_detail', pk=venta.id)
    
    if request.method == 'POST':
        form = NotaEntregaVentaForm(request.POST)
        formset = DetalleNotaEntregaFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Crear la nota de entrega
                    nota = form.save(commit=False)
                    nota.venta = venta
                    nota.usuario = request.user
                    nota.save()
                    
                    # Guardar los detalles
                    formset.instance = nota
                    detalles = formset.save()
                    
                    # Aplicar descuento de inventario si se solicitó
                    if request.POST.get('aplicar_inventario') == 'true':
                        nota.aplicar_descuento_inventario()
                        messages.success(request, f'Nota de entrega #{nota.id} creada y descuento de inventario aplicado.')
                    else:
                        messages.success(request, f'Nota de entrega #{nota.id} creada. Recuerda aplicar el descuento de inventario cuando corresponda.')
                    
                    return redirect('venta_detail', pk=venta.id)
            except Exception as e:
                messages.error(request, f'Error al crear la nota de entrega: {str(e)}')
    else:
        form = NotaEntregaVentaForm()
        formset = DetalleNotaEntregaFormSet()
        
        # Configurar el formset para mostrar solo productos de esta venta
        for form_detalle in formset:
            productos_venta = venta.detalles.values_list('producto', flat=True)
            form_detalle.fields['producto'].queryset = Producto.objects.filter(id__in=productos_venta)
    
    return render(request, 'notas_entrega/form.html', {
        'form': form,
        'formset': formset,
        'venta': venta,
        'resumen_entregas': venta.resumen_entregas,
        'title': f'Nueva Nota de Entrega - Venta #{venta.id}'
    })


@login_required
def nota_entrega_list(request, venta_id):
    """Listar todas las notas de entrega de una venta"""
    venta = get_object_or_404(Venta, pk=venta_id)
    notas = venta.notas_entrega.select_related('usuario').prefetch_related('detalles_entrega__producto').order_by('-fecha_entrega')
    
    return render(request, 'notas_entrega/list.html', {
        'venta': venta,
        'notas': notas,
        'resumen_entregas': venta.resumen_entregas
    })


@login_required
def nota_entrega_detail(request, pk):
    """Ver detalle de una nota de entrega"""
    nota = get_object_or_404(NotaEntregaVenta, pk=pk)
    detalles = nota.detalles_entrega.select_related('producto')
    
    return render(request, 'notas_entrega/detail.html', {
        'nota': nota,
        'detalles': detalles,
        'venta': nota.venta
    })


@login_required
def nota_entrega_aplicar_inventario(request, pk):
    """Aplicar descuento de inventario a una nota de entrega"""
    nota = get_object_or_404(NotaEntregaVenta, pk=pk)
    
    if request.method == 'POST':
        try:
            if nota.aplicar_descuento_inventario():
                messages.success(request, f'Descuento de inventario aplicado a la nota #{nota.id}')
            else:
                messages.warning(request, f'El descuento de inventario ya había sido aplicado a la nota #{nota.id}')
        except Exception as e:
            messages.error(request, f'Error al aplicar descuento: {str(e)}')
    
    return redirect('nota_entrega_detail', pk=nota.id)


@login_required
def nota_entrega_revertir_inventario(request, pk):
    """Revertir descuento de inventario de una nota de entrega"""
    nota = get_object_or_404(NotaEntregaVenta, pk=pk)
    
    if request.method == 'POST':
        try:
            if nota.revertir_descuento_inventario():
                messages.success(request, f'Descuento de inventario revertido para la nota #{nota.id}')
            else:
                messages.warning(request, f'El descuento de inventario no estaba aplicado en la nota #{nota.id}')
        except Exception as e:
            messages.error(request, f'Error al revertir descuento: {str(e)}')
    
    return redirect('nota_entrega_detail', pk=nota.id)


# === GESTIÓN DE SUCURSALES ===

@login_required
def sucursal_list(request):
    """Lista de sucursales"""
    search = request.GET.get('search', '')
    sucursales = Sucursal.objects.all()
    
    if search:
        sucursales = sucursales.filter(
            Q(nombre__icontains=search) | 
            Q(codigo__icontains=search) |
            Q(ciudad__icontains=search)
        )
    
    return render(request, 'sucursales/list.html', {
        'sucursales': sucursales,
        'search': search
    })

@login_required
def sucursal_add(request):
    """Agregar nueva sucursal"""
    if request.method == 'POST':
        form = SucursalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sucursal agregada exitosamente.')
            return redirect('sucursal_list')
    else:
        form = SucursalForm()
    
    return render(request, 'sucursales/form.html', {
        'form': form,
        'title': 'Agregar Sucursal'
    })

@login_required
def sucursal_edit(request, pk):
    """Editar sucursal existente"""
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    if request.method == 'POST':
        form = SucursalForm(request.POST, instance=sucursal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sucursal actualizada exitosamente.')
            return redirect('sucursal_list')
    else:
        form = SucursalForm(instance=sucursal)
    
    return render(request, 'sucursales/form.html', {
        'form': form,
        'title': 'Editar Sucursal',
        'sucursal': sucursal
    })

@login_required
def sucursal_delete(request, pk):
    """Eliminar sucursal"""
    sucursal = get_object_or_404(Sucursal, pk=pk)
    if request.method == 'POST':
        sucursal.delete()
        messages.success(request, 'Sucursal eliminada exitosamente.')
        return redirect('sucursal_list')
    
    return render(request, 'sucursales/delete.html', {'sucursal': sucursal})

# === GESTIÓN DE REPARTIDORES ===

@login_required
def repartidor_list(request):
    """Lista de repartidores"""
    search = request.GET.get('search', '')
    estado = request.GET.get('estado', '')
    
    repartidores = Repartidor.objects.all()
    
    if search:
        repartidores = repartidores.filter(
            Q(nombre__icontains=search) | 
            Q(documento__icontains=search) |
            Q(telefono__icontains=search)
        )
    
    if estado:
        repartidores = repartidores.filter(estado=estado)
    
    return render(request, 'repartidores/list.html', {
        'repartidores': repartidores,
        'search': search,
        'estado_selected': estado,
        'estados': Repartidor.ESTADO_CHOICES
    })

@login_required
def repartidor_add(request):
    """Agregar nuevo repartidor"""
    if request.method == 'POST':
        form = RepartidorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Repartidor agregado exitosamente.')
            return redirect('repartidor_list')
    else:
        form = RepartidorForm()
    
    return render(request, 'repartidores/form.html', {
        'form': form,
        'title': 'Agregar Repartidor'
    })

@login_required
def repartidor_edit(request, pk):
    """Editar repartidor existente"""
    repartidor = get_object_or_404(Repartidor, pk=pk)
    
    if request.method == 'POST':
        form = RepartidorForm(request.POST, instance=repartidor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Repartidor actualizado exitosamente.')
            return redirect('repartidor_list')
    else:
        form = RepartidorForm(instance=repartidor)
    
    return render(request, 'repartidores/form.html', {
        'form': form,
        'title': 'Editar Repartidor',
        'repartidor': repartidor
    })

@login_required
def repartidor_delete(request, pk):
    """Eliminar repartidor"""
    repartidor = get_object_or_404(Repartidor, pk=pk)
    if request.method == 'POST':
        repartidor.delete()
        messages.success(request, 'Repartidor eliminado exitosamente.')
        return redirect('repartidor_list')
    
    return render(request, 'repartidores/delete.html', {'repartidor': repartidor})

# === DOMICILIOS - DASHBOARD Y GESTIÓN DE RUTAS ===

@login_required
def domicilios_home(request):
    """Dashboard principal de domicilios con tabs"""
    estado = request.GET.get('estado', 'todas')
    
    rutas = RutaEntrega.objects.select_related('sucursal_origen', 'repartidor').prefetch_related('detalles__venta')
    
    if estado != 'todas':
        rutas = rutas.filter(estado=estado.upper())
    
    context = {
        'rutas': rutas.order_by('-fecha_creacion'),
        'rutas_planificadas': RutaEntrega.objects.filter(estado='PLANIFICADA').count(),
        'rutas_en_curso': RutaEntrega.objects.filter(estado='EN_CURSO').count(),
        'rutas_completadas': RutaEntrega.objects.filter(estado='COMPLETADA').count(),
        'estado_selected': estado
    }
    return render(request, 'domicilios/dashboard.html', context)

@login_required
def domicilios_planificar(request):
    """Vista para planificar nuevas rutas"""
    ventas_en_rutas_activas = DetalleRuta.objects.filter(
        ~Q(ruta__estado='CANCELADA')  # El ~Q niega la condición
    ).values_list('venta_id', flat=True)

    ventas_pendientes = Venta.objects.filter(
        requiere_domicilio=True,
        estado='PAGADA_PENDIENTE_ENTREGA'
    ).exclude(
        id__in=ventas_en_rutas_activas
    ).select_related('cliente').prefetch_related('detalles__producto')
    
    sucursales = Sucursal.objects.filter(activa=True)
    repartidores = Repartidor.objects.filter(estado='ACTIVO')
    
    return render(request, 'domicilios/planificar.html', {
        'ventas': ventas_pendientes,
        'sucursales': sucursales,
        'repartidores': repartidores
    })

@login_required
def ruta_detail(request, pk):
    """Detalle de una ruta específica"""
    ruta = get_object_or_404(RutaEntrega, pk=pk)
    detalles = ruta.detalles.select_related('venta__cliente').order_by('orden_entrega')
    
    return render(request, 'domicilios/ruta_detail.html', {
        'ruta': ruta,
        'detalles': detalles
    })

@login_required
def ruta_cambiar_estado(request, pk):
    """Cambiar estado de una ruta"""
    ruta = get_object_or_404(RutaEntrega, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(RutaEntrega.ESTADO_CHOICES):
            # Validar que todas las entregas estén completadas antes de marcar como COMPLETADA
            if nuevo_estado == 'COMPLETADA':
                entregas_pendientes = ruta.detalles.filter(entregado=False).count()
                if entregas_pendientes > 0:
                    messages.error(request, f'No se puede completar la ruta. Hay {entregas_pendientes} entrega(s) pendiente(s). Debes marcar todas las entregas como completadas primero.')
                    return redirect('ruta_detail', pk=ruta.id)
            
            if nuevo_estado == 'CANCELADA':
                with transaction.atomic():
                    # Obtenemos todas las ventas asociadas a esta ruta
                    detalles_ruta = ruta.detalles.select_related('venta').all()
                    ventas_a_liberar_ids = []

                    for detalle in detalles_ruta:
                        # ¡IMPORTANTE! Solo liberamos las ventas que NO fueron entregadas
                        if not detalle.entregado:
                            ventas_a_liberar_ids.append(detalle.venta.id)

                    if ventas_a_liberar_ids:
                        # Cambiamos el estado de las ventas no entregadas de vuelta a PENDIENTE
                        Venta.objects.filter(id__in=ventas_a_liberar_ids).update(
                            estado='PAGADA_PENDIENTE_ENTREGA'
                        )
                        messages.info(request, f'{len(ventas_a_liberar_ids)} venta(s) no entregada(s) han sido liberadas y están disponibles para otra ruta.')

            ruta.estado = nuevo_estado
            
            # Registrar hora de inicio/fin
            if nuevo_estado == 'EN_CURSO' and not ruta.hora_inicio_real:
                ruta.hora_inicio_real = timezone.now()
            elif nuevo_estado == 'COMPLETADA' and not ruta.hora_fin_real:
                ruta.hora_fin_real = timezone.now()
            
            ruta.save()
            messages.success(request, f'Estado de la ruta #{ruta.id} actualizado a {ruta.get_estado_display()}')
        
        return redirect('ruta_detail', pk=ruta.id)
    
    return redirect('domicilios_home')

@login_required
def ruta_marcar_entrega(request, detalle_id):
    """Marcar una entrega como completada"""
    detalle = get_object_or_404(DetalleRuta, pk=detalle_id)
    
    if request.method == 'POST':
        detalle.entregado = True
        detalle.hora_entrega_real = timezone.now()
        detalle.observaciones = request.POST.get('observaciones', '')
        detalle.save()
        
        # Actualizar estado de la venta (sin validar stock)
        venta = detalle.venta
        venta.estado = 'COMPLETADA'
        # Usar update para evitar el método save() que valida stock
        Venta.objects.filter(id=venta.id).update(estado='COMPLETADA')
        
        messages.success(request, f'Entrega #{detalle.venta.id} marcada como completada')
        
        # Verificar si todas las entregas de la ruta están completadas
        ruta = detalle.ruta
        entregas_pendientes = ruta.detalles.filter(entregado=False).count()
        
        if entregas_pendientes == 0 and ruta.estado == 'EN_CURSO':
            # Auto-completar la ruta si todas las entregas están hechas
            ruta.estado = 'COMPLETADA'
            ruta.hora_fin_real = timezone.now()
            ruta.save()
            messages.success(request, f'¡Ruta #{ruta.id} completada automáticamente! Todas las entregas fueron realizadas.')
        
        return redirect('ruta_detail', pk=detalle.ruta.id)
    
    return redirect('ruta_detail', pk=detalle.ruta.id)

# === APIs PARA DOMICILIOS ===

@login_required
def api_ventas_pendientes(request):
    """API: Obtener ventas pendientes de domicilio"""
    # IDs de ventas que ya están en rutas activas (no canceladas)
    ventas_en_rutas_activas = DetalleRuta.objects.filter(
        ~Q(ruta__estado='CANCELADA')  # El ~Q niega la condición
    ).values_list('venta_id', flat=True)

    ventas = Venta.objects.filter(
        requiere_domicilio=True,
        estado='PAGADA_PENDIENTE_ENTREGA'
    ).exclude(
        id__in=ventas_en_rutas_activas
    ).select_related('cliente').prefetch_related('detalles__producto')
    
    data = []
    for v in ventas:
        peso_total = 0
        volumen_total = 0
        productos_list = []
        
        for d in v.detalles.all():
            peso = float(d.producto.peso_kg) * d.cantidad if d.producto.peso_kg else 0
            volumen = float(d.producto.volumen_m3) * d.cantidad if d.producto.volumen_m3 else 0
            peso_total += peso
            volumen_total += volumen
            
            productos_list.append({
                'nombre': d.producto.nombre,
                'cantidad': d.cantidad,
                'peso_kg': peso,
                'volumen_m3': volumen
            })
        
        data.append({
            'id': v.id,
            'cliente': v.cliente.nombre if v.cliente else 'Sin cliente',
            'direccion': v.direccion_entrega,
            'coords': [float(v.latitud_entrega), float(v.longitud_entrega)] if v.latitud_entrega and v.longitud_entrega else None,
            'prioridad': v.prioridad_entrega,
            'monto': float(v.monto_total),
            'peso_total_kg': peso_total,
            'volumen_total_m3': volumen_total,
            'productos': productos_list,
            'ventana_inicio': v.ventana_tiempo_inicio.strftime('%H:%M') if v.ventana_tiempo_inicio else None,
            'ventana_fin': v.ventana_tiempo_fin.strftime('%H:%M') if v.ventana_tiempo_fin else None,
        })
    
    return JsonResponse({'ventas': data})

@login_required
def api_calcular_ruta_optima(request):
    """
    API: Calcular ruta óptima con restricciones de capacidad y ventanas de tiempo.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body) 
        sucursal_id = data.get('sucursal_id')
        repartidor_id = data.get('repartidor_id')
        ventas_ids = data.get('ventas_ids', [])
        fecha_entrega_str = data.get('fecha_entrega')

        print(f"\n{'='*80}")
        print(f"🚀 INICIANDO CÁLCULO DE RUTA")
        print(f"{'='*80}")
        print(f"📦 Ventas solicitadas: {ventas_ids}")
        print(f"🏪 Sucursal ID: {sucursal_id}")
        print(f"🚗 Repartidor ID: {repartidor_id}")

        if not all([sucursal_id, repartidor_id, ventas_ids, fecha_entrega_str]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        # --- PASO 1: OBTENER DATOS ---
        sucursal = Sucursal.objects.get(id=sucursal_id)
        repartidor = Repartidor.objects.get(id=repartidor_id)
        ventas = Venta.objects.filter(id__in=ventas_ids).prefetch_related('detalles__producto')
        
        print(f"\n📊 VALIDANDO VENTAS:")
        print(f"   Ventas encontradas en BD: {ventas.count()}")
        
        nodos = [{'tipo': 'sucursal', 'obj': sucursal, 'coords': [float(sucursal.latitud), float(sucursal.longitud)]}]
        ventas_a_procesar = []
        ventas_descartadas = []
        
        for v in ventas:
            print(f"\n   Venta #{v.id}:")
            print(f"     - Cliente: {v.cliente.nombre if v.cliente else 'Sin cliente'}")
            print(f"     - Dirección: {v.direccion_entrega}")
            print(f"     - Coordenadas: lat={v.latitud_entrega}, lng={v.longitud_entrega}")
            
            if v.latitud_entrega and v.longitud_entrega:
                nodos.append({
                    'tipo': 'venta', 
                    'obj': v, 
                    'coords': [float(v.latitud_entrega), float(v.longitud_entrega)]
                })
                ventas_a_procesar.append(v)
                print(f"     ✅ INCLUIDA en ruta")
            else:
                ventas_descartadas.append(v)
                print(f"     ❌ DESCARTADA (sin coordenadas)")
        
        print(f"\n📈 RESUMEN VALIDACIÓN:")
        print(f"   ✅ Ventas válidas para ruta: {len(ventas_a_procesar)}")
        print(f"   ❌ Ventas descartadas: {len(ventas_descartadas)}")
        
        if len(ventas_descartadas) > 0:
            print(f"\n⚠️ ALERTA: Las siguientes ventas no tienen coordenadas:")
            for v in ventas_descartadas:
                print(f"      - Venta #{v.id}: {v.cliente.nombre if v.cliente else 'N/A'}")
        
        if len(nodos) <= 1:
            return JsonResponse({
                'error': f'No hay suficientes puntos válidos. Ventas con coordenadas: {len(ventas_a_procesar)}'
            }, status=400)

        # --- PASO 2: MATRIZ DE TIEMPOS ---
        print(f"\n🗺️ CALCULANDO MATRIZ DE DISTANCIAS:")
        print(f"   Nodos totales: {len(nodos)}")
        
        coords_str = ';'.join([f"{n['coords'][1]},{n['coords'][0]}" for n in nodos])
        url_matrix = f"https://router.project-osrm.org/table/v1/driving/{coords_str}?annotations=duration"
        
        response_matrix = requests.get(url_matrix, timeout=20)
        osrm_matrix_data = response_matrix.json()
        
        if osrm_matrix_data.get('code') != 'Ok':
            return JsonResponse({'error': f"Error OSRM: {osrm_matrix_data.get('message', '')}"}, status=500)
        
        time_matrix = [[int(t or 0) for t in row] for row in osrm_matrix_data['durations']]
        print(f"   ✅ Matriz calculada: {len(time_matrix)}x{len(time_matrix[0])}")

        # --- PASO 3: OR-TOOLS ---
        print(f"\n🔧 CONFIGURANDO OR-TOOLS:")
        
        demands_kg = [0] + [int(v.peso_total_kg * 100) for v in ventas_a_procesar]
        demands_m3 = [0] + [int(v.volumen_total_m3 * 1000) for v in ventas_a_procesar]
        vehicle_capacities_kg = [int(repartidor.capacidad_maxima_kg * 100)]
        vehicle_capacities_m3 = [int(repartidor.capacidad_maxima_m3 * 1000)]

        print(f"   Demandas KG: {[d/100 for d in demands_kg]}")
        print(f"   Capacidad vehículo: {vehicle_capacities_kg[0]/100} kg")

        time_windows = [(0, 86400)]  # Sucursal: todo el día
        
        for v in ventas_a_procesar:
            if v.ventana_tiempo_inicio and v.ventana_tiempo_fin:
                start_s = v.ventana_tiempo_inicio.hour * 3600 + v.ventana_tiempo_inicio.minute * 60
                end_s = v.ventana_tiempo_fin.hour * 3600 + v.ventana_tiempo_fin.minute * 60
                time_windows.append((start_s, end_s))
                print(f"   Venta #{v.id}: ventana {v.ventana_tiempo_inicio} - {v.ventana_tiempo_fin}")
            else:
                time_windows.append((8 * 3600, 18 * 3600))  # Default 8am-6pm
                print(f"   Venta #{v.id}: ventana DEFAULT 8:00-18:00")

        # --- PASO 4: RESOLVER ---
        print(f"\n🧮 RESOLVIENDO CON OR-TOOLS...")
        
        manager = pywrapcp.RoutingIndexManager(len(time_matrix), 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        def demand_callback_kg(from_index):
            return demands_kg[manager.IndexToNode(from_index)]
        demand_callback_index_kg = routing.RegisterUnaryTransitCallback(demand_callback_kg)
        routing.AddDimensionWithVehicleCapacity(demand_callback_index_kg, 0, vehicle_capacities_kg, True, 'CapacityKG')
        
        def demand_callback_m3(from_index):
            return demands_m3[manager.IndexToNode(from_index)]
        demand_callback_index_m3 = routing.RegisterUnaryTransitCallback(demand_callback_m3)
        routing.AddDimensionWithVehicleCapacity(demand_callback_index_m3, 0, vehicle_capacities_m3, True, 'CapacityM3')
        
        routing.AddDimension(transit_callback_index, 3600, 86400, False, 'Time')
        time_dimension = routing.GetDimensionOrDie('Time')
        
        for loc_idx, time_win in enumerate(time_windows):
            if loc_idx == 0: continue
            index = manager.NodeToIndex(loc_idx)
            time_dimension.CumulVar(index).SetRange(time_win[0], time_win[1])

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.FromSeconds(30)

        solution = routing.SolveWithParameters(search_parameters)
        
        if not solution:
            print(f"   ❌ NO SE ENCONTRÓ SOLUCIÓN")
            return JsonResponse({'error': 'No se encontró solución viable (posibles restricciones de capacidad o tiempo)'}, status=400)
        
        print(f"   ✅ Solución encontrada")
        print(f"   Costo total: {solution.ObjectiveValue()}")

        # --- PASO 5: EXTRAER RUTA ---
        print(f"\n🛣️ CONSTRUYENDO SECUENCIA DE RUTA:")
        
        route_sequence_indices = []
        index = routing.Start(0)
        route_nodes_visited = []
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_nodes_visited.append(node_index)
            
            if node_index != 0:  # Excluir sucursal del inicio
                route_sequence_indices.append(node_index)
                print(f"   Parada: nodo {node_index} (venta #{ventas_a_procesar[node_index-1].id})")
            else:
                print(f"   Inicio: nodo {node_index} (sucursal)")
            
            index = solution.Value(routing.NextVar(index))
        
        # Nodo final (debería ser la sucursal)
        final_node = manager.IndexToNode(index)
        route_nodes_visited.append(final_node)
        print(f"   Fin: nodo {final_node} (sucursal)")
        
        print(f"\n📊 RESUMEN RUTA:")
        print(f"   Nodos visitados: {route_nodes_visited}")
        print(f"   Entregas en secuencia: {len(route_sequence_indices)}")
        
        ventas_ordenadas = [nodos[i]['obj'] for i in route_sequence_indices]
        
        print(f"\n📦 VENTAS EN ORDEN DE ENTREGA:")
        for idx, venta in enumerate(ventas_ordenadas):
            print(f"   {idx+1}. Venta #{venta.id} - {venta.cliente.nombre if venta.cliente else 'N/A'}")

        # --- PASO 6: CONSTRUIR COORDENADAS PARA OSRM ---
        print(f"\n🌐 PREPARANDO GEOMETRÍA:")
        
        coords_para_osrm = []
        
        # Sucursal inicio
        coords_para_osrm.append([float(sucursal.latitud), float(sucursal.longitud)])
        print(f"   1. Sucursal (inicio): [{sucursal.latitud}, {sucursal.longitud}]")
        
        # Entregas
        for idx, venta in enumerate(ventas_ordenadas):
            coords_para_osrm.append([float(venta.latitud_entrega), float(venta.longitud_entrega)])
            print(f"   {idx+2}. Venta #{venta.id}: [{venta.latitud_entrega}, {venta.longitud_entrega}]")
        
        # Sucursal fin
        coords_para_osrm.append([float(sucursal.latitud), float(sucursal.longitud)])
        print(f"   {len(coords_para_osrm)}. Sucursal (fin): [{sucursal.latitud}, {sucursal.longitud}]")

        # --- PASO 7: LLAMAR A OSRM ---
        print(f"\n🗺️ OBTENIENDO GEOMETRÍA DE OSRM:")
        
        coords_str_ruta = ';'.join([f"{c[1]},{c[0]}" for c in coords_para_osrm])
        url_route = f"https://router.project-osrm.org/route/v1/driving/{coords_str_ruta}"
        params_route = {'overview': 'full', 'geometries': 'geojson', 'steps': 'true', 'annotations': 'true'}
        
        response_route = requests.get(url_route, params=params_route, timeout=15)
        osrm_route_data = response_route.json()
        
        if osrm_route_data.get('code') != 'Ok':
            return JsonResponse({'error': 'No se pudo calcular geometría de ruta'}, status=400)
        
        route = osrm_route_data['routes'][0]
        geometry = route['geometry']
        
        print(f"   ✅ Geometría obtenida: {len(geometry['coordinates'])} puntos")

        # --- PASO 8: WAYPOINTS PARA FRONTEND ---
        final_waypoints_info = []
        
        final_waypoints_info.append({
            'type': 'sucursal',
            'lat': float(sucursal.latitud),
            'lng': float(sucursal.longitud),
            'label': 'S',
            'popup': f"<b>Sucursal de Salida</b><br>{sucursal.nombre}<br><small>Inicio y Fin de ruta</small>"
        })

        for i, venta in enumerate(ventas_ordenadas):
            final_waypoints_info.append({
                'type': 'entrega',
                'lat': float(venta.latitud_entrega),
                'lng': float(venta.longitud_entrega),
                'label': str(i + 1),
                'popup': f"<b>Parada #{i + 1}</b><br>{venta.cliente.nombre if venta.cliente else 'N/A'}<br><small>{venta.direccion_entrega}</small>"
            })

        # --- PASO 9: WAYPOINTS PARA BD ---
        waypoints_completos = []
        
        waypoints_completos.append({
            'lat': float(sucursal.latitud),
            'lng': float(sucursal.longitud),
            'tipo': 'sucursal',
            'nombre': sucursal.nombre
        })
        
        for i, venta in enumerate(ventas_ordenadas):
            waypoints_completos.append({
                'lat': float(venta.latitud_entrega),
                'lng': float(venta.longitud_entrega),
                'tipo': 'entrega',
                'venta_id': venta.id,
                'orden': i + 1,
                'cliente': venta.cliente.nombre if venta.cliente else 'N/A',
                'direccion': venta.direccion_entrega
            })
        
        waypoints_completos.append({
            'lat': float(sucursal.latitud),
            'lng': float(sucursal.longitud),
            'tipo': 'sucursal',
            'nombre': sucursal.nombre
        })

        # --- PASO 10: PLAN DE CARGUE ---
        plan_cargue = []
        orden_entrega = list(range(1, len(ventas_ordenadas) + 1))
        orden_carga = list(reversed(orden_entrega))
        
        for idx, venta in enumerate(ventas_ordenadas):
            productos_list = []
            for detalle in venta.detalles.all():
                productos_list.append({
                    'nombre': detalle.producto.nombre,
                    'cantidad': detalle.cantidad
                })

            plan_cargue.append({
                'venta_id': venta.id,
                'orden_carga': orden_carga[idx],
                'orden_entrega': orden_entrega[idx],
                'cliente': venta.cliente.nombre if venta.cliente else 'Sin cliente',
                'telefono': venta.cliente.telefono if venta.cliente else 'N/A',
                'email': venta.cliente.email if venta.cliente and venta.cliente.email else 'N/A',
                'direccion': venta.direccion_entrega,
                'productos': productos_list,
                'peso_total_kg': round(float(venta.peso_total_kg), 2),
                'volumen_total_m3': round(float(venta.volumen_total_m3), 3),
                'instruccion': f"Cargar en posición {orden_carga[idx]} (entregar en parada {orden_entrega[idx]})"
            })
        
        peso_total_ruta = sum(item['peso_total_kg'] for item in plan_cargue)
        volumen_total_ruta = sum(item['volumen_total_m3'] for item in plan_cargue)
        
        # --- PASO 11: INSTRUCCIONES ---
        instrucciones = []
        if 'legs' in route:
            paso_numero = 1
            for leg in route['legs']:
                if 'steps' in leg:
                    for step in leg['steps']:
                        if 'maneuver' in step:
                            maneuver = step['maneuver']
                            street_name = step.get('name', '')
                            base_instruction = maneuver.get('instruction', 'Continuar')
                            final_instruction = f"Continúa por {street_name}" if base_instruction.lower() in ['continue', 'go straight', 'continuar'] and street_name else base_instruction
                            instrucciones.append({
                                'paso': paso_numero,
                                'distancia_m': round(step.get('distance', 0)),
                                'duracion_s': round(step.get('duration', 0)),
                                'instruccion': final_instruction,
                                'tipo': maneuver.get('type', 'turn'),
                                'modificador': maneuver.get('modifier', ''),
                                'coordenadas': maneuver.get('location', [])
                            })
                            paso_numero += 1
        
        # --- RESPUESTA FINAL ---
        print(f"\n✅ RUTA CALCULADA EXITOSAMENTE:")
        print(f"   Distancia: {round(route['distance'] / 1000, 2)} km")
        print(f"   Tiempo: {round(route['duration'] / 60)} min")
        print(f"   Paradas: {len(ventas_ordenadas)}")
        print(f"{'='*80}\n")
        
        return JsonResponse({
            'success': True,
            'ruta': {
                'distancia_km': round(route['distance'] / 1000, 2),
                'tiempo_min': round(route['duration'] / 60),
                'geometria': geometry,
                'waypoints': waypoints_completos,
                'waypoints_info': final_waypoints_info,
                'trafico': route.get('annotations', {}),
                'instrucciones': instrucciones
            },
            'plan_cargue': plan_cargue,
            'peso_total_kg': round(peso_total_ruta, 2),
            'volumen_total_m3': round(volumen_total_ruta, 3),
            'numero_paradas': len(ventas_ordenadas)
        })
        
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR:")
        traceback.print_exc()
        return JsonResponse({'error': f"Error: {str(e)}"}, status=500)

# 10.953649, -74.808417
@login_required
def api_guardar_ruta(request):
    """API: Guardar ruta planificada en la base de datos"""
    import json as json_module
    from decimal import Decimal
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json_module.loads(request.body)
        
        with transaction.atomic():
            # Crear ruta
            ruta = RutaEntrega.objects.create(
                sucursal_origen_id=data['sucursal_id'],
                repartidor_id=data.get('repartidor_id'),
                fecha_entrega=data['fecha_entrega'],
                distancia_total_km=Decimal(str(data['distancia_km'])),
                tiempo_estimado_min=data['tiempo_min'],
                numero_paradas=data['numero_paradas'],
                waypoints=data['waypoints'],
                geometria_ruta=data['geometria'],
                estado_trafico=data.get('trafico', {}),
                plan_cargue=data['plan_cargue'],
                instrucciones_navegacion=data.get('instrucciones', []),
                peso_total_kg=Decimal(str(data['peso_total_kg'])),
                volumen_total_m3=Decimal(str(data['volumen_total_m3'])),
                estado='PLANIFICADA'
            )
            
            # Crear detalles
            for item in data['plan_cargue']:
                DetalleRuta.objects.create(
                    ruta=ruta,
                    venta_id=item['venta_id'],
                    orden_entrega=item['orden_entrega'],
                    orden_carga=item['orden_carga'],
                    peso_productos_kg=Decimal(str(item['peso_total_kg'])),
                    volumen_productos_m3=Decimal(str(item['volumen_total_m3']))
                )
            
            return JsonResponse({
                'success': True,
                'ruta_id': ruta.id,
                'message': f'Ruta #{ruta.id} creada exitosamente'
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def ruta_descargar_plan_cargue(request, ruta_id):
    """Descargar plan de cargue en PDF con mapa de la ruta"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from django.http import HttpResponse
    from io import BytesIO
    from datetime import datetime
    
    ruta = get_object_or_404(RutaEntrega, id=ruta_id)
    detalles = ruta.detalles.select_related('venta__cliente').order_by('orden_entrega')
    
    # Generar análisis inteligente con Gemini
    analisis = None
    try:
        from core.services.gemini_analyzer import GeminiCargaAnalyzer
        analyzer = GeminiCargaAnalyzer()
        ruta_info = {
            'distancia_km': float(ruta.distancia_total_km),
            'tiempo_min': ruta.tiempo_estimado_min,
            'num_paradas': ruta.numero_paradas
        }
        analisis = analyzer.analizar_carga(ruta.plan_cargue, ruta_info)
    except Exception as e:
        print(f"Error generando análisis con Gemini: {e}")
        analisis = None
    
    # Crear el PDF con márgenes personalizados
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        borderPadding=8,
        backColor=colors.HexColor('#f1f5f9'),
        borderWidth=0,
        borderRadius=4
    )
    
    # Encabezado
    elements.append(Paragraph(f"PLAN DE CARGUE - RUTA #{ruta.id}", title_style))
    elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Información general
    elements.append(Paragraph("INFORMACIÓN GENERAL", section_title_style))
    elements.append(Spacer(1, 0.15*inch))
    
    info_data = [
        ['Sucursal:', ruta.sucursal_origen.nombre],
        ['Repartidor:', ruta.repartidor.nombre if ruta.repartidor else 'No asignado'],
        ['Fecha:', ruta.fecha_entrega.strftime('%d/%m/%Y')],
        ['Distancia:', f"{ruta.distancia_total_km} km"],
        ['Tiempo estimado:', f"{ruta.tiempo_estimado_min} min"],
        ['Peso total:', f"{ruta.peso_total_kg} kg"],
        ['Paradas:', str(ruta.numero_paradas)]
    ]
    
    info_table = Table(info_data, colWidths=[2.2*inch, 4.3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2ff')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Resumen visual de paradas
    elements.append(Paragraph("RESUMEN DE ENTREGAS", section_title_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # Crear tabla de resumen de paradas
    paradas_data = [['#', 'Cliente', 'Dirección', 'Peso']]
    for detalle in detalles:
        paradas_data.append([
            str(detalle.orden_entrega),
            detalle.venta.cliente.nombre if detalle.venta.cliente else 'Sin cliente',
            detalle.venta.direccion_entrega[:40] + '...' if len(detalle.venta.direccion_entrega) > 40 else detalle.venta.direccion_entrega,
            f"{detalle.peso_productos_kg} kg"
        ])
    
    paradas_table = Table(paradas_data, colWidths=[0.5*inch, 2*inch, 3*inch, 1*inch])
    paradas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    elements.append(paradas_table)
    
    # Nota sobre el mapa
    note_style = ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER,
        spaceAfter=0,
        spaceBefore=10
    )
    elements.append(Paragraph("💡 Consulta el mapa interactivo en la vista web para ver la ruta completa", note_style))
    elements.append(Spacer(1, 0.4*inch))
    
    # Instrucciones de Navegación
    if ruta.instrucciones_navegacion:
        elements.append(Paragraph("INSTRUCCIONES DE NAVEGACIÓN", section_title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Crear tabla de instrucciones
        instrucciones_data = [['#', 'Instrucción', 'Distancia', 'Tiempo']]
        for inst in ruta.instrucciones_navegacion[:15]:  # Limitar a 15 para no saturar el PDF
            instrucciones_data.append([
                str(inst['paso']),
                inst['instruccion'][:50] + '...' if len(inst['instruccion']) > 50 else inst['instruccion'],
                f"{inst['distancia_m']} m",
                f"{inst['duracion_s']} s"
            ])
        
        instrucciones_table = Table(instrucciones_data, colWidths=[0.5*inch, 4*inch, 1*inch, 1*inch])
        instrucciones_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(instrucciones_table)
        
        if len(ruta.instrucciones_navegacion) > 15:
            elements.append(Paragraph(f"<i>Mostrando las primeras 15 de {len(ruta.instrucciones_navegacion)} instrucciones. Consulta la vista web para ver todas.</i>", note_style))
        
        elements.append(Spacer(1, 0.4*inch))
    
    # GUÍA INTELIGENTE DE CARGA CON GEMINI
    if analisis:
        elements.append(PageBreak())
        elements.append(Paragraph("📋 GUÍA DE CARGA PARA EL REPARTIDOR", section_title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Resumen para el repartidor
        resumen_style = ParagraphStyle(
            'ResumenRepartidor',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=15,
            rightIndent=15,
            backColor=colors.HexColor('#dbeafe'),
            borderColor=colors.HexColor('#3b82f6'),
            borderWidth=2,
            borderPadding=15,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph(f"📢 {analisis.resumen_para_repartidor}", resumen_style))
        elements.append(Spacer(1, 0.15*inch))
        
        # Nivel de dificultad y tiempo
        info_row = [[
            Paragraph(f"<b>Dificultad:</b> {analisis.nivel_dificultad}", styles['Normal']),
            Paragraph(f"<b>Tiempo de carga:</b> {analisis.tiempo_estimado_carga}", styles['Normal'])
        ]]
        info_table = Table(info_row, colWidths=[3.25*inch, 3.25*inch])
        dificultad_colors = {
            'Fácil': colors.HexColor('#10b981'),
            'Normal': colors.HexColor('#f59e0b'),
            'Difícil': colors.HexColor('#ef4444')
        }
        dificultad_color = dificultad_colors.get(analisis.nivel_dificultad, colors.HexColor('#6b7280'))
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), dificultad_color),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # PASOS DE MONTAJE
        elements.append(Paragraph("🔧 PASOS PARA CARGAR EL VEHÍCULO", section_title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        for paso in analisis.pasos_montaje:
            paso_data = [[
                Paragraph(f"<b>PASO {paso.numero}</b>", ParagraphStyle('PasoNum', parent=styles['Normal'], fontSize=11, textColor=colors.white, fontName='Helvetica-Bold')),
                Paragraph(f"<b>{paso.accion}</b>", styles['Normal'])
            ]]
            paso_header = Table(paso_data, colWidths=[0.8*inch, 5.7*inch])
            paso_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#3b82f6')),
                ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#eff6ff')),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (1, 0), (1, 0), 12),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ]))
            elements.append(paso_header)
            
            paso_body_data = [[
                Paragraph(f"<b>📍 Ubicación:</b> {paso.ubicacion}", styles['Normal'])
            ], [
                Paragraph(f"<b>💡 Por qué:</b> {paso.razon}", styles['Normal'])
            ]]
            paso_body = Table(paso_body_data, colWidths=[6.5*inch])
            paso_body.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
                ('LINEABOVE', (0, 1), (-1, 1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            elements.append(paso_body)
            elements.append(Spacer(1, 0.12*inch))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # DISTRIBUCIÓN DE PESO
        elements.append(Paragraph("⚖️ CÓMO DISTRIBUIR EL PESO", section_title_style))
        elements.append(Spacer(1, 0.1*inch))
        peso_style = ParagraphStyle(
            'DistribucionPeso',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1e293b'),
            leftIndent=12,
            rightIndent=12,
            backColor=colors.HexColor('#f0fdf4'),
            borderColor=colors.HexColor('#10b981'),
            borderWidth=1,
            borderPadding=12
        )
        elements.append(Paragraph(analisis.distribucion_peso, peso_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # PRODUCTOS ESPECIALES
        if analisis.productos_especiales:
            elements.append(Paragraph("⚠️ PRODUCTOS QUE NECESITAN CUIDADO ESPECIAL", section_title_style))
            elements.append(Spacer(1, 0.1*inch))
            productos_text = '<br/>'.join([f"• {prod}" for prod in analisis.productos_especiales])
            productos_style = ParagraphStyle(
                'ProductosEspeciales',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#92400e'),
                backColor=colors.HexColor('#fef3c7'),
                borderColor=colors.HexColor('#f59e0b'),
                borderWidth=2,
                borderPadding=12,
                leftIndent=12
            )
            elements.append(Paragraph(productos_text, productos_style))
            elements.append(Spacer(1, 0.3*inch))
        
        # Recomendaciones
        elements.append(Paragraph("💡 RECOMENDACIONES", section_title_style))
        elements.append(Spacer(1, 0.15*inch))
        
        for idx, rec in enumerate(analisis.recomendaciones, 1):
            # Color según prioridad
            prioridad_colors = {
                'Alta': colors.HexColor('#dc2626'),
                'Media': colors.HexColor('#f59e0b'),
                'Baja': colors.HexColor('#10b981')
            }
            prioridad_color = prioridad_colors.get(rec.prioridad, colors.HexColor('#6b7280'))
            
            rec_data = [[
                Paragraph(f"<b>{idx}. {rec.titulo}</b>", styles['Normal']),
                Paragraph(f"<b>{rec.prioridad}</b>", ParagraphStyle('PrioridadTag', parent=styles['Normal'], textColor=colors.white, fontSize=9, alignment=TA_CENTER))
            ]]
            
            rec_header = Table(rec_data, colWidths=[5.5*inch, 1*inch])
            rec_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f8fafc')),
                ('BACKGROUND', (1, 0), (1, 0), prioridad_color),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (0, 0), 12),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ]))
            elements.append(rec_header)
            
            rec_body_data = [[
                Paragraph(f"<b>Categoría:</b> {rec.categoria}", styles['Normal']),
            ], [
                Paragraph(rec.descripcion, styles['Normal'])
            ]]
            
            rec_body = Table(rec_body_data, colWidths=[6.5*inch])
            rec_body.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
                ('LINEABOVE', (0, 1), (-1, 1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            elements.append(rec_body)
            elements.append(Spacer(1, 0.15*inch))
        
        # CHECKLIST ANTES DE SALIR
        if analisis.checklist_antes_salir:
            elements.append(PageBreak())
            elements.append(Paragraph("✅ CHECKLIST ANTES DE SALIR", section_title_style))
            elements.append(Spacer(1, 0.15*inch))
            
            checklist_text = '<br/>'.join(analisis.checklist_antes_salir)
            checklist_style = ParagraphStyle(
                'Checklist',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#065f46'),
                backColor=colors.HexColor('#d1fae5'),
                borderColor=colors.HexColor('#10b981'),
                borderWidth=2,
                borderPadding=15,
                leftIndent=12,
                fontName='Helvetica-Bold'
            )
            elements.append(Paragraph(checklist_text, checklist_style))
            elements.append(Spacer(1, 0.3*inch))
        
        # TIPS PARA LAS ENTREGAS
        if analisis.tips_entrega:
            elements.append(Paragraph("🎯 TIPS PARA LAS ENTREGAS", section_title_style))
            elements.append(Spacer(1, 0.15*inch))
            
            for idx, tip in enumerate(analisis.tips_entrega, 1):
                tip_style = ParagraphStyle(
                    'Tip',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#1e293b'),
                    backColor=colors.HexColor('#fef9c3'),
                    borderColor=colors.HexColor('#eab308'),
                    borderWidth=1,
                    borderPadding=10,
                    leftIndent=10,
                    spaceAfter=8
                )
                elements.append(Paragraph(f"<b>{idx}.</b> {tip}", tip_style))
            elements.append(Spacer(1, 0.2*inch))
        
        elements.append(PageBreak())
    
    # Plan de cargue
    elements.append(Paragraph("ORDEN DE CARGA (LIFO)", section_title_style))
    
    lifo_note_style = ParagraphStyle(
        'LIFONote',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#f59e0b'),
        spaceAfter=16,
        spaceBefore=8,
        leftIndent=12
    )
    elements.append(Paragraph("⚠️ <b>Último en cargar, primero en entregar</b> - Cargar en orden inverso al de entrega", lifo_note_style))
    elements.append(Spacer(1, 0.2*inch))
    
    item_header_style = ParagraphStyle(
        'ItemHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        spaceAfter=0
    )
    
    for idx, item in enumerate(ruta.plan_cargue, 1):
        # Color de fondo según posición (más oscuro = cargar primero)
        bg_colors = [
            colors.HexColor('#dc2626'),  # Rojo oscuro - cargar primero
            colors.HexColor('#f97316'),  # Naranja
            colors.HexColor('#f59e0b'),  # Amarillo
        ]
        bg_color = bg_colors[min(idx-1, len(bg_colors)-1)]
        
        # Encabezado del item con color
        header_data = [[
            Paragraph(f"📦 Posición de Carga: {item['orden_carga']}", item_header_style),
            Paragraph(f"📍 Parada: {item['orden_entrega']}", item_header_style)
        ]]
        
        header_table = Table(header_data, colWidths=[3.25*inch, 3.25*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(header_table)
        
        # Detalles del item
        productos_text = '<br/>'.join([f"• {p['cantidad']}x {p['nombre']} ({p['cantidad'] * p.get('peso_kg', 0):.2f} kg)" for p in item['productos']])
        
        # Información de contacto
        contacto_text = f"📞 {item.get('telefono', 'N/A')}"
        if item.get('email') and item.get('email') != 'N/A':
            contacto_text += f" | ✉️ {item['email']}"
        
        item_data = [
            [Paragraph('<b>Cliente:</b>', styles['Normal']), Paragraph(item['cliente'], styles['Normal'])],
            [Paragraph('<b>Contacto:</b>', styles['Normal']), Paragraph(contacto_text, styles['Normal'])],
            [Paragraph('<b>Dirección:</b>', styles['Normal']), Paragraph(item['direccion'], styles['Normal'])],
            [Paragraph('<b>Peso Total:</b>', styles['Normal']), Paragraph(f"<b>{item['peso_total_kg']} kg</b>", styles['Normal'])],
            [Paragraph('<b>Productos:</b>', styles['Normal']), Paragraph(productos_text, styles['Normal'])],
        ]
        
        item_table = Table(item_data, colWidths=[1.8*inch, 4.7*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ]))
        elements.append(item_table)
        
        # Alerta visual
        alert_style = ParagraphStyle(
            'Alert',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#dc2626'),
            backColor=colors.HexColor('#fef2f2'),
            borderColor=colors.HexColor('#fca5a5'),
            borderWidth=1,
            borderPadding=8,
            spaceAfter=0
        )
        elements.append(Paragraph(f"⚠️ <b>IMPORTANTE:</b> Cargar en posición {item['orden_carga']} (entregar en parada {item['orden_entrega']})", alert_style))
        elements.append(Spacer(1, 0.25*inch))
    
    # Generar PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="plan_cargue_ruta_{ruta.id}.pdf"'
    return response

