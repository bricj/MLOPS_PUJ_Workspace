# Taller # 5 - Pruebas de carga con locust

El servicio de locust se ha levantado en un docker compose difererente a los demás servicios. Por tal motivo, es hace necesario conectar mediante redes externas de docker los archivos compose. Para ello debes ejecutar la siguiente sentencia:

``` docker network create --driver bridge my_shared_network``` 

Con la anterior instrucción, se ha creado una red externa que conecta los dos archivos compose. De esta manera, se establece comunicación entre locust y el endpoint de inferencia expuesto a través de FASTAPI.

Además, en los dos compose se debe agregar:

networks:
  my_shared_network:
    external: true

## Pruebas con una sola instancia del servicio API

1. Primer escenario: 10.000 usuarios y 500 peticiones

La primera prueba realizada se hizo limitando a **10 gigas** la memoria del servicio. Como la memoria disponible para toda la máquina virtual es de 16 gigas y, además, servicios adicionales como mlflow y airflow se encontraban corriendo tambien, la interfaz gráfica de la misma perdió conexión al ejecutarse el test de 10.000 usuarios con 500 peticiones en simultáneao.

![10gigas](imgs/10gigas.png)

2. Segundo escenario

Entonces se optó por realizar la misma prueba, pero esta vez limitando la memoria a solo 3 gigas.

![3gigas](imgs/3gigas-2.png)
![3gigas-running](imgs/3gigas-running2.png)
![3gigas-stats](imgs/3gigas-stats.png)

3. Tercer escenario

Una tercera prueba se ejecutó limitando aún mas la memoria, esta vez a 700 megas.

![700megas](imgs/700m.png)
![700megas-stats](imgs/700m-stats.png)
![700megas-error](imgs/700m-error.png)

## Pruebas con más de una instancia del servicio API

Para generar las réplicas, se ha utilizado docker swarm, para ello, es necesario activarlo con el siguiente comando:

``` docker swarm init``` 

Docker swarm permite la creación de un nodo manager para el cluster, el cual permite agregar workers o managers. La red interna permite balanceo mediante un mecanismo automático o ngix.

En este caso, las ejecuciones se realizaron con "docker compose up --build", no con docker stack deploy, de ahí la necesidad de ajustar los puertos como se indica más adelante.

En el docker compose de locust, se incluye la siguiente información:

```
deploy:
      mode: replicated
      replicas: "cantidad de replicas"
      resources:
        limits:
          memory: "limite de memoria"
          cpus: "limite de cpu"
```

Así mismo, se deben disponibilizar puertos conforme a la cantidad de réplicas, este es el ejemplo para 6 réplicas:

```
ports:
      - "8089-8094:8089"
```

En la carpeta **imgs** se encuentra un archivo **evidencia_prueba_locust.pdf**, el cual contiene las muestras de los resultados que se abordarán a continuación.

Se realizaron múltiples iteraciones para encontrar los recursos suficientes para la recepción de 10.000 usuarios y 500 peticiones, no obstante, no se encontraron escenarios óptimos en cuanto a procesamiento, tiempo de ejecución y respuesta. La principal consideración es que docker no puede acceder a todos lo recursos disponibles en la máquina virtual, donde emerge otro aspecto, y es que si consume los recursos necesarios, otros procesos se detendrían, generando el colapse del sistema operativo como ocurrió en el primer escenario. 

Por consiguiente, se consideraron los siguientes escenarios:
 - 10 clientes - 10 peticiones 
 - 500 clientes - 50 peticiones 
 - 1000 clientes - 50 peticiones
 
 Estos para identificar un escenario con buenos niveles de respuesta (entre 1 y 3 segundos), buscando establecer el ejercicio en un caso de la vida real (a pesar que 3 segundos es demasiado). 

Las ejecuciones sin restricción y sin replicas expusieron para los tres escenarios mencionados tiempos de 1-3 segundos, 1-6 segundos y 150-180 segundos por inferencia respectivamente. Dado lo anterior, se consideran los primeros dos escenarios para experimentar con limitaciones de recursos y aumento de réplicas.

Las ejecuciones con 2 réplicas, CPU 1.5 y memoria 1000M arrojaron un tiempo de respuesta para 10 cliente entre 1-2.5 segundos y 120 segundos para 500 clientes. La novedad para el segundo escenario se debe a que docker no realiza un equilibrio de cargas (balanceador) entre las réplicas, por ello, la cola de peticiones se acumuló. 
Cabe resaltar que el consumo de memoria se divide entre las réplicas de manera proporcional, situación que ocurre siempre.

Posteriormente, se incrementó a 4 réplicas con las misma restricciones de memoria y CPU, evidenciando un deterioro en los tiempos de ejecución del primer escenario porque el tiempo de inferencia estaba entre 1.5 y 4 segundos, e identificando una mejora sustancial en el escenario de 500 clientes, donde la inferencia se tomaba entre 1.5 y 4 segundos, producto de un balanceo en las cargas de trabajo. El deterioro en el performance del escenario se justifica en que a mayor cantidad de réplicas, hay mayor competencia por los recursos disponibles, los cuales son limitados para la ejecución realizada. En este caso, aplica que una mayor cantidad de trabajadores no representa mayor productividad si las tareas y los recursos disponibles para cada trabajador no son definidos de manera **óptima**.

Dando continuidad a la experimentación, se incrementaron las réplicas a 6 y se redujeron recursos a CPU 0.5 y memoria 500M. Para el escenario de 10 cliente, en un principio, los tiempos de respuesta eran inferiores a 2 segundos, sin embargo, conforme entraban en cola nuevas peticiones, el tiempo llegó a alcanzar 8 segundos. Por otro lado, el escenario de 500 clientes exponía que las inferencias tardaban más de 200 segundos. Lo anterior permite reafirmar que existe un trade-off entre réplicas y recursos, donde no es eficiente contar con gran cantidad de contenedores porque compiten por recursos. De igual forma, es necesario balancear las cargas entre los **agentes** que procesan las solicitudes.

La ventaja de implementar réplicas es que existe mayor concurrencia para atender más solicitudes, existe tolerancia a fallos y si hay balanceadores de carga, es posible ser escalable de forma horizontal. No obstante, incrementar las réplicas no siempre garantiza eficiencia porque compiten por recursos. Reducir la disponibilidad de cómputo e incrementar réplicas no es un proceso de compensación.

## Conclusiones ##

- Es importante definir un balanceador de carga para hacer un proceso con escalabilidad horizontal.

- Incrementar las réplicas y disminuir recursos no garantiza estabilidad en el rendimiento porque **las réplicas compiten por recursos** y son ineficientes.

- **docker stats** es una gran herramienta para monitorear el consumo de recursos.

