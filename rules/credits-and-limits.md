# Credits and Limits System

Universal guide for AI agents building a credit-based usage, quota, or billing system in any project.

## Rule

When a product charges users with credits, usage units, tokens, seats, minutes, generations, exports, or similar limits, use an append-only credit ledger as the source of truth.

Derive the user's available balance from signed transaction rows, check affordability before expensive work starts, and make all payment and usage operations idempotent.

## When To Use This Pattern

Use this rule for:

- AI generation credits, token budgets, image generations, transcription minutes, render minutes, API usage units, exports, or other usage-based features.
- Prepaid credit systems where users top up before spending.
- Subscription plans that grant recurring credits.
- Free trial credits, promotional credits, manual adjustments, refunds, and support-issued compensation.
- Internal limits where the unit is money-adjacent or operationally expensive.

Do not treat this rule as a complete accounting, tax, invoicing, or regulated financial ledger. Payment providers, invoices, revenue recognition, taxes, and legal accounting records must remain in dedicated billing systems.

## Core Principles

1. **Single balance, single source of truth.** A user's balance is always derived from `SUM(amount)` over credit transactions. Do not store a separate `balance` column that can drift from the ledger.
2. **Ledger-style accounting.** Every balance change is a signed row. Positive amounts add credits. Negative amounts spend, expire, or remove credits. This gives the product a durable audit trail.
3. **Decimal precision.** Use `NUMERIC(18, 6)` or the closest exact decimal equivalent. Do not use floating-point types for credits or money-adjacent values.
4. **Credits are not money.** Store money paid, currency, invoices, and tax details separately in the payment provider or billing tables. The credit ledger records product entitlement, not cash accounting.
5. **Idempotent payments.** Store a unique external payment event ID, checkout session ID, invoice ID, or provider transaction ID. Check it before crediting a user so repeated webhooks cannot grant credits twice.
6. **Check before execute.** Verify the user has enough credits before starting expensive work. Do not run the work first and hope post-hoc billing succeeds.
7. **Check and spend atomically.** The affordability check and the spend or reservation write must happen in the same database transaction with concurrency protection.
8. **Reserve for uncertain costs.** If final cost is unknown, reserve the maximum expected amount first, then settle after the operation by capturing the actual cost and releasing the unused portion.
9. **Refund failed work.** If credits were charged or reserved and the operation fails before delivering value, write a positive reversal or release the reservation.
10. **Never hide mutations.** Every credit mutation must have a type, reason, actor or system source, and reference to the operation, payment, job, or admin action that caused it.
11. **Prevent accidental debt.** Do not allow negative balances unless the product explicitly supports credit lines. If debt is supported, model it as a deliberate policy with limits and alerts.
12. **Separate credits from feature limits.** Credits pay for usage. Plan limits control access, rate, seats, concurrency, storage, or feature availability. Keep both concepts explicit.
13. **Make it inspectable.** A developer should be able to answer "why does this user have this balance?" by reading the ledger and linked references.

## Recommended Architecture

Prefer this flow:

```text
Payment provider webhook
  -> idempotency check
  -> positive credit transaction
  -> balance is derived from ledger

User requests expensive operation
  -> estimate or determine cost
  -> lock the user's credit account
  -> compute available balance
  -> insert spend or reservation
  -> start the operation
  -> settle, refund, or release if needed
```

Use these main concepts:

- `credit_accounts`: one row per user or organization, used for ownership and transactional locking. It does not store balance.
- `credit_transactions`: append-only signed ledger rows. This is the source of truth.
- `credit_reservations`: optional holds for operations with uncertain or delayed final cost.
- `usage_events`: optional product-level records for reporting and user-facing usage history.
- Billing provider tables or metadata: optional mirror of provider IDs, invoices, checkout sessions, subscriptions, and webhook events.

## Credit Account Contract

Create an account row for the entity that owns credits. This may be a user, team, organization, workspace, tenant, or project.

```sql
CREATE TABLE credit_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_type TEXT NOT NULL,
  owner_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (owner_type, owner_id)
);
```

The account row exists so the application has one stable row to lock during credit mutations:

```sql
SELECT id
FROM credit_accounts
WHERE owner_type = $1 AND owner_id = $2
FOR UPDATE;
```

Do not add `balance` to this table.

## Credit Transaction Contract

Use an append-only table for every credit mutation:

```sql
CREATE TABLE credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES credit_accounts(id),
  amount NUMERIC(18, 6) NOT NULL,
  type TEXT NOT NULL,
  reason TEXT NOT NULL,
  reference_type TEXT,
  reference_id TEXT,
  external_provider TEXT,
  external_transaction_id TEXT,
  idempotency_key TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (amount <> 0)
);

CREATE INDEX credit_transactions_account_created_idx
  ON credit_transactions (account_id, created_at);

CREATE UNIQUE INDEX credit_transactions_idempotency_key_idx
  ON credit_transactions (idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX credit_transactions_external_tx_idx
  ON credit_transactions (external_provider, external_transaction_id)
  WHERE external_provider IS NOT NULL
    AND external_transaction_id IS NOT NULL;
```

