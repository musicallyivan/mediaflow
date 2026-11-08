# Activación de licencias PRO

La licencia de Stripe se firma con Ed25519: la app lleva la clave pública y el servidor conserva la privada. No publiques la clave privada ni la incluyas en el instalador.

## Preparar claves

1. Instala dependencias: `python -m pip install -r requirements.txt`.
2. Ejecuta `python license_server.py --generate-keys` en un entorno seguro.
3. Guarda `MEDIA_FLOW_LICENSE_PRIVATE_KEY` como secreto del hosting. Configura `MEDIA_FLOW_LICENSE_PUBLIC_KEY` como variable del flujo de compilación de Windows en GitHub Actions. El flujo la incrusta en `license_public_key.txt` dentro del paquete.
4. Vuelve a compilar y distribuir la app con esa clave pública. Las instalaciones anteriores no podrán validar las licencias nuevas.

## Configurar Stripe y correo

Recomiendo **Render** para alojar el webhook y **Resend** para entregar los correos. Ya añadí `render.yaml`: al crear el Blueprint, Render configura el servicio Python, HTTPS, health check, disco persistente y los campos secretos. El plan gratuito no sirve para producción con esta SQLite: los servicios gratuitos se duermen y el almacenamiento del servicio es efímero. Render documenta que los discos persistentes requieren un servicio de pago, y factura el almacenamiento por separado ([discos persistentes](https://render.com/docs/disks), [planes y límites](https://render.com/docs/faq)).

En Resend, verifica un dominio remitente y crea una API key SMTP. Usa `smtp.resend.com`, puerto `587`, usuario `resend`, la API key como contraseña y un remitente de ese dominio verificado. Resend admite SMTP con STARTTLS en 587 ([credenciales SMTP](https://resend.com/changelog/smtp-service)).

Configura estas variables en Render:

- `STRIPE_WEBHOOK_SECRET`: secreto del endpoint webhook.
- `STRIPE_PAYMENT_LINK_ID`: ID `plink_...` del Payment Link PRO.
- `MEDIA_FLOW_LICENSE_PRIVATE_KEY`: clave privada Ed25519 en Base64.
- `MEDIA_FLOW_SMTP_HOST=smtp.resend.com`, `MEDIA_FLOW_SMTP_PORT=587`, `MEDIA_FLOW_SMTP_USER=resend`, `MEDIA_FLOW_SMTP_PASSWORD` (la API key SMTP), `MEDIA_FLOW_EMAIL_FROM` (remitente verificado).
- `MEDIA_FLOW_LICENSE_DB`: ruta persistente para `licenses.sqlite3`.
- `PORT`: puerto que indique el hosting.

Crea en Stripe un endpoint `https://TU-DOMINIO/stripe/webhook` y suscribe `checkout.session.completed`. Configura el Payment Link para recoger el correo del comprador y copia su ID al servidor. El webhook exige pago único abonado y ese Payment Link. Los eventos repetidos no vuelven a emitir licencias.

Las licencias se verifican sin conexión. Reembolsos y contracargos no revocan una clave ya emitida; para revocación inmediata haría falta una verificación online adicional.

## Activar el botón Stripe

El botón no debe permitir pagar hasta probar el webhook y el correo en modo de prueba. Cuando la entrega esté desplegada y comprobada, establece la variable GitHub Actions `MEDIA_FLOW_STRIPE_FULFILLMENT_READY=1` y publica una nueva versión.

## Microsoft Store

En Partner Center copia el **Store ID** del complemento durable PRO (no el Product ID interno) y confirma que está asociado a la ficha publicada de Media Flow. `GetStoreProductsAsync` busca Store IDs de complementos asociados a la app en ejecución.

El MSIX debe usar exactamente el Package/Publisher identity de Partner Center. Los valores confirmados para Media Flow son `MSIX_PACKAGE_NAME=MusicallyIvan.MediaFlow` y `MSIX_PUBLISHER=CN=33EC4121-53F8-4312-9812-C8687536BF5A`; coinciden con los valores predeterminados del manifiesto y del flujo de compilación. El Store ID del complemento ya está configurado como `9N6VZZ3HDFHJ`. Los instaladores `.exe` y ZIP no tienen identidad MSIX y no pueden consultar compras de Store de forma fiable.
