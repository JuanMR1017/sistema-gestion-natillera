# language: es
Característica: Autenticación por roles (HU-05)

  Escenario: Ahorrador inicia sesión
    Dado un usuario "juan" con rol "Ahorrador" y contraseña "clave123"
    Cuando ingresa sus credenciales correctas
    Entonces es redirigido a su panel de ahorrador con sesión activa

  Escenario: Administrador inicia sesión
    Dado un usuario "admin" con rol "Administrador" y contraseña "clave123"
    Cuando ingresa sus credenciales correctas
    Entonces es redirigido al panel de administración con sesión activa

  Escenario: Credenciales inválidas
    Dado un usuario "juan" con rol "Ahorrador" y contraseña "clave123"
    Cuando ingresa una contraseña incorrecta
    Entonces ve un error genérico sin revelar el dato fallido
