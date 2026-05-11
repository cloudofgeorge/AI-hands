# Google OAuth Authentication

Guide for AI agents implementing Google login and registration in any project.

## Purpose

Use this rule when a product needs users to authenticate with Google OAuth. The goal is to create a secure, predictable login flow that works for both first-time registration and returning-user sign in.

This rule covers:

- Google OAuth authorization flow
- Backend and frontend responsibilities
- Environment variables
- User creation and account linking
- JWT or session token generation
- Security requirements
- Testing and rollout checklist

## Rule

When adding Google authentication, make the backend the source of truth for OAuth exchange, user lookup, account linking, and application token creation.

The frontend may start the flow and update client auth state, but it must not own Google client secrets, validate Google identity by itself, or create application sessions.

## Recommended Flow

Use this flow when the Google redirect URI points to the backend:

```text
1. User clicks "Sign in with Google".
2. Frontend requests a Google authorization URL from the backend.
3. Backend creates a state value, stores it temporarily, and returns the authorization URL.
4. Frontend redirects the browser to Google's consent screen.
5. Google redirects to the backend callback URL with ?code=...&state=...
6. Backend verifies state and exchanges the authorization code with Google.
7. Backend fetches or verifies Google user identity.
8. Backend creates or updates the local user and linked Google account.
9. Backend creates the application session, JWT pair, or one-time app login code.
10. Backend redirects to the frontend callback page.
11. Frontend completes auth state setup and sends the user to the intended page.
```

Prefer exchanging the Google authorization code inside the backend callback. If the existing project requires the frontend callback page to POST a code back to the backend, the backend should redirect with a short-lived one-time application code instead of the raw Google authorization code.

## Alternative PKCE Flow

Use a frontend callback only when the project is intentionally using OAuth with PKCE:

```text
1. Frontend creates a code verifier and code challenge.
2. Frontend requests or builds the Google authorization URL with the code challenge.
3. Google redirects to the frontend callback URL with ?code=...&state=...
4. Frontend POSTs the code and code verifier to the backend.
5. Backend exchanges the code with Google.
6. Backend creates or updates the user and returns the application auth result.
```

Do not mix the backend-secret flow and PKCE flow accidentally. Choose one pattern and make the redirect URI, state handling, and token exchange match it.

## Environment Variables

Document required variables in `.env.example` or the project's setup guide.

```env
# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Frontend redirects
FRONTEND_URL=http://localhost:3000
FRONTEND_AUTH_CALLBACK_PATH=/auth/google/callback

# JWT or application session
JWT_SECRET_KEY=change-me-in-production
JWT_ACCESS_TOKEN_EXPIRES_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRES_DAYS=30
```

Rules:

- Never expose `GOOGLE_CLIENT_SECRET` or `JWT_SECRET_KEY` to the browser.
- Use `NEXT_PUBLIC_*`, `VITE_*`, or other public env prefixes only for non-secret frontend values.
- Use different Google OAuth clients or redirect URIs for local, staging, and production.
- Validate that `GOOGLE_REDIRECT_URI` exactly matches the URI configured in Google Cloud Console.
- Do not commit real client secrets, JWT secrets, refresh tokens, or access tokens.

## Backend Endpoints

Use these endpoint names unless the project already has a convention.

```text
GET  /api/auth/google/url
GET  /api/auth/google/callback
POST /api/auth/google/exchange
POST /api/auth/logout
GET  /api/auth/me
```

### `GET /api/auth/google/url`

Responsibilities:

- Generate a cryptographically random `state`.
- Store `state` temporarily in a signed cookie, server-side cache, session table, or short-lived auth table.
- Include the minimum required Google scopes.
- Return the authorization URL to the frontend.
- Include the user's intended return path only through a validated value, not an arbitrary external URL.

Recommended scopes:

```text
openid email profile
```

Response shape:

```json
{
  "url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

### `GET /api/auth/google/callback`

Responsibilities:

- Read `code`, `state`, and optional `error` from the query string.
- Reject missing, invalid, expired, or already-used `state`.
- Handle Google errors by redirecting to a frontend error state.
- Exchange the authorization code with Google from the backend.
- Verify the ID token or fetch the userinfo profile.
- Create or update the local user and Google account link.
- Create application auth tokens or a server session.
- Redirect to the frontend callback or final return path.

If returning a one-time application code to the frontend, keep it short-lived, single-use, and tied to the same user/session context.

### `POST /api/auth/google/exchange`

Use this endpoint only for the PKCE flow or for exchanging a backend-created one-time application code.

Request shape for one-time application code:

```json
{
  "code": "one-time-app-code"
}
```

Response shape:

```json
{
  "accessToken": "...",
  "refreshToken": "...",
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "Example User",
    "avatarUrl": "https://..."
  }
}
```

If the project uses httpOnly cookies for sessions, return only the user object and set cookies in the response.

## Frontend Responsibilities

The frontend should:

- Render a clear "Sign in with Google" action.
- Request the Google auth URL from the backend.
- Redirect the browser to that URL.
- Handle callback loading, success, and error states.
- Store the authenticated user in the app's auth state.
- Redirect the user to the page they originally intended to visit.
- Show a friendly error if Google auth fails or is cancelled.

Example frontend flow:

```text
Click Google button
  -> GET /api/auth/google/url
  -> window.location.href = response.url
  -> callback page loads
  -> auth state is refreshed
  -> user is redirected to return path
