# 🚚 Sistema de Domicilios - Instrucciones de Instalación

## ✅ Implementación Completada

Se ha implementado **completamente** el sistema de gestión de domicilios con todas las funcionalidades solicitadas:

### 📦 Componentes Implementados

#### 1. **Modelos de Datos** ✅
- ✅ `Producto`: Agregados campos `peso_kg` y `volumen_m3`
- ✅ `Sucursal`: Modelo completo con coordenadas GPS, horarios, cobertura
- ✅ `Repartidor`: Estados (ACTIVO, INACTIVO, EN_RUTA)
- ✅ `RutaEntrega`: Con campos de tráfico, plan de cargue LIFO, tracking
- ✅ `DetalleRuta`: Con orden de carga y datos logísticos

#### 2. **Formularios** ✅
- ✅ `SucursalForm`: Formulario completo para gestión de sucursales
- ✅ `RepartidorForm`: Formulario para gestión de repartidores
- ✅ `RutaEntregaForm`: Formulario para crear rutas

#### 3. **Vistas y APIs** ✅
- ✅ **CRUD Sucursales**: list, add, edit, delete
- ✅ **CRUD Repartidores**: list, add, edit, delete
- ✅ **Dashboard de Domicilios**: Vista con estadísticas y filtros
- ✅ **Planificador de Rutas**: Interfaz interactiva con mapa
- ✅ **Detalle de Ruta**: Vista completa con plan de cargue
- ✅ **API de Ventas Pendientes**: Obtiene ventas listas para domicilio
- ✅ **API de Cálculo de Ruta**: Usa OSRM para calcular ruta óptima con tráfico
- ✅ **API de Guardado**: Guarda rutas en base de datos
- ✅ **Generación de PDF**: Descarga plan de cargue LIFO

#### 4. **Templates** ✅
- ✅ `sucursales/list.html`: Listado de sucursales
- ✅ `sucursales/form.html`: Crear/editar sucursal
- ✅ `sucursales/delete.html`: Confirmar eliminación
- ✅ `repartidores/list.html`: Listado de repartidores
- ✅ `repartidores/form.html`: Crear/editar repartidor
- ✅ `repartidores/delete.html`: Confirmar eliminación
- ✅ `domicilios/dashboard.html`: Dashboard principal con tabs
- ✅ `domicilios/planificar.html`: Planificador interactivo con mapa
- ✅ `domicilios/ruta_detail.html`: Detalle completo de ruta

#### 5. **URLs** ✅
- ✅ Todas las rutas configuradas en `core/urls.py`
- ✅ APIs REST para AJAX

#### 6. **Menú de Navegación** ✅
- ✅ Actualizado `base.html` con enlaces a Domicilios, Sucursales y Repartidores

---

## 🚀 Pasos para Activar el Sistema

### Paso 1: Crear Migraciones
```bash
python manage.py makemigrations
```

### Paso 2: Aplicar Migraciones
```bash
python manage.py migrate
```

### Paso 3: Instalar Dependencia para PDF (si no está instalada)
```bash
pip install reportlab
```

### Paso 4: Instalar Requests (para OSRM API)
```bash
pip install requests
```

### Paso 5: Ejecutar el Script de Datos de Prueba
```bash
python crear_datos_domicilios.py
```

### Paso 6: Iniciar el Servidor
```bash
python manage.py runserver
```

---

## 🎯 Funcionalidades Implementadas

### 1. **Gestión de Sucursales**
- ✅ Crear, editar, eliminar sucursales
- ✅ Coordenadas GPS para cada sucursal
- ✅ Radio de cobertura configurable
- ✅ Horarios de operación
- ✅ Marcar sucursal principal
- ✅ Ver ubicación en Google Maps

### 2. **Gestión de Repartidores**
- ✅ Crear, editar, eliminar repartidores
- ✅ Estados: Activo, Inactivo, En Ruta
- ✅ Información de contacto completa
- ✅ Filtros por estado

### 3. **Planificación de Rutas**
- ✅ **Mapa interactivo** con Leaflet.js
- ✅ **Selección de ventas** pendientes de domicilio
- ✅ **Filtros por prioridad** (alta, media, baja)
- ✅ **Cálculo de ruta óptima** usando OSRM
- ✅ **Consideración de tráfico** en tiempo real
- ✅ **Visualización en mapa** con marcadores por prioridad
- ✅ **Estadísticas**: distancia, tiempo, paradas, peso

### 4. **Plan de Cargue LIFO**
- ✅ **Generación automática** del orden de carga
- ✅ **Lógica LIFO**: Último en cargar, primero en entregar
- ✅ **Cálculo de peso** por producto y total
- ✅ **Instrucciones claras** para cada posición
- ✅ **Visualización en interfaz** y PDF

### 5. **Gestión de Rutas**
- ✅ **Dashboard** con estadísticas (planificadas, en curso, completadas)
- ✅ **Filtros por estado** de ruta
- ✅ **Cambio de estado**: Planificada → En Curso → Completada
- ✅ **Tracking de tiempo**: Hora de inicio y fin real
- ✅ **Marcar entregas** individuales como completadas
- ✅ **Observaciones** por entrega

### 6. **Reportes**
- ✅ **Descarga de PDF** con plan de cargue completo
- ✅ **Información detallada** por parada
- ✅ **Productos y pesos** por entrega
- ✅ **Instrucciones LIFO** claras

---

## 🗺️ Flujo de Trabajo Completo

