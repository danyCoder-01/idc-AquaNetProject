// Extraction de la telemetría actual del dispositivo
let humedadActual = msg.payload.humedad;

// Recuperación de la predicción de precipitación desde el contexto global
let lluviaPrevista = flow.get("lluviaPrevistaHoy") || 0;

// Log de control en la consola de Node-RED
node.warn(`[LÓGICA] Evaluación: Humedad ${humedadActual}% | Previsión Lluvia: ${lluviaPrevista}mm`);

// Condición lógica de activación (Umbral crítico por debajo del 40%)
if (humedadActual < 45 && lluviaPrevista < 1) {

    node.warn("Estado: Sequía detectada. Generando orden de apertura.");

    // El protocolo de bajada de The Things Network requiere codificación Base64.
    // El byte 1 (comando de apertura) se traduce a "AQ==" en Base64.
    let payloadBase64 = Buffer.from([1]).toString('base64');

    // Estructura de carga útil compatible con The Things Stack v3
    msg.payload = {
        "downlinks": [
            {
                "frm_payload": payloadBase64,
                "f_port": 15,          // Puerto lógico asignado al actuador
                "priority": "NORMAL"
            }
        ]
    };

    // Enrutamiento dinámico mediante el Topic MQTT de la aplicación
    msg.topic = "v3/idc-aquanetproject@ttn/devices/riego-pico-1/down/push";

    return msg;
}

// Si los parámetros no cumplen el criterio de riego, se aborta la ejecución del flujo
node.warn("Estado: Nivel de humedad adecuado o precipitación inminente. Ejecución desestimada.");
return null;
