// Validamos que la pulsación del botón sea correcta
if (msg.payload === 1) {

    // El byte 1 activa el relé. En Base64 se codifica como "AQ=="
    let payloadBase64 = Buffer.from([1]).toString('base64');

    // Estructura JSON requerida por el API MQTT de The Things Stack v3
    msg.payload = {
        "downlinks": [
            {
                "frm_payload": payloadBase64,
                "f_port": 15,          // Mismo puerto lógico que usa el firmware
                "priority": "HIGH"     // Prioridad alta para saltarse colas ordinarias
            }
        ]
    };

    // Enrutamiento al dispositivo específico en vuestra aplicación TTN
    msg.topic = "v3/idc-aquanetproject@ttn/devices/riego-pico-1/down/push";

    return msg;
}
return null;
