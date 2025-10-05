# Guía de Tests - Synkro

## Suite de Tests Completa

Esta suite de tests verifica todas las funcionalidades críticas del sistema de inventario Synkro, incluyendo:

### 📦 Gestión de Stock
- **Ventas**: Descuento automático de stock al completar ventas
- **Pedidos**: Incremento automático de stock al recibir pedidos
- **Estados**: Manejo correcto de stock según estados (COMPLETADA, CANCELADA, PENDIENTE, RECIBIDO)
- **Reversiones**: Stock se reintegra al cancelar ventas o revertir pedidos

### 💰 Cálculos Financieros
- **Totales de ventas**: Suma automática de detalles
- **Totales de pedidos**: Cálculo de costos totales
- **Pagos a proveedores**: Acumulación de pagos parciales
- **Saldos**: Cálculo correcto de saldos pendientes
- **Ganancias**: Cálculo de ganancia unitaria y margen de ganancia

### 🔄 Flujos de Integración
- **Compra → Stock → Venta**: Flujo completo desde pedido a proveedor hasta venta al cliente
- **Pagos parciales**: Registro de múltiples pagos hasta saldar un pedido
- **Trazabilidad**: Verificación de historial de operaciones

### 🎯 Validaciones
- **Stock insuficiente**: Prevención de ventas sin stock
- **Estados válidos**: Solo estados permitidos por el sistema
- **Cálculos correctos**: Propiedades del modelo calculan valores precisos

---

## 🚀 Cómo Ejecutar los Tests

### 1. Ejecutar TODOS los tests
```powershell
python manage.py test
```

### 2. Ejecutar tests de un módulo específico
```powershell
python manage.py test core
```

### 3. Ejecutar una clase de tests específica
```powershell
# Tests de gestión de stock en ventas
python manage.py test core.tests.VentaStockTest

# Tests de pedidos a proveedores
python manage.py test core.tests.PedidoProveedorStockTest

# Tests de pagos
python manage.py test core.tests.PagoProveedorTest

# Tests de integración (flujos completos)
python manage.py test core.tests.IntegrationTest
```

### 4. Ejecutar un test individual
```powershell
python manage.py test core.tests.VentaStockTest.test_venta_descuenta_stock_al_completar
```

### 5. Ejecutar con verbosidad (ver detalles)
```powershell
python manage.py test --verbosity=2
```

### 6. Ejecutar con cobertura de código
```powershell
# Instalar coverage
pip install coverage

# Ejecutar tests con coverage
coverage run --source='.' manage.py test core

# Ver reporte en consola
coverage report

# Generar reporte HTML
coverage html
# Abrir: htmlcov/index.html
```

---

## 📊 Clases de Tests Disponibles

### `ProductoModelTest`
- **Qué prueba**: Modelo Producto y sus propiedades calculadas
- **Tests incluidos**:
  - Creación de productos
  - Cálculo de ganancia unitaria
  - Cálculo de margen de ganancia
  - Detección de stock bajo (necesita_reposicion)

### `VentaStockTest`
- **Qué prueba**: Gestión de stock en ventas
- **Tests incluidos**:
  - Descuento de stock al completar venta
  - No descuenta stock en cotizaciones
  - Ajuste de stock al cambiar estado de venta
  - Cálculo automático de monto total

### `PedidoProveedorStockTest`
- **Qué prueba**: Gestión de stock en pedidos
- **Tests incluidos**:
  - Incremento de stock al recibir pedido
  - Stock no cambia mientras el pedido esté pendiente
  - Cálculo automático de costo total
  - Reversión de stock al cambiar estado

### `PagoProveedorTest`
- **Qué prueba**: Sistema de pagos a proveedores
- **Tests incluidos**:
  - Pedido sin pagos tiene saldo completo
  - Pago reduce saldo pendiente
  - Múltiples pagos se acumulan correctamente

### `VentaViewTest`
- **Qué prueba**: Vistas de ventas (HTTP)
- **Tests incluidos**:
  - Crear venta descuenta stock
  - Lista de ventas es accesible

### `PedidoViewTest`
- **Qué prueba**: Vistas de pedidos (HTTP)
- **Tests incluidos**:
  - Crear pedido no afecta stock inicial
  - Lista de pedidos es accesible

### `DashboardViewTest`
- **Qué prueba**: Dashboard principal
- **Tests incluidos**:
  - Dashboard es accesible
  - Muestra estadísticas básicas

