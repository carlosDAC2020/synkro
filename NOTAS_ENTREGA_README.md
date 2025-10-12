# Sistema de Notas de Entrega - Implementación Completa

## 📋 Descripción

Se ha implementado un sistema completo de **Notas de Entrega** para las ventas que permite:

- ✅ Registrar entregas parciales de mercancía
- ✅ Descontar inventario gradualmente según las entregas
- ✅ Rastrear qué productos y cantidades se entregaron en cada visita
- ✅ Solo permitir notas en estados específicos de venta
- ✅ Validar que no se entregue más de lo vendido
- ✅ Visualizar progreso de entregas por producto

## 🎯 Características Principales

### 1. **Modelo NotaEntregaVenta**
- Registra información de cada entrega (fecha, usuario, descripción)
- Control de descuento de inventario aplicado/pendiente
- Métodos para aplicar y revertir descuentos de inventario

### 2. **Modelo DetalleNotaEntrega**
- Especifica productos y cantidades entregadas
- Validación automática de cantidades (no permite exceder lo vendido)
- Relación con productos y notas de entrega

### 3. **Propiedades en Venta**
- `permite_notas_entrega`: Indica si la venta acepta notas (estados: PAGADA_PENDIENTE_ENTREGA, BORRADOR)
- `tiene_notas_entrega`: Verifica si hay notas registradas
- `resumen_entregas`: Resumen completo de entregas por producto
- `entrega_completa`: Indica si todos los productos fueron entregados
- `cantidad_entregada_producto(producto)`: Total entregado de un producto
- `cantidad_pendiente_producto(producto)`: Cantidad pendiente de entregar

## 🚀 Pasos para Activar el Sistema

### 1. Crear y Aplicar Migraciones

```bash
python manage.py makemigrations core
python manage.py migrate
```

### 2. Verificar Instalación

El sistema está completamente integrado en:
- ✅ Modelos: `core/models.py`
- ✅ Formularios: `core/forms.py`
- ✅ Vistas: `core/views.py`
- ✅ URLs: `core/urls.py`
- ✅ Admin: `core/admin.py`
- ✅ Templates: `core/templates/notas_entrega/`

### 3. Acceder al Sistema

#### Desde el Admin de Django:
1. Ir a `/admin/`
2. Buscar sección "Notas de Entrega"
3. Crear/editar notas con interfaz completa

#### Desde la Interfaz de Usuario:
1. Ir a una venta en estado "PAGADA_PENDIENTE_ENTREGA" o "BORRADOR"
2. En la página de detalle de la venta, verás la sección "Notas de Entrega"
3. Click en "Nueva Nota" para crear una nota de entrega
4. Llenar el formulario con:
   - Descripción de la entrega
   - Productos y cantidades entregadas
   - Opción de aplicar inventario inmediatamente

## 📊 Flujo de Uso

### Escenario Típico:

1. **Venta Creada**: Cliente compra 10 unidades del Producto A y 5 del Producto B
2. **Primera Entrega**: Cliente viene y recoge 5 unidades del Producto A
   - Se crea nota de entrega con descripción: "Cliente recogió 5 unidades del Producto A"
   - Se aplica descuento de inventario (opcional)
3. **Segunda Entrega**: Cliente viene por el resto
   - Se crea otra nota: "Cliente recogió 5 unidades del Producto A y 5 del Producto B"
   - Se aplica descuento de inventario
4. **Resultado**: Sistema muestra que la entrega está completa (100%)

## 🔧 URLs Disponibles

```python
# Crear nota de entrega para una venta
/ventas/<venta_id>/notas-entrega/crear/

# Listar todas las notas de una venta
/ventas/<venta_id>/notas-entrega/

# Ver detalle de una nota específica
/notas-entrega/<nota_id>/

# Aplicar descuento de inventario
/notas-entrega/<nota_id>/aplicar-inventario/

# Revertir descuento de inventario
/notas-entrega/<nota_id>/revertir-inventario/
```

## 🎨 Interfaz de Usuario

### Vista de Detalle de Venta
- Muestra sección "Notas de Entrega" si la venta lo permite
- Tabla con resumen de entregas por producto
- Barra de progreso visual para cada producto
- Historial de notas con badges de estado
- Botón para crear nueva nota

### Formulario de Nota de Entrega
- Información de la venta en sidebar
- Estado actual de entregas por producto
- Formulario dinámico para agregar múltiples productos
- Checkbox para aplicar inventario inmediatamente
- Validación en tiempo real

### Lista de Notas
- Resumen visual de entregas
- Cards con información de cada nota
- Indicadores de estado (aplicado/pendiente)
- Acciones rápidas (ver detalle, aplicar inventario)

## 🛡️ Validaciones Implementadas

1. **No exceder cantidades**: No se puede entregar más de lo vendido
2. **Productos válidos**: Solo productos de la venta pueden agregarse
3. **Stock suficiente**: Verifica stock antes de aplicar descuento
4. **Estados permitidos**: Solo ciertas ventas permiten notas
5. **Descuento único**: No se puede aplicar dos veces el mismo descuento

## 📝 Ejemplo de Uso en Admin

### Acciones Masivas Disponibles:
- **Aplicar descuento de inventario**: Aplica descuento a notas seleccionadas
- **Revertir descuento de inventario**: Revierte descuento de notas seleccionadas

### Campos de Solo Lectura:
- Fecha de entrega (se asigna automáticamente)
- Estado de descuento de inventario
- Resumen visual de la venta

## 🔍 Consultas Útiles

### Obtener notas pendientes de aplicar inventario:
```python
notas_pendientes = NotaEntregaVenta.objects.filter(descuento_inventario_aplicado=False)
```

### Obtener resumen de entregas de una venta:
```python
venta = Venta.objects.get(id=1)
resumen = venta.resumen_entregas
```

### Verificar si una venta está completamente entregada:
```python
if venta.entrega_completa:
    print("Todos los productos han sido entregados")
```

## ⚠️ Consideraciones Importantes

1. **Inventario**: El descuento de inventario es opcional al crear la nota. Puede aplicarse después manualmente.

2. **Estados de Venta**: Por defecto, solo las ventas en estado "PAGADA_PENDIENTE_ENTREGA" y "BORRADOR" permiten notas. Puedes modificar esto en el método `permite_notas_entrega` del modelo `Venta`.

3. **Reversión**: Si se revierte un descuento de inventario, el stock se devuelve automáticamente.

4. **Validaciones**: Las validaciones se ejecutan tanto en el modelo como en el formulario para máxima seguridad.

## 🎓 Próximos Pasos Sugeridos

1. **Notificaciones**: Agregar notificaciones cuando se crea una nota
2. **Reportes**: Crear reportes de entregas pendientes
3. **Integración con Domicilios**: Vincular notas con rutas de entrega
4. **Firma Digital**: Permitir que el cliente firme al recibir
5. **Fotos**: Agregar fotos de evidencia de entrega

## 📞 Soporte

Si encuentras algún problema o necesitas ayuda:
1. Revisa los logs de Django
2. Verifica que las migraciones se aplicaron correctamente
3. Asegúrate de que los templates están en la ruta correcta

---

**Implementado por**: Sistema Synkro
**Fecha**: 2025
**Versión**: 1.0
