# core/management/commands/populate_db.py

import random
from datetime import timedelta
from faker import Faker
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal

from core.models import (
    Categoria, Producto, Cliente, Proveedor, Venta, VentaDetalle,
    PedidoProveedor, PedidoDetalle, PagoProveedor, NotaEntregaVenta,
    DetalleNotaEntrega, Sucursal, Repartidor, RutaEntrega, DetalleRuta
)

User = get_user_model()
fake = Faker('es_ES')

# --- CONSTANTES ---
HOY = timezone.make_aware(timezone.datetime(2026, 10, 25))
START_DATE = HOY - timedelta(days=180)

NUM_CLIENTES = 50
NUM_PROVEEDORES = 15
NUM_PRODUCTOS = 100
NUM_PEDIDOS = 30
NUM_VENTAS = 250
NUM_SUCURSALES = 3
NUM_REPARTIDORES = 5
NUM_RUTAS = 10

# 🆕 COORDENADAS REALISTAS DE BARRANQUILLA Y ALREDEDORES
ZONAS_BARRANQUILLA = [
    # Barranquilla Norte
    {'nombre': 'Alto Prado', 'lat_range': (11.010, 11.020), 'lng_range': (-74.820, -74.810)},
    {'nombre': 'Villa Country', 'lat_range': (11.000, 11.010), 'lng_range': (-74.825, -74.815)},
    {'nombre': 'El Prado', 'lat_range': (10.995, 11.005), 'lng_range': (-74.805, -74.795)},
    
    # Barranquilla Centro
    {'nombre': 'Centro', 'lat_range': (10.985, 10.995), 'lng_range': (-74.795, -74.785)},
    {'nombre': 'Boston', 'lat_range': (10.980, 10.990), 'lng_range': (-74.800, -74.790)},
    
    # Barranquilla Sur
    {'nombre': 'Soledad', 'lat_range': (10.915, 10.925), 'lng_range': (-74.775, -74.765)},
    {'nombre': 'Malambo', 'lat_range': (10.855, 10.865), 'lng_range': (-74.780, -74.770)},
    
    # Zona Metropolitana
    {'nombre': 'Puerto Colombia', 'lat_range': (10.985, 10.995), 'lng_range': (-74.960, -74.950)},
    {'nombre': 'Galapa', 'lat_range': (10.895, 10.905), 'lng_range': (-74.880, -74.870)},
    
    # Zonas adicionales
    {'nombre': 'Ciudadela 20 de Julio', 'lat_range': (10.965, 10.975), 'lng_range': (-74.785, -74.775)},
    {'nombre': 'Los Nogales', 'lat_range': (11.005, 11.015), 'lng_range': (-74.810, -74.800)},
    {'nombre': 'Recreo', 'lat_range': (10.970, 10.980), 'lng_range': (-74.795, -74.785)},
]


