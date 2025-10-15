"""
Servicio de análisis inteligente de carga usando Gemini y LangChain
"""
import os
from typing import Dict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class PasoMontaje(BaseModel):
    """Paso específico de montaje"""
    numero: int = Field(description="Número del paso")
    accion: str = Field(description="Acción a realizar en lenguaje sencillo")
    razon: str = Field(description="Por qué es importante este paso")
    ubicacion: str = Field(description="Dónde colocar en el vehículo (adelante, atrás, izquierda, derecha, arriba, abajo)")


class RecomendacionCarga(BaseModel):
    """Modelo de recomendación de carga"""
    titulo: str = Field(description="Título corto y claro")
    descripcion: str = Field(description="Descripción práctica en lenguaje sencillo para repartidores")
    prioridad: str = Field(description="Alta, Media o Baja")
    categoria: str = Field(description="Seguridad, Orden, Cuidado, Tiempo, etc.")


class AnalisisCarga(BaseModel):
    """Modelo completo del análisis de carga"""
    resumen_para_repartidor: str = Field(description="Resumen en lenguaje sencillo para el repartidor")
    pasos_montaje: List[PasoMontaje] = Field(description="Pasos detallados de cómo cargar el vehículo")
    distribucion_peso: str = Field(description="Cómo distribuir el peso en el vehículo (lenguaje sencillo)")
    productos_especiales: List[str] = Field(description="Productos que necesitan cuidado especial con el nombre del producto y cliente específico")
    recomendaciones: List[RecomendacionCarga] = Field(description="4-5 recomendaciones CLAVE basadas en los productos específicos")
    checklist_antes_salir: List[str] = Field(description="Lista de verificación antes de salir (5 items)")
    tips_entrega: List[str] = Field(description="Consejos para las entregas (3-4 tips)")
    tiempo_estimado_carga: str = Field(description="Tiempo estimado para cargar el vehículo")
    nivel_dificultad: str = Field(description="Fácil, Normal o Difícil")


class GeminiCargaAnalyzer:
    """Analizador de carga usando Gemini"""
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=api_key,
            temperature=0.3
        )
        
        self.parser = PydanticOutputParser(pydantic_object=AnalisisCarga)
    
    def analizar_carga(self, plan_cargue: List[Dict], ruta_info: Dict) -> AnalisisCarga:
        """
        Analiza el plan de cargue y genera recomendaciones inteligentes
        
        Args:
            plan_cargue: Lista de items del plan de cargue
            ruta_info: Información de la ruta (distancia, tiempo, paradas)
        
        Returns:
            AnalisisCarga con el análisis completo
        """
        
        # Preparar datos para el prompt
        total_peso = sum(item.get('peso_total_kg', 0) for item in plan_cargue)
        total_volumen = sum(item.get('volumen_total_m3', 0) for item in plan_cargue)
        num_paradas = len(plan_cargue)
        
        # Extraer información de productos
        productos_info = []
        for idx, item in enumerate(plan_cargue, 1):
            productos_list = []
            for prod in item.get('productos', []):
                productos_list.append(f"{prod['cantidad']}x {prod['nombre']} ({prod['peso_kg']}kg)")
            
            productos_info.append({
                'orden_carga': item.get('orden_carga'),
                'orden_entrega': item.get('orden_entrega'),
                'cliente': item.get('cliente'),
                'peso_kg': item.get('peso_total_kg'),
                'volumen_m3': item.get('volumen_total_m3'),
                'productos': productos_list
            })
        
        # Crear el prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Eres un supervisor de logística experimentado que entrena a repartidores. 
Tu trabajo es crear una GUÍA PRÁCTICA Y DETALLADA para que el repartidor sepa EXACTAMENTE cómo cargar 
el vehículo y hacer las entregas de forma eficiente y segura.

