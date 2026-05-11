# Lemon Squeezy Integration Rule

Universal guide for AI agents integrating payments through Lemon Squeezy in any project.

## Purpose

Use this rule when a product needs checkout links, one-time payments, subscriptions, license keys, paid entitlements, or customer portal access through Lemon Squeezy.

This rule covers:

- Required environment variables
- Server-side checkout creation
- Dynamic pricing with `custom_price`
- Passing local user data into checkout
- Webhook signature verification
- Payment and subscription state synchronization
- Security requirements
- Testing and rollout checklist

## Rule

Always create Lemon Squeezy checkouts from a trusted backend and treat verified webhooks as the source of truth for paid state.

The frontend may request a checkout URL and redirect the user to it, but it must not contain the Lemon Squeezy API key, create privileged payment records, or unlock paid access before the backend receives a valid signed webhook.

## Environment Variables

Every Lemon Squeezy integration must document these four variables in `.env.example` or the project setup guide:

```env
# Bearer token from Lemon Squeezy Settings > API
LEMONSQUEEZY_API_KEY=...

# Store ID from Lemon Squeezy Settings > Stores
LEMONSQUEEZY_STORE_ID=...

# Product variant ID. Use one configured variant and apply dynamic pricing with custom_price when needed.
LEMONSQUEEZY_VARIANT_ID=...

# Signing secret configured in Lemon Squeezy Settings > Webhooks
LEMONSQUEEZY_WEBHOOK_SECRET=...
```

Optional variables are allowed when the project needs them:

```env
APP_URL=http://localhost:3000
LEMONSQUEEZY_TEST_MODE=true
LEMONSQUEEZY_SUCCESS_URL=http://localhost:3000/billing/success
```

Rules:

- Never expose `LEMONSQUEEZY_API_KEY` or `LEMONSQUEEZY_WEBHOOK_SECRET` to the browser.
- Use public frontend env prefixes only for non-secret display values.
- Use separate API keys, store data, webhook secrets, and variant IDs for test and production environments.
- Keep `LEMONSQUEEZY_VARIANT_ID` as the default variant and use request-time `custom_price` for customer-specific pricing.
- Do not commit real API keys, webhook secrets, checkout URLs tied to a customer, license keys, or webhook payloads containing customer data.

## Recommended Architecture

Use this structure unless the project already has a strong convention:

```text
server/
  payments/
    lemonsqueezy-client
    create-checkout
    verify-webhook
    sync-entitlements

routes/
  POST /api/billing/checkout
  POST /api/webhooks/lemonsqueezy

database/
  users
  purchases or subscriptions
  payment_events
```

The preferred flow is:

```text
User clicks upgrade or buy
  -> Frontend POSTs selected product and local context to backend
  -> Backend validates user, amount, and entitlement target
  -> Backend creates Lemon Squeezy checkout
  -> Frontend redirects to returned checkout URL
  -> Lemon Squeezy sends signed webhook
  -> Backend verifies signature using raw body
  -> Backend stores event and updates local paid state idempotently
  -> Frontend refreshes billing state from backend
```

## Creating a Checkout

Create checkouts on the backend with:

```text
POST https://api.lemonsqueezy.com/v1/checkouts
```

Headers:

```text
Accept: application/vnd.api+json
Content-Type: application/vnd.api+json
Authorization: Bearer {LEMONSQUEEZY_API_KEY}
```

Payload shape:

```json
{
  "data": {
    "type": "checkouts",
    "attributes": {
      "custom_price": 5000,
      "product_options": {
        "enabled_variants": [123],
        "redirect_url": "https://example.com/billing/success"
      },
      "checkout_data": {
        "email": "customer@example.com",
        "custom": {
          "user_id": "local-user-id",
          "plan": "pro"
        }
      },
      "test_mode": true
    },
    "relationships": {
      "store": {
        "data": {
          "type": "stores",
          "id": "456"
        }
      },
      "variant": {
        "data": {
          "type": "variants",
          "id": "123"
        }
      }
    }
  }
}
```

