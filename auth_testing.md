# SI FOUR AM Authentication Hardening Test Plan

1. `POST /api/auth/identify` with `baa` and both consent values set to `true` returns an account token.
2. The same endpoint with an unknown or inactive identifier returns HTTP 401 without revealing account status.
3. `POST /api/auth/login` with the returned account token and a wrong PIN returns HTTP 401.
4. The same endpoint with PIN `130994` sets the secure, HttpOnly `si4am_session` cookie.
5. `GET /api/auth/me` with the session cookie returns active Owner data.
6. Owner creates an Admin, Bar Team, and Rider using `POST /api/users`; confirm six-digit PIN validation.
7. Deactivate a test account using `PUT /api/users/{id}` and confirm both identify and authenticated API access are blocked.
8. Confirm Rider cannot use Owner-only reports or user-management endpoints after the test account is created.
9. `POST /api/auth/verify-pin` with an authenticated token and the six-digit owner PIN `130994`
   returns `{ "ok": true }`; four- or five-digit values return HTTP 400 without unlocking POS.
10. Submit five incorrect six-digit PIN values to `/api/auth/verify-pin` from the same session/IP;
    the next request must return HTTP 429 for 15 minutes. A successful PIN clears the lock record.
11. Confirm normal inactivity never logs any role out. A Rider logs out exactly three hours after daily EOD
    close; activity must not extend this fixed three-hour deadline. Owner, Admin, and Bar Team logout at
    00:00 WIB regardless of activity, with the session date stored as `si4am_session_wib_date`.
12. `POST /api/auth/logout` clears the cookie and invalidates the server-side session; `/api/auth/me`
    must then return HTTP 401.
13. More than ten identify, login, or PIN-gate requests from one client within one minute returns HTTP 429.
14. Verify an inactive user and a revoked session are rejected on every following API request.
