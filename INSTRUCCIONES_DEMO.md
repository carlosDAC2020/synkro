# 🎯 Preparar Demo para el Cliente

## 📋 **Pasos para Preparar la Base de Datos**

### **Paso 1: Limpiar Base de Datos**

Este script elimina **todos los datos** excepto los usuarios:

```bash
python limpiar_base_datos.py
```

**⚠️ ADVERTENCIA:** Te pedirá confirmación. Escribe `SI` para continuar.

**Elimina:**
- ✅ Todas las ventas y detalles
- ✅ Todos los productos y categorías
- ✅ Todos los clientes y proveedores
- ✅ Todos los pedidos a proveedores
- ✅ Todas las sucursales y repartidores
- ✅ Todas las rutas de entrega

**Mantiene:**
- ✅ Usuarios del sistema

---

### **Paso 2: Generar Datos de Demo**

Este script crea datos realistas y completos para demostración:

```bash
python generar_datos_demo.py
```

**Genera:**

#### **📁 Categorías (5)**
- Alimentos
- Bebidas
- Aseo
- Cuidado Personal
- Snacks

#### **📦 Productos (18)**
Con datos completos:
- Nombre, SKU, precio, costo
- Stock actual y mínimo
- **Peso en kg** (para logística)
- **Volumen en m³** (para logística)

Ejemplos:
- Arroz Diana 500g - $2,500 (0.5 kg)
- Coca-Cola 2L - $5,500 (2.1 kg)
- Detergente Ariel 1kg - $12,000 (1.0 kg)

#### **🏢 Sucursales (3)**
- Sucursal Centro (Principal) - Calle 72 #45-23
- Sucursal Norte - Calle 98 #50-10
- Sucursal Sur - Calle 30 #40-15

Con coordenadas GPS reales de Barranquilla.

#### **🏍️ Repartidores (4)**
- Carlos Rodríguez
- María González
- Luis Martínez
- Ana López

Con teléfono, email y documento.

#### **👥 Clientes (10)**
Con nombre, teléfono, email y dirección completa.

#### **🏭 Proveedores (3)**
- Distribuidora La Costa
- Alimentos del Caribe
- Bebidas y Más

#### **💰 Ventas Completadas (15)**
Ventas históricas sin domicilio, con 2-5 productos cada una.
Fechas aleatorias de los últimos 30 días.

#### **🚚 Ventas Pendientes de Domicilio (10)**
Listas para planificar rutas:
- Estado: `PAGADA_PENDIENTE_ENTREGA`
- Con coordenadas GPS de Barranquilla
- Con dirección completa
- Prioridad: alta, media o baja
- 1-4 productos por venta

---

## 🎯 **Flujo Completo de Demo**

### **1. Preparación**
```bash
# Limpiar BD
python limpiar_base_datos.py

# Generar datos
python generar_datos_demo.py
```

### **2. Demostrar Módulo de Productos**
- Ver catálogo de 18 productos
- Mostrar alertas de stock bajo
- Crear/editar productos
- Mostrar cálculo de ganancias

### **3. Demostrar Módulo de Ventas**
- Crear nueva venta
- Agregar múltiples productos
- Calcular total automáticamente
- Marcar como "Requiere Domicilio"
- Agregar coordenadas GPS

### **4. Demostrar Módulo de Domicilios**

#### **a) Dashboard**
- Ver estadísticas: 0 planificadas, 0 en curso, 0 completadas
- Ver 10 ventas pendientes de domicilio

#### **b) Planificar Ruta**
1. Ir a "Domicilios" → "Planificar Nueva Ruta"
2. Seleccionar "Sucursal Centro"
3. Seleccionar repartidor (ej: Carlos Rodríguez)
4. Elegir fecha de entrega (hoy o mañana)
5. Ver mapa con 10 marcadores de ventas pendientes
6. Seleccionar 3-5 ventas (usar checkboxes)
7. Click "Calcular Ruta Óptima"
   - Ver ruta dibujada en el mapa
   - Ver distancia total (ej: 6.8 km)
   - Ver tiempo estimado (ej: 10 min)
   - Ver peso total
8. Revisar **Plan de Cargue LIFO** generado automáticamente
9. Click "Guardar Ruta"

#### **c) Ver Detalle de Ruta**
1. Ir a "Domicilios" → Ver ruta creada
2. Click "Ver Detalle"
3. Mostrar:
   - **Mapa interactivo** con la ruta completa
   - Marcadores numerados por orden de entrega
   - Información general (distancia, tiempo, paradas)
   - Plan de cargue LIFO completo
   - Lista de entregas pendientes

