from machine import UART, Pin
import time
import dht

# ==========================================
# CONFIGURACIÓN Y CREDENCIALES
# ==========================================
BAUDRATE = 19200
APP_KEY = "1C55D10DCBABDA137AA8542FA4314DE3"
APP_EUI = "0000000000000000"

# TEMPORIZACIÓN (En segundos)
INTERVALO_ENVIO = 900       # 15 minutos entre transmisiones (Normativa LoRaWAN)
TIEMPO_RIEGO_SEGUNDOS = 30  # Duración activa del riego antes del apagado automático

# ==========================================
# INICIALIZACIÓN DE PERIFÉRICOS (HARDWARE)
# ==========================================
# 1. Módulo Grove LoRa-E5 (UART0: GP0=TX, GP1=RX)
lora = UART(0, baudrate=BAUDRATE, tx=Pin(0), rx=Pin(1), timeout=5000)

# 2. Sensor de Temperatura y Humedad DHT11 (GPIO 15)
sensor_dht = dht.DHT11(Pin(15))

# 3. Módulo Relé de 5V para Electroválvula (GPIO 14)
# Solución de arranque: Se inicializa como ENTRADA (Alta impedancia).
# Al no haber paso de corriente, el relé arranca apagado de forma segura.
valvula = Pin(14, Pin.IN)

# ==========================================
# FUNCIONES LÓGICAS Y COMANDOS AT
# ==========================================
def enviar_cmd(comando, espera=1):
    """Envía un comando AT al módulo LoRa y devuelve su respuesta limpia."""
    if lora.any():
        lora.read() # Limpieza del buffer de entrada de la UART
        
    print(f"[UART] Enviando: {comando}")
    lora.write(comando + "\r\n")
    time.sleep(espera)
    
    if lora.any():
        try:
            respuesta = lora.read().decode('utf-8')
            print(f"[UART] Respuesta:\n{respuesta.strip()}")
            return respuesta
        except:
            print("[ERROR] Fallo en la decodificación de la respuesta UART.")
    return ""

def inicializar_modulo():
    """Configura los parámetros de red e identidad del módulo Grove LoRa-E5."""
    print("\n--- [FASE 1] CONFIGURANDO HARDWARE LORA ---")
    enviar_cmd("AT+DR=EU868")
    enviar_cmd("AT+MODE=OTAA")
    enviar_cmd(f'AT+ID=APPEUI,"{APP_EUI}"')
    enviar_cmd(f'AT+KEY=APPKEY,"{APP_KEY}"')

def conectar_lorawan():
    """Ejecuta el procedimiento de JOIN (OTAA) mediante reintentos."""
    print("\n--- [FASE 2] INICIANDO APRETÓN DE MANOS (JOIN) ---")
    conectado = False
    intento = 1
    
    while not conectado:
        print(f"\n[Intento {intento}] Transmitiendo petición de acceso...")
        respuesta = enviar_cmd("AT+JOIN", espera=12)
        
        if "joined" in respuesta.lower() or "success" in respuesta.lower():
            print("\nEnlace establecido correctamente con The Things Network.")
            conectado = True
        else:
            print(f"\n[!] Fallo de Join. Reintentando en 15 segundos...")
            intento += 1
            time.sleep(15)

def leer_sensores_locales():
    """Ejecuta la lectura del bus One-Wire del DHT11 y evalúa el estado del relé."""
    try:
        sensor_dht.measure()
        h = sensor_dht.humidity()
        t = sensor_dht.temperature()
    except Exception as e:
        print(f"[HARDWARE ERROR] Fallo al leer DHT11: {e}")
        h, t = 0, 0 # Valores seguros por defecto ante fallo físico
        
    # Mapeo lógico del Relé bajo la solución de impedancia:
    # Si el pin está configurado como SALIDA (OUT) y su valor es 0, el relé está activado (1).
    # Si está configurado como ENTRADA (IN), está en reposo/apagado (0).
    # Usamos try/except por si el método mode() no está disponible en esta compilación de MicroPython.
    try:
        # Si el relé está en modo salida y a nivel bajo, está conmutado
        estado_valvula = 1 if (valvula.value() == 0 and Pin(14).mode() == Pin.OUT) else 0
    except:
        # Alternativa de lectura directa si falla la introspección de modo
        estado_valvula = 0 if valvula.value() == 1 else 1
    
    return h, t, estado_valvula