IMPORTANTE:
- Usa lenguaje SENCILLO y CLARO (evita términos técnicos complejos)
- Da instrucciones PASO A PASO muy específicas
- ANALIZA LOS PRODUCTOS ESPECÍFICOS que se van a entregar
- Identifica productos que necesitan cuidado especial (electrónicos, frágiles, pesados, líquidos, etc.)
- Menciona el NOMBRE DEL PRODUCTO y el CLIENTE cuando des recomendaciones específicas
- Explica el POR QUÉ de cada recomendación
- Considera el orden LIFO (lo último que se carga se entrega primero)
- Da SOLO 4-5 recomendaciones CLAVE (las más importantes según los productos)
- Sé ESPECÍFICO sobre dónde colocar cada cosa en el vehículo

El repartidor necesita saber:
1. Cómo cargar el vehículo paso a paso
2. Dónde poner cada cosa según el tipo de producto
3. Qué productos específicos necesitan cuidado especial
4. Qué verificar antes de salir
5. Tips para las entregas

{format_instructions}"""),
            ("human", """Crea una guía completa de carga para el repartidor:

📊 INFORMACIÓN DE LA RUTA:
- Distancia total: {distancia_km} km
- Tiempo estimado: {tiempo_min} minutos
- Número de paradas: {num_paradas}
- Peso total: {total_peso} kg
- Volumen total: {total_volumen} m³

📦 PLAN DE CARGUE (LIFO - Último en cargar, primero en entregar):
{productos_detalle}

ANALIZA LOS PRODUCTOS Y GENERA:
1. Resumen sencillo para el repartidor
2. Pasos específicos de montaje (paso a paso, con ubicación exacta)
3. Cómo distribuir el peso según los productos
4. Lista de productos especiales con NOMBRE DEL PRODUCTO y CLIENTE (ej: "Laptop Dell para Cliente Juan - Proteger de golpes")
5. SOLO 4-5 recomendaciones CLAVE basadas en los productos específicos
6. Checklist antes de salir (5 items esenciales)
7. Tips para las entregas (3-4 tips prácticos)
8. Tiempo estimado de carga

