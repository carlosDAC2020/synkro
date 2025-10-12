import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import (
    Categoria, Producto, Cliente, Proveedor, Venta, VentaDetalle,
    PedidoProveedor, PedidoDetalle, PagoProveedor,
    Sucursal, Repartidor, RutaEntrega, DetalleRuta
)
from django.contrib.auth import get_user_model

User = get_user_model()

print("🧹 Limpiando base de datos...")
print("=" * 60)

# Confirmar acción
respuesta = input("\n⚠️  ADVERTENCIA: Esto eliminará TODOS los datos excepto usuarios.\n¿Estás seguro? (escribe 'SI' para confirmar): ")

if respuesta != 'SI':
    print("❌ Operación cancelada.")
    exit()

print("\n🗑️  Eliminando datos...")

# Eliminar en orden correcto (respetando foreign keys)
try:
    # Domicilios
    DetalleRuta.objects.all().delete()
    print("  ✅ DetalleRuta eliminados")
    
    RutaEntrega.objects.all().delete()
    print("  ✅ RutaEntrega eliminadas")
    
    Repartidor.objects.all().delete()
    print("  ✅ Repartidores eliminados")
    
    Sucursal.objects.all().delete()
    print("  ✅ Sucursales eliminadas")
    
    # Pagos a proveedores
    PagoProveedor.objects.all().delete()
    print("  ✅ PagoProveedor eliminados")
    
    # Pedidos a proveedores
    PedidoDetalle.objects.all().delete()
    print("  ✅ PedidoDetalle eliminados")
    
    PedidoProveedor.objects.all().delete()
    print("  ✅ PedidoProveedor eliminados")
    
    # Ventas
    VentaDetalle.objects.all().delete()
    print("  ✅ VentaDetalle eliminados")
    
    Venta.objects.all().delete()
    print("  ✅ Ventas eliminadas")
    
    # Productos y categorías
    Producto.objects.all().delete()
    print("  ✅ Productos eliminados")
    
    Categoria.objects.all().delete()
    print("  ✅ Categorías eliminadas")
    
    # Clientes y proveedores
    Cliente.objects.all().delete()
    print("  ✅ Clientes eliminados")
    
    Proveedor.objects.all().delete()
    print("  ✅ Proveedores eliminados")
    
    print("\n✨ Base de datos limpiada exitosamente!")
    print(f"👤 Usuarios activos: {User.objects.count()}")
    
except Exception as e:
    print(f"\n❌ Error al limpiar: {e}")
