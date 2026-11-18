# Auth0 setup for JobPull login (with Google SSO)

This is the checklist **you** complete in the Auth0 dashboard. It takes ~10 min.
When you're done, send me the three values at the bottom and I'll wire the app.

We use the **SPA + API** pattern:
- The **Next.js app** (`UI/`, dev server on **port 3000**) logs users in with Auth0 via `@auth0/auth0-react` (PKCE — no client secret in the browser).
- The FastAPI backend (`BE/`) verifies the Auth0 access token (RS256 via JWKS) before serving `/api/*`.
- Google sign-in is an Auth0 "social connection" — users click **Continue with Google**.

> Note: the login lives in the new Next.js UI, which runs on **`http://localhost:3000`** — so that is the URL Auth0 needs below, **not** the old `:8000` console.

---

## 1. Create an Auth0 account + tenant
1. Go to https://auth0.com → sign up (free tier is plenty).
2. Pick a region (e.g. US/EU). Auth0 gives you a tenant domain like `dev-ab12cd34.us.auth0.com`.

## 2. Create the Application (the login client)
1. **Applications → Applications → Create Application**.
2. Name: `JobPull`. Type: **Single Page Web Applications**. Click **Create**.
3. Open the **Settings** tab and note the **Domain** and **Client ID** (you'll send these to me).
4. Scroll to **Application URIs** and set all three to the Next.js dev URL (comma-separate the deployed URL once you deploy):
   - **Allowed Callback URLs:** `http://localhost:3000`
   - **Allowed Logout URLs:** `http://localhost:3000`
   - **Allowed Web Origins:** `http://localhost:3000`
5. Click **Save Changes**.

> SPA apps use PKCE, so there is **no client secret** in the frontend. Don't send me a secret.

## 3. Create the API (so the backend can verify tokens)
1. **Applications → APIs → Create API**.
2. Name: `JobPull API`. Identifier: `https://jobpull-api` (just an ID — it does **not** need to be a real URL). Signing Algorithm: **RS256**.
3. Click **Create**. The Identifier is the **Audience** (you'll send this to me).

## 4. Turn on Google sign-in (SSO)
1. **Authentication → Social → Create Connection → Google / Gmail**.
2. Auth0 ships **development keys**, so you can test Google login immediately — just **Create / enable** it.
3. Open the connection's **Applications** tab and toggle **JobPull ON**.
4. *(Production, optional later)* Replace the dev keys with your own **Google OAuth Client ID + Secret** from Google Cloud Console → removes Auth0's dev-key limits and the extra consent screen. We can do this before launch.

## 5. Allow freshers to self-register
- **Google login self-registers** automatically on first sign-in — nothing to do.
- If you also want email/password signup: **Authentication → Database → Username-Password-Authentication → Settings** → make sure **Disable Sign Ups** is **OFF**.

---

## Send me these three values when done
| Value | Example | Where it came from |
|-------|---------|--------------------|
| **Domain** | `dev-ab12cd34.us.auth0.com` | Application → Settings |
| **Client ID** | `aBcD1234...` | Application → Settings |
| **Audience** | `https://jobpull-api` | APIs → Identifier |

I'll put them in **two** files:

**`UI/.env.local`** — the Next.js frontend (the `NEXT_PUBLIC_` prefix exposes them to the browser, which is fine; they're public):
```
NEXT_PUBLIC_AUTH0_DOMAIN=dev-ab12cd34.us.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=aBcD1234...
NEXT_PUBLIC_AUTH0_AUDIENCE=https://jobpull-api
```

**`BE/.env`** — the FastAPI backend (to validate every token's signature + audience):
```
AUTH0_DOMAIN=dev-ab12cd34.us.auth0.com
AUTH0_AUDIENCE=https://jobpull-api
```
The frontend signs users in with `@auth0/auth0-react` and attaches the access token to each `/api/*` call; the backend verifies it against Auth0's JWKS. (The Client ID is only needed by the frontend.)

> None of these are secrets — Domain and Client ID are public by design, and the Audience is just an identifier. Safe to paste in chat.

---

## Troubleshooting

**`Client "…" is not authorized to access resource server "https://jobpull-api"`**
The login reached Auth0 fine, but the app isn't allowed to request tokens for the API. Fix in the dashboard:
1. **Applications → APIs** — confirm an API exists with **Identifier exactly `https://jobpull-api`** (no trailing slash). If it's missing, create it (step 3 above).
2. Open that **API → "Application Access"** tab (older tenants call it "Machine To Machine Applications") → find **JobPull** and **enable / authorize** it → **Save**. This grants the app access to the API and clears this error.
3. Retry the login.

**`Callback URL mismatch`** — add `http://localhost:3000` to **Allowed Callback URLs** (step 2.4).
