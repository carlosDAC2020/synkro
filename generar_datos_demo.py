import os
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import (
    Categoria, Producto, Cliente, Proveedor, Venta, VentaDetalle,
    PedidoProveedor, PedidoDetalle, Sucursal, Repartidor
)
from django.contrib.auth import get_user_model

User = get_user_model()

print("🚀 Generando datos de DEMO completos...")
print("=" * 60)

# Verificar que hay usuarios
usuario = User.objects.first()
if not usuario:
    print("❌ No hay usuarios en el sistema. Crea uno primero con 'python manage.py createsuperuser'")
    exit()

# === 1. CATEGORÍAS ===
print("\n📁 Creando categorías...")
categorias_data = [
    {'nombre': 'Alimentos', 'descripcion': 'Productos alimenticios'},
    {'nombre': 'Bebidas', 'descripcion': 'Bebidas y refrescos'},
    {'nombre': 'Aseo', 'descripcion': 'Productos de aseo y limpieza'},
    {'nombre': 'Cuidado Personal', 'descripcion': 'Productos de higiene personal'},
    {'nombre': 'Snacks', 'descripcion': 'Snacks y golosinas'},
]

categorias = {}
for cat_data in categorias_data:
    cat, created = Categoria.objects.get_or_create(
        nombre=cat_data['nombre'],
        defaults={'descripcion': cat_data['descripcion']}
    )
    categorias[cat.nombre] = cat
    print(f"  {'✅' if created else 'ℹ️ '} {cat.nombre}")

# === 2. PRODUCTOS ===
print("\n📦 Creando productos...")
productos_data = [
    # Alimentos
    {'nombre': 'Arroz Diana 500g', 'sku': 'ALI001', 'categoria': 'Alimentos', 'precio': 2500, 'costo': 1800, 'stock': 50, 'peso': 0.5, 'volumen': 0.001},
    {'nombre': 'Aceite Girasol 1L', 'sku': 'ALI002', 'categoria': 'Alimentos', 'precio': 8500, 'costo': 6000, 'stock': 30, 'peso': 0.92, 'volumen': 0.001},
    {'nombre': 'Azúcar 1kg', 'sku': 'ALI003', 'categoria': 'Alimentos', 'precio': 3200, 'costo': 2200, 'stock': 40, 'peso': 1.0, 'volumen': 0.0015},
    {'nombre': 'Sal 500g', 'sku': 'ALI004', 'categoria': 'Alimentos', 'precio': 1500, 'costo': 900, 'stock': 60, 'peso': 0.5, 'volumen': 0.0008},
    {'nombre': 'Pasta Spaghetti 500g', 'sku': 'ALI005', 'categoria': 'Alimentos', 'precio': 3500, 'costo': 2400, 'stock': 45, 'peso': 0.5, 'volumen': 0.002},
    
    # Bebidas
    {'nombre': 'Coca-Cola 2L', 'sku': 'BEB001', 'categoria': 'Bebidas', 'precio': 5500, 'costo': 3800, 'stock': 80, 'peso': 2.1, 'volumen': 0.002},
    {'nombre': 'Agua Cristal 600ml', 'sku': 'BEB002', 'categoria': 'Bebidas', 'precio': 1800, 'costo': 1200, 'stock': 100, 'peso': 0.6, 'volumen': 0.0006},
    {'nombre': 'Jugo Hit 1L', 'sku': 'BEB003', 'categoria': 'Bebidas', 'precio': 4200, 'costo': 2900, 'stock': 50, 'peso': 1.05, 'volumen': 0.001},
    {'nombre': 'Cerveza Águila 330ml', 'sku': 'BEB004', 'categoria': 'Bebidas', 'precio': 2500, 'costo': 1700, 'stock': 120, 'peso': 0.35, 'volumen': 0.00033},
    
    # Aseo
    {'nombre': 'Detergente Ariel 1kg', 'sku': 'ASE001', 'categoria': 'Aseo', 'precio': 12000, 'costo': 8500, 'stock': 25, 'peso': 1.0, 'volumen': 0.0015},
    {'nombre': 'Jabón Rey 300g', 'sku': 'ASE002', 'categoria': 'Aseo', 'precio': 3500, 'costo': 2400, 'stock': 40, 'peso': 0.3, 'volumen': 0.0005},
    {'nombre': 'Cloro Varela 1L', 'sku': 'ASE003', 'categoria': 'Aseo', 'precio': 4500, 'costo': 3000, 'stock': 35, 'peso': 1.1, 'volumen': 0.001},
    
    # Cuidado Personal
    {'nombre': 'Shampoo Head & Shoulders 400ml', 'sku': 'PER001', 'categoria': 'Cuidado Personal', 'precio': 18000, 'costo': 13000, 'stock': 30, 'peso': 0.42, 'volumen': 0.0004},
    {'nombre': 'Jabón Protex 120g', 'sku': 'PER002', 'categoria': 'Cuidado Personal', 'precio': 3800, 'costo': 2600, 'stock': 50, 'peso': 0.12, 'volumen': 0.0002},
    {'nombre': 'Papel Higiénico Familia x4', 'sku': 'PER003', 'categoria': 'Cuidado Personal', 'precio': 8500, 'costo': 6000, 'stock': 40, 'peso': 0.4, 'volumen': 0.003},
    
    # Snacks
    {'nombre': 'Papas Margarita 150g', 'sku': 'SNK001', 'categoria': 'Snacks', 'precio': 3500, 'costo': 2300, 'stock': 60, 'peso': 0.15, 'volumen': 0.0008},
    {'nombre': 'Galletas Oreo 432g', 'sku': 'SNK002', 'categoria': 'Snacks', 'precio': 8900, 'costo': 6200, 'stock': 35, 'peso': 0.43, 'volumen': 0.0012},
    {'nombre': 'Chocolatina Jet 50g', 'sku': 'SNK003', 'categoria': 'Snacks', 'precio': 2200, 'costo': 1500, 'stock': 80, 'peso': 0.05, 'volumen': 0.0001},
]

