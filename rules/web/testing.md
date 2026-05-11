# Testing Full Stack Web Projects

Guide for AI agents working on full stack web projects that use Vitest for unit tests and Playwright for frontend end-to-end tests.

## Purpose

Use this rule whenever creating, changing, or reviewing application code. The goal is to keep the project covered by fast, reliable tests at the right level:

- Vitest for unit tests and small integration tests
- Playwright for browser-based frontend end-to-end tests
- Manual checks only as a supplement, not as a replacement for automated tests

## Rule

Every meaningful code change must include or update automated tests at the lowest useful level.

Prefer Vitest for isolated logic, components, hooks, API handlers, services, validators, formatters, and state management. Use Playwright only for user-visible browser flows that prove the frontend works with the app running.

Do not use Playwright to test simple pure logic. Do not use Vitest as a substitute for a real browser journey when the behavior depends on routing, forms, authentication, browser APIs, or frontend-backend interaction.

## Test Strategy

Use this decision order:

```text
Can the behavior be tested as pure logic?
  -> Write a Vitest unit test.

Does it depend on framework wiring, API handlers, stores, hooks, or components?
  -> Write a Vitest test with the smallest realistic setup.

Does it depend on the user interacting with the app in a browser?
  -> Write a Playwright e2e test.

Is it a critical business flow?
  -> Cover the core logic with Vitest and the happy path with Playwright.
```

Critical flows should normally have both:

- Vitest tests for edge cases, validation, branching, and error handling
- Playwright tests for the main user journey

## Vitest Rules

Use Vitest for fast feedback and broad coverage.

Test with Vitest when working on:

- Business logic and domain rules
- Utility functions and data transformations
- API handlers, request validation, and response shaping
- Authentication and authorization helpers
- Database access wrappers or repository functions
- React hooks, stores, reducers, and state machines
- Components whose behavior can be verified without a full browser flow

Vitest tests should:

- Be deterministic and isolated
- Avoid real network calls
- Mock external services such as payment providers, email, analytics, storage, and third-party APIs
- Use clear test data factories instead of copy-pasted large fixtures
- Cover success, failure, empty, and boundary cases when relevant
- Assert observable behavior, not private implementation details
- Keep snapshots small and intentional

Prefer test names that describe behavior:

```ts
it("rejects signup when the email is already used", async () => {
  // ...
});
```

Avoid vague names:

```ts
it("works", async () => {
  // ...
});
```

## Playwright Rules

Use Playwright for real frontend behavior in a running app.

Test with Playwright when working on:

- Sign up, login, logout, and password reset flows
- Navigation and protected routes
- Forms with validation and submission
- Checkout, billing, credits, or other revenue-critical flows
- Onboarding and other first-run experiences
- Dashboards or pages that depend on frontend-backend integration
- Regression coverage for bugs that only appear in the browser

Playwright tests should:

- Use accessible locators such as `getByRole`, `getByLabel`, and `getByText` first
- Use `data-testid` only when accessible locators are not stable enough
- Avoid brittle CSS selectors and arbitrary timeouts
- Seed or create test data through stable helpers, fixtures, or API setup calls
- Clean up data after the test when the project does not use an isolated test database
- Assert user-visible outcomes, not internal state
- Cover the happy path for important flows and one or two high-value failure states

Prefer:

```ts
await page.getByRole("button", { name: "Create project" }).click();
await expect(page.getByText("Project created")).toBeVisible();
```

Avoid:

```ts
await page.locator(".btn-primary").click();
await page.waitForTimeout(1000);
```

## Full Stack Coverage

For full stack features, verify the contract between frontend and backend.

When adding or changing an API endpoint:

- Add Vitest coverage for request validation, authorization, success responses, and error responses
- Update frontend tests or mocks that depend on the response shape
- Add Playwright coverage when the endpoint powers a critical user-facing flow

When adding or changing frontend behavior:

- Add Vitest coverage for local logic, state, and component behavior when useful
- Add Playwright coverage when the change affects a real user journey
- Do not rely only on visual inspection

When changing database behavior:

- Test query logic, filtering, permissions, and edge cases with Vitest or the project's existing integration-test setup
- Keep database tests isolated and repeatable
- Never point automated tests at production data

## Commands

Before running tests, inspect the project scripts and use the package manager already used by the repository.

Common commands:

```bash
npm run test
npm run test:unit
npm run test:e2e
npm run test:coverage
```

Equivalent commands with `pnpm`, `yarn`, or `bun` are fine when the project uses them.

Do not invent new commands when package scripts already exist. If scripts are missing, add clear scripts for Vitest and Playwright before relying on tests.

## CI Expectations

The project should be able to run all automated tests in CI.

CI should normally run:

- Type checking
- Linting
- Vitest tests
- Playwright tests for critical browser flows

Playwright in CI must use deterministic setup:

- A known base URL
- A clean or isolated test database
- Seeded test data
- Mocked third-party services where possible
- Stored traces, screenshots, or videos only on failure unless the project requires otherwise

## Test Data And Mocks

Keep test data small, realistic, and local to the test unless it is reused widely.

Rules:

- Do not use production credentials or production data
- Do not call real payment, email, analytics, AI, storage, or external APIs from automated tests
- Prefer local mocks, fake services, test containers, or dedicated sandbox credentials
- Make dates, timers, random IDs, and environment-dependent values deterministic
- Keep secrets out of fixtures, snapshots, traces, and screenshots

## Definition Of Done

A task is not finished until:

- Relevant Vitest tests are added or updated
- Relevant Playwright tests are added or updated for user-facing flows
- Existing affected tests pass locally when practical
- Any skipped or missing tests are explained clearly
- The final response tells the user which tests were run and what passed

If tests cannot be run because dependencies, browsers, services, or environment variables are missing, explain the blocker and name the exact command that should be run once the environment is ready.
