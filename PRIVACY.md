# Politica de privacidad

Ultima actualizacion: 2026-08-21

Media Flow procesa archivos localmente en el equipo del usuario.

## Datos que recoge la app

La app no recoge, almacena ni vende datos personales relacionados con la conversión de archivos. Las funciones gratuitas no requieren crear una cuenta ni iniciar sesión.

## Archivos del usuario

Los archivos seleccionados se procesan localmente con `ffmpeg`. La app no sube archivos a servidores propios ni a servicios externos.

Si el usuario elige una carpeta sincronizada de OneDrive, Google Drive o iCloud Drive, el archivo convertido se guarda en esa carpeta local. La sincronizacion posterior la realiza el cliente oficial instalado por el usuario y queda sujeta a las politicas de privacidad del proveedor correspondiente.

## Conexion a internet

La app puede consultar GitHub Releases para comprobar si hay una version nueva. Si existe una actualizacion, puede descargar el instalador oficial y ejecutarlo localmente. Esa comprobacion y descarga no envian archivos del usuario.

## Complemento PRO y pagos opcionales

Media Flow ofrece un complemento PRO opcional. La activación puede realizarse con una clave de licencia o mediante Stripe o Microsoft Store. Los proveedores procesan el pago y los datos de tarjeta conforme a sus políticas. Para entregar licencias Stripe, Media Flow recibe el correo del comprador y el identificador de la sesión de pago, como se explica abajo; esos datos no se usan para procesar ni analizar tus archivos.

La activación de PRO no modifica el tratamiento de tus archivos: el contenido multimedia sigue procesándose localmente y no se sube a servidores de Media Flow.

## Licencias compradas con Stripe

Para entregar las licencias, el webhook de Media Flow recibe del checkout el correo del comprador y el identificador de la sesión de pago. Cloudflare D1 conserva esos datos junto con la licencia emitida para evitar duplicados y facilitar la recuperación de la compra. El correo se envía mediante Resend y el webhook se ejecuta en Cloudflare Workers. No se reciben ni almacenan números de tarjeta. Puedes solicitar soporte o la eliminación de los datos asociados a la licencia mediante el contacto del proyecto.

## Contacto

Para dudas de privacidad o soporte, usa la pagina del proyecto:

https://github.com/musicallyivan/mediaflow
