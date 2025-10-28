### **Introducción: El Problema de Ruteo de Vehículos (VRP)**

El problema que estás resolviendo no es simplemente "encontrar la ruta más corta". Es una versión mucho más compleja y del mundo real conocida como el **Problema de Ruteo de Vehículos con Capacidades y Ventanas de Tiempo** (Capacitated Vehicle Routing Problem with Time Windows - CVRP-TW).

En el contexto de tu proyecto, se puede definir así:

> "Dado un conjunto de ventas (clientes) que deben ser atendidas desde una sucursal (depósito) por un único repartidor (vehículo) con capacidad limitada (en peso y volumen), y respetando las ventanas de tiempo de entrega preferidas por cada cliente, encontrar el orden de visita que **minimice el tiempo total de viaje**."

Este es un problema de optimización combinatoria clásico, y OR-Tools está diseñado específicamente para resolverlo de manera eficiente.

---

### **Herramientas y Ecosistema Tecnológico del Optimizador**

Para resolver un problema tan complejo, tu proyecto no utiliza una única herramienta, sino un ecosistema de tecnologías especializadas donde cada una cumple un rol fundamental. Pensemos en ello como un equipo de expertos que colaboran para planificar la ruta.

*   **Django (El Orquestador General):**
    *   **Qué es:** Tu framework de desarrollo web.
    *   **Su Rol en el Proyecto:** Django es el centro de mando. La vista `api_calcular_ruta_optima` actúa como el director de orquesta. Se encarga de:
        1.  Recibir la solicitud del usuario con las ventas, el repartidor y la sucursal.
        2.  Usar sus **Modelos** (`Venta`, `Repartidor`, `Sucursal`) para consultar la base de datos y obtener toda la información necesaria (capacidades, demandas, ventanas de tiempo, coordenadas).
        3.  Coordinar las llamadas a los otros servicios (OSRM y OR-Tools).
        4.  Formatear la solución final en un JSON y enviarla de vuelta al frontend para que sea visualizada.

*   **Google OR-Tools (El Cerebro de la Optimización):**
    *   **Qué es:** Una biblioteca de software de código abierto para resolver problemas de optimización combinatoria.
    *   **Su Rol en el Proyecto:** Es el componente más importante, el que realmente "piensa". Su trabajo es tomar los datos estructurados que Django le proporciona (la matriz de tiempos, las demandas, las capacidades, las ventanas horarias) y resolver el modelo matemático del VRP. Clases como `pywrapcp.RoutingModel` y funciones como `AddDimensionWithVehicleCapacity` y `SolveWithParameters` son las que implementan la función objetivo y las restricciones que describimos. **Su única salida es la secuencia óptima de paradas (ej: 0 -> 4 -> 2 -> 1 -> 3 -> 0).** No sabe nada de calles ni mapas, solo de nodos, costos y reglas.

*   **OSRM - Open Source Routing Machine (El Cartógrafo Experto en Rutas):**
    *   **Qué es:** Un motor de enrutamiento de alto rendimiento que utiliza datos de OpenStreetMap.
    *   **Su Rol en el Proyecto:** Es el experto en el mundo real. Cumple dos funciones vitales:
        1.  **Alimentar al Cerebro:** Antes de la optimización, Django le pregunta a OSRM (a través de su API `table`): "Dame una matriz con los tiempos de viaje entre todos estos puntos". El resultado es la `time_matrix` (`t_ij`), el dato más crucial para que OR-Tools pueda tomar buenas decisiones.
        2.  **Visualizar la Solución:** Una vez que OR-Tools ha decidido la secuencia óptima de paradas, Django le pregunta de nuevo a OSRM (a través de su API `route`): "Ahora, dame la geometría exacta del camino, las calles y las curvas para ir de la parada A a la B, luego a la C, en este orden específico". El resultado es el `geometry` que se dibuja en el mapa.

*   **Leaflet.js (El Lienzo Interactivo):**
    *   **Qué es:** Una biblioteca de JavaScript para crear mapas interactivos.
    *   **Su Rol en el Proyecto:** Es la capa de visualización en tu `planificador.html`. Se encarga de tomar los datos procesados que le envía Django (la geometría de la ruta de OSRM y la información de las paradas) y dibujarlos en el navegador del usuario, permitiéndole ver los marcadores, la línea de la ruta y la información en los popups.


### **El Modelo Matemático Formal**

Para entender lo que OR-Tools hace "por debajo", vamos a formalizar el problema con notación matemática. Esto te ayudará a ver cómo cada línea de tu código en `api_calcular_ruta_optima` se corresponde con una parte del modelo.

#### 1. Conjuntos y Parámetros (Los Datos de Entrada)

Estos son los datos fijos que le proporcionas al modelo, extraídos de tu base de datos y de la API de OSRM.

*   **Conjunto de Nodos (`N`):** Es el conjunto de todas las ubicaciones.
    *   `N = {0} ∪ C`
    *   Donde `{0}` representa el depósito, es decir, tu `Sucursal`.
    *   `C` es el conjunto de clientes a visitar, es decir, las `Ventas` seleccionadas. `C = {1, 2, ..., n}`.

