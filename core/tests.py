# core/tests.py

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    Categoria, Producto, Cliente, Proveedor, 
    Venta, VentaDetalle, 
    PedidoProveedor, PedidoDetalle, PagoProveedor
)


class ProductoModelTest(TestCase):
    """Tests para el modelo Producto y sus propiedades."""
    
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Electrónica")
        self.producto = Producto.objects.create(
            nombre="Laptop",
            sku="LAP001",
            categoria=self.categoria,
            stock_actual=10,
            stock_minimo=5,
            precio_venta=Decimal('1200.00'),
            costo_unitario=Decimal('800.00')
        )
    
    def test_producto_creacion(self):
        """Verifica que el producto se crea correctamente."""
        self.assertEqual(self.producto.nombre, "Laptop")
        self.assertEqual(self.producto.stock_actual, 10)
    
    def test_ganancia_unitaria(self):
        """Calcula correctamente la ganancia unitaria."""
        self.assertEqual(self.producto.ganancia_unitaria, Decimal('400.00'))
    
    def test_margen_ganancia(self):
        """Calcula correctamente el margen de ganancia."""
        self.assertEqual(self.producto.margen_ganancia, 50.0)  # (400/800) * 100
    
    def test_necesita_reposicion(self):
        """Detecta cuando el stock está bajo."""
        self.assertFalse(self.producto.necesita_reposicion)
        self.producto.stock_actual = 4
        self.assertTrue(self.producto.necesita_reposicion)


class VentaStockTest(TestCase):
    """Tests para la gestión de stock en ventas."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.cliente = Cliente.objects.create(nombre="Cliente Test", email="test@test.com")
        self.producto = Producto.objects.create(
            nombre="Mouse",
            sku="MOU001",
            stock_actual=20,
            stock_minimo=5,
            precio_venta=Decimal('25.00'),
            costo_unitario=Decimal('15.00')
        )
    
    def test_venta_descuenta_stock_al_completar(self):
        """El stock se descuenta cuando una venta se marca como COMPLETADA."""
        stock_inicial = self.producto.stock_actual
        
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            estado='COMPLETADA'
        )
        VentaDetalle.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=5,
            precio_unitario_venta=Decimal('25.00')
        )
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial - 5)
    
    def test_venta_no_descuenta_stock_si_es_cotizacion(self):
        """El stock NO se descuenta si la venta es solo cotización."""
        stock_inicial = self.producto.stock_actual
        
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            estado='COTIZACION'
        )
        VentaDetalle.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=5,
            precio_unitario_venta=Decimal('25.00')
        )
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial)
    
    def test_cambio_estado_venta_ajusta_stock(self):
        """Cambiar el estado de una venta ajusta el stock correctamente."""
        stock_inicial = self.producto.stock_actual
        
        # Crear venta en estado borrador
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            estado='BORRADOR'
        )
        VentaDetalle.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=3,
            precio_unitario_venta=Decimal('25.00')
        )
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial)
        
        # Cambiar a COMPLETADA
        venta.estado = 'COMPLETADA'
        venta.save()
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial - 3)
        
        # Cancelar venta (debe reintegrar stock)
        venta.estado = 'CANCELADA'
        venta.save()
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial)
    
    def test_venta_calcula_monto_total(self):
        """El monto total de la venta se calcula automáticamente."""
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            estado='COTIZACION'
        )
        VentaDetalle.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=4,
            precio_unitario_venta=Decimal('25.00')
        )
        
        venta.refresh_from_db()
        self.assertEqual(venta.monto_total, Decimal('100.00'))  # 4 * 25


class PedidoProveedorStockTest(TestCase):
    """Tests para la gestión de stock en pedidos a proveedores."""
    
    def setUp(self):
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor Test",
            email="proveedor@test.com"
        )
        self.producto = Producto.objects.create(
            nombre="Teclado",
            sku="TEC001",
            stock_actual=5,
            stock_minimo=10,
            precio_venta=Decimal('50.00'),
            costo_unitario=Decimal('30.00')
        )
    
    def test_pedido_aumenta_stock_al_recibir(self):
        """El stock aumenta cuando un pedido se marca como RECIBIDO."""
        stock_inicial = self.producto.stock_actual
        
        pedido = PedidoProveedor.objects.create(
            proveedor=self.proveedor,
            estado='PENDIENTE'
        )
        PedidoDetalle.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=15,
            costo_unitario_compra=Decimal('28.00')
        )
        
        # Stock no cambia mientras esté pendiente
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial)
        
        # Marcar como recibido
        pedido.estado = 'RECIBIDO'
        pedido.save()
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial + 15)
    
    def test_pedido_calcula_costo_total(self):
        """El costo total del pedido se calcula automáticamente."""
        pedido = PedidoProveedor.objects.create(
            proveedor=self.proveedor,
            estado='PENDIENTE'
        )
        PedidoDetalle.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=10,
            costo_unitario_compra=Decimal('28.00')
        )
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.costo_total, Decimal('280.00'))  # 10 * 28
    
    def test_revertir_pedido_recibido_descuenta_stock(self):
        """Si un pedido RECIBIDO se revierte a PENDIENTE, el stock se descuenta."""
        stock_inicial = self.producto.stock_actual
        
        pedido = PedidoProveedor.objects.create(
            proveedor=self.proveedor,
            estado='RECIBIDO'
        )
        PedidoDetalle.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=10,
            costo_unitario_compra=Decimal('28.00')
        )
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial + 10)
        
        # Revertir a PENDIENTE
        pedido.estado = 'PENDIENTE'
        pedido.save()
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial)


class PagoProveedorTest(TestCase):
    """Tests para el sistema de pagos a proveedores."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='cajero', password='12345')
        self.proveedor = Proveedor.objects.create(nombre="Proveedor XYZ")
        self.producto = Producto.objects.create(
            nombre="Monitor",
            sku="MON001",
            stock_actual=3,
            precio_venta=Decimal('300.00'),
            costo_unitario=Decimal('200.00')
        )
        self.pedido = PedidoProveedor.objects.create(
            proveedor=self.proveedor,
            estado='PENDIENTE'
        )
        PedidoDetalle.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=5,
            costo_unitario_compra=Decimal('200.00')
        )
        self.pedido.refresh_from_db()
    
    def test_pedido_sin_pagos_tiene_saldo_completo(self):
        """Un pedido sin pagos tiene saldo igual al costo total."""
        self.assertEqual(self.pedido.total_pagado, 0)
        self.assertEqual(self.pedido.saldo_pendiente, self.pedido.costo_total)
    
    def test_pago_reduce_saldo_pendiente(self):
        """Registrar un pago reduce el saldo pendiente."""
        PagoProveedor.objects.create(
            pedido=self.pedido,
            monto=Decimal('500.00'),
            metodo_pago='Transferencia',
            referencia='REF001',
            usuario=self.user
        )
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.total_pagado, Decimal('500.00'))
        self.assertEqual(self.pedido.saldo_pendiente, Decimal('500.00'))  # 1000 - 500
    
    def test_multiples_pagos_acumulan(self):
        """Múltiples pagos se acumulan correctamente."""
        PagoProveedor.objects.create(
            pedido=self.pedido,
            monto=Decimal('300.00'),
            metodo_pago='Efectivo',
            usuario=self.user
        )
        PagoProveedor.objects.create(
            pedido=self.pedido,
            monto=Decimal('400.00'),
            metodo_pago='Cheque',
            usuario=self.user
        )
        PagoProveedor.objects.create(
            pedido=self.pedido,
            monto=Decimal('300.00'),
            metodo_pago='Transferencia',
            usuario=self.user
        )
        
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.total_pagado, Decimal('1000.00'))
        self.assertEqual(self.pedido.saldo_pendiente, Decimal('0.00'))


