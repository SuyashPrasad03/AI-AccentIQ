# API Documentation

## Base URL
Development: `http://localhost:8000`
Production: Deployed on Render (see README for live URL).

## Authentication
- **Anonymous**: First 3 analyses free, tracked by server-side session cookie.
- **Registered**: JWT access token in `Authorization: Bearer <token>` header. Access tokens expire in 15 minutes; use the refresh endpoint to get a new one.

## Endpoints

### Health
- `GET /health` — Check service health. Returns `{status, mysql, mongo}`.

### Auth
- `POST /auth/register` — Send OTP to email. Body: `{email}`.
- `POST /auth/verify-otp` — Verify OTP and create account. Body: `{email, otp, password}`.
- `POST /auth/login` — Login. Body: `{email, password}`. Returns access token.
- `POST /auth/refresh` — Rotate refresh token (from httpOnly cookie).
- `POST /auth/logout` — Revoke refresh token.
- `GET /auth/me` — Get current user info (requires auth).

### Quota
- `GET /quota/status` — Current usage for the caller.

### Consent
- `POST /consent` — Record a consent event. Body: `{consent_type}` (audio_processing, data_retention, privacy_policy).
- `GET /consent/status` — Check what consents exist.

### Recordings
- `POST /recordings/upload` — Upload audio file (multipart form). Requires consent + quota.
- `GET /recordings/{id}` — Get recording metadata.
- `GET /recordings/{id}/status` — Poll processing status.
- `GET /recordings/{id}/transcript` — Get word-level transcript.
- `GET /recordings/{id}/score` — Get pronunciation score and breakdown.
- `GET /recordings/{id}/words/{index}/explain` — Get AI explanation for a word.
- `GET /recordings/{id}/comparison` — Compare with previous recording.

### Practice
- `GET /practice/today` — Get today's personalized practice set.
- `POST /practice/regenerate` — Generate new practice sentences.

### Progress
- `GET /progress/history` — Full score timeline (registered users, paginated).

### Assistant
- `POST /assistant/ask` — Ask a question about the app. Body: `{question}`.

## Error Format
All errors return: `{error_code, message, details}` with appropriate HTTP status codes.

## Rate Limits
- OTP requests: 5 per email per hour.
- Upload: subject to quota (3 free for anonymous, unlimited for registered).
- Assistant: reasonable use (no explicit limit in current version).