productos = {}
for prod_data in productos_data:
    prod, created = Producto.objects.get_or_create(
        sku=prod_data['sku'],
        defaults={
            'nombre': prod_data['nombre'],
            'categoria': categorias[prod_data['categoria']],
            'precio_venta': Decimal(str(prod_data['precio'])),
            'costo_unitario': Decimal(str(prod_data['costo'])),
            'stock_actual': prod_data['stock'],
            'stock_minimo': 10,
            'peso_kg': Decimal(str(prod_data['peso'])),
            'volumen_m3': Decimal(str(prod_data['volumen']))
        }
    )
    productos[prod.sku] = prod
    print(f"  {'✅' if created else 'ℹ️ '} {prod.nombre}")

# === 3. SUCURSALES ===
print("\n🏢 Creando sucursales...")
sucursales_data = [
    {'nombre': 'Sucursal Centro', 'codigo': 'SUC001', 'direccion': 'Calle 72 #45-23, Barranquilla', 
     'latitud': Decimal('10.9685'), 'longitud': Decimal('-74.7813'), 'es_principal': True, 
     'telefono': '3001234567', 'radio_cobertura_km': Decimal('10.0')},
    {'nombre': 'Sucursal Norte', 'codigo': 'SUC002', 'direccion': 'Calle 98 #50-10, Barranquilla',
     'latitud': Decimal('11.0185'), 'longitud': Decimal('-74.8013'), 'es_principal': False,
     'telefono': '3009876543', 'radio_cobertura_km': Decimal('8.0')},
    {'nombre': 'Sucursal Sur', 'codigo': 'SUC003', 'direccion': 'Calle 30 #40-15, Barranquilla',
     'latitud': Decimal('10.9185'), 'longitud': Decimal('-74.7613'), 'es_principal': False,
     'telefono': '3005555555', 'radio_cobertura_km': Decimal('8.0')},
]

sucursales = {}
for suc_data in sucursales_data:
    suc, created = Sucursal.objects.get_or_create(
        codigo=suc_data['codigo'],
        defaults=suc_data
    )
    sucursales[suc.codigo] = suc
    print(f"  {'✅' if created else 'ℹ️ '} {suc.nombre}")

# === 4. REPARTIDORES ===
print("\n🏍️  Creando repartidores...")
repartidores_data = [
    {'nombre': 'Carlos Rodríguez', 'telefono': '3001234567', 'documento': '1234567890'},
    {'nombre': 'María González', 'telefono': '3009876543', 'documento': '0987654321'},
    {'nombre': 'Luis Martínez', 'telefono': '3005555555', 'documento': '5555555555'},
    {'nombre': 'Ana López', 'telefono': '3007777777', 'documento': '7777777777'},
]