class Command(BaseCommand):
    help = 'Limpia y puebla la base de datos con datos de prueba realistas para Barranquilla.'

    def add_arguments(self, parser):
        parser.add_argument('--clean', action='store_true', help='Limpia la base de datos antes de poblarla.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clean']:
            self.limpiar_base_de_datos()

        self.stdout.write(self.style.SUCCESS('\n🚀 Iniciando población de la base de datos'))

        user = self.crear_usuarios()
        sucursales = self.crear_sucursales()
        repartidores = self.crear_repartidores()
        categorias = self.crear_categorias()
        productos = self.crear_productos(categorias)
        clientes = self.crear_clientes()
        proveedores = self.crear_proveedores()
        self.crear_pedidos_a_proveedores(proveedores, productos, user)
        ventas_para_domicilio = self.crear_ventas(clientes, productos, user)
        self.crear_notas_de_entrega(user)
        self.crear_rutas_de_entrega(ventas_para_domicilio, sucursales, repartidores)

        self.stdout.write(self.style.SUCCESS('\n✅ ¡Proceso completado exitosamente!'))
        self.stdout.write('Credenciales:')
        self.stdout.write(self.style.HTTP_INFO('  Admin     -> user: admin, pass: adminpass'))
        self.stdout.write(self.style.HTTP_INFO('  Vendedor  -> user: vendedor, pass: vendedorpass'))

    def limpiar_base_de_datos(self):
        self.stdout.write(self.style.WARNING('🧹 Limpiando base de datos...'))
        DetalleRuta.objects.all().delete()
        RutaEntrega.objects.all().delete()
        DetalleNotaEntrega.objects.all().delete()
        NotaEntregaVenta.objects.all().delete()
        VentaDetalle.objects.all().delete()
        Venta.objects.all().delete()
        PagoProveedor.objects.all().delete()
        PedidoDetalle.objects.all().delete()
        PedidoProveedor.objects.all().delete()
        Producto.objects.all().delete()
        Categoria.objects.all().delete()
        Cliente.objects.all().delete()
        Proveedor.objects.all().delete()
        Repartidor.objects.all().delete()
        Sucursal.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('✅ Base de datos limpiada'))

    def crear_usuarios(self):
        self.stdout.write('👤 Creando usuarios...')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
        
        user, created = User.objects.get_or_create(
            username='vendedor',
            defaults={'first_name': 'Juan', 'last_name': 'Ventas', 'email': 'vendedor@example.com', 'is_staff': True}
        )
        if created or not user.has_usable_password():
            user.set_password('vendedorpass')
            user.save()
        return user

    def obtener_coordenadas_aleatorias(self):
        """
        Genera coordenadas aleatorias dentro de una zona realista de Barranquilla.
        """
        zona = random.choice(ZONAS_BARRANQUILLA)
        lat = Decimal(str(random.uniform(*zona['lat_range'])))
        lng = Decimal(str(random.uniform(*zona['lng_range'])))
        return lat, lng, zona['nombre']

    def crear_sucursales(self):
        self.stdout.write('🏪 Creando sucursales...')
        sucursales_data = [
            {'nombre': 'Bodega Principal Zaragocilla', 'codigo': 'SUC-001', 'lat': 10.9089039, 'lng': -74.7824409, 'principal': True},
            {'nombre': 'Bodega Norte Riomar', 'codigo': 'SUC-002', 'lat': 11.0089, 'lng': -74.8100, 'principal': False},
            {'nombre': 'Bodega Sur Soledad', 'codigo': 'SUC-003', 'lat': 10.9200, 'lng': -74.7700, 'principal': False},
        ]
        
        sucursales = []
        for data in sucursales_data[:NUM_SUCURSALES]:
            sucursal = Sucursal.objects.create(
                nombre=data['nombre'],
                codigo=data['codigo'],
                direccion=fake.address(),
                ciudad="Barranquilla",
                latitud=Decimal(str(data['lat'])),
                longitud=Decimal(str(data['lng'])),
                es_principal=data['principal'],
                radio_cobertura_km=Decimal(random.choice([10, 15, 20]))
            )
            sucursales.append(sucursal)
        return sucursales

    def crear_repartidores(self):
        self.stdout.write('🚗 Creando repartidores...')
        return [
            Repartidor.objects.create(
                nombre=fake.name(),
                telefono=fake.phone_number(),
                documento=fake.unique.ssn(),
                capacidad_maxima_kg=Decimal(random.choice([500, 1000, 1500])),
                capacidad_maxima_m3=Decimal(random.choice([3, 5, 8]))
            ) for _ in range(NUM_REPARTIDORES)
        ]

    def crear_categorias(self):
        self.stdout.write('📦 Creando categorías...')
        nombres = ['Ferretería', 'Hogar', 'Tecnología', 'Jardinería', 'Construcción', 
                   'Pinturas', 'Electricidad', 'Plomería', 'Automotriz', 'Seguridad Industrial']
        return [Categoria.objects.create(nombre=nombre) for nombre in nombres]

    def crear_productos(self, categorias):
        self.stdout.write('🛒 Creando productos...')
        productos = []
        for i in range(NUM_PRODUCTOS):
            costo = Decimal(random.uniform(5.0, 800.0))
            producto = Producto.objects.create(
                nombre=f"Producto {fake.word().capitalize()} {i}",
                sku=f"SKU-{fake.unique.ean8()}",
                categoria=random.choice(categorias),
                descripcion=fake.text(max_nb_chars=150),
                stock_actual=random.randint(50, 300),
                stock_minimo=random.randint(10, 20),
                costo_unitario=costo,
                precio_venta=costo * Decimal(random.uniform(1.3, 2.1)),
                peso_kg=Decimal(random.uniform(0.1, 50.0)),
                volumen_m3=Decimal(random.uniform(0.001, 0.5))
            )
            productos.append(producto)
        return productos

    def crear_clientes(self):
        self.stdout.write('👥 Creando clientes...')
        return [
            Cliente.objects.create(
                nombre=fake.name(),
                telefono=fake.phone_number(),
                email=fake.unique.email(),
                direccion=fake.address()
            ) for _ in range(NUM_CLIENTES)
        ]

    def crear_proveedores(self):
        self.stdout.write('🏭 Creando proveedores...')
        return [
            Proveedor.objects.create(
                nombre=fake.company(),
                contacto=fake.name(),
                telefono=fake.phone_number(),
                email=fake.company_email()
            ) for _ in range(NUM_PROVEEDORES)
        ]

    def crear_pedidos_a_proveedores(self, proveedores, productos, user):
        self.stdout.write('📋 Creando pedidos a proveedores...')
        for _ in range(NUM_PEDIDOS):
            fecha_pedido = fake.date_time_between(
                start_date=START_DATE,
                end_date=HOY,
                tzinfo=timezone.get_current_timezone()
            )
            pedido = PedidoProveedor.objects.create(
                proveedor=random.choice(proveedores),
                fecha_pedido=fecha_pedido,
                estado='PENDIENTE'
            )
            
            productos_en_pedido = random.sample(productos, k=random.randint(2, 8))
            for producto in productos_en_pedido:
                PedidoDetalle.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=random.randint(10, 50),
                    costo_unitario_compra=producto.costo_unitario * Decimal(random.uniform(0.95, 1.05))
                )
            
            if random.random() < 0.85 and pedido.fecha_pedido < (HOY - timedelta(days=7)):
                pedido.estado = 'RECIBIDO'
                pedido.save()
                
                if random.random() < 0.7:
                    PagoProveedor.objects.create(
                        pedido=pedido,
                        monto=pedido.costo_total * Decimal(random.uniform(0.5, 1.0)),
                        usuario=user,
                        metodo_pago=random.choice(['Transferencia', 'Efectivo'])
                    )

    def crear_ventas(self, clientes, productos, user):
        self.stdout.write('💰 Creando ventas...')
        ventas_para_domicilio = []
        ventas_creadas = 0
        
        for i in range(NUM_VENTAS):
            if i % 20 == 0:
                self.stdout.write(f'  Progreso: {i}/{NUM_VENTAS}...', ending='\r')
            
            fecha_venta = fake.date_time_between(
                start_date=START_DATE,
                end_date=HOY,
                tzinfo=timezone.get_current_timezone()
            )
            cliente_venta = random.choice(clientes)
            
            # Crear venta en estado BORRADOR
            venta = Venta.objects.create(
                cliente=cliente_venta,
                usuario=user,
                fecha=fecha_venta,
                estado='BORRADOR'
            )

            # Agregar productos
            productos_a_vender = random.sample(productos, k=random.randint(1, 5))
            for producto in productos_a_vender:
                if producto.stock_actual > 0:
                    cantidad = random.randint(1, min(5, producto.stock_actual))
                    VentaDetalle.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario_venta=producto.precio_venta
                    )
            
            # Si no tiene productos, eliminar
            if not venta.detalles.exists():
                venta.delete()
                continue
            
            # 🆕 DETERMINAR SI REQUIERE DOMICILIO Y ASIGNAR COORDENADAS
            requiere_domicilio = random.random() < 0.6  # 60% de ventas con domicilio
            
            if requiere_domicilio:
                lat, lng, zona = self.obtener_coordenadas_aleatorias()
                venta.requiere_domicilio = True
                venta.direccion_entrega = f"Calle {random.randint(1, 100)} #{random.randint(1, 200)}-{random.randint(1, 200)}, {zona}, Barranquilla"
                venta.latitud_entrega = lat
                venta.longitud_entrega = lng
                venta.prioridad_entrega = random.choice(['alta', 'media', 'baja'])
                
                # Ventanas de tiempo aleatorias
                if random.random() < 0.3:  # 30% tiene ventana específica
                    hora_inicio = random.randint(8, 14)
                    venta.ventana_tiempo_inicio = timezone.datetime.strptime(f"{hora_inicio}:00", "%H:%M").time()
                    venta.ventana_tiempo_fin = timezone.datetime.strptime(f"{hora_inicio + 4}:00", "%H:%M").time()
            
            # Definir estado final
            if requiere_domicilio:
                # Ventas con domicilio: mayormente pendientes de entrega
                estado_final = random.choices(
                    ['PAGADA_PENDIENTE_ENTREGA', 'COMPLETADA', 'BORRADOR'],
                    [0.70, 0.20, 0.10],
                    k=1
                )[0]
            else:
                # Ventas sin domicilio: mayormente completadas
                estado_final = random.choices(
                    ['COMPLETADA', 'PENDIENTE_PAGO', 'CANCELADA'],
                    [0.80, 0.15, 0.05],
                    k=1
                )[0]
            
            venta.estado = estado_final
            venta.save()
            
            # 🆕 AGREGAR A LISTA DE DOMICILIOS SOLO SI TIENE COORDENADAS
            if venta.requiere_domicilio and venta.latitud_entrega and venta.longitud_entrega:
                if venta.estado in ['PAGADA_PENDIENTE_ENTREGA', 'BORRADOR']:
                    ventas_para_domicilio.append(venta)
            
            ventas_creadas += 1
        
        self.stdout.write(f'\n  ✅ {ventas_creadas} ventas creadas')
        self.stdout.write(f'  📍 {len(ventas_para_domicilio)} ventas con domicilio y coordenadas válidas')
        return ventas_para_domicilio

    def crear_notas_de_entrega(self, user):
        self.stdout.write('📝 Creando notas de entrega...')
        ventas_aptas = Venta.objects.filter(
            estado='PAGADA_PENDIENTE_ENTREGA',
            detalles__cantidad__gt=1
        ).distinct()
        
        for venta in random.sample(list(ventas_aptas), k=min(8, len(ventas_aptas))):
            detalle_venta = venta.detalles.filter(cantidad__gt=1).first()
            if not detalle_venta:
                continue
            
            nota = NotaEntregaVenta.objects.create(
                venta=venta,
                usuario=user,
                descripcion="Entrega parcial realizada por el cliente."
            )
            
            cantidad_a_entregar = random.randint(1, detalle_venta.cantidad - 1)
            DetalleNotaEntrega.objects.create(
                nota_entrega=nota,
                producto=detalle_venta.producto,
                cantidad_entregada=cantidad_a_entregar
            )
            
            try:
                nota.aplicar_descuento_inventario()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ⚠️ Error en nota venta #{venta.id}: {e}'))
    
    def crear_rutas_de_entrega(self, ventas_domicilio, sucursales, repartidores):
        self.stdout.write('🗺️ Creando rutas de entrega...')
        
        # Filtrar ventas sin ruta asignada
        ventas_disponibles = list(filter(
            lambda v: not hasattr(v, 'detalleruta') and v.latitud_entrega and v.longitud_entrega,
            ventas_domicilio
        ))
        
        self.stdout.write(f'  Ventas disponibles para rutas: {len(ventas_disponibles)}')

        rutas_creadas = 0
        for _ in range(NUM_RUTAS):
            if len(ventas_disponibles) < 2:
                break
            
            paradas = random.randint(2, min(6, len(ventas_disponibles)))
            ventas_en_ruta = random.sample(ventas_disponibles, k=paradas)
            ventas_disponibles = [v for v in ventas_disponibles if v not in ventas_en_ruta]
            
            fecha_entrega = fake.date_between(
                start_date=(HOY - timedelta(days=30)).date(),
                end_date=HOY.date()
            )
            
            ruta = RutaEntrega.objects.create(
                sucursal_origen=random.choice(sucursales),
                repartidor=random.choice(repartidores),
                fecha_entrega=fecha_entrega,
                distancia_total_km=Decimal(random.uniform(15, 80)),
                tiempo_estimado_min=random.randint(60, 240),
                numero_paradas=paradas,
                waypoints=[v.coordenadas_entrega for v in ventas_en_ruta if v.coordenadas_entrega],
                peso_total_kg=sum(v.peso_total_kg for v in ventas_en_ruta),
                volumen_total_m3=sum(v.volumen_total_m3 for v in ventas_en_ruta),
                estado='PLANIFICADA'
            )
            
            for i, venta_ruta in enumerate(ventas_en_ruta):
                DetalleRuta.objects.create(
                    ruta=ruta,
                    venta=venta_ruta,
                    orden_entrega=i + 1,
                    peso_productos_kg=venta_ruta.peso_total_kg,
                    volumen_productos_m3=venta_ruta.volumen_total_m3
                )
            
            if ruta.fecha_entrega < HOY.date():
                ruta.estado = 'COMPLETADA'
                ruta.save()
                Venta.objects.filter(
                    id__in=[d.venta.id for d in ruta.detalles.all()]
                ).update(estado='COMPLETADA')
                ruta.detalles.all().update(entregado=True)
            elif ruta.fecha_entrega == HOY.date():
                ruta.estado = random.choice(['PLANIFICADA', 'EN_CURSO'])
                ruta.save()
            
            rutas_creadas += 1
        
        self.stdout.write(f'  ✅ {rutas_creadas} rutas creadas')