Recommended transaction types:

- `top_up`: positive credits bought by the user.
- `subscription_grant`: positive credits granted by a recurring plan.
- `trial_grant`: positive credits granted for onboarding or promotion.
- `admin_adjustment`: positive or negative manual correction with an audit reason.
- `spend`: negative credits consumed by a completed operation with known cost.
- `reservation_capture`: negative credits captured from a prior reservation.
- `refund`: positive credits returned for failed, cancelled, or reversed work.
- `expiration`: negative credits removed because a grant expired.

Avoid updating or deleting transaction rows. If a correction is needed, insert a reversing row.

## Balance Query

Always derive balance with an exact aggregate:

```sql
SELECT COALESCE(SUM(amount), 0)::NUMERIC(18, 6) AS balance
FROM credit_transactions
WHERE account_id = $1;
```

If reservations are used, available balance is:

```text
available_balance = ledger_balance - active_reserved_amount
```

Keep user-facing balance formatting separate from internal precision. For example, the UI may show `12.50 credits`, while the database stores `12.500000`.

## Atomic Spend

Never perform this sequence:

```text
read balance in application code
return to caller
later insert spend
```

Use a single transaction:

```text
1. Begin transaction.
2. Lock the credit account row.
3. Compute current available balance.
4. If balance < cost, abort with an insufficient credits error.
5. Insert a negative credit transaction or create a reservation.
6. Commit.
7. Start the expensive operation only after the commit succeeds.
```

Example direct spend:

```sql
BEGIN;

SELECT id
FROM credit_accounts
WHERE id = $1
FOR UPDATE;

SELECT COALESCE(SUM(amount), 0)::NUMERIC(18, 6) AS balance
FROM credit_transactions
WHERE account_id = $1;

-- Application checks balance >= cost inside this transaction.

INSERT INTO credit_transactions (
  account_id,
  amount,
  type,
  reason,
  reference_type,
  reference_id,
  idempotency_key
) VALUES (
  $1,
  -$2,
  'spend',
  'ai_generation',
  'generation',
  $3,
  $4
);

COMMIT;
```

For high-concurrency systems, keep the row lock or use serializable isolation plus retry handling. Do not rely on a plain read of `SUM(amount)` under concurrency.

## Reservations

Use reservations when the final cost depends on runtime behavior, duration, token count, file size, provider response, or job completion.

Recommended reservation table:

```sql
CREATE TABLE credit_reservations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES credit_accounts(id),
  amount NUMERIC(18, 6) NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  reason TEXT NOT NULL,
  reference_type TEXT,
  reference_id TEXT,
  idempotency_key TEXT,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  settled_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  CHECK (amount > 0)
);

CREATE INDEX credit_reservations_active_idx
  ON credit_reservations (account_id, status, expires_at);

CREATE UNIQUE INDEX credit_reservations_idempotency_key_idx
  ON credit_reservations (idempotency_key)
  WHERE idempotency_key IS NOT NULL;
```

Reservation statuses:

- `active`: credits are held and unavailable for other work.
- `captured`: final spend has been written to the ledger.
- `released`: no credits were consumed.
- `expired`: the hold timed out and should no longer reduce available balance.

Settlement rules:

- Capture actual cost with a negative `reservation_capture` transaction.
- If actual cost is lower than reserved amount, capture only the actual cost.
- If the operation fails before delivering value, release the reservation and write no spend.
- If actual cost exceeds the reservation, require a second affordability check before capturing the extra amount.
- Expire stale reservations with a scheduled job so credits are not held forever.

## Payment Webhooks

Payment webhooks must be idempotent and auditable.

For each provider event:

```text
1. Parse and verify the webhook signature.
2. Extract the stable provider event ID and payment object ID.
3. Start a transaction.
4. Check whether the provider event or payment transaction was already processed.
5. Resolve the credit account.
6. Insert the positive credit transaction.
7. Store provider IDs, amount paid, currency, and plan or package metadata.
8. Commit.
```

Webhook rules:

- Never trust client-side success pages to grant credits.
- Never grant credits before the provider confirms payment success.
- Store enough provider metadata to debug support requests.
- Handle webhook retries as normal behavior, not exceptional behavior.
- Decide how refunds, disputes, chargebacks, and cancelled subscriptions affect credits before shipping.

## Subscription Credits

For subscriptions that grant recurring credits:

- Grant credits from confirmed invoice or subscription renewal events, not from optimistic client state.
- Use the invoice ID or subscription period ID as the idempotency key.
- Decide whether unused credits roll over, expire, or reset at period boundaries.
- Make expiration explicit with `expiration` transactions rather than hidden balance resets.
- Keep plan entitlements separate from credit balance.

Common policies:

