# Async Jobs and Workers

Guide for AI agents building an async job processing system with this default pattern:

```text
Backend -> jobs table -> worker
```

## Rule

When a product needs background work, default to a PostgreSQL-backed jobs table and one worker process before introducing Redis, RabbitMQ, Kafka, Celery, Sidekiq, or distributed schedulers.

Use the database as the queue, keep the worker simple, make jobs safe to retry, and add more infrastructure only when the workload proves it needs it.

## When To Use This Pattern

Use this pattern for:

- Email delivery, webhook fan-out, notifications, exports, imports, report generation, billing syncs, AI calls, file processing, and other background tasks triggered by application events.
- Workloads that can tolerate polling latency, usually a few seconds.
- Jobs where at-least-once execution is acceptable.
- Systems where operational simplicity matters more than maximum queue throughput.
- Early and mid-stage products that already depend on PostgreSQL.

Do not use this pattern as the default for:

- Hard real-time processing.
- Very high throughput queues with many competing consumers.
- Strict global FIFO ordering at scale.
- Workloads that require a dedicated workflow engine, external broker semantics, or cross-service event streaming.
- Jobs that cannot be made idempotent.

## Core Principles

1. **Database as the queue.** Use PostgreSQL as the job queue for most workloads. It is durable, observable, transactional, and already part of the system. Avoid adding Redis or RabbitMQ until there is a measured need.
2. **Single worker, simple polling.** Start with one worker process that polls for due jobs and processes them. Avoid distributed locks, advisory locks, and competing consumers in the first version.
3. **Sequential claim, concurrent execution.** The worker may pick jobs sequentially but execute them concurrently with bounded `asyncio` tasks. Concurrency is an implementation detail, not a queue coordination mechanism.
4. **Fail gracefully, retry automatically.** Retry transient failures with backoff. Mark a job as `failed` only after all attempts are exhausted or after a known permanent error.
5. **Make every job idempotent.** Assume a job may run more than once. Use idempotency keys, unique constraints, external request identifiers, or domain state checks to prevent duplicate side effects.
6. **Persist useful state.** Store status, attempts, next run time, timestamps, and the last error. A developer should be able to inspect the table and understand what happened.
7. **Keep payloads small.** Store identifiers and compact parameters in the payload. Store large files, generated artifacts, or verbose inputs elsewhere and reference them from the job.
8. **Bound everything.** Set concurrency limits, timeouts, retry limits, and payload size expectations. A broken job must not starve the whole worker.
9. **Observe the lifecycle.** Log every status transition and expose counts for pending, running, succeeded, failed, and retrying jobs.

## Job Lifecycle

Use a small, explicit status model:

- `pending`: the job is ready or scheduled for the future.
- `running`: the worker has started the job.
- `succeeded`: the job completed successfully.
- `retrying`: the job failed with a transient error and is scheduled to run again.
- `failed`: the job will not be retried.
- `cancelled`: the job was intentionally stopped before completion.

The normal flow is:

```text
pending -> running -> succeeded
pending -> running -> retrying -> running -> succeeded
pending -> running -> retrying -> failed
pending -> cancelled
```

## Jobs Table Contract

Create a table that is boring, inspectable, and easy to query. A typical shape is:

```sql
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  queue TEXT NOT NULL DEFAULT 'default',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  result JSONB,
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  last_error TEXT,
  idempotency_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX jobs_poll_idx
  ON jobs (queue, status, run_at, created_at);

CREATE UNIQUE INDEX jobs_idempotency_key_idx
  ON jobs (idempotency_key)
  WHERE idempotency_key IS NOT NULL;
```

Prefer `status`, `run_at`, and `attempts` over hidden worker state. Avoid adding lock columns in the single-worker version unless there is a real recovery problem to solve.

## Backend Responsibilities

The backend should:

- Validate the user request before enqueueing work.
- Insert a job row in the same transaction as related domain changes when consistency matters.
- Use a stable `job_type` string that maps to one handler.
- Store only the data the worker needs to find the real domain records.
- Return the job ID when the caller needs status tracking.
- Avoid doing slow job work inline after inserting the row.

Example enqueue behavior:

```text
1. User requests an export.
2. Backend creates an export record.
3. Backend inserts a job with job_type = "generate_export" and payload = {"export_id": "..."}.
4. Backend returns the export ID or job ID.
5. Worker generates the export and updates the export record.
```

## Worker Responsibilities

The worker should:

- Poll for jobs where `status IN ('pending', 'retrying')` and `run_at <= now()`.
- Claim jobs by marking them `running` before execution.
- Dispatch by `job_type` to a small handler function.
- Run multiple handlers concurrently only through a bounded concurrency limit.
- Apply a per-job timeout.
- Update the job row after success, retry, failure, or cancellation.
- Sleep briefly when no jobs are available.
- Shut down gracefully by stopping polling and waiting for in-flight jobs up to a deadline.

For one worker process, a simple polling loop is enough. Do not design for multiple workers until the application actually needs them.

## Retry Policy

Classify errors before deciding the next state:

