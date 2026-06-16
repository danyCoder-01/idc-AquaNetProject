// Validamos que el JSON contenga los datos meteorológicos esperados
if (msg.payload && msg.payload.daily && msg.payload.daily.precipitation_sum) {

    // Extraemos los mm de lluvia previstos para hoy
    let lluviaHoy = msg.payload.daily.precipitation_sum[0];

    // Guardamos el valor en la memoria global del flujo
    flow.set("lluviaPrevistaHoy", lluviaHoy);

    // Preparamos la salida para el debug
    msg.payload = {
        estado: "API OK",
        lluvia_hoy_mm: lluviaHoy
    };
    return msg;
} else {
    node.warn("La API no respondió con el formato correcto o está inaccesible.");
    return null;
}
