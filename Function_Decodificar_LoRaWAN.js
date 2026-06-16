if (msg.payload && msg.payload.uplink_message && msg.payload.uplink_message.frm_payload) {

    let b64Payload = msg.payload.uplink_message.frm_payload;
    let rawBytes = Buffer.from(b64Payload, 'base64');

    // Desempaquetado según el nuevo orden del firmware:
    let humedad = rawBytes[0];
    let temperatura = rawBytes[1];
    let valvulaEstado = rawBytes[2];

    // Creamos el objeto limpio
    msg.payload = {
        dispositivo: msg.payload.end_device_ids.device_id,
        humedad: humedad,
        temperatura: temperatura,
        valvula: valvulaEstado === 1 ? "ABIERTA" : "CERRADA",
        valvula_bin: valvulaEstado,
        timestamp: msg.payload.received_at
    };

    return msg;
}
return null;
