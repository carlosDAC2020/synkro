import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from faker import Faker

from core.models import (
    Categoria, Producto, Cliente, Proveedor,
    Venta, VentaDetalle, PedidoProveedor, PedidoDetalle
)

# --- CONFIGURACIÓN DE LA CANTIDAD DE DATOS A CREAR ---
NUM_CLIENTES = 25
NUM_PROVEEDORES = 10
NUM_PRODUCTOS = 80
NUM_VENTAS = 150
NUM_PEDIDOS_PROVEEDOR = 20
MAX_PRODUCTOS_POR_TRANSACCION = 5 # Máximo de productos por venta o pedido

class Command(BaseCommand):
    help = 'Llena la base de datos con datos de prueba realistas.'

    @transaction.atomic # Usamos una transacción para que todo se ejecute o nada lo haga
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Este comando eliminará TODOS los datos existentes. Piénsalo bien.'))
        confirmacion = input('Escribe "si" para confirmar: ')
        if confirmacion != 'si':
            self.stdout.write(self.style.ERROR('Operación cancelada.'))
            return

        self.stdout.write("Eliminando datos antiguos...")
        # El orden de eliminación es importante para evitar errores de clave foránea
        VentaDetalle.objects.all().delete()
        PedidoDetalle.objects.all().delete()
        Venta.objects.all().delete()
        PedidoProveedor.objects.all().delete()
        Producto.objects.all().delete()
        Categoria.objects.all().delete()
        Cliente.objects.all().delete()
        Proveedor.objects.all().delete()
        
        # Necesitamos un usuario para asociar a las ventas. Usaremos el primer superusuario.
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                self.stdout.write(self.style.ERROR('No se encontró un superusuario. Por favor, crea uno con `python manage.py createsuperuser`.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al buscar superusuario: {e}'))
            return

        faker = Faker('es_ES') # Usar datos en español

        # 1. Crear Categorías
        self.stdout.write("Creando categorías...")
        categorias_nombres = ['Electrónica', 'Ropa y Accesorios', 'Hogar y Cocina', 'Deportes', 'Libros', 'Juguetes', 'Salud y Belleza']
        categorias = [Categoria.objects.create(nombre=nombre) for nombre in categorias_nombres]

        # 2. Crear Proveedores
        self.stdout.write("Creando proveedores...")
        proveedores = [Proveedor.objects.create(
            nombre=faker.company(), 
            contacto=faker.name(), 
            telefono=faker.phone_number(), 
            email=faker.company_email()
        ) for _ in range(NUM_PROVEEDORES)]

        # 3. Crear Clientes
        self.stdout.write("Creando clientes...")
        clientes = [Cliente.objects.create(
            nombre=faker.name(), 
            telefono=faker.phone_number(), 
            email=faker.unique.email()
        ) for _ in range(NUM_CLIENTES)]

        # 4. Crear Productos (inicialmente sin stock)
        self.stdout.write("Creando productos...")
        productos = [Producto.objects.create(
            nombre=f'Producto {faker.bs().title()}',
            sku=faker.unique.ean(length=8),
            categoria=random.choice(categorias),
            stock_actual=0, # El stock se añadirá con los pedidos
            stock_minimo=random.randint(5, 15),
            precio_venta=round(random.uniform(5.99, 299.99), 2)
        ) for _ in range(NUM_PRODUCTOS)]

        # 5. Crear Pedidos a Proveedores para añadir stock
        self.stdout.write("Creando y procesando pedidos a proveedores para generar stock...")
        for _ in range(NUM_PEDIDOS_PROVEEDOR):
            pedido = PedidoProveedor.objects.create(
                proveedor=random.choice(proveedores),
                # El 80% de los pedidos estarán ya recibidos para tener stock disponible
                estado=random.choice(['RECIBIDO'] * 8 + ['PENDIENTE'] * 2) 
            )
            # Añadir detalles al pedido
            productos_en_pedido = random.sample(productos, k=random.randint(1, MAX_PRODUCTOS_POR_TRANSACCION))
            for producto in productos_en_pedido:
                costo = float(producto.precio_venta) * random.uniform(0.5, 0.7)
                PedidoDetalle.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=random.randint(10, 50),
                    costo_unitario_compra=round(costo, 2)
                )

        # 6. Crear Ventas (usando el stock generado)
        self.stdout.write("Creando ventas y descontando stock...")
        productos_con_stock = list(Producto.objects.filter(stock_actual__gt=0))
        for _ in range(NUM_VENTAS):
            # Solo vender productos que realmente tengan stock
            if not productos_con_stock:
                break # No podemos vender si no hay nada en el inventario

            venta = Venta.objects.create(
                cliente=random.choice(clientes),
                usuario=admin_user,
                estado=random.choice(['COMPLETADA'] * 9 + ['CANCELADA'] * 1) # 90% completadas
            )
            # Añadir detalles a la venta
            productos_a_vender = random.sample(
                productos_con_stock, 
                k=min(random.randint(1, MAX_PRODUCTOS_POR_TRANSACCION), len(productos_con_stock))
            )

            for producto in productos_a_vender:
                # No vender más de lo que hay
                cantidad_a_vender = random.randint(1, min(5, producto.stock_actual))
                
                if cantidad_a_vender > 0:
                    VentaDetalle.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad_a_vender
                        # El precio se toma automáticamente del producto
                    )
                    # Actualizamos la lista en memoria para reflejar el nuevo stock
                    producto.stock_actual -= cantidad_a_vender

        self.stdout.write(self.style.SUCCESS('¡La base de datos ha sido llenada con éxito!'))