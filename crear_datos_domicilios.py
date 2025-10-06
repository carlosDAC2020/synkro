import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Sucursal, Venta, Cliente, Producto, VentaDetalle, Repartidor
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

print("🚀 Creando datos de prueba para el módulo de domicilios...\n")

# 1. Crear Sucursales (si no existen)
print("📍 Creando sucursales...")
sucursales_data = [
    {'nombre': 'Sucursal Centro', 'codigo': 'SUC001', 'direccion': 'Calle 72 #45-23, Barranquilla', 
     'latitud': Decimal('10.9685'), 'longitud': Decimal('-74.7813'), 'es_principal': True},
    {'nombre': 'Sucursal Norte', 'codigo': 'SUC002', 'direccion': 'Calle 98 #50-10, Barranquilla',
     'latitud': Decimal('11.0185'), 'longitud': Decimal('-74.8013'), 'es_principal': False},
    {'nombre': 'Sucursal Sur', 'codigo': 'SUC003', 'direccion': 'Calle 30 #40-15, Barranquilla',
     'latitud': Decimal('10.9185'), 'longitud': Decimal('-74.7613'), 'es_principal': False},
]

for suc_data in sucursales_data:
    sucursal, created = Sucursal.objects.get_or_create(
        codigo=suc_data['codigo'],
        defaults=suc_data
    )
    if created:
        print(f"  ✅ {sucursal.nombre} creada")
    else:
        print(f"  ℹ️  {sucursal.nombre} ya existe")

# 2. Crear Repartidores
print("\n🏍️ Creando repartidores...")
repartidores_data = [
    {'nombre': 'Carlos Rodríguez', 'telefono': '3001234567', 'documento': '1234567890'},
    {'nombre': 'María González', 'telefono': '3009876543', 'documento': '0987654321'},
    {'nombre': 'Luis Martínez', 'telefono': '3005555555', 'documento': '5555555555'},
]

for rep_data in repartidores_data:
    repartidor, created = Repartidor.objects.get_or_create(
        documento=rep_data['documento'],
        defaults=rep_data
    )
    if created:
        print(f"  ✅ {repartidor.nombre} creado")
    else:
        print(f"  ℹ️  {repartidor.nombre} ya existe")

# 3. Crear Clientes y Ventas con Domicilio
print("\n🛒 Creando ventas con domicilio...")

# Obtener o crear usuario
usuario = User.objects.first()
if not usuario:
    print("  ⚠️  No hay usuarios. Crea uno primero.")
    exit()

# Obtener o crear producto
producto = Producto.objects.first()
if not producto:
    print("  ⚠️  No hay productos. Crea uno primero.")
    exit()

ventas_data = [
    {'cliente': 'Juan Pérez', 'direccion': 'Calle 85 #52-30, Barranquilla', 
     'lat': Decimal('10.9985'), 'lng': Decimal('-74.7713'), 'prioridad': 'alta'},
    {'cliente': 'Ana Martínez', 'direccion': 'Carrera 43 #70-10, Barranquilla',
     'lat': Decimal('10.9585'), 'lng': Decimal('-74.7813'), 'prioridad': 'media'},
    {'cliente': 'Pedro López', 'direccion': 'Calle 76 #48-20, Barranquilla',
     'lat': Decimal('10.9685'), 'lng': Decimal('-74.7913'), 'prioridad': 'alta'},
    {'cliente': 'Laura Silva', 'direccion': 'Carrera 50 #80-15, Barranquilla',
     'lat': Decimal('10.9885'), 'lng': Decimal('-74.8013'), 'prioridad': 'baja'},
    {'cliente': 'Diego Ramírez', 'direccion': 'Calle 90 #55-25, Barranquilla',
     'lat': Decimal('10.9785'), 'lng': Decimal('-74.7913'), 'prioridad': 'media'},
]

for venta_data in ventas_data:
    # Crear o obtener cliente
    cliente, _ = Cliente.objects.get_or_create(
        nombre=venta_data['cliente'],
        defaults={'telefono': '3001111111'}
    )
    
    # Crear venta
    venta = Venta.objects.create(
        cliente=cliente,
        usuario=usuario,
        estado='COMPLETADA',
        requiere_domicilio=True,
        direccion_entrega=venta_data['direccion'],
        latitud_entrega=venta_data['lat'],
        longitud_entrega=venta_data['lng'],
        prioridad_entrega=venta_data['prioridad']
    )
    
    # Agregar detalle
    VentaDetalle.objects.create(
        venta=venta,
        producto=producto,
        cantidad=1,
        precio_unitario_venta=producto.precio_venta
    )
    
    print(f"  ✅ Venta #{venta.id} para {cliente.nombre} - Prioridad: {venta_data['prioridad']}")

print("\n✨ ¡Datos de prueba creados exitosamente!")
print("\n📋 Resumen:")
print(f"  • Sucursales: {Sucursal.objects.count()}")
print(f"  • Repartidores: {Repartidor.objects.count()}")
print(f"  • Ventas con domicilio: {Venta.objects.filter(requiere_domicilio=True).count()}")
print("\n🚀 Ahora puedes ir a 'Domicilios > Planificar Rutas' para probar el sistema!")
