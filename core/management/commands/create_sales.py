# core/management/commands/create_sales.py

import random
import time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from core.models import Cliente, Producto, Venta, VentaDetalle

class Command(BaseCommand):
    help = 'Crea un número especificado de ventas aleatorias para pruebas de estrés y volumen.'

    def add_arguments(self, parser):
        # Argumento posicional y obligatorio: el número de ventas a crear
        parser.add_argument('num_sales', type=int, help='El número de ventas que se deben crear.')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        num_sales = kwargs['num_sales']
        start_time = time.time()
        self.stdout.write(f"Iniciando la creación de {num_sales} ventas...")

        # --- 1. PRE-CARGA DE DATOS PARA EFICIENCIA ---
        # Cargamos los IDs en memoria para evitar consultas repetitivas a la BD dentro del bucle
        clientes_ids = list(Cliente.objects.values_list('id', flat=True))
        # Cargamos los productos que SÍ tienen stock en una lista de objetos
        productos_con_stock = list(Producto.objects.filter(stock_actual__gt=0))
        admin_user = User.objects.filter(is_superuser=True).first()

        # --- 2. VALIDACIONES INICIALES ---
        if not clientes_ids:
            self.stdout.write(self.style.ERROR('No hay clientes en la base de datos. Ejecuta `seed_db` primero.'))
            return
        if not productos_con_stock:
            self.stdout.write(self.style.ERROR('No hay productos con stock disponible. Crea pedidos a proveedores primero.'))
            return
        if not admin_user:
            self.stdout.write(self.style.ERROR('No se encontró un superusuario.'))
            return

        # --- 3. BUCLE PRINCIPAL DE CREACIÓN DE VENTAS ---
        ventas_creadas = 0
        for i in range(num_sales):
            # Si en el proceso nos quedamos sin stock de todos los productos, paramos.
            if not productos_con_stock:
                self.stdout.write(self.style.WARNING('\nSe agotó el stock de todos los productos. Deteniendo la creación de ventas.'))
                break

            # Seleccionamos un cliente al azar
            cliente_id_aleatorio = random.choice(clientes_ids)

            # Creamos la venta. El estado 'COMPLETADA' activará la lógica para descontar stock.
            venta = Venta.objects.create(
                cliente_id=cliente_id_aleatorio,
                usuario=admin_user,
                estado='COMPLETADA'
            )

            # Añadimos entre 1 y 4 productos diferentes a la venta
            num_items_en_venta = random.randint(1, min(4, len(productos_con_stock)))
            productos_para_la_venta = random.sample(productos_con_stock, k=num_items_en_venta)

            for producto in productos_para_la_venta:
                # Vendemos entre 1 y 3 unidades, pero nunca más del stock disponible
                cantidad_a_vender = random.randint(1, min(3, producto.stock_actual))

                VentaDetalle.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad_a_vender
                )
                
                # Actualizamos el stock del producto EN MEMORIA para el resto de la ejecución
                producto.stock_actual -= cantidad_a_vender
            
            # Limpiamos la lista de productos en memoria eliminando los que se quedaron sin stock
            productos_con_stock = [p for p in productos_con_stock if p.stock_actual > 0]
            
            ventas_creadas += 1

            # Imprimimos una barra de progreso
            self.stdout.write(f'\rProgreso: [{i+1}/{num_sales}] ventas creadas.', ending='')
            self.stdout.flush()

        end_time = time.time()
        duracion = round(end_time - start_time, 2)

        self.stdout.write(self.style.SUCCESS(f'\n\n¡Operación completada!'))
        self.stdout.write(f'Se crearon {ventas_creadas} ventas en {duracion} segundos.')