# Security

## Security boundary

The public browser reaches nginx and the versioned FastAPI API. PostgreSQL, Redis, Chroma, the RAG worker, and inference service have no published ports. The inference API also requires a constant-time-checked internal token. Docker network isolation is defense in depth, not a substitute for host firewalling or TLS.

Use a trusted TLS reverse proxy in front of port 8080. Keep both Compose host bindings on `127.0.0.1`, allow only 80/443 and SSH through the VM firewall, and set `SECURE_COOKIES=true`, the exact public origin, and the exact public host.

## Authentication

- The bootstrap administrator is configured only by `ADMIN_USERNAME` and an Argon2id `ADMIN_PASSWORD_HASH`; no authentication table is added to PostgreSQL.
- Access JWTs are short lived and held in frontend memory, not local storage.
- Refresh JWTs use `HttpOnly`, `SameSite=Strict` cookies. Their JTIs are tracked and revoked in Redis.
- Refresh and logout require a matching double-submit CSRF cookie/header.
- Login, refresh, logout, chat, and admin operations are Redis-rate-limited.
- Authentication errors do not disclose whether the username or password was wrong.

Generate a password hash inside the pinned backend image:

```bash
docker compose build backend
docker compose run --rm --no-deps backend python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass('Admin password: ')))"
```

Keep the result single-quoted in `.env`; otherwise Compose may interpret its dollar signs. The environment-backed administrator is suitable for this scoped deployment, not for multi-user authorization, SSO, MFA, or per-record audit requirements. Replace the `AuthService` boundary with an institutional identity provider before adding multiple privileged operators.

## Input and API controls

- Pydantic models reject unknown fields and enforce lengths, UUIDs, enums, dates, numbers, and pagination caps.
- SQLAlchemy issues parameterized statements; request data is never interpolated into raw SQL.
- Request bodies are size-limited before parsing.
- Trusted-host and explicit CORS allowlists are environment-configured.
- Session mutation uses a renewable token-owned Redis lock, and retries can use an `Idempotency-Key`.
- Safe exception mapping removes stack traces and dependency detail from production responses.
- Security headers include CSP, frame denial, MIME sniffing protection, referrer policy, and restricted browser capabilities.
- Admin deletion is dependency-aware; deactivation is the normal lifecycle action.

Keep `CORS_ORIGINS` and `TRUSTED_HOSTS` narrow. Never use wildcard CORS with credentialed cookies. The backend host port is for loopback health/operations only and should not be internet-facing.

## Model and RAG controls

Academic chunks and the original user message are untrusted reference data. They are sent in a separate user/data-role message below a static system policy, selected by typed metadata, and cannot override system policy. Retrieval does not fetch arbitrary URLs or dynamically load code. Model adapters use `trust_remote_code: false` and `local_files_only: true`.

The generated answer is constrained by known facts and forbidden assumptions, then checked for unsupported money, duration, accreditation, certification, mobility, career, and admission claim categories. Recommendation choices originate in deterministic catalogue/eligibility services. This reduces hallucinations but does not turn probabilistic generation into a formal proof. Admission is never represented as final or automatic, and public tariffs remain indicative.

Do not place secrets, private student information, credentials, or operator instructions in academic content. Chroma is derived from PostgreSQL, so malicious admin content can reach prompts after indexing; protect admin credentials and review source provenance.

## Secrets

Required production secrets are:

- `APP_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `INFERENCE_SERVICE_TOKEN`
- `ADMIN_PASSWORD_HASH`
- `JWT_SECRET`

Use independently generated values with at least 256 bits for application/JWT/inference secrets. The Redis password must be URL-safe because Compose embeds it in `REDIS_URL`. Do not put secrets in images, source files, CI logs, shell history, or support bundles. Restrict `.env` on the VM:

```bash
chmod 600 .env
```

For a mature deployment, inject secrets from the platform secret manager and add `_FILE`/provider adapters rather than retaining a plaintext `.env`.

## Logging and privacy

Structured logs redact configured sensitive fields. `LOG_RAW_MESSAGES` defaults to `false` and must remain false in production unless an approved, time-bounded diagnostic requires otherwise. Do not log access/refresh tokens, cookies, passwords, CSRF values, full prompts, retrieved chunks, or raw student messages.

Anonymous conversation state expires from Redis. It is operational context, not a student record. Establish an institutional retention policy before enabling any analytics or durable transcripts.

## Container and host hardening

- Application images run as UID/GID 10001 and frontend runs as nginx.
- Application root filesystems are read-only with limited `tmpfs` mounts.
- `no-new-privileges` is applied to every service.
- Model files are staged, not downloaded during image build.
- Database, queue, vectors, and models use separate named volumes.
- Pin images by digest in the release environment after validating the selected versions.
- Apply OS, Docker, NVIDIA driver/runtime, Python, Node, and base-image security updates through a tested upgrade process.

The Compose file does not configure TLS, a WAF, backups, host auditd, intrusion detection, centralized log retention, or vulnerability scanning. Those remain deployment responsibilities.

## Release checklist

1. Replace all `REPLACE_*` values and confirm `.env` mode is `0600`.
2. Verify HTTPS, secure cookies, host/CORS allowlists, and reverse-proxy forwarded headers.
3. Confirm only 22 (restricted), 80, and 443 are exposed by the host firewall.
4. Confirm PostgreSQL, Redis, Chroma, and inference have no host port mapping.
5. Verify `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and model provenance/checksums.
6. Run dependency, image, secret, and static-code scans in CI.
7. Run migrations, unit/integration/security tests, frontend build checks, and restore rehearsal.
8. Exercise login throttling, token refresh/revocation, CSRF failure, request-size rejection, and session races.
9. Review academic sources and a representative RAG answer set with authorized IIT staff.
10. Record database backup and rollback identifiers before release.

No runtime security test or scan was executed while these files were created.