repartidores = {}
for rep_data in repartidores_data:
    rep, created = Repartidor.objects.get_or_create(
        documento=rep_data['documento'],
        defaults=rep_data
    )
    repartidores[rep.documento] = rep
    print(f"  {'✅' if created else 'ℹ️ '} {rep.nombre}")

# === 5. CLIENTES ===
print("\n👥 Creando clientes...")
clientes_data = [
    {'nombre': 'Juan Pérez', 'telefono': '3001111111', 'email': 'juan@example.com', 'direccion': 'Calle 85 #52-30'},
    {'nombre': 'Ana Martínez', 'telefono': '3002222222', 'email': 'ana.m@example.com', 'direccion': 'Carrera 43 #70-10'},
    {'nombre': 'Pedro López', 'telefono': '3003333333', 'email': 'pedro@example.com', 'direccion': 'Calle 76 #48-20'},
    {'nombre': 'Laura Silva', 'telefono': '3004444444', 'email': 'laura@example.com', 'direccion': 'Carrera 50 #80-15'},
    {'nombre': 'Diego Ramírez', 'telefono': '3005555555', 'email': 'diego@example.com', 'direccion': 'Calle 90 #55-25'},
    {'nombre': 'Sofía Torres', 'telefono': '3006666666', 'email': 'sofia@example.com', 'direccion': 'Calle 68 #42-18'},
    {'nombre': 'Miguel Ángel Castro', 'telefono': '3007777777', 'email': 'miguel@example.com', 'direccion': 'Carrera 38 #75-22'},
    {'nombre': 'Valentina Ruiz', 'telefono': '3008888888', 'email': 'valentina@example.com', 'direccion': 'Calle 82 #50-35'},
    {'nombre': 'Andrés Moreno', 'telefono': '3009999999', 'email': 'andres@example.com', 'direccion': 'Carrera 45 #88-12'},
    {'nombre': 'Camila Vargas', 'telefono': '3000000000', 'email': 'camila@example.com', 'direccion': 'Calle 95 #58-40'},
]

clientes = []
for cli_data in clientes_data:
    cli = Cliente.objects.filter(nombre=cli_data['nombre']).first()
    if not cli:
        cli = Cliente.objects.create(**cli_data)
        print(f"  ✅ {cli.nombre}")
    else:
        print(f"  ℹ️  {cli.nombre}")
    clientes.append(cli)

# === 6. PROVEEDORES ===
print("\n🏭 Creando proveedores...")
proveedores_data = [
    {'nombre': 'Distribuidora La Costa', 'contacto': 'Roberto Gómez', 'telefono': '3101234567', 
     'email': 'ventas@lacosta.com', 'direccion': 'Calle 30 #20-15'},
    {'nombre': 'Alimentos del Caribe', 'contacto': 'Patricia Ruiz', 'telefono': '3109876543',
     'email': 'info@alimentoscaribe.com', 'direccion': 'Carrera 38 #45-22'},
    {'nombre': 'Bebidas y Más', 'contacto': 'Carlos Mendoza', 'telefono': '3105555555',
     'email': 'pedidos@bebidasmas.com', 'direccion': 'Calle 72 #30-18'},
]

proveedores = []
for prov_data in proveedores_data:
    prov, created = Proveedor.objects.get_or_create(
        nombre=prov_data['nombre'],
        defaults=prov_data
    )
    proveedores.append(prov)
    print(f"  {'✅' if created else 'ℹ️ '} {prov.nombre}")

# === 7. VENTAS COMPLETADAS (sin domicilio) ===
print("\n💰 Creando ventas completadas (sin domicilio)...")
for i in range(15):
    cliente = random.choice(clientes)
    fecha = datetime.now() - timedelta(days=random.randint(1, 30))
    
    venta = Venta.objects.create(
        cliente=cliente,
        usuario=usuario,
        estado='COMPLETADA',
        requiere_domicilio=False,
        fecha=fecha
    )
    
    # Agregar 2-5 productos aleatorios
    num_productos = random.randint(2, 5)
    productos_seleccionados = random.sample(list(productos.values()), num_productos)
    
    monto_total = Decimal('0')
    for producto in productos_seleccionados:
        cantidad = random.randint(1, 5)
        detalle = VentaDetalle.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario_venta=producto.precio_venta
        )
        monto_total += producto.precio_venta * cantidad
    
    venta.monto_total = monto_total
    venta.save()
    
    print(f"  ✅ Venta #{venta.id} - {cliente.nombre} - ${monto_total:,.0f}")