#### **d) Descargar Plan de Cargue**
1. Click "Descargar Plan de Cargue"
2. Mostrar PDF generado con:
   - Información de la ruta
   - Mapa de referencia (coordenadas)
   - Plan de cargue LIFO detallado
   - Instrucciones por posición

#### **e) Ejecutar Ruta**
1. Click "Iniciar Ruta" (estado: EN_CURSO)
2. Simular entregas:
   - Click "Marcar Entregado" en primera parada
   - Agregar observaciones (opcional)
   - Ver marcador cambiar a verde en el mapa
   - Repetir con 2-3 paradas más
3. Mostrar progreso: "3 de 5 completadas"
4. Intentar completar ruta → Ver mensaje de error
5. Marcar las 2 entregas restantes
6. Ver ruta completarse automáticamente

#### **f) Dashboard Actualizado**
- Ver estadísticas actualizadas
- Ver ruta en estado "Completada"

---

## 🎨 **Características a Destacar**

### **Planificación Inteligente**
- ✅ Cálculo de ruta óptima con OSRM
- ✅ Consideración de tráfico en tiempo real
- ✅ Visualización en mapa interactivo
- ✅ Filtros por prioridad

### **Plan de Cargue LIFO**
- ✅ Generación automática
- ✅ Lógica: Último en cargar, primero en entregar
- ✅ Cálculo de peso por producto
- ✅ Instrucciones claras por posición

### **Gestión de Rutas**
- ✅ Estados: Planificada → En Curso → Completada
- ✅ Tracking de tiempo real
- ✅ Validación: No se puede completar sin entregar todo
- ✅ Auto-completar al marcar última entrega

### **Reportes**
- ✅ PDF profesional con plan de cargue
- ✅ Mapa de referencia
- ✅ Información detallada por parada

### **Interfaz Moderna**
- ✅ Mapas interactivos con Leaflet
- ✅ Marcadores de colores por estado
- ✅ Diseño responsivo con Bootstrap 5
- ✅ Iconos con Font Awesome

---

## 📊 **Datos de Ejemplo**

### **Coordenadas de Barranquilla**
Todas las ventas tienen coordenadas GPS reales de diferentes zonas:
- Centro: Calle 72, Calle 76, Calle 85
- Norte: Calle 90, Calle 95, Calle 98
- Sur: Calle 30, Calle 68

### **Productos con Peso Real**
- Arroz 500g → 0.5 kg
- Coca-Cola 2L → 2.1 kg
- Detergente 1kg → 1.0 kg
- Agua 600ml → 0.6 kg

### **Rutas Realistas**
- Distancia: 5-10 km
- Tiempo: 8-15 min
- Paradas: 3-10
- Peso total: 5-20 kg

---

## 🐛 **Solución de Problemas**

### **Error: "No hay ventas pendientes"**
```bash
# Verificar estado de ventas
python manage.py shell
```
```python
from core.models import Venta
ventas = Venta.objects.filter(requiere_domicilio=True, estado='PAGADA_PENDIENTE_ENTREGA')
print(f"Ventas pendientes: {ventas.count()}")
```

### **Error: "No hay usuarios"**
```bash
python manage.py createsuperuser
```

### **Mapa no se muestra**
- Verificar conexión a internet (Leaflet usa CDN)
- Revisar consola del navegador

### **Regenerar datos desde cero**
```bash
# 1. Limpiar
python limpiar_base_datos.py

# 2. Generar nuevos datos
python generar_datos_demo.py
```

---

## 🎉 **¡Listo para el Demo!**

Con estos datos tendrás:
- ✅ 18 productos variados con peso y volumen
- ✅ 3 sucursales con GPS
- ✅ 4 repartidores activos
- ✅ 10 clientes con direcciones
- ✅ 15 ventas históricas
- ✅ **10 ventas listas para domicilio**

**Tiempo estimado de demo:** 15-20 minutos

**Funcionalidades a mostrar:**
1. Dashboard general (2 min)
2. Gestión de productos (3 min)
3. Crear venta con domicilio (3 min)
4. Planificar ruta con mapa (5 min)
5. Ejecutar ruta y marcar entregas (5 min)
6. Descargar PDF (2 min)

---

## 📝 **Notas Importantes**

1. **Coordenadas GPS:** Todas son de Barranquilla, Colombia
2. **OSRM:** Requiere conexión a internet
3. **PDF:** Incluye información del mapa (coordenadas)
4. **Peso y Volumen:** Configurados en todos los productos
5. **Estados:** Flujo completo implementado

**¡Disfruta tu demo!** 🚀