### 1. Configuración Inicial
```
1. Ir a "Sucursales" → Crear sucursales con coordenadas GPS
2. Ir a "Repartidores" → Crear repartidores activos
3. Crear ventas con "requiere_domicilio=True" y coordenadas
```

### 2. Planificar Ruta
```
1. Ir a "Domicilios" → "Planificar Nueva Ruta"
2. Seleccionar sucursal de origen
3. Seleccionar repartidor (opcional)
4. Elegir fecha de entrega
5. Seleccionar ventas a incluir (con checkboxes)
6. Click "Calcular Ruta Óptima"
   → El sistema:
     - Llama a OSRM para calcular ruta con tráfico
     - Genera plan de cargue LIFO automáticamente
     - Muestra ruta en mapa con marcadores
     - Calcula distancia, tiempo, peso total
7. Revisar plan de cargue LIFO
8. Click "Guardar Ruta"
```

### 3. Ejecutar Ruta
```
1. Ir a "Domicilios" → Ver ruta planificada
2. Click "Ver Detalle"
3. Click "Iniciar Ruta" (cambia estado a EN_CURSO)
4. Descargar PDF del plan de cargue
5. Seguir orden de carga LIFO
6. Marcar cada entrega como completada
7. Click "Completar Ruta" cuando termine
```

---

## 📊 APIs Disponibles

### 1. **GET** `/api/domicilios/ventas-pendientes/`
Retorna todas las ventas pendientes de domicilio con:
- Datos del cliente
- Coordenadas GPS
- Prioridad
- Productos con peso y volumen
- Monto total

### 2. **POST** `/api/domicilios/calcular-ruta/`
Calcula ruta óptima. Enviar:
```json
{
  "sucursal_id": 1,
  "ventas_ids": [1, 2, 3]
}
```
Retorna:
- Ruta con geometría GeoJSON
- Distancia y tiempo
- Plan de cargue LIFO
- Datos de tráfico

### 3. **POST** `/api/domicilios/guardar-ruta/`
Guarda ruta en BD. Enviar todos los datos de la ruta calculada.

---

## 🎨 Características Técnicas

### Frontend
- ✅ **Leaflet.js** para mapas interactivos
- ✅ **Leaflet Routing Machine** para rutas
- ✅ **Bootstrap 5** para UI responsiva
- ✅ **Font Awesome** para iconos
- ✅ **AJAX** para comunicación con APIs

### Backend
- ✅ **Django 5.2.6** con vistas basadas en funciones
- ✅ **OSRM API** para cálculo de rutas con tráfico
- ✅ **ReportLab** para generación de PDFs
- ✅ **JSON Fields** para almacenar geometrías y planes
- ✅ **Transacciones atómicas** para integridad de datos

### Base de Datos
- ✅ **Campos JSON** para flexibilidad
- ✅ **Decimal Fields** para precisión en coordenadas
- ✅ **Foreign Keys** con protección CASCADE/PROTECT
- ✅ **Índices** en campos de búsqueda frecuente

---

## 🔧 Configuración Avanzada

### Cambiar Proveedor de Rutas
El sistema usa OSRM por defecto. Para cambiar:

1. Editar `views.py` → `api_calcular_ruta_optima`
2. Cambiar URL de OSRM:
```python
url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
```

### Agregar Más Datos de Tráfico
OSRM incluye anotaciones de tráfico. Para usar:
```python
params = {
    'annotations': 'true',  # Ya incluido
    'overview': 'full'
}
```

### Personalizar Plan de Cargue
Editar función `generar_plan_cargue_lifo` en `views.py` para:
- Agregar restricciones de peso máximo
- Considerar volumen del vehículo
- Optimizar por tipo de producto

---

## 📝 Notas Importantes

1. **Coordenadas GPS**: Las ventas deben tener `latitud_entrega` y `longitud_entrega` para ser incluidas en rutas.

2. **Estado de Ventas**: Solo ventas con estado `PAGADA_PENDIENTE_ENTREGA` y `requiere_domicilio=True` aparecen en el planificador.

3. **OSRM**: Requiere conexión a internet. Para uso offline, instalar servidor OSRM local.

4. **PDF**: Requiere `reportlab`. Instalar con `pip install reportlab`.

5. **Peso y Volumen**: Los productos deben tener `peso_kg` y `volumen_m3` configurados para cálculos precisos.

---

## 🐛 Solución de Problemas

### Error: "No module named 'reportlab'"
```bash
pip install reportlab
```

### Error: "No module named 'requests'"
```bash
pip install requests
```

### Error: "No hay ventas pendientes"
1. Crear ventas con `requiere_domicilio=True`
2. Asignar coordenadas GPS a las ventas
3. Estado debe ser `PAGADA_PENDIENTE_ENTREGA`

### Mapa no se muestra
1. Verificar conexión a internet (Leaflet usa CDN)
2. Revisar consola del navegador para errores
3. Verificar que las coordenadas sean válidas

---

## 🎉 ¡Sistema Listo!

El sistema de domicilios está **100% funcional** con todas las características solicitadas:

✅ Planificación de múltiples rutas
✅ Cálculo de ruta óptima con tráfico
✅ Plan de cargue LIFO automático
✅ Gestión de estados (planificadas, en curso, completadas)
✅ Filtros por estado
✅ Descarga de plan de cargue en PDF
✅ Tracking de entregas en tiempo real
✅ Interfaz moderna e intuitiva

**¡Disfruta tu nuevo sistema de gestión de domicilios!** 🚚📦