Rules:

- Build this request only on the server.
- Use `custom_price` as a positive integer in the smallest currency unit, such as cents for USD.
- Validate dynamic prices on the backend. Never trust a client-submitted price without checking it against server-side pricing rules.
- Remember that `custom_price` excludes tax; tax can be added during checkout.
- For subscriptions, `custom_price` is retained for future renewals until the customer is moved to another variant.
- Pass only minimal local identifiers through `checkout_data.custom`, such as `user_id`, `organization_id`, `plan`, or `checkout_intent_id`.
- Avoid putting raw emails, names, access tokens, secrets, internal notes, or sensitive metadata in custom data.
- Use `product_options.enabled_variants` when the checkout must show only the configured variant.
- Store enough local state before redirecting to reconcile the webhook later.

Expected response handling:

```text
1. Parse the JSON:API response.
2. Read the hosted checkout URL from data.attributes.url.
3. Return only the URL and any safe UI metadata to the frontend.
4. Redirect the browser to the URL or open it through the Lemon Squeezy overlay when the project uses the overlay.
```

Do not share converted cart URLs. Use checkout URLs created by the API or the Lemon Squeezy dashboard.

## Backend Checkout Endpoint

Use this endpoint name unless the project already has a convention:

```text
POST /api/billing/checkout
```

Responsibilities:

- Require an authenticated user when the purchase belongs to an account.
- Validate the requested plan, price, quantity, currency, and billing interval from server-side configuration.
- Create a local pending payment, checkout intent, or audit record before calling Lemon Squeezy.
- Include a local identifier in `checkout_data.custom` so the webhook can identify the target user or organization.
- Call Lemon Squeezy with JSON:API headers and Bearer authentication.
- Return the checkout URL to the frontend.
- Log non-sensitive failure details and return a safe error message.

Request shape:

```json
{
  "plan": "pro",
  "quantity": 1
}
```

Response shape:

```json
{
  "checkoutUrl": "https://example.lemonsqueezy.com/checkout/buy/..."
}
```

## Frontend Responsibilities

The frontend should:

- Show the product, plan, billing interval, and final action clearly before checkout.
- POST to the backend checkout endpoint.
- Redirect the user to the returned checkout URL.
- Show loading and failure states around checkout creation.
- After checkout success, refresh billing state from the backend.

The frontend must not:

- Call the Lemon Squeezy API directly with a secret key.
- Calculate authoritative payment status.
- Grant paid access immediately after redirect.
- Trust query string values from the success URL as proof of payment.

## Webhook Setup

Create a webhook in Lemon Squeezy Settings > Webhooks, or with the Webhooks API.

Required webhook settings:

```text
Callback URL: https://your-domain.com/api/webhooks/lemonsqueezy
Signing secret: value stored in LEMONSQUEEZY_WEBHOOK_SECRET
Events: only the events the app needs
```

Recommended events for one-time payments:

```text
order_created
order_refunded
license_key_created
license_key_updated
```

Recommended events for subscriptions:

```text
subscription_created
subscription_updated
subscription_cancelled
subscription_resumed
subscription_expired
subscription_paused
subscription_unpaused
subscription_payment_failed
subscription_payment_success
subscription_payment_recovered
```

Use the smallest event set that keeps local access correct.

## Webhook Signature Verification

Webhook verification must use the raw request body, not a parsed JSON object.

Lemon Squeezy sends the signature in:

```text
X-Signature: {signature}
```

Verification algorithm:

```text
1. Read the raw request body bytes or exact raw body string.
2. Compute HMAC-SHA256 over the raw body using LEMONSQUEEZY_WEBHOOK_SECRET.
3. Encode the digest as lowercase hex.
4. Compare the computed digest with X-Signature using a timing-safe comparison.
5. Reject the request before parsing JSON if the signature is missing or invalid.
```