# === 8. VENTAS PENDIENTES DE DOMICILIO ===
print("\n🚚 Creando ventas pendientes de domicilio...")
coordenadas_barranquilla = [
    {'lat': Decimal('10.9985'), 'lng': Decimal('-74.7713'), 'dir': 'Calle 85 #52-30, Barranquilla'},
    {'lat': Decimal('10.9585'), 'lng': Decimal('-74.7813'), 'dir': 'Carrera 43 #70-10, Barranquilla'},
    {'lat': Decimal('10.9685'), 'lng': Decimal('-74.7913'), 'dir': 'Calle 76 #48-20, Barranquilla'},
    {'lat': Decimal('10.9885'), 'lng': Decimal('-74.8013'), 'dir': 'Carrera 50 #80-15, Barranquilla'},
    {'lat': Decimal('10.9785'), 'lng': Decimal('-74.7913'), 'dir': 'Calle 90 #55-25, Barranquilla'},
    {'lat': Decimal('10.9485'), 'lng': Decimal('-74.7713'), 'dir': 'Calle 68 #42-18, Barranquilla'},
    {'lat': Decimal('10.9885'), 'lng': Decimal('-74.7613'), 'dir': 'Carrera 38 #75-22, Barranquilla'},
    {'lat': Decimal('11.0085'), 'lng': Decimal('-74.7913'), 'dir': 'Calle 82 #50-35, Barranquilla'},
    {'lat': Decimal('10.9585'), 'lng': Decimal('-74.8113'), 'dir': 'Carrera 45 #88-12, Barranquilla'},
    {'lat': Decimal('11.0185'), 'lng': Decimal('-74.7813'), 'dir': 'Calle 95 #58-40, Barranquilla'},
]

prioridades = ['alta', 'media', 'baja']

for i, coord in enumerate(coordenadas_barranquilla):
    cliente = clientes[i]
    
    venta = Venta.objects.create(
        cliente=cliente,
        usuario=usuario,
        estado='PAGADA_PENDIENTE_ENTREGA',
        requiere_domicilio=True,
        direccion_entrega=coord['dir'],
        latitud_entrega=coord['lat'],
        longitud_entrega=coord['lng'],
        prioridad_entrega=random.choice(prioridades)
    )
    
    # Agregar 1-4 productos
    num_productos = random.randint(1, 4)
    productos_seleccionados = random.sample(list(productos.values()), num_productos)
    
    monto_total = Decimal('0')
    for producto in productos_seleccionados:
        cantidad = random.randint(1, 3)
        detalle = VentaDetalle.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario_venta=producto.precio_venta
        )
        monto_total += producto.precio_venta * cantidad
    
    venta.monto_total = monto_total
    venta.save()
    
    print(f"  ✅ Venta #{venta.id} - {cliente.nombre} - Prioridad: {venta.prioridad_entrega} - ${monto_total:,.0f}")

# === RESUMEN ===
print("\n" + "=" * 60)
print("✨ ¡Datos de DEMO generados exitosamente!")
print("\n📊 Resumen:")
print(f"  • Categorías: {Categoria.objects.count()}")
print(f"  • Productos: {Producto.objects.count()}")
print(f"  • Sucursales: {Sucursal.objects.count()}")
print(f"  • Repartidores: {Repartidor.objects.count()}")
print(f"  • Clientes: {Cliente.objects.count()}")
print(f"  • Proveedores: {Proveedor.objects.count()}")
print(f"  • Ventas completadas: {Venta.objects.filter(estado='COMPLETADA').count()}")
print(f"  • Ventas pendientes domicilio: {Venta.objects.filter(requiere_domicilio=True, estado='PAGADA_PENDIENTE_ENTREGA').count()}")
print("\n🎉 ¡Listo para hacer pruebas exhaustivas con el cliente!")
