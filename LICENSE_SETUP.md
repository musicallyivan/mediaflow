# Stripe PRO license delivery (free deployment)

Production host: Cloudflare Workers Free + D1 Free. Email delivery: Resend Free. Cloudflare's free limits currently include 100,000 Worker requests/day, 5 million D1 rows read/day, 100,000 rows written/day, and 500 MB per D1 database. Resend Free includes 3,000 emails/month and 100/day. Check provider dashboards for current usage and limits.

## Already prepared

- `cloudflare/src/index.ts`: Stripe signature verification, paid-session validation, signed license issuance and Resend delivery.
- `cloudflare/migrations/0001_create_deliveries.sql`: persistent idempotency and delivery status table.
- `cloudflare/wrangler.toml`: Worker and D1 binding configuration.
- `license_crypto.py`: Windows app verifies the Ed25519 signature offline using the public key bundled at build time.

## Deploy the Worker

Install Node.js if needed, then in PowerShell:

```powershell
cd "G:\IVAN MUSICALLY CARPETA\mediaflow\cloudflare"
npx wrangler login
npx wrangler d1 create mediaflow-licenses
```

Copy the `database_id` printed by Wrangler into `wrangler.toml`, replacing `REPLACE_WITH_D1_DATABASE_ID`. Then create the table and deploy:

```powershell
npx wrangler d1 migrations apply mediaflow-licenses --remote
npx wrangler secret put MEDIA_FLOW_LICENSE_PRIVATE_KEY
npx wrangler secret put RESEND_API_KEY
npx wrangler secret put MEDIA_FLOW_EMAIL_FROM
npx wrangler deploy
```

At each `secret put` prompt, paste the value locally in the terminal, never into chat or Git. Use the private Ed25519 key generated earlier, the Resend Sending API key, and `licencias@musicallyivan.com`. The Worker URL will be printed after deployment; `/health` should return `ok`.

## Connect Stripe after deploying

1. In Stripe, create a webhook endpoint at `WORKER_URL/stripe/webhook` for `checkout.session.completed` and `checkout.session.async_payment_succeeded`.
2. Store its signing secret as a Worker secret: `npx wrangler secret put STRIPE_WEBHOOK_SECRET`.
3. Find the existing Payment Link's `plink_...` ID in Stripe and store it as `npx wrangler secret put STRIPE_PAYMENT_LINK_ID`.
4. Ensure the Payment Link collects the buyer's email. Keep it deactivated until the webhook and email delivery have been tested.

## Release the Windows app

In GitHub repository settings, add the public Ed25519 key as an Actions variable named `MEDIA_FLOW_LICENSE_PUBLIC_KEY`. Keep `MEDIA_FLOW_STRIPE_FULFILLMENT_READY` unset or `0` until Stripe's webhook and test email both work. Then set it to `1`, create a new release build, and publish the updated app/site. Never put the private signing key in GitHub.

The license database is persistent in D1 and email delivery retries use the same stored license. Free-plan request/email/database quotas apply. Refunds and chargebacks do not revoke an already issued offline license.

## Microsoft Store identity

The confirmed app identity is `MusicallyIvan.MediaFlow` / `CN=33EC4121-53F8-4312-9812-C8687536BF5A`; the add-on Store ID is `9N6VZZ3HDFHJ`. Install the app from Microsoft Store to query Store ownership. The `.exe` and ZIP builds do not carry the Store package identity.