- Transient errors: network failures, rate limits, database deadlocks, temporary provider errors, timeouts. Retry with backoff.
- Permanent errors: invalid payload, missing required domain record, permission failure, unsupported job type, malformed external response that cannot succeed on retry. Mark as `failed`.
- Cancellation: user-requested or system-requested stop. Mark as `cancelled`.

Use exponential backoff with jitter:

```text
delay_seconds = min(base_delay * 2^(attempts - 1), max_delay) + random_jitter
```

Good defaults:

- `max_attempts`: 3 to 5.
- `base_delay`: 30 seconds.
- `max_delay`: 15 minutes.
- `poll_interval`: 1 to 5 seconds.
- `job_timeout`: explicit per job type.

## Idempotency Rules

Every handler must be safe to retry. Before writing a handler, decide what makes the job complete and how duplicate side effects are prevented.

Use one or more of these techniques:

- Check domain state before acting, such as `export.status == 'completed'`.
- Use unique constraints for records created by the job.
- Pass idempotency keys to external APIs that support them.
- Store provider request IDs or delivery IDs.
- Split irreversible side effects from retryable preparation work.
- Make final updates atomic.

Never rely on "the worker only runs once" as a correctness guarantee.

## Handler Design

Keep each job handler small and explicit:

- Input is the job payload plus database access.
- Output is either success data or a raised typed error.
- Business logic lives in services that can be tested without the worker loop.
- The handler updates domain records, while the worker updates job lifecycle fields.
- Long handlers should checkpoint progress in domain tables, not only in memory.

Avoid handlers that:

- Parse many unrelated payload shapes.
- Depend on global mutable state.
- Hide retries inside the handler while the worker also retries.
- Swallow errors and pretend the job succeeded.

## Polling Query

For the single-worker version, keep the query straightforward:

```sql
SELECT id
FROM jobs
WHERE queue = $1
  AND status IN ('pending', 'retrying')
  AND run_at <= now()
ORDER BY run_at ASC, created_at ASC
LIMIT $2;
```

Then mark selected jobs as `running` before starting handlers.

Because there is only one worker process, avoid `FOR UPDATE SKIP LOCKED` as a default. Add it only if the system intentionally moves to multiple worker processes.

## Concurrency

Use concurrency to improve throughput inside the single worker process, not to create competing consumers.

Set a fixed concurrency limit per worker, for example:

```text
WORKER_CONCURRENCY=5
```

Use lower limits for jobs that call rate-limited external APIs or consume high memory. Use separate queues only when job classes have clearly different resource profiles, such as `default`, `email`, and `heavy`.

## Scheduling

Scheduled jobs do not need a second system. Set `run_at` in the future and let the worker pick the job when it becomes due.

For recurring jobs, prefer a small scheduler task that periodically inserts ordinary job rows with an idempotency key for the schedule window.

## Observability

At minimum, log:

- Job created.
- Job started.
- Job succeeded.
- Job scheduled for retry.
- Job failed.
- Job cancelled.

Track metrics:

- Jobs by status and queue.
- Job duration by type.
- Attempts by type.
- Failure count by type.
- Oldest pending job age.
- Retry count and exhausted retry count.

Add an admin view or support query before adding complex infrastructure. Most debugging should be possible from the jobs table.

## Operational Safety

Include these safeguards:

- A maximum payload size guideline.
- A timeout per job type.
- A dead-letter view for `failed` jobs.
- A manual retry path for failed jobs after the underlying issue is fixed.
- Graceful shutdown handling.
- Startup logs that show queue name, poll interval, concurrency, and enabled job types.

If the worker crashes while jobs are `running`, decide explicitly how to recover them. For the first version, it is acceptable to reset stale `running` jobs on startup if they have exceeded a conservative timeout and their handlers are idempotent.

## When To Add More Infrastructure

Only move beyond this pattern when there is evidence, such as:

- One worker cannot keep up even after reasonable concurrency tuning.
- Multiple independent services must consume the same event stream.
- Queue latency requirements are below what polling can provide.
- Broker-specific features are required, such as acknowledgements, priorities, routing, fan-out, or delayed delivery at large scale.
- Operational metrics show PostgreSQL queue queries are affecting core application performance.

When that happens, introduce the smallest next step:

1. Add `FOR UPDATE SKIP LOCKED` and multiple workers if PostgreSQL is still sufficient.
2. Split queues by resource profile if one job type starves others.
3. Move to a dedicated broker only when database-backed processing is no longer the right tool.

## Agent Checklist

When implementing async jobs, the AI agent must verify:

- The backend inserts a durable job row instead of doing slow work inline.
- The worker is a single polling process by default.
- The job table includes status, payload, attempts, max attempts, run time, timestamps, and error fields.
- Job handlers are idempotent.
- Transient and permanent errors are handled differently.
- Retries use backoff and stop after a fixed limit.
- Concurrency is bounded.
- Job payloads store references, not large blobs.
- Logs and metrics cover the job lifecycle.
- No Redis, RabbitMQ, distributed lock, advisory lock, or competing-consumer design was added without a documented reason.

## Default Decision

Start simple:

```text
PostgreSQL jobs table + one asyncio worker + bounded concurrency + retries with backoff
```

Scale the design only after real workload data shows that the simple version is not enough.
