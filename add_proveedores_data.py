#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synkro.settings')
django.setup()

from core.models import Proveedor, PedidoProveedor, PedidoDetalle, Producto

def crear_proveedores():
    """Crear proveedores de ejemplo"""
    proveedores_data = [
        {
            'nombre': 'TechSupply S.A.',
            'contacto': 'María González',
            'telefono': '+52 55 1234-5678',
            'email': 'ventas@techsupply.com'
        },
        {
            'nombre': 'ElectroDistribuidora',
            'contacto': 'Carlos Ramírez',
            'telefono': '+52 33 9876-5432',
            'email': 'pedidos@electrodist.mx'
        },
        {
            'nombre': 'AudioPro Internacional',
            'contacto': 'Ana Martínez',
            'telefono': '+52 81 5555-1234',
            'email': 'contacto@audiopro.com'
        },
        {
            'nombre': 'Componentes Electrónicos del Norte',
            'contacto': 'Roberto Silva',
            'telefono': '+52 55 7777-8888',
            'email': 'compras@cen.com.mx'
        }
    ]
    
    for data in proveedores_data:
        proveedor, created = Proveedor.objects.get_or_create(
            nombre=data['nombre'],
            defaults=data
        )
        if created:
            print(f"✅ Proveedor creado: {proveedor.nombre}")
        else:
            print(f"ℹ️  Proveedor ya existe: {proveedor.nombre}")

def crear_pedidos_ejemplo():
    """Crear algunos pedidos de ejemplo"""
    try:
        # Obtener algunos productos y proveedores
        productos = list(Producto.objects.all()[:3])
        proveedores = list(Proveedor.objects.all()[:2])
        
        if not productos or not proveedores:
            print("⚠️  Necesitas tener productos y proveedores para crear pedidos")
            return
        
        # Crear pedido pendiente
        pedido1 = PedidoProveedor.objects.create(
            proveedor=proveedores[0],
            estado='PENDIENTE'
        )
        
        # Agregar detalles al pedido
        PedidoDetalle.objects.create(
            pedido=pedido1,
            producto=productos[0],
            cantidad=50,
            costo_unitario_compra=250.00
        )
        
        if len(productos) > 1:
            PedidoDetalle.objects.create(
                pedido=pedido1,
                producto=productos[1],
                cantidad=25,
                costo_unitario_compra=180.00
            )
        
        # Recalcular total
        total = sum(d.cantidad * d.costo_unitario_compra for d in pedido1.detalles_pedido.all())
        pedido1.costo_total = total
        pedido1.save()
        
        print(f"✅ Pedido creado: #{pedido1.id} - ${pedido1.costo_total}")
        
        # Crear otro pedido ya recibido
        if len(proveedores) > 1:
            pedido2 = PedidoProveedor.objects.create(
                proveedor=proveedores[1],
                estado='RECIBIDO'
            )
            
            if len(productos) > 2:
                PedidoDetalle.objects.create(
                    pedido=pedido2,
                    producto=productos[2],
                    cantidad=30,
                    costo_unitario_compra=320.00
                )
                
                total2 = sum(d.cantidad * d.costo_unitario_compra for d in pedido2.detalles_pedido.all())
                pedido2.costo_total = total2
                pedido2.save()
                
                print(f"✅ Pedido recibido creado: #{pedido2.id} - ${pedido2.costo_total}")
        
    except Exception as e:
        print(f"❌ Error creando pedidos: {e}")

if __name__ == '__main__':
    print("🚀 Creando datos de proveedores y pedidos...")
    crear_proveedores()
    crear_pedidos_ejemplo()
    print("✅ ¡Datos creados exitosamente!")