IMPORTANTE: 
- Menciona productos específicos por nombre cuando des recomendaciones
- Si hay electrónicos, menciónalos y di cómo cuidarlos
- Si hay productos pesados, menciónalos y di cómo cargarlos
- Si hay productos frágiles, menciónalos y di cómo protegerlos
- Sé ESPECÍFICO con nombres de productos y clientes""")
        ])
        
        # Formatear detalles de productos
        productos_detalle = ""
        for info in productos_info:
            productos_detalle += f"\n📦 POSICIÓN DE CARGA {info['orden_carga']} → PARADA {info['orden_entrega']}\n"
            productos_detalle += f"   Cliente: {info['cliente']}\n"
            productos_detalle += f"   Peso: {info['peso_kg']} kg | Volumen: {info['volumen_m3']} m³\n"
            productos_detalle += f"   Productos:\n"
            for prod in info['productos']:
                productos_detalle += f"      - {prod}\n"
        
        # Crear el chain
        chain = prompt_template | self.llm | self.parser
        
        # Ejecutar análisis
        try:
            resultado = chain.invoke({
                "format_instructions": self.parser.get_format_instructions(),
                "distancia_km": ruta_info.get('distancia_km', 0),
                "tiempo_min": ruta_info.get('tiempo_min', 0),
                "num_paradas": num_paradas,
                "total_peso": round(total_peso, 2),
                "total_volumen": round(total_volumen, 3),
                "productos_detalle": productos_detalle
            })
            
            return resultado
            
        except Exception as e:
            # Si falla el parsing, crear un análisis básico
            print(f"Error en análisis con Gemini: {e}")
            return self._crear_analisis_basico(plan_cargue, ruta_info)
    
    def _crear_analisis_basico(self, plan_cargue: List[Dict], ruta_info: Dict) -> AnalisisCarga:
        """Crea un análisis básico si falla Gemini"""
        total_peso = sum(item.get('peso_total_kg', 0) for item in plan_cargue)
        num_paradas = len(plan_cargue)
        
        # Analizar productos específicos
        productos_especiales = []
        productos_pesados = []
        todos_productos = []
        
        for item in plan_cargue:
            cliente = item.get('cliente', 'cliente')
            for prod in item.get('productos', []):
                nombre_prod = prod.get('nombre', '').lower()
                peso_prod = prod.get('peso_kg', 0) * prod.get('cantidad', 1)
                todos_productos.append(f"{prod.get('nombre')} para {cliente}")
                
                # Detectar productos especiales
                if any(palabra in nombre_prod for palabra in ['laptop', 'computador', 'tablet', 'celular', 'electrónico', 'tv', 'monitor']):
                    productos_especiales.append(f"{prod.get('nombre')} para {cliente} - Proteger de golpes y humedad")
                elif any(palabra in nombre_prod for palabra in ['vidrio', 'cristal', 'frágil', 'cerámica']):
                    productos_especiales.append(f"{prod.get('nombre')} para {cliente} - Manejar con cuidado, es frágil")
                elif peso_prod > 10:
                    productos_pesados.append(f"{prod.get('nombre')} para {cliente} ({peso_prod:.1f} kg)")
        
        # Crear pasos de montaje con productos específicos
        pasos = []
        for idx, item in enumerate(reversed(plan_cargue), 1):
            productos_lista = ", ".join([p.get('nombre', '') for p in item.get('productos', [])])
            pasos.append(PasoMontaje(
                numero=idx,
                accion=f"Cargar {productos_lista} para {item.get('cliente', 'cliente')}",
                razon=f"Se entrega en la parada {item.get('orden_entrega')}, por eso se carga en posición {item.get('orden_carga')}",
                ubicacion="Al fondo del vehículo" if idx == 1 else "Más cerca de la puerta" if idx == num_paradas else "En el medio"
            ))
        
        # Crear recomendaciones basadas en productos
        recomendaciones = [
            RecomendacionCarga(
                titulo="Carga en orden inverso (LIFO)",
                descripcion="Lo último que cargues será lo primero que entregues. Empieza cargando lo de la última parada.",
                prioridad="Alta",
                categoria="Orden"
            ),
            RecomendacionCarga(
                titulo="Pesados abajo, livianos arriba",
                descripcion="Coloca las cajas pesadas en el piso del vehículo y las livianas encima. Así evitas que se aplasten.",
                prioridad="Alta",
                categoria="Seguridad"
            )
        ]
        
        # Agregar recomendaciones específicas según productos
        if productos_especiales:
            recomendaciones.append(RecomendacionCarga(
                titulo="Cuidado con productos delicados",
                descripcion=f"Tienes productos que necesitan cuidado especial. Colócalos donde no se golpeen.",
                prioridad="Alta",
                categoria="Cuidado"
            ))
        
        if productos_pesados:
            recomendaciones.append(RecomendacionCarga(
                titulo="Productos pesados al centro",
                descripcion=f"Coloca los productos pesados en el centro del vehículo para mejor balance.",
                prioridad="Media",
                categoria="Seguridad"
            ))
        
        recomendaciones.append(RecomendacionCarga(
            titulo="Asegura bien la carga",
            descripcion="Usa cuerdas o correas para que nada se mueva durante el viaje.",
            prioridad="Media",
            categoria="Seguridad"
        ))
        
        return AnalisisCarga(
            resumen_para_repartidor=f"Tienes {num_paradas} entregas con un total de {total_peso:.2f} kg. Recuerda: lo último que cargues será lo primero que entregues.",
            pasos_montaje=pasos,
            distribucion_peso="Coloca los productos más pesados abajo y al centro del vehículo. Los más livianos arriba. Distribuye el peso de forma pareja entre izquierda y derecha.",
            productos_especiales=productos_especiales if productos_especiales else ["No hay productos que requieran cuidado especial"],
            recomendaciones=recomendaciones[:5],  # Máximo 5
            checklist_antes_salir=[
                "✓ Todos los productos están cargados y bien asegurados",
                "✓ Tienes las direcciones de todas las entregas",
                "✓ Tu celular tiene batería y señal",
                "✓ El vehículo tiene suficiente combustible",
                "✓ Revisaste que no falte ningún producto"
            ],
            tips_entrega=[
                "Llama al cliente antes de llegar para confirmar que está",
                "Estaciona en un lugar seguro",
                "Revisa bien el nombre del cliente antes de entregar",
                "Pide firma o foto como comprobante"
            ],
            tiempo_estimado_carga="15-20 minutos aproximadamente",
            nivel_dificultad="Normal"
        )
