from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Categoria, Producto, Cliente, Venta, VentaDetalle

class Command(BaseCommand):
    help = 'Crea datos de ejemplo para demostrar el sistema'

    def handle(self, *args, **options):
        self.stdout.write('Creando datos de ejemplo...')
        
        # Crear usuario admin si no existe
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@synkro.com',
                password='admin123'
            )
            self.stdout.write(f'Usuario admin creado: admin/admin123')
        else:
            admin_user = User.objects.get(username='admin')
            self.stdout.write('Usuario admin ya existe')

        # Crear categorías
        categorias_data = [
            {'nombre': 'Electrónicos', 'descripcion': 'Productos electrónicos y tecnológicos'},
            {'nombre': 'Ropa', 'descripcion': 'Prendas de vestir y accesorios'},
            {'nombre': 'Hogar', 'descripcion': 'Artículos para el hogar'},
            {'nombre': 'Deportes', 'descripcion': 'Equipamiento deportivo'},
        ]
        
        for cat_data in categorias_data:
            categoria, created = Categoria.objects.get_or_create(
                nombre=cat_data['nombre'],
                defaults={'descripcion': cat_data['descripcion']}
            )
            if created:
                self.stdout.write(f'Categoría creada: {categoria.nombre}')

        # Crear productos
        productos_data = [
            {
                'nombre': 'Smartphone Samsung Galaxy',
                'sku': 'SAMS-GAL-001',
                'categoria': 'Electrónicos',
                'descripcion': 'Smartphone de última generación con cámara de 108MP',
                'stock_actual': 15,
                'stock_minimo': 5,
                'precio_venta': 899.99
            },
            {
                'nombre': 'Laptop HP Pavilion',
                'sku': 'HP-PAV-001',
                'categoria': 'Electrónicos',
                'descripcion': 'Laptop para uso profesional con procesador Intel i7',
                'stock_actual': 8,
                'stock_minimo': 3,
                'precio_venta': 1299.99
            },
            {
                'nombre': 'Camiseta Nike Dri-FIT',
                'sku': 'NIKE-DRI-001',
                'categoria': 'Deportes',
                'descripcion': 'Camiseta deportiva con tecnología Dri-FIT',
                'stock_actual': 25,
                'stock_minimo': 10,
                'precio_venta': 29.99
            },
            {
                'nombre': 'Jeans Levi\'s 501',
                'sku': 'LEVI-501-001',
                'categoria': 'Ropa',
                'descripcion': 'Jeans clásicos Levi\'s 501 Original',
                'stock_actual': 12,
                'stock_minimo': 8,
                'precio_venta': 89.99
            },
            {
                'nombre': 'Cafetera Nespresso',
                'sku': 'NESP-CAF-001',
                'categoria': 'Hogar',
                'descripcion': 'Cafetera automática con sistema de cápsulas',
                'stock_actual': 6,
                'stock_minimo': 3,
                'precio_venta': 199.99
            },
            {
                'nombre': 'Auriculares Sony WH-1000XM4',
                'sku': 'SONY-WH-001',
                'categoria': 'Electrónicos',
                'descripcion': 'Auriculares inalámbricos con cancelación de ruido',
                'stock_actual': 2,
                'stock_minimo': 5,
                'precio_venta': 349.99
            },
        ]
        
        for prod_data in productos_data:
            categoria = Categoria.objects.get(nombre=prod_data['categoria'])
            producto, created = Producto.objects.get_or_create(
                sku=prod_data['sku'],
                defaults={
                    'nombre': prod_data['nombre'],
                    'categoria': categoria,
                    'descripcion': prod_data['descripcion'],
                    'stock_actual': prod_data['stock_actual'],
                    'stock_minimo': prod_data['stock_minimo'],
                    'precio_venta': prod_data['precio_venta']
                }
            )
            if created:
                self.stdout.write(f'Producto creado: {producto.nombre}')

        # Crear clientes
        clientes_data = [
            {
                'nombre': 'Juan Pérez García',
                'telefono': '+52 55 1234 5678',
                'email': 'juan.perez@email.com'
            },
            {
                'nombre': 'María González López',
                'telefono': '+52 55 9876 5432',
                'email': 'maria.gonzalez@email.com'
            },
            {
                'nombre': 'Carlos Rodríguez Martín',
                'telefono': '+52 55 5555 1234',
                'email': 'carlos.rodriguez@email.com'
            },
            {
                'nombre': 'Ana Martínez Sánchez',
                'telefono': '+52 55 7777 8888',
                'email': 'ana.martinez@email.com'
            },
        ]
        
        for cliente_data in clientes_data:
            cliente, created = Cliente.objects.get_or_create(
                email=cliente_data['email'],
                defaults={
                    'nombre': cliente_data['nombre'],
                    'telefono': cliente_data['telefono']
                }
            )
            if created:
                self.stdout.write(f'Cliente creado: {cliente.nombre}')

        # Crear algunas ventas de ejemplo
        cliente1 = Cliente.objects.first()
        producto1 = Producto.objects.get(sku='SAMS-GAL-001')
        producto2 = Producto.objects.get(sku='NIKE-DRI-001')
        
        if not Venta.objects.exists():
            venta = Venta.objects.create(
                cliente=cliente1,
                usuario=admin_user,
                estado='COMPLETADA'
            )
            
            # Crear detalles de venta
            VentaDetalle.objects.create(
                venta=venta,
                producto=producto1,
                cantidad=1,
                precio_unitario_venta=producto1.precio_venta
            )
            
            VentaDetalle.objects.create(
                venta=venta,
                producto=producto2,
                cantidad=2,
                precio_unitario_venta=producto2.precio_venta
            )
            
            self.stdout.write(f'Venta de ejemplo creada: #{venta.id}')

        self.stdout.write(
            self.style.SUCCESS('¡Datos de ejemplo creados exitosamente!')
        )
        self.stdout.write('Puedes iniciar sesión con:')
        self.stdout.write('Usuario: admin')
        self.stdout.write('Contraseña: admin123')