*   **Vehículo (`k`):** En tu caso, es un único vehículo, tu `Repartidor`.

*   **Matriz de Costos (`t_ij`):** Es el costo de viajar del nodo `i` al nodo `j`.
    *   **En tu código:** Esta es la `time_matrix` que obtienes de OSRM. El costo es el **tiempo de viaje en segundos**.

*   **Demandas de los Clientes (`d`):** Cada cliente tiene una demanda que consume la capacidad del vehículo.
    *   `d_i^w`: Demanda de peso del cliente `i`. **En tu código:** `demands_kg` (el peso total de los productos de la venta `i`).
    *   `d_i^v`: Demanda de volumen del cliente `i`. **En tu código:** `demands_m3` (el volumen total de los productos de la venta `i`).
    *   La demanda del depósito es `d_0^w = 0` y `d_0^v = 0`.

*   **Capacidad del Vehículo (`Q`):** La capacidad máxima que el vehículo puede transportar.
    *   `Q^w`: Capacidad máxima en peso. **En tu código:** `vehicle_capacities_kg` (obtenido de `repartidor.capacidad_maxima_kg`).
    *   `Q^v`: Capacidad máxima en volumen. **En tu código:** `vehicle_capacities_m3` (obtenido de `repartidor.capacidad_maxima_m3`).

*   **Ventanas de Tiempo (`[e_i, l_i]`):** El intervalo de tiempo en el que el cliente `i` debe ser visitado.
    *   `e_i`: Hora de inicio más temprana (earliest).
    *   `l_i`: Hora de fin más tardía (latest).
    *   **En tu código:** `time_windows`. Calculas los segundos desde la medianoche para `venta.ventana_tiempo_inicio` y `venta.ventana_tiempo_fin`.

#### 2. Variables de Decisión (Lo que el Modelo debe Decidir)

Estas son las incógnitas que el solver de OR-Tools debe encontrar.

*   `x_ij`: Es una variable binaria.
    *   `x_ij = 1` si el repartidor viaja directamente del nodo `i` al nodo `j`.
    *   `x_ij = 0` en caso contrario.

*   `u_i`: Es una variable continua que representa el tiempo acumulado en la ruta al llegar al nodo `i`. En otras palabras, la hora de llegada al cliente `i`.

#### 3. Función Objetivo (Lo que se quiere Minimizar)

El objetivo principal es minimizar el tiempo total de viaje.

**Fórmula:**
$$
\text{Minimizar } Z = \sum_{i \in N} \sum_{j \in N} t_{ij} \cdot x_{ij}
$$

**Explicación:**
La fórmula suma los tiempos de viaje (`t_ij`) de todos los arcos (tramos entre nodos) que son parte de la solución (donde `x_ij = 1`).

**Correspondencia en tu Código:**
Esto se establece de forma muy directa aquí:

```python
# Se define la función que devuelve el costo (tiempo) entre dos puntos
def time_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return time_matrix[from_node][to_node]

transit_callback_index = routing.RegisterTransitCallback(time_callback)

# Se le dice al modelo que el costo de cada arco es el valor de time_callback
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
```
El solver de OR-Tools, por defecto, intentará encontrar una ruta que minimice la suma de los costos de todos los arcos. Al definir el costo como el tiempo de viaje, estás implementando directamente esta función objetivo.

#### 4. Restricciones (Las Reglas del Juego)

Estas son las condiciones que la solución final DEBE cumplir. Si no se cumplen, la solución no es válida.

##### **Restricción 1: Flujo y Visita**
*   Cada cliente debe ser visitado exactamente una vez.
*   El vehículo debe salir del depósito y regresar a él.

**Fórmula:**
$$
\sum_{i \in N, i \neq j} x_{ij} = 1, \quad \forall j \in C \quad \text{(A cada cliente se llega una vez)}
$$
$$
\sum_{j \in N, j \neq i} x_{ij} = 1, \quad \forall i \in C \quad \text{(De cada cliente se sale una vez)}
$$
$$
\sum_{j \in C} x_{0j} = 1 \quad \text{(El vehículo sale del depósito una vez)}
$$
$$
\sum_{i \in C} x_{i0} = 1 \quad \text{(El vehículo regresa al depósito una vez)}
$$

**Correspondencia en tu Código:**
OR-Tools maneja esto de forma implícita y elegante. Al definir el modelo con `pywrapcp.RoutingModel` y un único vehículo, la estructura misma del problema que resuelve garantiza que se formará una única ruta que empieza y termina en el depósito (`0`) y pasa por un subconjunto de los nodos (`C`). La solución que devuelve es, por definición, una secuencia de visitas, cumpliendo estas reglas.

##### **Restricción 2: Capacidad del Vehículo**
La suma de las demandas (peso y volumen) de los clientes en la ruta no puede exceder la capacidad del vehículo.

**Correspondencia en tu Código:**
Esta es una de las restricciones más claras en tu implementación. Usas "Dimensiones" en OR-Tools, que son variables que pueden acumularse a lo largo de la ruta.

