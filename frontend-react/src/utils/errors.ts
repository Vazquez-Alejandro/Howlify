const ERROR_MAP: Record<string, string> = {
  "limite": "Alcanzaste el límite de cacerías de tu plan. Mejorá tu plan desde Facturación.",
  "Token requerido": "Sesión expirada. Iniciá sesión de nuevo.",
  "Token inválido": "Sesión expirada. Iniciá sesión de nuevo.",
  "Cacería no encontrada": "Esa cacería ya no existe.",
  "Sin datos para actualizar": "No hay cambios para guardar.",
  "Admin only": "No tenés permisos de administrador.",
  "Sin datos para exportar": "No hay datos para exportar.",
  "No price configured for plan": "Este plan todavía no está disponible para contratar.",
  "Email not found": "No encontramos tu email. Contactá a soporte.",
  "Email not confirmed": "Debés confirmar tu email antes de ingresar. Revisá tu bandeja de entrada.",
  "Invalid signature": "Error de seguridad. Si el problema persiste, contactá a soporte.",
  "Webhook secret not configured": "Error de configuración de pagos. Contactá a soporte.",
  "Error de red": "No pudimos conectar con el servidor. Verificá tu conexión.",
  "Failed to fetch": "No pudimos conectar con el servidor. Verificá tu conexión.",
};

export function traducirError(error: string): string {
  const limpio = error.replace(/^Error:?\s*/i, "").trim();
  for (const [key, msg] of Object.entries(ERROR_MAP)) {
    if (limpio.includes(key)) return msg;
  }
  if (limpio.length > 80) return "Ocurrió un error inesperado. Intentalo de nuevo.";
  return limpio;
}

export function needsRetry(error: string): boolean {
  const noRetry = [
    "limite", "Admin only", "No price configured",
    "Sin datos para", "no existe", "Sesión expirada",
  ];
  return !noRetry.some(r => error.includes(r));
}