Node-style example:

```ts
import crypto from "node:crypto";

export function verifyLemonSqueezySignature(
  rawBody: string | Buffer,
  signature: string | null,
  secret: string,
) {
  if (!signature) return false;

  const digest = crypto
    .createHmac("sha256", secret)
    .update(rawBody)
    .digest("hex");

  const expected = Buffer.from(digest, "utf8");
  const received = Buffer.from(signature, "utf8");

  if (expected.length !== received.length) return false;
  return crypto.timingSafeEqual(expected, received);
}
```

Framework rules:

- Disable automatic body parsing when the framework consumes or mutates the raw request body.
- In Next.js App Router, use `await request.text()` once, verify that string, then `JSON.parse(rawBody)`.
- In Express, use a raw body middleware for the webhook route or preserve `req.rawBody`.
- In serverless runtimes, confirm whether the platform passes a string, bytes, or already-decoded body before computing the HMAC.

## Webhook Handler

Use this endpoint name unless the project already has a convention:

```text
POST /api/webhooks/lemonsqueezy
```

Responsibilities:

- Accept only `POST`.
- Read the raw body.
- Verify `X-Signature` before parsing JSON.
- Parse `meta.event_name` and `data`.
- Store the webhook event or deduplication key before doing side effects.
- Process the event idempotently.
- Return `200` quickly after the event is safely stored or processed.
- Queue slow work when email, provisioning, CRM sync, or analytics work might exceed webhook timeouts.

Recommended event handling:

```text
order_created
  -> Mark one-time purchase paid.
  -> Store Lemon Squeezy order ID, customer ID, variant ID, amount, currency, and custom_data.

order_refunded
  -> Revoke or downgrade the related one-time entitlement if product policy requires it.

subscription_created
  -> Create or update local subscription.
  -> Grant entitlement when status is active, on_trial, or otherwise allowed by product policy.

subscription_updated
  -> Sync status, variant, renewal date, cancellation state, pause state, and seat or quantity data.

subscription_cancelled
  -> Mark cancellation requested.
  -> Usually keep access until the period end if Lemon Squeezy reports the subscription remains active until then.

subscription_expired
  -> Revoke or downgrade subscription entitlement.

subscription_payment_failed
  -> Mark billing problem and notify the user without immediately destroying data.

subscription_payment_success
  -> Confirm the subscription is paid and update renewal metadata.

license_key_created
  -> Store license key metadata only if the product uses license keys.
```

Use `meta.custom_data` to connect the event back to the local user, organization, or checkout intent.

## Local Data Model

Keep Lemon Squeezy identifiers separate from local user records.

Recommended fields for purchases:

```text
purchases
  id
  user_id or organization_id
  lemonsqueezy_order_id
  lemonsqueezy_customer_id
  lemonsqueezy_variant_id
  status
  amount
  currency
  purchased_at
  refunded_at
  raw_event_id or latest_event_key
```

Recommended fields for subscriptions:

```text
subscriptions
  id
  user_id or organization_id
  lemonsqueezy_subscription_id
  lemonsqueezy_customer_id
  lemonsqueezy_order_id
  lemonsqueezy_variant_id
  status
  renews_at
  ends_at
  trial_ends_at
  cancelled_at
  paused_at
  quantity
  raw_event_id or latest_event_key
```

Recommended fields for webhook events:

```text
payment_events
  id
  provider
  event_name
  provider_object_type
  provider_object_id
  signature_valid
  processed_at
  payload_json
  created_at
```

Rules:

- Enforce uniqueness on Lemon Squeezy object IDs where possible.
- Make webhook processing idempotent. Retried events must not double-grant credits, duplicate invoices, or create duplicate subscriptions.
- Preserve raw payloads only when allowed by the project's privacy policy and retention rules.
- Prefer storing normalized fields required by the app over depending on raw JSON for runtime authorization.

## Entitlements

Paid access should be derived from local entitlement state updated by webhooks.

