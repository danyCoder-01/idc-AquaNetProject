#Sistema IoT de Riego Automático de Largo Alcance mediante LoRa **Asociado a:** Universidad Politècnica de València (Asignatura: Internet de las Cosas) 

**Descripción:**
Diseño y desarrollo integral de un sistema IoT de bucle cerrado orientado a la agricultura de precisión en zonas remotas sin conectividad convencional. El proyecto abarca desde la capa física y adquisición de datos en el *Edge* hasta la automatización inteligente en la nube.
 
- **Edge Computing:** Programación de firmware en MicroPython sobre una Raspberry Pi Pico WH para la lectura de sensores ambientales y empaquetado optimizado de telemetría en tramas binarias de 3 bytes.
- **Comunicaciones LPWAN:** Implementación de enlaces de radio de largo alcance utilizando el módulo Grove LoRa-E5, aprovisionamiento OTAA y gestión de colas de mensajes (Uplink/Downlink) en la plataforma The Things Network (TTN) respetando las normativas de espectro EU868. 
- **Infraestructura Backend:** Despliegue de un servidor automatizado mediante Docker Compose que aloja una instancia de Node-RED. Configuración de un puente REST-MQTT para cruzar la telemetría del suelo con predicciones climatológicas en tiempo real (API Open-Meteo) para la toma autónoma de decisiones de riego. 
- **Resolución de problemas técnicos:** Implementación de soluciones lógicas avanzadas para solventar incompatibilidades de voltaje mediante conmutación a Alta Impedancia (`Pin.IN`) en los actuadores y diseño de lógicas tolerantes a fallos de red en el microcontrolador.

**Aptitudes consolidadas:** MicroPython, LPWAN (LoRaWAN), Docker Compose, Node-RED, MQTT, Arquitectura de Sistemas IoT, Protocolos de Comunicación Asíncrona, Edge Computing.