```

Do not put Google client secrets, JWT signing secrets, or token exchange logic in frontend code.

## Token Storage

Prefer one of these patterns:

1. Server session with secure httpOnly cookies.
2. Refresh token in a secure httpOnly cookie and short-lived access token in memory.
3. Short-lived access token in browser storage only when the existing project already uses that pattern.

If localStorage is required by the project:

- Store only the minimum token data needed by the app.
- Keep access tokens short-lived.
- Do not store Google access tokens unless the app truly needs to call Google APIs from the browser.
- Never store refresh tokens in localStorage when httpOnly cookies are available.
- Clear stored tokens on logout and when refresh fails.

## User and Account Model

Keep local users separate from OAuth provider accounts.

Recommended model:

```text
users
  id
  email
  name
  avatar_url
  email_verified
  created_at
  updated_at

oauth_accounts
  id
  user_id
  provider
  provider_user_id
  provider_email
  created_at
  updated_at
```

Rules:

- Use Google's stable subject claim, usually `sub`, as `provider_user_id`.
- Enforce a unique constraint on `(provider, provider_user_id)`.
- Normalize emails before lookup, but do not use email alone as the provider identity.
- Respect Google's `email_verified` value.
- Link to an existing user by email only when the project's account-linking policy allows it.
- Do not create duplicate users for the same Google account.

## JWT or Session Claims

Application tokens should contain application identity, not raw Google token data.

Recommended access token claims:

```json
{
  "sub": "local-user-id",
  "email": "user@example.com",
  "iat": 1710000000,
  "exp": 1710000900,
  "type": "access"
}
```

Rules:

- Keep JWT payloads small.
- Include a token type when using both access and refresh tokens.
- Use strong signing secrets or asymmetric keys.
- Set short access-token expiration.
- Rotate or revoke refresh tokens when the project supports it.
- Do not put Google access tokens, refresh tokens, passwords, or secrets in application JWTs.

## Security Requirements

Every implementation must include:

- `state` protection against CSRF.
- Exact redirect URI matching.
- Server-side token exchange.
- ID token validation or trusted Google userinfo retrieval.
- Email verification handling.
- Safe account linking rules.
- Open redirect prevention for return paths.
- Rate limiting for auth endpoints where supported by the stack.
- Secure cookie settings when cookies are used: `HttpOnly`, `Secure`, `SameSite=Lax` or stricter.
- Clear logout behavior.

Return paths must be relative paths or allowlisted frontend URLs. Never redirect to an arbitrary URL supplied by the request.

## Error Handling

Handle these cases explicitly:

- User denies Google consent.
- Google returns an OAuth error.
- Missing `code` or `state`.
- Invalid, expired, or reused `state`.
- Token exchange fails.
- Google profile has no verified email.
- Account exists but linking is not allowed.
- User is disabled or banned in the local system.
- Session or JWT creation fails.

Frontend errors should be understandable, but logs should contain enough backend detail for debugging. Do not show provider tokens, secrets, or raw sensitive responses in the UI.

## Testing Checklist

Before marking Google OAuth complete, verify:

- The Google button starts the redirect flow.
- The authorization URL contains the expected scopes.
- The callback rejects missing or invalid `state`.
- The callback exchanges the code only on the backend.
- A new Google user can register.
- A returning Google user can log in.
- Duplicate users are not created for the same Google account.
- Account linking behavior matches the product policy.
- Logout clears the application session or tokens.
- Refresh behavior works when refresh tokens are used.
- Frontend callback handles success, cancellation, and failure.
- Local, staging, and production redirect URIs are documented.
- Secrets are present in environment configuration and absent from source control.
- Backend tests cover callback success and failure paths when the project has tests.
- Frontend tests cover callback UI states when the project has tests.

## Agent Implementation Instructions

When an AI agent applies this rule:

1. Inspect the existing auth, user, environment, routing, and database patterns before creating files.
2. Reuse the project's current token/session architecture when it is secure enough.
3. Add the smallest complete OAuth implementation: auth URL, callback, user upsert, token/session creation, frontend button, callback state, and logout wiring.
4. Keep Google-specific code isolated in an auth provider module or service.
5. Document new environment variables in `.env.example` or setup docs.
6. Add or update tests for state validation, user creation, returning login, and error handling.
7. Run the project's available validation commands, such as linting, type checks, backend tests, and frontend tests.

## Do Not

- Do not put `GOOGLE_CLIENT_SECRET` in frontend code.
- Do not skip `state` validation.
- Do not trust only an email string without validating the Google identity response.
- Do not use arbitrary redirect URLs from request parameters.
- Do not store refresh tokens in localStorage when secure cookies are available.
- Do not return raw Google tokens to the frontend unless the product explicitly needs browser-side Google API calls.
- Do not create a new user every time a Google login succeeds.
- Do not log authorization codes, access tokens, refresh tokens, ID tokens, or JWT secrets.
- Do not hardcode local redirect URIs in production code.