class VentaViewTest(TestCase):
    """Tests para las vistas de ventas."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='vendedor', password='12345')
        self.client = Client()
        self.client.login(username='vendedor', password='12345')
        
        self.cliente_obj = Cliente.objects.create(nombre="Cliente ABC", email="abc@test.com")
        self.producto = Producto.objects.create(
            nombre="Ratón",
            sku="RAT001",
            stock_actual=50,
            precio_venta=Decimal('20.00'),
            costo_unitario=Decimal('12.00')
        )
    
    def test_crear_venta_descuenta_stock(self):
        """Crear una venta completada descuenta el stock correctamente."""
        stock_inicial = self.producto.stock_actual
        
        # Crear venta directamente (test de modelo, no de vista HTTP)
        venta = Venta.objects.create(
            cliente=self.cliente_obj,
            usuario=self.user,
            estado='COMPLETADA'
        )
        VentaDetalle.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=5,
            precio_unitario_venta=Decimal('20.00')
        )
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial - 5)
    
    def test_lista_ventas_accesible(self):
        """La lista de ventas es accesible."""
        response = self.client.get(reverse('venta_list'))
        self.assertEqual(response.status_code, 200)


class PedidoViewTest(TestCase):
    """Tests para las vistas de pedidos."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='comprador', password='12345')
        self.client = Client()
        self.client.login(username='comprador', password='12345')
        
        self.proveedor = Proveedor.objects.create(nombre="Proveedor DEF")
        self.producto = Producto.objects.create(
            nombre="Cable HDMI",
            sku="HDMI001",
            stock_actual=10,
            precio_venta=Decimal('15.00'),
            costo_unitario=Decimal('8.00')
        )
    
    def test_crear_pedido_no_afecta_stock_inicial(self):
        """Crear un pedido NO afecta el stock hasta que se reciba."""
        stock_inicial = self.producto.stock_actual
        
        response = self.client.post(reverse('pedido_add'), {
            'proveedor': self.proveedor.id,
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-producto': self.producto.id,
            'form-0-cantidad': '20',
            'form-0-costo_unitario_compra': '7.50',
        })
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_inicial)
    
    def test_lista_pedidos_accesible(self):
        """La lista de pedidos es accesible."""
        response = self.client.get(reverse('pedido_list'))
        self.assertEqual(response.status_code, 200)