# ==========================================
# FLUJO PRINCIPAL DEL PROGRAMA
# ==========================================
try:
    inicializar_modulo()
    conectar_lorawan()
    
    print("\n--- [FASE 3] ENLACE CONFIGURADO - ENTRANDO EN BUCLE ---")
    
    while True:
        print("\n--- [NUEVA RECOLECCIÓN DE DATOS] ---")
        
        # 1. Adquisición de telemetría física
        humedad, temperatura, estado_valvula = leer_sensores_locales()
        print(f"[INFO] Humedad: {humedad}% | Temp: {temperatura}°C | Válvula: {estado_valvula}")
        
        # 2. Empaquetado binario (3 Bytes) y conversión a Hexadecimal
        payload = bytes([humedad, temperatura, estado_valvula])
        hex_payload = "".join("{:02x}".format(b) for b in payload)
        
        # 3. Transmisión Uplink y captura de la ventana de recepción (RX)
        print(f"[LoRaWAN] Transmitiendo Payload útil: {hex_payload}")
        respuesta_uart = enviar_cmd(f'AT+MSGHEX="{hex_payload}"', espera=5)
        
        # 4. Procesamiento del Downlink con Solución por Software de Alta Impedancia
        respuesta_limpia = respuesta_uart.lower().replace('"', '').replace("'", "")
        
        if "rx:" in respuesta_limpia:
            print("[LoRaWAN] Mensaje de bajada detectado en la ventana RX.")
            
            # Evaluación de la carga útil recibida
            if "rx: 01" in respuesta_limpia or "rx:01" in respuesta_limpia:
                print("[ACTUADOR] Orden de apertura validada. Activando relé.")
                
                # Modificación dinámica: Reconfiguramos el pin como salida y lo llevamos a masa (0V)
                valvula = Pin(14, Pin.OUT)
                valvula.value(0)  
                
                # Temporización síncrona en el dispositivo
                print(f"[ACTUADOR] Temporizador iniciado: Riego activo durante {TIEMPO_RIEGO_SEGUNDOS} segundos.")
                time.sleep(TIEMPO_RIEGO_SEGUNDOS)
                
                print("[ACTUADOR] Temporizador finalizado. Forzando cierre de válvula (Alta impedancia).")
                # Modificación dinámica: Cambiamos el pin a ENTRADA para simular la desconexión física
                valvula = Pin(14, Pin.IN) 
                
            elif "rx: 00" in respuesta_limpia or "rx:00" in respuesta_limpia:
                print("[ACTUADOR] Orden de cierre directa validada. Desactivando relé (Alta impedancia).")
                valvula = Pin(14, Pin.IN) 
        else:
            print("[LoRaWAN] Ventana RX finalizada sin instrucciones del servidor.")
        
        # 5. Suspensión del proceso (Compensando el tiempo empleado en regar)
        tiempo_suspension = INTERVALO_ENVIO
        if "rx: 01" in respuesta_limpia or "rx:01" in respuesta_limpia:
            tiempo_suspension = max(0, INTERVALO_ENVIO - TIEMPO_RIEGO_SEGUNDOS)
            
        print(f"[CLOCK] Ciclo finalizado. Suspensión durante {tiempo_suspension // 60} minutes...\n")
        time.sleep(tiempo_suspension)
        
except Exception as e:
    print(f"\n[CRITICAL ERROR] Excepción no controlada en el flujo principal: {e}")
