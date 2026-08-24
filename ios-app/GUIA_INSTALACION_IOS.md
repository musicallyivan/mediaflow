# Guía de Instalación de Media Flow en iPhone desde Windows (Gratis)

Esta guía explica cómo instalar el archivo **`MediaFlow.ipa`** en tu iPhone o iPad sin necesidad de Mac ni cuenta de pago de desarrollador de Apple.

---

## Método Recomendado: Usando Sideloadly (Windows)

**[Sideloadly](https://sideloadly.io/)** es la herramienta más rápida y sencilla para instalar aplicaciones `.ipa` desde un PC con Windows.

### Requisitos previos en Windows
1. Descarga e instala **[Sideloadly para Windows](https://sideloadly.io/)** (disponible en 64-bit).
2. Asegúrate de tener instalados **iTunes** y **iCloud** en Windows (las versiones directas de Apple, no las de la Microsoft Store; Sideloadly te ofrecerá instalarlas automáticamente si no las tienes).

---

### Paso a Paso para la Instalación

#### 1. Obtener el archivo `.ipa`
1. Entra en tu repositorio de GitHub.
2. Ve a la pestaña **Actions** -> **Build iOS IPA** -> Haz clic en la última ejecución completada.
3. Descarga el artefacto **`MediaFlow-iOS-IPA`** (o descárgalo desde la sección **Releases** si publicaste una versión).
4. Descomprime el ZIP si viene comprimido para obtener el archivo **`MediaFlow.ipa`**.

#### 2. Conectar tu iPhone y cargar la App
1. Conecta tu iPhone al PC mediante el cable USB.
2. Si tu iPhone te pregunta *"¿Confiar en este ordenador?"*, pulsa **Confiar** e introduce tu código de desbloqueo.
3. Abre **Sideloadly** en Windows.
4. Tu iPhone aparecerá detectado en el campo **iDevice**.
5. Arrastra el archivo **`MediaFlow.ipa`** a la ventana de Sideloadly (en el recuadro grande con el icono de la app).
6. En el campo **Apple ID**, introduce el correo de tu cuenta de Apple (tu ID gratuito habitual).
7. Haz clic en el botón **Start**.
8. Introduce la contraseña de tu Apple ID y el código de verificación en dos pasos (2FA) que aparecerá en tu iPhone.
9. Espera unos segundos hasta que Sideloadly muestre el mensaje **`Done.`**.

---

### Paso 3: Autorizar la App en tu iPhone (Solo la primera vez)

1. En tu iPhone, ve a **Ajustes** -> **General** -> **Gestión de dispositivos y VPN** (o *Administración de dispositivos*).
2. Bajo *"App de desarrollador"*, verás tu correo de Apple ID. Púlsalo.
3. Pulsa **"Confiar en [tu correo]"** y confirma.
4. *(Solo en iOS 16 o posterior)*:
   - Ve a **Ajustes** -> **Privacidad y seguridad** -> baja hasta el final y activa el **Modo de desarrollador**.
   - El iPhone te pedirá reiniciar. Al reiniciar, confirma activar el modo de desarrollador.
5. ¡Listo! Ya puedes abrir **Media Flow** en tu pantalla de inicio y usarlo con total normalidad.

---

## Preguntas Frecuentes

### ¿Por qué caduca a los 7 días?
Apple establece que las apps firmadas con cuentas gratuitas de Apple ID son válidas durante **7 días**. Cuando pasen 7 días:
- Conecta el iPhone de nuevo al PC, abre Sideloadly y vuelve a darle a **Start** (o activa la opción de *Automatic Refresh* en Sideloadly por WiFi).
- No perderás tus configuraciones ni datos de la app.
