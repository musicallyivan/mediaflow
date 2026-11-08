interface Env {
  DB: D1Database;
  STRIPE_WEBHOOK_SECRET: string;
  STRIPE_PAYMENT_LINK_ID: string;
  MEDIA_FLOW_LICENSE_PRIVATE_KEY: string;
  RESEND_API_KEY: string;
  MEDIA_FLOW_EMAIL_FROM: string;
}

interface CheckoutSession {
  id?: string;
  mode?: string;
  payment_status?: string;
  payment_link?: string | null;
  customer_email?: string | null;
  customer_details?: { email?: string | null } | null;
}

const encoder = new TextEncoder();

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function fromBase64(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function hexToBytes(value: string): Uint8Array | null {
  if (!/^[0-9a-f]{64}$/i.test(value)) return null;
  return Uint8Array.from(value.match(/.{2}/g) ?? [], (pair) => parseInt(pair, 16));
}

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a[i] ^ b[i];
  return diff === 0;
}

async function verifyStripe(raw: string, header: string, secret: string): Promise<boolean> {
  if (!secret || !header) return false;
  const parts = header.split(",").map((part) => part.split("=", 2));
  const timestamp = parts.find(([key]) => key === "t")?.[1];
  const signatures = parts.filter(([key]) => key === "v1").map(([, value]) => value);
  if (!timestamp || Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) return false;

  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const expected = new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(`${timestamp}.${raw}`)));
  return signatures.some((signature) => {
    const candidate = hexToBytes(signature);
    return candidate !== null && bytesEqual(expected, candidate);
  });
}

async function makeLicense(env: Env, purchaseId: string, email: string): Promise<string> {
  const privateKey = await crypto.subtle.importKey(
    "raw",
    fromBase64(env.MEDIA_FLOW_LICENSE_PRIVATE_KEY),
    { name: "Ed25519" },
    false,
    ["sign"],
  );
  const payload = encoder.encode(JSON.stringify({
    product: "mediaflow-pro",
    purchase: purchaseId,
    email,
    issued: Math.floor(Date.now() / 1000),
    nonce: crypto.randomUUID().replaceAll("-", ""),
  }));
  const signature = new Uint8Array(await crypto.subtle.sign("Ed25519", privateKey, payload));
  return `MFPRO1.${base64Url(payload)}.${base64Url(signature)}`;
}

async function sendLicense(env: Env, email: string, key: string): Promise<void> {
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.MEDIA_FLOW_EMAIL_FROM,
      to: [email],
      subject: "Tu licencia de Media Flow PRO",
      text: "Gracias por comprar Media Flow PRO.\n\nAbre Media Flow > Complemento PRO, pega esta licencia y pulsa Activar:\n\n"
        + `${key}\n\nGuarda este correo para futuras instalaciones.`,
    }),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Resend returned ${response.status}: ${message.slice(0, 500)}`);
  }
}

async function deliver(env: Env, session: CheckoutSession): Promise<void> {
  if (session.mode !== "payment" || session.payment_status !== "paid") return;
  if (session.payment_link !== env.STRIPE_PAYMENT_LINK_ID) throw new Error("Unexpected Stripe Payment Link");

  const purchaseId = session.id;
  const email = session.customer_details?.email || session.customer_email;
  if (!purchaseId || !email) throw new Error("Paid session has no purchase ID or customer email");

  const licenseKey = await makeLicense(env, purchaseId, email);
  await env.DB.prepare(
    "INSERT OR IGNORE INTO deliveries (purchase_id, email, license_key, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
  ).bind(purchaseId, email, licenseKey, new Date().toISOString()).run();

  const row = await env.DB.prepare(
    "SELECT email, license_key, status FROM deliveries WHERE purchase_id = ?",
  ).bind(purchaseId).first<{ email: string; license_key: string; status: string }>();
  if (!row) throw new Error("Could not persist license delivery");
  if (row.status === "sent") return;

  await sendLicense(env, row.email, row.license_key);
  await env.DB.prepare("UPDATE deliveries SET status = 'sent' WHERE purchase_id = ?").bind(purchaseId).run();
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") return new Response("ok");
    if (request.method !== "POST" || url.pathname !== "/stripe/webhook") return new Response("Not found", { status: 404 });

    const raw = await request.text();
    if (raw.length > 1_000_000) return new Response("Payload too large", { status: 413 });
    if (!await verifyStripe(raw, request.headers.get("Stripe-Signature") ?? "", env.STRIPE_WEBHOOK_SECRET)) {
      return new Response("Invalid signature", { status: 400 });
    }

    try {
      const event = JSON.parse(raw) as { type?: string; data?: { object?: CheckoutSession } };
      if (["checkout.session.completed", "checkout.session.async_payment_succeeded"].includes(event.type ?? "")) {
        await deliver(env, event.data?.object ?? {});
      }
      return new Response("ok", { status: 200 });
    } catch (error) {
      console.error("License webhook failed", error);
      return new Response("License delivery failed; Stripe may retry", { status: 500 });
    }
  },
};
