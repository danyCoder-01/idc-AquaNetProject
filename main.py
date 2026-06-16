from machine import UART, Pin
import time
import dht

# ============================================================================
# CONFIGURACIÓN DE CONSTANTES Y PARÁMETROS GLOBAL
# ============================================================================
BAUDRATE = 19200
APP_KEY = "APPIKEY"  # Pon aquí tu APP_KEY de TNN
APP_EUI = "0000000000000000"

INTERVALO_ENVIO = 900          # 15 minutos entre transmisiones (Duty Cycle EU868)
TIEMPO_RIEGO_SEGUNDOS = 300    # 5 minutos de apertura controlada
ESPERA_POST_RIEGO_CICLOS = 2   # Ciclos de guarda para evitar sobresaturación

# Configuración de Periféricos
lora = UART(0, baudrate=BAUDRATE, tx=Pin(0), rx=Pin(1), timeout=5000)
sensor_dht = dht.DHT11(Pin(15))

# Inicialización del actuador en Alta Impedancia (Seguridad de arranque)
PIN_VALVULA = 14
valvula = Pin(PIN_VALVULA, Pin.IN)

# Variables de Control de Estado (Software State)
ciclos_bloqueo_restantes = 0
estado_valvula_software = 0   # 0 = Cerrada (Alta Impedancia), 1 = Abierta (Salida Low)

# ============================================================================
# FUNCIONES DE COMUNICACIÓN Y SUBSISTEMAS
# ============================================================================

def enviar_cmd(comando, espera=1):
    """Limpia el buffer UART, transmite un comando AT y retorna la respuesta escaneada"""
    if lora.any():
        lora.read()
        
    print(f"[UART] Enviando: {comando}")
    lora.write(comando + "\r\n")
    time.sleep(espera)
    
    if lora.any():
        try:
            respuesta = lora.read().decode('utf-8')
            print(f"[UART] Respuesta:\n{respuesta.strip()}")
            return respuesta
        except Exception as e:
            print(f"[ERROR] Fallo en la decodificación UART: {e}")
    return ""

def inicializar_modulo():
    """Configura los parámetros regionales y el modo de operación del módem LoRa-E5"""
    print("\n--- [FASE 1] CONFIGURANDO HARDWARE LORA ---")
    enviar_cmd("AT+DR=EU868")
    enviar_cmd("AT+MODE=OTAA")
    enviar_cmd(f'AT+ID=APPEUI,"{APP_EUI}"')
    enviar_cmd(f'AT+KEY=APPKEY,"{APP_KEY}"')

def conectar_lorawan():
    """Realiza el procedimiento de negociación Over-The-Air Activation (OTAA)"""
    print("\n--- [FASE 2] INICIANDO APRETÓN DE MANOS (JOIN) ---")
    conectado = False
    intento = 1
    while not conectado:
        print(f"\n[Intento {intento}] Transmitiendo petición de acceso a la red...")
        respuesta = enviar_cmd("AT+JOIN", espera=12)
        if "joined" in respuesta.lower() or "success" in respuesta.lower():
            print("\n[OK] Enlace establecido correctamente con The Things Network.")
            conectado = True
        else:
            print("\n[!] Fallo de Join. Reintentando en 15 segundos...")
            intento += 1
            time.sleep(15)

def leer_sensores_locales():
    """Lee el entorno climático y retorna las variables junto al estado real del actuador"""
    global estado_valvula_software
    try:
        sensor_dht.measure()
        h = sensor_dht.humidity()
        t = sensor_dht.temperature()
    except Exception as e:
        print(f"[HARDWARE ERROR] Fallo al leer DHT11: {e}")
        h, t = 0, 0
        
    return h, t, estado_valvula_software

# ============================================================================
# EJECUCIÓN DEL FLUJO PRINCIPAL (BUCLE CERRADO)
# ============================================================================

