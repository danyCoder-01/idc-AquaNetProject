from machine import UART, Pin
import time
import dht

BAUDRATE = 19200
APP_KEY = "1C55D10DCBABDA137AA8542FA4314DE3"
APP_EUI = "0000000000000000"

INTERVALO_ENVIO = 900          
TIEMPO_RIEGO_SEGUNDOS = 300    
ESPERA_POST_RIEGO_CICLOS = 2   

lora = UART(0, baudrate=BAUDRATE, tx=Pin(0), rx=Pin(1), timeout=5000)
sensor_dht = dht.DHT11(Pin(15))
valvula = Pin(14, Pin.IN)

ciclos_bloqueo_restantes = 0

def enviar_cmd(comando, espera=1):
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
        except:
            print("[ERROR] Fallo en la decodificación de la respuesta UART.")
    return ""

def inicializar_modulo():
    print("\n--- [FASE 1] CONFIGURANDO HARDWARE LORA ---")
    enviar_cmd("AT+DR=EU868")
    enviar_cmd("AT+MODE=OTAA")
    enviar_cmd(f'AT+ID=APPEUI,"{APP_EUI}"')
    enviar_cmd(f'AT+KEY=APPKEY,"{APP_KEY}"')

def conectar_lorawan():
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
    try:
        sensor_dht.measure()
        h = sensor_dht.humidity()
        t = sensor_dht.temperature()
    except Exception as e:
        print(f"[HARDWARE ERROR] Fallo al leer DHT11: {e}")
        h, t = 0, 0
    try:
        estado_valvula = 1 if (valvula.value() == 0 and Pin(14).mode() == Pin.OUT) else 0
    except:
        estado_valvula = 0 if valvula.value() == 1 else 1
    return h, t, estado_valvula

try:
    inicializar_modulo()
    conectar_lorawan()
    print("\n--- [FASE 3] ENLACE CONFIGURADO - ENTRANDO EN BUCLE ---")
    
    while True:
        print("\n--- [NUEVA RECOLECCIÓN DE DATOS] ---")
        
        humedad, temperatura, estado_valvula = leer_sensores_locales()
        print(f"[INFO] Humedad: {humedad}% | Temp: {temperatura}°C | Válvula: {estado_valvula}")
        
        payload = bytes([humedad, temperatura, estado_valvula])
        hex_payload = "".join("{:02x}".format(b) for b in payload)
        
        print(f"[LoRaWAN] Transmitiendo Payload útil: {hex_payload}")
        respuesta_uart = enviar_cmd(f'AT+MSGHEX="{hex_payload}"', espera=5)
        
        respuesta_limpia = respuesta_uart.lower().replace('"', '').replace("'", "")
        
        if "rx:" in respuesta_limpia:
            print("[LoRaWAN] Mensaje de bajada detectado en la ventana RX.")
            
            if "rx: 01" in respuesta_limpia or "rx:01" in respuesta_limpia:
                if ciclos_bloqueo_restantes > 0:
                    print(f"[ACTUADOR] Orden denegada. Periodo de absorción activo. Ciclos restantes: {ciclos_bloqueo_restantes}")
                else:
                    print("[ACTUADOR] Orden de apertura validada. Activando relé.")
                    valvula = Pin(14, Pin.OUT)
                    valvula.value(0)
                    
                    print(f"[ACTUADOR] Temporizador iniciado: Riego activo durante {TIEMPO_RIEGO_SEGUNDOS} segundos.")
                    time.sleep(TIEMPO_RIEGO_SEGUNDOS)
                    
                    print("[ACTUADOR] Temporizador finalizado. Forzando cierre de válvula (Alta impedancia).")
                    valvula = Pin(14, Pin.IN)
                    ciclos_bloqueo_restantes = ESPERA_POST_RIEGO_CICLOS
                
            elif "rx: 00" in respuesta_limpia or "rx:00" in respuesta_limpia:
                print("[ACTUADOR] Orden de cierre directa validada. Desactivando relé.")
                valvula = Pin(14, Pin.IN)
                
        else:
            print("[LoRaWAN] Ventana RX finalizada sin instrucciones del servidor.")
            if ciclos_bloqueo_restantes > 0:
                ciclos_bloqueo_restantes -= 1
        
        tiempo_suspension = INTERVALO_ENVIO
        if "rx: 01" in respuesta_limpia or "rx:01" in respuesta_limpia:
            if ciclos_bloqueo_restantes == ESPERA_POST_RIEGO_CICLOS:
                tiempo_suspension = max(0, INTERVALO_ENVIO - TIEMPO_RIEGO_SEGUNDOS)
            
        print(f"[CLOCK] Ciclo finalizado. Suspensión durante {tiempo_suspension // 60} minutos...\n")
        time.sleep(tiempo_suspension)
        
except Exception as e:
    print(f"\n[CRITICAL ERROR] Excepción no controlada en el flujo principal: {e}")
