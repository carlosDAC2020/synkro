from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, F

from .models import Cliente, Producto, Categoria, Venta, VentaDetalle, Proveedor, PedidoProveedor, PedidoDetalle, PagoProveedor
from .forms import ClienteForm, ProductoForm, VentaForm, VentaDetalleFormSet, ProveedorForm, PedidoProveedorForm, PedidoDetalleFormSet, PagoProveedorForm

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
