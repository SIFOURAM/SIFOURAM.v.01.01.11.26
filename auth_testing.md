# SI FOUR AM Authentication Test Plan

1. `POST /api/auth/identify` with `baa` and both consent values set to `true` returns an account token.
2. The same endpoint with an unknown or inactive identifier returns the Indonesian account-not-found message.
3. `POST /api/auth/login` with the returned account token and a wrong PIN returns HTTP 401.
4. The same endpoint with PIN `130994` returns an access token and Owner role.
5. `GET /api/auth/me` with the access token returns active Owner data.
6. Owner creates an Admin, Bar Team, and Rider using `POST /api/users`; confirm six-digit PIN validation.
7. Deactivate a test account using `PUT /api/users/{id}` and confirm both identify and authenticated API access are blocked.
8. Confirm Rider cannot use Owner-only reports or user-management endpoints after the test account is created.
9. `POST /api/auth/verify-pin` with an authenticated token and the six-digit owner PIN `130994`
   returns `{ "ok": true }`; four- or five-digit values return HTTP 400 without unlocking POS.
10. Submit five incorrect six-digit PIN values to `/api/auth/verify-pin` from the same session/IP;
    the next request must return HTTP 429 for 15 minutes. A successful PIN clears the lock record.
11. Confirm normal inactivity no longer logs the user out after ten minutes. After `POST /api/sales/eod/close`,
    verify the browser records `si4am_eod_closed`; only three hours of no activity after that point logs out.
