from machine import UART, Pin
import time
import dht

# ==========================================
# CONFIGURACIÓN Y CREDENCIALES
# ==========================================
BAUDRATE = 19200
APP_KEY = "1C55D10DCBABDA137AA8542FA4314DE3"
APP_EUI = "0000000000000000"

# INTERVALO DE ENVÍO: 15 minutos (900 segundos) para cumplir el ciclo de trabajo LoRa
INTERVALO_ENVIO = 900 

# ==========================================
# INICIALIZACIÓN DE PERIFÉRICOS (HARDWARE)
# ==========================================
# 1. Módulo LoRa-E5 (UART0: GP0=TX, GP1=RX)
lora = UART(0, baudrate=BAUDRATE, tx=Pin(0), rx=Pin(1), timeout=5000)

# 2. Sensor de Temperatura y Humedad DHT11 (GPIO 15)
sensor_dht = dht.DHT11(Pin(15))

# 3. Módulo Relé de 5V (GPIO 14)
# NOTA: Los módulos de relés de 5V suelen ser "Active Low" (se activan con un 0 lógico)
valvula = Pin(14, Pin.OUT)
valvula.value(1) # Arranca apagado (Válvula Cerrada)

# ==========================================
# FUNCIONES LÓGICAS Y COMANDOS AT
# ==========================================
def enviar_cmd(comando, espera=1):
    """Envía un comando AT al módulo LoRa y devuelve su respuesta limpia."""
    if lora.any():
        lora.read() # Limpieza de buffer
        
    print(f"[UART] Enviando: {comando}")
    lora.write(comando + "\r\n")
    time.sleep(espera)
    
    if lora.any():
        try:
            respuesta = lora.read().decode('utf-8')
            print(f"[UART] Respuesta:\n{respuesta.strip()}")
            return respuesta
        except:
            print("[ERROR] No se pudo decodificar la respuesta.")
    return ""

def inicializar_modulo():
    """Configura los parámetros de identidad y región del módulo."""
    print("\n--- [FASE 1] CONFIGURANDO HARDWARE LORA ---")
    enviar_cmd("AT+DR=EU868")
    enviar_cmd("AT+MODE=OTAA")
    enviar_cmd(f'AT+ID=APPEUI,"{APP_EUI}"')
    enviar_cmd(f'AT+KEY=APPKEY,"{APP_KEY}"')

def conectar_lorawan():
    """Lanza el intento de JOIN en bucle hasta conectar."""
    print("\n--- [FASE 2] INICIANDO APRETÓN DE MANOS (JOIN) ---")
    conectado = False
    intento = 1
    
    while not conectado:
        print(f"\n[Intento {intento}] Lanzando petición al aire...")
        respuesta = enviar_cmd("AT+JOIN", espera=12)
        
        if "joined" in respuesta.lower() or "success" in respuesta.lower():
            print("\nMódulo enlazado correctamente a The Things Network.")
            conectado = True
        else:
            print(f"\n[!] Fallo de Join. Reintentando en 15 segundos...")
            intento += 1
            time.sleep(15)

def leer_sensores_locales():
    """Lee el DHT11 y devuelve la Humedad, Temperatura y Estado de la Válvula."""
    try:
        sensor_dht.measure()
        h = sensor_dht.humidity()
        t = sensor_dht.temperature()
    except Exception as e:
        print(f"[HARDWARE ERROR] Fallo al leer DHT11: {e}")
        h, t = 0, 0 # Valores de rescate en caso de fallo físico
        
    # Mapeo del Relé: Si el pin está en 0 (GND), el relé conmuta y abre la válvula (1)
    estado_valvula = 1 if valvula.value() == 0 else 0
    
    return h, t, estado_valvula

# ==========================================
# FLUJO PRINCIPAL DEL PROGRAMA
# ==========================================
try:
    # Ejecutamos la configuración y el enlace inicial
    inicializar_modulo()
    conectar_lorawan()
    
    print("\n--- [FASE 3] ENLACE CONFIGURADO - ENTRANDO EN BUCLE ---")
    
    while True:
        print("\n--- [NUEVA RECOLECCIÓN DE DATOS] ---")
        
        # 1. Recolectar variables reales
        humedad, temperatura, estado_valvula = leer_sensores_locales()
        print(f"[INFO] Humedad: {humedad}% | Temp: {temperatura}°C | Válvula: {estado_valvula}")
        
        # 2. Empaquetar en estructura binaria (3 Bytes puros)
        payload = bytes([humedad, temperatura, estado_valvula])
        
        # 3. Codificar a texto Hexadecimal puro (Ej: bytes [42, 22, 0] -> "2a1600")
        hex_payload = "".join("{:02x}".format(b) for b in payload)
        
        # 4. Transmitir por radio a través del comando MSGHEX de LoRa-E5
        # Le damos 5 segundos de espera para procesar el envío y escuchar posibles downlinks
        print(f"[LoRaWAN] Enviando Payload útil: {hex_payload}")
        enviar_cmd(f'AT+MSGHEX="{hex_payload}"', espera=5)
        
        # 5. Dormir el sistema hasta la próxima lectura
        print(f"[CLOCK] Durmiendo durante {INTERVALO_ENVIO // 60} minutos...")
        time.sleep(INTERVALO_ENVIO)
        
except Exception as e:
    print(f"\n[CRITICAL ERROR] Ocurrió un fallo en el programa: {e}")
