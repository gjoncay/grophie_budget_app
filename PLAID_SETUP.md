# Setting up Plaid

Hearth needs a Plaid `client_id` and `secret` to connect bank/brokerage
accounts. Plaid's sandbox tier is free — no real bank connections happen
until you deliberately switch to production keys.

## 1. Create a developer account

1. Go to [dashboard.plaid.com/signup](https://dashboard.plaid.com/signup) and sign up (free).
2. Once in the dashboard, go to **Team Settings → Keys**
   ([dashboard.plaid.com/developers/keys](https://dashboard.plaid.com/developers/keys)).
3. Copy your `client_id` and the **Sandbox** `secret` (not the
   Development/Production one yet).

## 2. Add the keys to `.env`

If you haven't already, copy the example env file:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
PLAID_CLIENT_ID=<your client_id>
PLAID_SECRET=<your sandbox secret>
PLAID_ENV=sandbox
```

Leave `TOKEN_ENCRYPTION_KEY` blank — the app generates one itself on
first run and writes it back into `.env` (see `app/security.py`). Don't
hand-edit that line afterward or you'll lose the ability to decrypt
already-stored access tokens.

Restart the app (or `systemctl --user restart hearth` if you're running
it as the systemd service) so it picks up the new `.env` values.

## 3. Connect a sandbox account

1. Open the app → **Accounts** → **Connect an account**.
2. In Plaid Link's institution search, pick any test institution — e.g.
   search "Platypus" (Plaid's default sandbox bank).
3. When asked to log in, use Plaid's sandbox test credentials:
   - Username: `user_good`
   - Password: `pass_good`
   - If prompted for a 2FA/MFA code: `1234` (or "code" for some flows)
4. Select any accounts offered and finish the flow. You should land back
   on the Accounts page with sandbox accounts and (within a few
   seconds) backfilled transactions on the Transactions page.

Sandbox data is fake but behaves like the real API — good for
exercising the whole app (Dashboard, Investments, Transactions,
Targets) before connecting anything real.

## 4. Going to production (real accounts)

When you're ready to connect real bank/brokerage accounts:

1. In the Plaid dashboard, request **Production** access (Team Settings
   → Keys → Production). Plaid reviews this — it's not instant, and
   beyond a small free allowance of connected Items, it requires a paid
   plan. See [plaid.com/pricing](https://plaid.com/pricing).
2. Once approved, copy the **Production** `secret`.
3. Update `.env`:
   ```env
   PLAID_SECRET=<your production secret>
   PLAID_ENV=production
   ```
4. Restart the app and connect your real accounts the same way as
   sandbox (Accounts → Connect an account).

## Notes

- `PLAID_CLIENT_ID` stays the same across sandbox and production;
  only `PLAID_SECRET` and `PLAID_ENV` change.
- Access tokens are encrypted at rest (`app/security.py`) and `.env` is
  gitignored — neither should ever end up in a commit.
- No webhooks are used (the app is local-only, not reachable from the
  internet); syncing happens via the daily scheduled job and the
  "Sync all now" button on Settings instead.
