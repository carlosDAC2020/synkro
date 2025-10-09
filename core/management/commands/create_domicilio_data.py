from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import (
    Sucursal, Repartidor, Cliente, Producto, Categoria, 
    Venta, VentaDetalle
)
from decimal import Decimal
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Crea datos de muestra para el módulo de domicilios'

    def handle(self, *args, **options):
        self.stdout.write('Creando datos de muestra para domicilios...')
        
        # Crear categorías si no existen
        categoria_electronica, _ = Categoria.objects.get_or_create(
            nombre='Electrónicos',
            defaults={'descripcion': 'Productos electrónicos y tecnología'}
        )
        
        categoria_hogar, _ = Categoria.objects.get_or_create(
            nombre='Hogar',
            defaults={'descripcion': 'Productos para el hogar'}
        )
        
        categoria_ropa, _ = Categoria.objects.get_or_create(
            nombre='Ropa',
            defaults={'descripcion': 'Ropa y accesorios'}
        )

        # Crear productos de muestra
        productos_data = [
            {'nombre': 'Laptop HP Pavilion', 'sku': 'LAP001', 'categoria': categoria_electronica, 'precio': 2500000, 'costo': 1800000, 'stock': 15},
            {'nombre': 'Mouse Logitech', 'sku': 'MOU001', 'categoria': categoria_electronica, 'precio': 85000, 'costo': 50000, 'stock': 50},
            {'nombre': 'Teclado Mecánico', 'sku': 'TEC001', 'categoria': categoria_electronica, 'precio': 120000, 'costo': 70000, 'stock': 30},
            {'nombre': 'Monitor Samsung 24"', 'sku': 'MON001', 'categoria': categoria_electronica, 'precio': 800000, 'costo': 550000, 'stock': 20},
            {'nombre': 'Silla de Oficina', 'sku': 'SIL001', 'categoria': categoria_hogar, 'precio': 450000, 'costo': 280000, 'stock': 25},
            {'nombre': 'Escritorio de Madera', 'sku': 'ESC001', 'categoria': categoria_hogar, 'precio': 600000, 'costo': 350000, 'stock': 12},
            {'nombre': 'Camiseta Básica', 'sku': 'CAM001', 'categoria': categoria_ropa, 'precio': 35000, 'costo': 20000, 'stock': 100},
            {'nombre': 'Pantalón Jeans', 'sku': 'PAN001', 'categoria': categoria_ropa, 'precio': 120000, 'costo': 70000, 'stock': 80},
        ]

        productos = []
        for prod_data in productos_data:
            producto, created = Producto.objects.get_or_create(
                sku=prod_data['sku'],
                defaults={
                    'nombre': prod_data['nombre'],
                    'categoria': prod_data['categoria'],
                    'precio_venta': prod_data['precio'],
                    'costo_unitario': prod_data['costo'],
                    'stock_actual': prod_data['stock'],
                    'stock_minimo': 5
                }
            )
            productos.append(producto)
            if created:
                self.stdout.write(f'  ✓ Producto creado: {producto.nombre}')

        # Usar sucursales existentes o crear nuevas
        sucursales = []
        
        # Buscar sucursales existentes
        try:
            sucursal_centro = Sucursal.objects.get(codigo='SUC001')
            self.stdout.write(f'  → Usando sucursal existente: {sucursal_centro.nombre}')
        except Sucursal.DoesNotExist:
            sucursal_centro = Sucursal.objects.create(
                nombre='Sucursal Centro',
                codigo='SUC001',
                direccion='Calle 72 #45-23, Centro, Barranquilla',
                latitud=10.9685,
                longitud=-74.7813,
                telefono='3001234567',
                email='centro@synkro.com',
                es_principal=True,
                radio_cobertura_km=15.0
            )
            self.stdout.write(f'  ✓ Sucursal creada: {sucursal_centro.nombre}')
        sucursales.append(sucursal_centro)
        
        try:
            sucursal_norte = Sucursal.objects.get(codigo='SUC002')
            self.stdout.write(f'  → Usando sucursal existente: {sucursal_norte.nombre}')
        except Sucursal.DoesNotExist:
            sucursal_norte = Sucursal.objects.create(
                nombre='Sucursal Norte',
                codigo='SUC002',
                direccion='Carrera 50 #80-15, Norte, Barranquilla',
                latitud=11.0185,
                longitud=-74.8013,
                telefono='3001234568',
                email='norte@synkro.com',
                es_principal=False,
                radio_cobertura_km=12.0
            )
            self.stdout.write(f'  ✓ Sucursal creada: {sucursal_norte.nombre}')
        sucursales.append(sucursal_norte)
        
        try:
            sucursal_sur = Sucursal.objects.get(codigo='SUC003')
            self.stdout.write(f'  → Usando sucursal existente: {sucursal_sur.nombre}')
        except Sucursal.DoesNotExist:
            sucursal_sur = Sucursal.objects.create(
                nombre='Sucursal Sur',
                codigo='SUC003',
                direccion='Calle 85 #52-30, Sur, Barranquilla',
                latitud=10.9185,
                longitud=-74.7613,
                telefono='3001234569',
                email='sur@synkro.com',
                es_principal=False,
                radio_cobertura_km=10.0
            )
            self.stdout.write(f'  ✓ Sucursal creada: {sucursal_sur.nombre}')
        sucursales.append(sucursal_sur)

        # Crear repartidores
        repartidores_data = [
            {'nombre': 'Luis Gómez', 'telefono': '3001111111', 'documento': '12345678'},
            {'nombre': 'Ana Silva', 'telefono': '3002222222', 'documento': '87654321'},
            {'nombre': 'Carlos Ruiz', 'telefono': '3003333333', 'documento': '11223344'},
            {'nombre': 'María Torres', 'telefono': '3004444444', 'documento': '44332211'},
        ]

        repartidores = []
        for rep_data in repartidores_data:
            try:
                repartidor = Repartidor.objects.get(documento=rep_data['documento'])
                self.stdout.write(f'  → Repartidor ya existe: {repartidor.nombre}')
            except Repartidor.DoesNotExist:
                repartidor = Repartidor.objects.create(**rep_data)
                self.stdout.write(f'  ✓ Repartidor creado: {repartidor.nombre}')
            repartidores.append(repartidor)

        # Crear clientes
        clientes_data = [
            {'nombre': 'Juan Pérez', 'telefono': '3005555555', 'email': 'juan@email.com', 'direccion': 'Calle 72 #45-23'},
            {'nombre': 'María García', 'telefono': '3006666666', 'email': 'maria@email.com', 'direccion': 'Carrera 50 #80-15'},
            {'nombre': 'Carlos López', 'telefono': '3007777777', 'email': 'carlos@email.com', 'direccion': 'Calle 85 #52-30'},
            {'nombre': 'Ana Martínez', 'telefono': '3008888888', 'email': 'ana@email.com', 'direccion': 'Carrera 43 #70-10'},
            {'nombre': 'Pedro Rodríguez', 'telefono': '3009999999', 'email': 'pedro@email.com', 'direccion': 'Calle 76 #48-20'},
            {'nombre': 'Laura Jiménez', 'telefono': '3001010101', 'email': 'laura@email.com', 'direccion': 'Carrera 60 #90-25'},
            {'nombre': 'Diego Herrera', 'telefono': '3002020202', 'email': 'diego@email.com', 'direccion': 'Calle 100 #15-40'},
            {'nombre': 'Sofía Vargas', 'telefono': '3003030303', 'email': 'sofia@email.com', 'direccion': 'Carrera 30 #45-60'},
        ]

        clientes = []
        for cli_data in clientes_data:
            try:
                cliente = Cliente.objects.get(email=cli_data['email'])
                self.stdout.write(f'  → Cliente ya existe: {cliente.nombre}')
            except Cliente.DoesNotExist:
                cliente = Cliente.objects.create(**cli_data)
                self.stdout.write(f'  ✓ Cliente creado: {cliente.nombre}')
            clientes.append(cliente)

        # Obtener usuario admin
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = User.objects.create_user(
                    username='admin',
                    email='admin@synkro.com',
                    password='admin123',
                    is_superuser=True,
                    is_staff=True
                )
        except:
            admin_user = User.objects.first()

        # Crear ventas con domicilio
        direcciones_entrega = [
            {'direccion': 'Calle 72 #45-23, Centro', 'lat': 10.9785, 'lng': -74.7913},
            {'direccion': 'Carrera 50 #80-15, Norte', 'lat': 10.9885, 'lng': -74.8013},
            {'direccion': 'Calle 85 #52-30, Sur', 'lat': 10.9985, 'lng': -74.7713},
            {'direccion': 'Carrera 43 #70-10, Centro', 'lat': 10.9585, 'lng': -74.7813},
            {'direccion': 'Calle 76 #48-20, Norte', 'lat': 10.9685, 'lng': -74.7913},
            {'direccion': 'Carrera 60 #90-25, Sur', 'lat': 10.9385, 'lng': -74.7513},
            {'direccion': 'Calle 100 #15-40, Centro', 'lat': 10.9885, 'lng': -74.7713},
            {'direccion': 'Carrera 30 #45-60, Norte', 'lat': 11.0085, 'lng': -74.8113},
        ]

        prioridades = ['alta', 'media', 'baja']
        
        # Crear ventas pendientes de entrega
        for i in range(8):
            cliente = random.choice(clientes)
            direccion = direcciones_entrega[i]
            prioridad = random.choice(prioridades)
            
            # Crear venta
            venta = Venta.objects.create(
                cliente=cliente,
                usuario=admin_user,
                estado='COMPLETADA',
                requiere_domicilio=True,
                direccion_entrega=direccion['direccion'],
                latitud_entrega=direccion['lat'],
                longitud_entrega=direccion['lng'],
                prioridad_entrega=prioridad
            )
            
            # Agregar productos a la venta
            num_productos = random.randint(1, 3)
            productos_venta = random.sample(productos, num_productos)
            
            for producto in productos_venta:
                cantidad = random.randint(1, 2)
                VentaDetalle.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario_venta=producto.precio_venta
                )
            
            # Calcular total
            total = sum(d.cantidad * d.precio_unitario_venta for d in venta.detalles.all())
            venta.monto_total = total
            venta.save()
            
            self.stdout.write(f'  ✓ Venta creada: #{venta.id} - {cliente.nombre} - ${total:,.0f}')

        self.stdout.write(
            self.style.SUCCESS(
                '\n✅ Datos de muestra creados exitosamente!\n'
                'Ahora puedes probar el módulo de domicilios con:\n'
                '- 3 sucursales\n'
                '- 4 repartidores\n'
                '- 8 clientes\n'
                '- 8 productos\n'
                '- 8 ventas pendientes de entrega\n\n'
                'Accede a: /domicilios/planificar-rutas/'
            )
        )
