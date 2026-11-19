# Point `jobs.companion-lms.com` → the JobPull frontend (Vercel)

Registrar: **GoDaddy** · Frontend host: **Vercel**. Use your exact domain spelling
if it differs from `companion-lms.com`.

---

## 1. Add the subdomain in Vercel
1. Vercel → your **JobPull** project → **Settings → Domains**.
2. Type `jobs.companion-lms.com` → **Add**.
3. Vercel shows the DNS record to create. For a subdomain it's a **CNAME**:
   - Name: `jobs`  →  Value: `cname.vercel-dns.com`
   - Use **exactly** what Vercel displays (it occasionally differs). Leave this tab open.

## 2. Add the DNS record in GoDaddy
1. GoDaddy → **My Products → companion-lms.com → DNS** (Manage DNS).
2. **Add** a record:
   - **Type:** CNAME
   - **Name / Host:** `jobs`  ← just the label, **not** the full domain
   - **Value / Points to:** `cname.vercel-dns.com`  ← what Vercel showed
   - **TTL:** 1 Hour (default)
3. **Save**. (If a record named `jobs` already exists, edit that one instead.)
4. Propagation: usually a few minutes, up to ~1 hour.

## 3. Verify + HTTPS (back in Vercel)
- Vercel auto-verifies once DNS resolves and issues a free SSL cert. When it shows
  **"Valid Configuration"**, `https://jobs.companion-lms.com` is live.

## 4. Set the frontend env vars in Vercel  ⚠️ important
`.env.local` is **not** in git, so Vercel needs these set manually.
Vercel → project → **Settings → Environment Variables** (Production), then **redeploy**:
```
NEXT_PUBLIC_AUTH0_DOMAIN=dev-jobhunt.us.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=OreUdfXEN5VBYwZ7BKtLvEpbwjZWEacl
NEXT_PUBLIC_AUTH0_AUDIENCE=https://jobpull-api
BACKEND_ORIGIN=https://<your-cloud-run-service-url>
```
- Without the `NEXT_PUBLIC_AUTH0_*` vars, the deployed app **skips login**.
- `BACKEND_ORIGIN` = your Cloud Run service URL (Cloud Run console → the service → URL,
  e.g. `https://jobpull-ui-abc123-uc.a.run.app`). The Next server proxies `/api/*` there.
- After adding vars: **Deployments → ⋯ → Redeploy** so they take effect.

## 5. Update Auth0 for the new domain
Auth0 → **Applications → JobPull** (SPA) → **Settings → Application URIs**. Add the new
origin to **all three** (keep `http://localhost:3000` too — comma-separated):
- **Allowed Callback URLs:** `https://jobs.companion-lms.com`
- **Allowed Logout URLs:** `https://jobs.companion-lms.com`
- **Allowed Web Origins:** `https://jobs.companion-lms.com`

**Save Changes.**

## 6. Test
Open `https://jobs.companion-lms.com` → **Continue with Google** → you should land in
the app (the track picker on first login).

---

### Notes
- The Cloud Run backend must be **public** (`-AllowUnauthenticated`) so Vercel's proxy
  can reach it — Auth0 JWT still protects the data at the app layer.
- Auth0's **dev Google keys** are fine to launch with; swap in your own Google OAuth
  client later to remove the extra consent screen and rate limits.
- No backend/DNS change is needed for the API — the browser only ever talks to
  `jobs.companion-lms.com`, and Vercel forwards `/api/*` to Cloud Run server-side.
