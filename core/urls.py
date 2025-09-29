from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Clientes
    path('clientes/', views.cliente_list, name='cliente_list'),
    path('clientes/agregar/', views.cliente_add, name='cliente_add'),
    path('clientes/<int:pk>/editar/', views.cliente_edit, name='cliente_edit'),
    path('clientes/<int:pk>/eliminar/', views.cliente_delete, name='cliente_delete'),
    
    # Productos
    path('productos/', views.producto_list, name='producto_list'),
    path('productos/agregar/', views.producto_add, name='producto_add'),
    path('productos/<int:pk>/editar/', views.producto_edit, name='producto_edit'),
    path('productos/<int:pk>/eliminar/', views.producto_delete, name='producto_delete'),
    
    # Ventas
    path('ventas/', views.venta_list, name='venta_list'),
    path('ventas/nueva/', views.nueva_venta, name='nueva_venta'),
    path('ventas/<int:pk>/', views.venta_detail, name='venta_detail'),
    
    # Proveedores
    path('proveedores/', views.proveedor_list, name='proveedor_list'),
    path('proveedores/agregar/', views.proveedor_add, name='proveedor_add'),
    path('proveedores/<int:pk>/editar/', views.proveedor_edit, name='proveedor_edit'),
    path('proveedores/<int:pk>/eliminar/', views.proveedor_delete, name='proveedor_delete'),
    
    # Pedidos
    path('pedidos/', views.pedido_list, name='pedido_list'),
    path('pedidos/nuevo/', views.pedido_add, name='pedido_add'),
    path('pedidos/<int:pk>/', views.pedido_detail, name='pedido_detail'),
    path('pedidos/<int:pk>/cambiar-estado/', views.pedido_cambiar_estado, name='pedido_cambiar_estado'),
    
    # API endpoints
    path('api/producto/<int:producto_id>/precio/', views.get_producto_precio, name='get_producto_precio'),
    path('api/buscar-productos/', views.buscar_productos, name='buscar_productos'),
]