class DashboardViewTest(TestCase):
    """Tests para el dashboard."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='12345')
        self.client = Client()
        self.client.login(username='admin', password='12345')
    
    def test_dashboard_accesible(self):
        """El dashboard es accesible."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_muestra_estadisticas_basicas(self):
        """El dashboard incluye estadísticas básicas."""
        # Crear datos de prueba
        Producto.objects.create(
            nombre="Producto Test",
            sku="TEST001",
            stock_actual=5,
            precio_venta=Decimal('100.00'),
            costo_unitario=Decimal('60.00')
        )
        Cliente.objects.create(nombre="Cliente Test")
        Proveedor.objects.create(nombre="Proveedor Test")
        
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Total Productos')
        self.assertContains(response, 'Total Clientes')


class ClienteProveedorTest(TestCase):
    """Tests para Clientes y Proveedores."""
    
    def test_crear_cliente_con_todos_los_campos(self):
        """Se puede crear un cliente con todos los campos."""
        cliente = Cliente.objects.create(
            nombre="Empresa XYZ",
            telefono="555-1234",
            email="xyz@empresa.com",
            razon_social="Empresa XYZ S.A. de C.V.",
            direccion="Calle 123, Ciudad"
        )
        self.assertEqual(cliente.nombre, "Empresa XYZ")
        self.assertEqual(cliente.razon_social, "Empresa XYZ S.A. de C.V.")
    
    def test_crear_proveedor_con_todos_los_campos(self):
        """Se puede crear un proveedor con todos los campos."""
        proveedor = Proveedor.objects.create(
            nombre="Proveedor ABC",
            contacto="Juan Pérez",
            razon_social="ABC Distribuidora S.A.",
            direccion="Av. Principal 456",
            telefono="555-5678",
            email="contacto@abc.com"
        )
        self.assertEqual(proveedor.nombre, "Proveedor ABC")
        self.assertEqual(proveedor.contacto, "Juan Pérez")


class IntegrationTest(TestCase):
    """Tests de integración que prueban flujos completos."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='integrador', password='12345')
        self.cliente = Cliente.objects.create(nombre="Cliente Final")
        self.proveedor = Proveedor.objects.create(nombre="Proveedor Principal")
        self.producto = Producto.objects.create(
            nombre="Producto Integración",
            sku="INT001",
            stock_actual=0,
            stock_minimo=5,
            precio_venta=Decimal('100.00'),
            costo_unitario=Decimal('60.00')
        )
    
    def test_flujo_completo_compra_venta(self):
        """
        Flujo completo: 
        1. Crear pedido a proveedor
        2. Recibir pedido (aumenta stock)
        3. Hacer venta (descuenta stock)
        4. Verificar stock final
        """
        # 1. Crear pedido
        pedido = PedidoProveedor.objects.create(
            proveedor=self.proveedor,
            estado='PENDIENTE'
        )
        PedidoDetalle.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=50,
            costo_unitario_compra=Decimal('60.00')
        )
        
        # 2. Recibir pedido
        pedido.estado = 'RECIBIDO'
        pedido.save()
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 50)
        
        # 3. Hacer venta
        venta = Venta.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            estado='COMPLETADA'
        )
        VentaDetalle.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=10,
            precio_unitario_venta=Decimal('100.00')
        )
        
        # 4. Verificar stock final
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 40)
    
    def test_flujo_completo_pagos_proveedor(self):
        """
        Flujo completo de pagos:
        1. Crear pedido con costo total
        2. Hacer pagos parciales
        3. Verificar saldos
        """
        # 1. Crear pedido
        pedido = PedidoProveedor.objects.create(
            proveedor=self.proveedor,
            estado='PENDIENTE'
        )
        PedidoDetalle.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=20,
            costo_unitario_compra=Decimal('60.00')
        )
        pedido.refresh_from_db()
        
        # Verificar costo total
        self.assertEqual(pedido.costo_total, Decimal('1200.00'))
        self.assertEqual(pedido.saldo_pendiente, Decimal('1200.00'))
        
        # 2. Primer pago parcial
        PagoProveedor.objects.create(
            pedido=pedido,
            monto=Decimal('500.00'),
            metodo_pago='Transferencia',
            usuario=self.user
        )
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.total_pagado, Decimal('500.00'))
        self.assertEqual(pedido.saldo_pendiente, Decimal('700.00'))
        
        # 3. Segundo pago parcial
        PagoProveedor.objects.create(
            pedido=pedido,
            monto=Decimal('700.00'),
            metodo_pago='Efectivo',
            usuario=self.user
        )
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.total_pagado, Decimal('1200.00'))
        self.assertEqual(pedido.saldo_pendiente, Decimal('0.00'))
