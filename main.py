from machine import UART, Pin
import time

# ==========================================
# CONFIGURACIÓN Y CREDENCIALES
# ==========================================
BAUDRATE = 19200
APP_KEY = "1C55D10DCBABDA137AA8542FA4314DE3"
APP_EUI = "0000000000000000"

# Inicializamos la UART0 (GP0=TX, GP1=RX) con un timeout alto para comandos largos
lora = UART(0, baudrate=BAUDRATE, tx=Pin(0), rx=Pin(1), timeout=5000)

def enviar_cmd(comando, espera=1):
    """Envia un comando AT al módulo LoRa y devuelve su respuesta limpia."""
    # Limpiamos el buffer antes de enviar por si acaso
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
            print("[ERROR] No se pudo decodificar la respuesta.")
    return ""

def inicializar_modulo():
    """Configura los parámetros de identidad y región del módulo Grove LoRa-E5."""
    print("\n--- [FASE 1] CONFIGURANDO HARDWARE ---")
    
    # 1. Aseguramos la región europea (868 MHz)
    enviar_cmd("AT+DR=EU868")
    
    # 2. Forzamos el modo de activación Over-The-Air (OTAA)
    enviar_cmd("AT+MODE=OTAA")
    
    # 3. Sincronizamos el AppEUI con los ceros de la consola de TTN
    enviar_cmd(f'AT+ID=APPEUI,"{APP_EUI}"')
    
    # 4. Guardamos la clave maestra de cifrado simétrico
    enviar_cmd(f'AT+KEY=APPKEY,"{APP_KEY}"')

def conectar_lorawan():
    """Lanza el intento de JOIN en bucle hasta que consiga conectar con la red."""
    print("\n--- [FASE 2] INICIANDO APRETÓN DE MANOS (JOIN) ---")
    conectado = False
    intento = 1
    
    while not conectado:
        print(f"\n[Intento {intento}] Lanzando petición al aire...")
        # Le damos 12 segundos para que escuche el "Accept" de la antena
        respuesta = enviar_cmd("AT+JOIN", espera=12)
        
        if "joined" in respuesta.lower() or "success" in respuesta.lower():
            print("\nMódulo enlazado correctamente a The Things Network.")
            conectado = True
        else:
            print(f"\n[!] Fallo de Join. Reintentando en 15 segundos...")
            print("(Si estás dentro del búnker, acerca la placa a la ventana)")
            intento += 1
            time.sleep(15)

# ==========================================
# FLUJO PRINCIPAL DEL PROGRAMA
# ==========================================
try:
    inicializar_modulo()
    conectar_lorawan()
    
    print("\n--- [FASE 3] LISTO PARA ENVIAR DATOS ---")
    print("Canal de radio abierto. Pasando a la fase de Node-RED...")
    
except Exception as e:
    print(f"\n[CRITICAL ERROR] Ocurrió un fallo en el programa: {e}")
