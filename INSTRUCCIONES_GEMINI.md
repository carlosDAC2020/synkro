# 🤖 Análisis Inteligente de Carga con Gemini

## 📋 Características Implementadas

### 1. **Modal de Generación de Reporte**
- ✅ Modal con spinner animado
- ✅ Barra de progreso con estados
- ✅ Previene múltiples clicks
- ✅ Feedback visual al usuario

### 2. **Análisis con Gemini + LangChain**
- ✅ Análisis de peso y volumen
- ✅ Análisis de productos y compatibilidad
- ✅ Recomendaciones priorizadas (Alta/Media/Baja)
- ✅ Consideraciones especiales
- ✅ Nivel de complejidad de la carga

### 3. **Reporte PDF Mejorado**
- ✅ Sección de análisis inteligente
- ✅ Recomendaciones con colores según prioridad
- ✅ Resumen ejecutivo
- ✅ Consideraciones especiales destacadas

## 🚀 Instalación

### 1. Instalar dependencias

```bash
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar API Key de Gemini

La API key ya está configurada en tu archivo `.env`:

```env
GEMINI_API_KEY=AIzaSyBEgA-7FQjO8YzKBH8akPB2wqQoBLZU2p0
```

### 3. Aplicar migraciones (si es necesario)

```bash
python manage.py migrate
```

## 📖 Uso

### Generar Reporte con Análisis IA

1. Ve a **Domicilios** → **Rutas**
2. Selecciona una ruta existente
3. Click en **"Descargar Plan de Cargue"**
4. Verás el modal de generación con progreso
5. El PDF se descargará con el análisis de Gemini incluido

## 📄 Estructura del Análisis

El análisis de Gemini incluye:

### 1. **Resumen Ejecutivo**
Visión general de la carga y la ruta

### 2. **Nivel de Complejidad**
- 🟢 **Bajo**: Carga simple, pocas paradas
- 🟡 **Medio**: Carga moderada, requiere atención
- 🔴 **Alto**: Carga compleja, requiere planificación detallada

### 3. **Análisis de Peso y Volumen**
- Distribución de peso
- Balance del vehículo
- Optimización del espacio

### 4. **Análisis de Productos**
- Compatibilidad entre productos
- Productos frágiles o especiales
- Recomendaciones de empaque

### 5. **Recomendaciones Priorizadas**
Cada recomendación incluye:
- **Título**: Descripción corta
- **Descripción**: Detalles de la recomendación
- **Prioridad**: Alta (🔴), Media (🟡), Baja (🟢)
- **Categoría**: Seguridad, Eficiencia, Optimización, etc.

### 6. **Consideraciones Especiales**
Puntos importantes a tener en cuenta durante la carga y entrega

## 🔧 Troubleshooting

### Error: "GEMINI_API_KEY no está configurada"

**Solución**: Verifica que el archivo `.env` tenga la API key:
```env
GEMINI_API_KEY=tu_api_key_aqui
```

### Error: "Module 'langchain' not found"

**Solución**: Instala las dependencias:
```bash
pip install langchain langchain-google-genai google-generativeai
```

### El análisis no aparece en el PDF

**Solución**: 
1. Verifica que la API key sea válida
2. Revisa los logs de Django para ver errores
3. El sistema tiene un fallback que genera un análisis básico si Gemini falla

## 🎨 Personalización

### Modificar el Prompt de Gemini

Edita el archivo `core/services/gemini_analyzer.py`:

```python
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Tu prompt personalizado aquí..."""),
    ("human", """...""")
])
```

### Cambiar Colores del PDF

Edita `core/views.py` en la función `ruta_descargar_plan_cargue`:

```python
prioridad_colors = {
    'Alta': colors.HexColor('#tu_color'),
    'Media': colors.HexColor('#tu_color'),
    'Baja': colors.HexColor('#tu_color')
}
```

## 📊 Ejemplo de Salida

El PDF generado incluirá:

```
📄 PLAN DE CARGUE - RUTA #3
├── 📋 Información General
├── 📍 Resumen de Entregas
├── 🗺️ Instrucciones de Navegación
├── 🤖 ANÁLISIS INTELIGENTE DE CARGA
│   ├── Resumen Ejecutivo
│   ├── Nivel de Complejidad
│   ├── Análisis de Peso y Volumen
│   ├── Análisis de Productos
│   ├── 💡 Recomendaciones (priorizadas)
│   └── ⚠️ Consideraciones Especiales
└── 📦 ORDEN DE CARGA (LIFO)
    ├── Posición 1 → Parada 3
    ├── Posición 2 → Parada 2
    └── Posición 3 → Parada 1
```

## 🔐 Seguridad

- ✅ La API key está en `.env` (no en el código)
- ✅ El archivo `.env` está en `.gitignore`
- ✅ Manejo de errores con fallback
- ✅ Timeout configurado para evitar bloqueos

## 📝 Notas

- El análisis se genera en tiempo real al descargar el PDF
- Si Gemini falla, se genera un análisis básico automáticamente
- El modal muestra progreso simulado para mejor UX
- Los lints en el template son falsos positivos del IDE

## 🎯 Próximas Mejoras

- [ ] Cache de análisis para rutas ya analizadas
- [ ] Análisis comparativo entre rutas
- [ ] Sugerencias de re-optimización
- [ ] Integración con datos históricos
- [ ] Análisis de eficiencia post-entrega