```text
Monthly plan grants 100 credits
  -> insert +100 subscription_grant on paid invoice
Unused monthly credits expire after 30 days
  -> insert negative expiration rows for the expired grant
Plan allows 3 concurrent jobs
  -> enforce as a plan limit, not as credits
```

## Free Trials and Promotions

Trial and promotional credits must be traceable.

Rules:

- Use explicit `trial_grant` or promotional transaction types.
- Attach campaign, coupon, invite, or onboarding metadata.
- Apply clear expiration rules if credits are temporary.
- Prevent repeated abuse with idempotency keys and owner-level uniqueness where needed.
- Never mix promotional credits with payment confirmation logic.

## Usage Events

Use usage events for product analytics and user-facing history. Do not use them as the financial source of truth.

Example usage event:

```sql
CREATE TABLE usage_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES credit_accounts(id),
  credit_transaction_id UUID REFERENCES credit_transactions(id),
  event_type TEXT NOT NULL,
  units NUMERIC(18, 6) NOT NULL,
  unit_name TEXT NOT NULL,
  reference_type TEXT,
  reference_id TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Usage events are useful for dashboards, exports, cost breakdowns, rate analysis, and support tooling. The ledger remains authoritative.

## Pricing and Cost Calculation

Keep pricing logic deterministic and testable.

Rules:

- Define a stable cost function per billable operation.
- Store the cost basis in metadata, such as model name, token count, image size, duration, or unit rate.
- Version pricing rules when prices may change.
- Do not silently change the cost of an already completed operation.
- Round only at deliberate boundaries. Prefer storing exact fractional credits internally.
- Show the estimated cost to users before work starts when the action is expensive or surprising.

Example:

```text
operation = "transcription"
unit = "minute"
rate = 0.25 credits per minute
duration = 3.42 minutes
cost = 0.855 credits
```

## Insufficient Credits UX

When the user cannot afford an operation:

- Return a clear `insufficient_credits` error.
- Include required credits and available credits when safe to expose.
- Do not enqueue jobs that cannot be paid for.
- Do not partially execute expensive work.
- Offer top-up or plan upgrade paths if the product has them.

Recommended response shape:

```json
{
  "error": "insufficient_credits",
  "required": "5.000000",
  "available": "2.750000"
}
```

## Admin Adjustments

Manual changes must be rare, explicit, and auditable.

Rules:

- Require a reason for every admin adjustment.
- Store the admin actor ID when available.
- Prefer small correction transactions over editing historical rows.
- For support compensation, use positive `admin_adjustment`.
- For abuse, fraud, or correction, use negative `admin_adjustment` or `expiration` with a clear reason.
- Log admin changes in the product's audit log if one exists.

## Security and Abuse Prevention

Credit systems are abuse targets. Build guardrails early.

- Verify payment webhooks with provider signatures.
- Do not accept credit amounts from untrusted clients.
- Compute package credits and prices server-side.
- Protect admin adjustment endpoints with strong authorization.
- Rate-limit expensive operations and top-up attempts.
- Alert on unusual credits granted, sudden high spend, repeated failed payments, and negative-balance attempts.
- Keep metadata free of secrets, access tokens, raw payment details, and unnecessary personal data.

## Testing Checklist

Test at least these cases:

- Balance is derived from transactions and has no stored duplicate.
- Positive top-up increases derived balance.
- Negative spend decreases derived balance.
- Spend is rejected when balance is insufficient.
- Two concurrent spends cannot overspend the same balance.
- Duplicate payment webhooks do not grant credits twice.
- Failed jobs release reservations or create refunds.
- Subscription renewal grants credits exactly once per billing period.
- Expiration removes credits through explicit ledger rows.
- Admin adjustments require a reason and are visible in audit history.
- Decimal costs do not suffer floating-point rounding errors.

## Agent Implementation Instructions

When implementing credits and limits, AI agents must:

- Create the ledger first, then build UI, webhook, and usage features around it.
- Use exact decimal database types and exact decimal libraries in application code when needed.
- Lock the credit account or use a proven serializable transaction strategy before spending.
- Put affordability checks on the server, never only in the client.
- Make webhook handlers idempotent before adding provider-specific branching.
- Add tests for duplicate webhooks and concurrent spends.
- Document the unit conversion between product usage and credits.
- Keep the implementation boring, searchable, and support-friendly.

## Do Not

- Do not store a mutable `users.balance` or `accounts.balance` as the source of truth.
- Do not use `FLOAT`, `REAL`, JavaScript `number`, or similar imprecise types for authoritative credit math when exact decimals are available.
- Do not grant credits from client-side checkout success callbacks.
- Do not process a payment webhook without an idempotency key.
- Do not start expensive work before checking and reserving or spending credits.
- Do not update old ledger rows to "fix" history.
- Do not silently reset balances at subscription renewal.
- Do not combine credits, plan limits, invoices, taxes, and provider payment state into one overloaded table.
- Do not rely on background workers running exactly once.
- Do not hide failed charges, refunds, expirations, or admin corrections from the ledger.