### `ClienteProveedorTest`
- **Qué prueba**: Modelos Cliente y Proveedor
- **Tests incluidos**:
  - Creación con todos los campos (razón social, dirección, etc.)

### `IntegrationTest`
- **Qué prueba**: Flujos completos de negocio
- **Tests incluidos**:
  - Flujo: Pedido → Recepción → Venta
  - Flujo: Pedido → Pagos parciales → Saldar deuda

---

## ✅ Resultados Esperados

Al ejecutar `python manage.py test`, deberías ver algo como:

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
..................................................
----------------------------------------------------------------------
Ran 50 tests in 2.345s

OK
Destroying test database for alias 'default'...
```

Si todos los tests pasan, verás `OK` al final.

---

## 🐛 Si un Test Falla

### 1. Lee el mensaje de error
Django te mostrará:
- Qué test falló
- Qué esperaba vs. qué obtuvo
- El traceback completo

### 2. Ejecuta solo ese test con verbosidad
```powershell
python manage.py test core.tests.VentaStockTest.test_venta_descuenta_stock_al_completar --verbosity=2
```

### 3. Verifica la lógica de negocio
- Revisa el modelo correspondiente
- Verifica los métodos `save()` y propiedades `@property`
- Asegúrate de que las transacciones funcionan correctamente

### 4. Usa el shell de Django para debugging
```powershell
python manage.py shell
```

```python
from core.models import Producto, Venta, VentaDetalle
from django.contrib.auth.models import User

# Reproduce el escenario del test
producto = Producto.objects.create(
    nombre="Test",
    sku="TST001",
    stock_actual=10,
    precio_venta=100,
    costo_unitario=60
)

print(f"Stock inicial: {producto.stock_actual}")
print(f"Ganancia: {producto.ganancia_unitaria}")
print(f"Margen: {producto.margen_ganancia}")
```

---

## 📝 Notas Importantes

### Base de datos de tests
- Django crea automáticamente una base de datos temporal para tests
- Esta BD se destruye al finalizar
- **Tus datos reales NO se ven afectados**

### Migra antes de testear
Si has hecho cambios en modelos:
```powershell
python manage.py makemigrations
python manage.py migrate
```

### Tests independientes
Cada test es independiente y no afecta a otros. Django usa transacciones para revertir cambios después de cada test.

---

## 🎯 Casos de Uso Cubiertos

### Flujo 1: Nueva Compra
1. ✅ Crear pedido a proveedor (estado PENDIENTE)
2. ✅ Verificar que stock NO cambia
3. ✅ Marcar pedido como RECIBIDO
4. ✅ Verificar que stock aumenta

### Flujo 2: Nueva Venta
1. ✅ Crear venta (estado COMPLETADA)
2. ✅ Verificar que stock disminuye
3. ✅ Verificar cálculo de total

### Flujo 3: Cancelar Venta
1. ✅ Crear venta COMPLETADA
2. ✅ Cambiar estado a CANCELADA
3. ✅ Verificar que stock se reintegra

### Flujo 4: Pagos Parciales
1. ✅ Crear pedido con costo $1000
2. ✅ Pagar $300 → Saldo: $700
3. ✅ Pagar $400 → Saldo: $300
4. ✅ Pagar $300 → Saldo: $0

---

## 🔧 Comandos Útiles

```powershell
# Ejecutar tests y detener al primer fallo
python manage.py test --failfast

# Ejecutar tests en paralelo (más rápido)
python manage.py test --parallel

# Conservar la BD de tests para inspección
python manage.py test --keepdb

# Ver queries SQL ejecutadas
python manage.py test --debug-mode
```

---

## 📚 Próximos Pasos

Para expandir la cobertura de tests, considera agregar:

1. **Tests de permisos**: Verificar que solo usuarios autenticados pueden acceder
2. **Tests de formularios**: Validaciones de campos requeridos
3. **Tests de API**: Si agregas endpoints REST
4. **Tests de templates**: Verificar que se renderizan correctamente
5. **Tests de performance**: Medir tiempos de respuesta

---

## 🎉 ¡Tests Pasando!

Si todos tus tests pasan, significa que:
- ✅ La gestión de stock funciona correctamente
- ✅ Los cálculos financieros son precisos
- ✅ Los flujos de negocio funcionan end-to-end
- ✅ Las validaciones están en su lugar
- ✅ Tu código está listo para producción

**¡Felicitaciones por mantener un código bien testeado!** 🚀