Use one of these patterns:

```text
One-time purchase:
  paid entitlement exists while purchase status is paid and not refunded.

Subscription:
  paid entitlement exists while subscription status is active, on_trial, or another explicitly allowed state.

License key:
  paid entitlement exists while the license key is valid and mapped to the local account or installation.
```

Rules:

- Keep entitlement checks local and fast.
- Refresh from Lemon Squeezy only for admin repair flows or rare reconciliation jobs, not on every request.
- Do not grant access from the checkout success page alone.
- Do not remove access on a payment failure until the product policy says access should end.

## Error Handling

Checkout creation errors:

- Return a safe message to the frontend.
- Log Lemon Squeezy status code, response code, and request correlation ID if available.
- Do not log API keys, webhook secrets, full customer payloads, or payment details.
- Handle `401`, `403`, `404`, `422`, and `429` explicitly when practical.
- Retry only safe transient failures.

Webhook errors:

- Return `401` or `400` for invalid signatures.
- Return `200` after storing an event that will be processed asynchronously.
- Return a non-2xx response only when Lemon Squeezy should retry the event.
- Make retries safe through idempotency.

## Testing Checklist

Before shipping:

- `.env.example` includes the four required Lemon Squeezy variables.
- API key and webhook secret are server-only.
- Checkout endpoint rejects unauthenticated or invalid purchase requests.
- Dynamic prices are computed or validated on the backend.
- Checkout payload includes `checkout_data.custom` with the local identifier needed by webhooks.
- Checkout response returns only safe fields to the browser.
- Webhook route verifies `X-Signature` against the raw body.
- Invalid signatures are rejected.
- Webhook processing is idempotent.
- Success-page redirects do not grant access by themselves.
- Order, refund, subscription, failed payment, recovery, cancellation, expiration, and license-key cases are tested when relevant.
- Test mode and production mode use separate Lemon Squeezy configuration.
- Logs and stored payloads do not leak secrets or unnecessary personal data.

## Agent Implementation Instructions

When adding Lemon Squeezy to a project:

1. Read the existing auth, user, billing, and database patterns first.
2. Add the four required environment variables to the project's example env file.
3. Implement a server-only Lemon Squeezy client with the JSON:API headers.
4. Implement `POST /api/billing/checkout` or the project's equivalent route.
5. Include local user or organization identifiers in `checkout_data.custom`.
6. Implement `POST /api/webhooks/lemonsqueezy` with raw-body signature verification.
7. Update local purchase, subscription, license, or entitlement records from verified webhooks.
8. Add focused tests for checkout creation, signature verification, webhook idempotency, and entitlement updates.
9. Document dashboard setup steps for API keys, store ID, variant ID, and webhook secret.

## Do Not

- Do not put Lemon Squeezy secret keys in frontend code.
- Do not create checkouts directly from the browser with Bearer auth.
- Do not trust `custom_price`, plan names, quantities, or user IDs sent by the client without server validation.
- Do not parse webhook JSON before verifying the raw body signature.
- Do not use checkout success redirects as proof of payment.
- Do not process webhook retries in a way that duplicates credits or entitlements.
- Do not subscribe to every webhook event by default.
- Do not store more customer or payment data than the app needs.

## Official References

- [Lemon Squeezy API requests](https://docs.lemonsqueezy.com/api/getting-started/requests)
- [Create a checkout](https://docs.lemonsqueezy.com/api/checkouts/create-checkout)
- [Taking payments developer guide](https://docs.lemonsqueezy.com/guides/developer-guide/taking-payments)
- [Passing custom data](https://docs.lemonsqueezy.com/help/checkout/passing-custom-data)
- [Webhooks](https://docs.lemonsqueezy.com/help/webhooks)
- [Sync with webhooks](https://docs.lemonsqueezy.com/guides/developer-guide/webhooks)
- [Signing webhook requests](https://docs.lemonsqueezy.com/help/webhooks/signing-requests)