try:
    inicializar_modulo()
    conectar_lorawan()
    print("\n--- [FASE 3] ENLACE CONFIGURADO - ENTRANDO EN BUCLE ---")
    
    while True:
        print("\n--- [NUEVA RECOLECCIÓN DE DATOS] ---")
        
        # Muestreo de Telemetría
        humedad, temperatura, estado_valvula = leer_sensores_locales()
        print(f"[INFO] Humedad: {humedad}% | Temp: {temperatura}°C | Válvula: {estado_valvula}")
        
        # Construcción de Payload Binario Optimizado (3 Bytes)
        payload = bytes([humedad, temperatura, estado_valvula])
        hex_payload = "".join("{:02x}".format(b) for b in payload)
        
        # Transmisión del Mensaje Ascendente (Uplink)
        print(f"[LoRaWAN] Transmitiendo Payload útil: {hex_payload}")
        respuesta_uart = enviar_cmd(f'AT+MSGHEX="{hex_payload}"', espera=5)
        
        # Tratamiento de cadenas para aislar el Downlink
        respuesta_limpia = respuesta_uart.lower().replace('"', '').replace("'", "")
        
        # Procesamiento de Órdenes de Bajada (Downlink)
        if "rx:" in respuesta_limpia:
            print("[LoRaWAN] Mensaje de bajada detectado en la ventana RX.")
            
            # Caso A: Orden de Apertura (Payload 01)
            if "rx: 01" in respuesta_limpia or "rx:01" in respuesta_limpia:
                if ciclos_bloqueo_restantes > 0:
                    print(f"[ACTUADOR] Orden denegada. Periodo de absorción activo. Ciclos restantes: {ciclos_bloqueo_restantes}")
                else:
                    print("[ACTUADOR] Orden de apertura validada. Activando relé por conmutación a Masa.")
                    valvula = Pin(PIN_VALVULA, Pin.OUT)
                    valvula.value(0)  # Active Low para excitar el optoacoplador de 5V
                    estado_valvula_software = 1
                    
                    print(f"[ACTUADOR] Temporizador iniciado: Riego activo durante {TIEMPO_RIEGO_SEGUNDOS} segundos.")
                    time.sleep(TIEMPO_RIEGO_SEGUNDOS)
                    
                    # Solución al diferencial de tensión: Retorno seguro a Alta Impedancia
                    print("[ACTUADOR] Temporizador finalizado. Forzando aislamiento eléctrico (Alta impedancia).")
                    valvula = Pin(PIN_VALVULA, Pin.IN)
                    estado_valvula_software = 0
                    ciclos_bloqueo_restantes = ESPERA_POST_RIEGO_CICLOS
            
            # Caso B: Orden de Cierre Directo (Payload 00)
            elif "rx: 00" in respuesta_limpia or "rx:00" in respuesta_limpia:
                print("[ACTUADOR] Orden de cierre directa validada. Aislando relé.")
                valvula = Pin(PIN_VALVULA, Pin.IN)
                estado_valvula_software = 0
                
        else:
            print("[LoRaWAN] Ventana RX finalizada sin instrucciones del servidor.")
            if ciclos_bloqueo_restantes > 0:
                ciclos_bloqueo_restantes -= 1
        
        # Cálculo Dinámico de Temporización de Ciclo (Compensación de desfase por riego)
        tiempo_suspension = INTERVALO_ENVIO
        if "rx: 01" in respuesta_limpia or "rx:01" in respuesta_limpia:
            if ciclos_bloqueo_restantes == ESPERA_POST_RIEGO_CICLOS:
                # Restamos el tiempo que el microprocesador estuvo en `time.sleep` regando
                tiempo_suspension = max(0, INTERVALO_ENVIO - TIEMPO_RIEGO_SEGUNDOS)
                
        print(f"[CLOCK] Ciclo finalizado. Suspensión durante {tiempo_suspension // 60} minutos...\n")
        time.sleep(tiempo_suspension)
        
except Exception as e:
    print(f"\n[CRITICAL ERROR] Excepción no controlada en el flujo principal: {e}")