*   **Para el Peso:**
    ```python
    def demand_callback_kg(from_index):
        return demands_kg[manager.IndexToNode(from_index)]
    
    demand_callback_index_kg = routing.RegisterUnaryTransitCallback(demand_callback_kg)
    
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index_kg,
        0,  # slack_max (no se permite sobrecarga)
        vehicle_capacities_kg, # Array con las capacidades
        True,  # start_cumul_to_zero (la carga empieza en 0)
        'CapacityKG' # Nombre de la dimensión
    )
    ```
    **Explicación:** Creas una dimensión llamada `CapacityKG`. Para cada nodo de la ruta, el solver llama a `demand_callback_kg` para saber cuánto peso se añade y lo acumula. La restricción `AddDimensionWithVehicleCapacity` se asegura de que este valor acumulado nunca supere `vehicle_capacities_kg[0]`.

*   **Para el Volumen:** Se hace exactamente lo mismo para `CapacityM3` y `demands_m3`.

##### **Restricción 3: Ventanas de Tiempo**
La llegada a cada cliente `i` debe ocurrir dentro de su ventana de tiempo `[e_i, l_i]`.

**Fórmula:**
$$
u_i + t_{ij} \le u_j, \quad \forall (i, j) \text{ donde } x_{ij} = 1 \quad \text{(Consistencia del tiempo)}
$$
$$
e_i \le u_i \le l_i, \quad \forall i \in C \quad \text{(Cumplimiento de la ventana)}
$$

**Correspondencia en tu Código:**
De nuevo, se utiliza una dimensión, esta vez para el tiempo acumulado.

```python
# Se añade la dimensión para el tiempo
routing.AddDimension(
    transit_callback_index, # Cómo se incrementa el tiempo (viajando)
    3600,  # slack_max (tiempo máximo de espera en un nodo)
    86400, # capacity (horizonte de tiempo total del día en segundos)
    False, # start_cumul_to_zero
    'Time'
)
time_dimension = routing.GetDimensionOrDie('Time')

# Se aplica la restricción para cada localización
for loc_idx, time_win in enumerate(time_windows):
    if loc_idx == 0: continue # No hay ventana para el depósito
    index = manager.NodeToIndex(loc_idx)
    time_dimension.CumulVar(index).SetRange(time_win[0], time_win[1])
```
**Explicación:**
1.  `AddDimension` crea una variable `u_i` (llamada `CumulVar` internamente) para cada nodo. Esta variable acumula el tiempo de viaje (`transit_callback_index`).
2.  El bucle `for` itera sobre cada cliente y usa `SetRange(e_i, l_i)` para establecer la restricción de que el valor de la variable de tiempo acumulado (`u_i`) para ese nodo debe estar entre los límites de su ventana de tiempo.

### **Resumen del Proceso en tu Vista `api_calcular_ruta_optima`**

1.  **Preparación (Parámetros del Modelo):**
    *   Recibes los `ventas_ids`, `sucursal_id`, y `repartidor_id`.
    *   Consultas la base de datos para obtener los objetos y sus propiedades (coordenadas, demandas de peso/volumen, ventanas de tiempo). Defines los conjuntos `N` y `C`, los parámetros `d_i`, `Q`, y `[e_i, l_i]`.
    *   Llamas a OSRM para construir la matriz de costos `t_ij`.

2.  **Construcción del Modelo (En OR-Tools):**
    *   `manager = pywrapcp.RoutingIndexManager(...)`: Inicializas la estructura del problema.
    *   `routing = pywrapcp.RoutingModel(manager)`: Creas el objeto principal del modelo.
    *   `routing.SetArcCostEvaluatorOfAllVehicles(...)`: Defnes la **Función Objetivo**.
    *   `routing.AddDimensionWithVehicleCapacity(...)`: Añades las **Restricciones de Capacidad**.
    *   `routing.AddDimension(...)` y `time_dimension.CumulVar(...).SetRange(...)`: Añades las **Restricciones de Ventanas de Tiempo**.

3.  **Resolución:**
    *   `search_parameters = pywrapcp.DefaultRoutingSearchParameters()`: Configuras el comportamiento del algoritmo de búsqueda. `PATH_CHEAPEST_ARC` es una heurística para encontrar una primera solución rápida, y `GUIDED_LOCAL_SEARCH` es una metaheurística más avanzada para mejorar esa solución hasta encontrar un óptimo local (o global, si tiene tiempo).
    *   `solution = routing.SolveWithParameters(search_parameters)`: **Aquí ocurre la magia.** El solver explora el inmenso espacio de posibles rutas, descartando las que violan las restricciones y buscando la que minimiza la función objetivo. Te devuelve la mejor que encontró.

4.  **Post-Procesamiento (Interpretación de la Solución):**
    *   El resto del código extrae la secuencia de nodos de la `solution`, la cual representa los valores óptimos de las variables `x_ij`.
    *   Usa esta secuencia para obtener la geometría detallada de OSRM, generar el plan de cargue (LIFO: Last-In, First-Out, que es la estrategia correcta para un único compartimento de carga), y preparar la respuesta JSON para tu frontend.

