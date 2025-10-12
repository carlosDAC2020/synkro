from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, F

from .models import Cliente, Producto, Categoria, Venta, VentaDetalle, Proveedor, PedidoProveedor, PedidoDetalle, PagoProveedor, NotaEntregaVenta, DetalleNotaEntrega, Sucursal, Repartidor, RutaEntrega, DetalleRuta
from .forms import ClienteForm, ProductoForm, VentaForm, VentaDetalleFormSet, ProveedorForm, PedidoProveedorForm, PedidoDetalleFormSet, PagoProveedorForm, NotaEntregaVentaForm, DetalleNotaEntregaFormSet, SucursalForm, RepartidorForm, RutaEntregaForm

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
    venta = get_object_or_404(Venta, pk=pk)
    detalles = venta.detalles.select_related('producto')
    return render(request, 'ventas/detail.html', {
        'venta': venta,
        'detalles': detalles,
    })

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
    ventas_pendientes = Venta.objects.filter(
        requiere_domicilio=True,
        estado='PAGADA_PENDIENTE_ENTREGA'
    ).exclude(
        id__in=DetalleRuta.objects.values_list('venta_id', flat=True)
    ).select_related('cliente')
    
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
    ventas = Venta.objects.filter(
        requiere_domicilio=True,
        estado='PAGADA_PENDIENTE_ENTREGA'
    ).exclude(
        id__in=DetalleRuta.objects.values_list('venta_id', flat=True)
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
            'productos': productos_list
        })
    
    return JsonResponse({'ventas': data})

@login_required
def api_calcular_ruta_optima(request):
    """API: Calcular ruta óptima con tráfico usando OSRM"""
    import requests
    import json as json_module
    from decimal import Decimal
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json_module.loads(request.body)
        sucursal_id = data.get('sucursal_id')
        ventas_ids = data.get('ventas_ids', [])
        
        if not sucursal_id or not ventas_ids:
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        # Obtener coordenadas
        sucursal = Sucursal.objects.get(id=sucursal_id)
        ventas = Venta.objects.filter(id__in=ventas_ids).prefetch_related('detalles__producto')
        
        # Construir waypoints
        waypoints = [[float(sucursal.latitud), float(sucursal.longitud)]]
        ventas_ordenadas = []
        
        for v in ventas:
            if v.latitud_entrega and v.longitud_entrega:
                waypoints.append([float(v.latitud_entrega), float(v.longitud_entrega)])
                ventas_ordenadas.append(v)
        
        # Llamar a OSRM para calcular ruta
        coords_str = ';'.join([f"{w[1]},{w[0]}" for w in waypoints])
        url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'true',
            'annotations': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        osrm_data = response.json()
        
        if osrm_data.get('code') != 'Ok':
            return JsonResponse({'error': 'No se pudo calcular la ruta'}, status=400)
        
        route = osrm_data['routes'][0]
        
        # Generar plan de cargue LIFO
        plan_cargue = []
        orden_entrega = list(range(1, len(ventas_ordenadas) + 1))
        orden_carga = list(reversed(orden_entrega))
        
        for idx, venta in enumerate(ventas_ordenadas):
            peso_total = 0
            volumen_total = 0
            productos_list = []
            
            for detalle in venta.detalles.all():
                peso = float(detalle.producto.peso_kg) * detalle.cantidad if detalle.producto.peso_kg else 0
                volumen = float(detalle.producto.volumen_m3) * detalle.cantidad if detalle.producto.volumen_m3 else 0
                peso_total += peso
                volumen_total += volumen
                
                productos_list.append({
                    'nombre': detalle.producto.nombre,
                    'cantidad': detalle.cantidad,
                    'peso_kg': round(peso, 2),
                    'volumen_m3': round(volumen, 3)
                })
            
            plan_cargue.append({
                'venta_id': venta.id,
                'orden_carga': orden_carga[idx],
                'orden_entrega': orden_entrega[idx],
                'cliente': venta.cliente.nombre if venta.cliente else 'Sin cliente',
                'direccion': venta.direccion_entrega,
                'productos': productos_list,
                'peso_total_kg': round(peso_total, 2),
                'volumen_total_m3': round(volumen_total, 3),
                'instruccion': f"Cargar en posición {orden_carga[idx]} (entregar en parada {orden_entrega[idx]})"
            })
        
        # Calcular totales
        peso_total_ruta = sum(item['peso_total_kg'] for item in plan_cargue)
        volumen_total_ruta = sum(item['volumen_total_m3'] for item in plan_cargue)
        
        return JsonResponse({
            'success': True,
            'ruta': {
                'distancia_km': round(route['distance'] / 1000, 2),
                'tiempo_min': round(route['duration'] / 60),
                'geometria': route['geometry'],
                'waypoints': waypoints,
                'trafico': route.get('annotations', {})
            },
            'plan_cargue': plan_cargue,
            'peso_total_kg': round(peso_total_ruta, 2),
            'volumen_total_m3': round(volumen_total_ruta, 3),
            'numero_paradas': len(ventas_ordenadas)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
    """Descargar plan de cargue en PDF"""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from django.http import HttpResponse
    from io import BytesIO
    
    ruta = get_object_or_404(RutaEntrega, id=ruta_id)
    
    # Crear el PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=1  # Center
    )
    elements.append(Paragraph(f"Plan de Cargue - Ruta #{ruta.id}", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Información general
    info_data = [
        ['Sucursal:', ruta.sucursal_origen.nombre],
        ['Repartidor:', ruta.repartidor.nombre if ruta.repartidor else 'No asignado'],
        ['Fecha:', str(ruta.fecha_entrega)],
        ['Distancia:', f"{ruta.distancia_total_km} km"],
        ['Tiempo estimado:', f"{ruta.tiempo_estimado_min} min"],
        ['Peso total:', f"{ruta.peso_total_kg} kg"],
        ['Paradas:', str(ruta.numero_paradas)]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Plan de cargue
    elements.append(Paragraph("ORDEN DE CARGA (LIFO - Último en cargar, primero en entregar)", styles['Heading2']))
    elements.append(Spacer(1, 0.2*inch))
    
    for item in ruta.plan_cargue:
        # Encabezado de cada item
        item_title = f"Posición {item['orden_carga']} - Parada {item['orden_entrega']}: {item['cliente']}"
        elements.append(Paragraph(item_title, styles['Heading3']))
        
        # Detalles
        item_data = [
            ['Dirección:', item['direccion']],
            ['Peso:', f"{item['peso_total_kg']} kg"],
            ['Productos:', ', '.join([f"{p['cantidad']}x {p['nombre']}" for p in item['productos']])]
        ]
        
        item_table = Table(item_data, colWidths=[1.5*inch, 4.5*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 0.15*inch))
    
    # Generar PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="plan_cargue_ruta_{ruta.id}.pdf"'
    return response

