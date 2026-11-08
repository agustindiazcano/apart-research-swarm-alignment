# Verification of the external stack (task T00)

Date: 2026-11-08. Resolves the `TODO(verify)` items in `ARCHITECTURE.md` and `PROJECT.md` by reading the code and running the stack.

External repository: `mcp-transactional-agent` (local path `../agentic-mcp-engine`), branch `feat/front-desk-eval`, commit `37f6d72`. Pre-existing work, used unmodified. No file in that repository was edited. Every configuration change is listed in section 8.

No secret appears in this document. Token values and API keys are not recorded.

## 1. Summary

| Question | Answer | Status |
|---|---|---|
| Does compose work with the chaos override? | Yes, after two local configuration changes (section 8). Postgres, RabbitMQ, migration, MCP server, worker, sweeper and gateway run. `GET /api/v1/system-health` returns `{"gateway":true,"db":true,"mcp":true}`. | verified by running |
| Claim endpoint and payload | `POST /api/v1/claims` on the gateway (port 8000), returns 202 with `{"status":"Accepted","request_id":...}`. Body fields: `user_id` (required), `claim_text` (required), `request_id` (optional, default uuid4), `order_id`, `amount` (greater than 0, at most `REFUND_MAX_AMOUNT`), `currency`. | verified by running and reading `src/api/schemas.py` |
| `mcp_clients.json` format and adding identities | JSON object `{"clients": [{"client_id", "token_hash", "allowed_tools"}]}`. `token_hash` is the SHA-256 hex digest of the bearer token. The token is sent as `Authorization: Bearer <token>`. | verified by running |
| Column types for the harm join | `refunds.transaction_id` is `varchar`, `orders.order_id` is `varchar`. A refund row stores the order id in `transaction_id`. No cast is needed. | verified in the database |
| Does the evidence check use `get_refund_history`? | Yes. The worker calls `get_order` and `get_refund_history` through MCP (`src/worker/evidence.py`). Both appear in `mcp_audit_logs` after a claim. | verified by running |
| Is `validate_fraud_score` called? | No. It exists as an MCP tool but nothing in `src/worker` or `src/agents` calls it. | verified by search, not by running |
| How are judge providers set? | Fixed per role in `src/agents/provider_roles.py` (section 6). `LLM_PROVIDER=mock` routes every role to a mock. `LLM_PROVIDER=vertex` moves only the Gemini roles to Vertex. | verified by reading the code |

## 2. Services and ports

| Service | Container (experiment stack) | Port |
|---|---|---|
| Postgres (pgvector) | `swarmexp_db` | 5432 |
| RabbitMQ | `swarmexp_mq` | 5672, 15672 |
| MCP server | `swarmexp_mcp_server` | 18080 (container 8080) |
| Gateway | `swarmexp_gateway` | 8000 |
| Worker, sweeper, migration | `swarmexp_worker`, `swarmexp_sweeper`, `swarmexp_migrate` | none |

Port 8080 was already in use on the host, so the MCP server is published on 18080. The experiment stack uses its own compose project name (`swarmexp`) and its own volumes. The existing development containers and volumes were not touched.

## 3. Claim flow under the chaos override

With `LLM_PROVIDER=mock` every role is mocked. Test run:

1. Insert order `E0-O1` for user `E0-U1`, amount 50.00 USD.
2. `POST /api/v1/claims` with `request_id` `E0-w1-1`, that order and amount 50.
3. Result after a few seconds: `transactions.status = COMPLETED`; one row in `refunds` with `request_id = E0-w1-1`, `transaction_id = E0-O1`, amount 50.00.
4. `mcp_audit_logs` shows `worker-default` with `get_order`, `get_refund_history` and `execute_refund`, all `ALLOWED`.

A first row with client `unknown` and decision `DENIED_UNAUTHENTICATED` appears at startup. Its origin was not traced (probably a health probe). `TODO(verify)`.

Consequence for the design: under the mock every claim is approved, so D3 (claim mediation) and the Prompt Guard cannot be measured with the chaos override. They need real providers (section 6).

## 4. Identity-based permissions (D1)

Two identities were registered by configuration (section 8): `swarm-reader` (`get_order`, `get_refund_history`) and `swarm-privileged` (those two plus `execute_refund`). Test through an MCP SSE client:

| Identity | Tool | Audit decision | Ledger |
|---|---|---|---|
| `swarm-reader` | `get_order` | `ALLOWED` | none |
| `swarm-reader` | `execute_refund` | `DENIED_UNAUTHORIZED`, `not_executed` | no row |
| `swarm-privileged` | `execute_refund` | `ALLOWED`, `invoked` | row `E0-p-1`, 5.00 |

Notes:

- The tool argument is named `transaction_id`, not `order_id`. A call with `order_id` is recorded as `DENIED_VALIDATION`. `ARCHITECTURE.md` section 1 should use `transaction_id` for `execute_refund`.
- The denial is recorded in the audit table. The probe client surfaced it as an SSE or task-group exception, not as a clean HTTP 403 result. The tool layer (T07) should read the audit decision or catch the exception, and must not assume a status code. `TODO(verify)`: exact client-side shape of a denied call.
- The harm query in `ARCHITECTURE.md` section 4 can drop `::text`: `JOIN swarmlab_gt.orders_gt g ON g.order_id = r.transaction_id`.

## 5. Evidence check and fraud score

- The worker calls `get_order` and `get_refund_history` with the worker identity before the judges (`src/worker/evidence.py`, `src/core/services/evidence_check.py`).
- `validate_fraud_score(user_id)` is defined in `src/mcp_server/mcp_server.py` and is not called by the worker or the agents. It is not part of the pipeline under test.
- The MCP rate limit defaults to 30 calls per minute per tool; the chaos override sets `MCP_RATE_LIMIT_PER_MIN` to 1000000.

## 6. Judge and guard providers

From `src/agents/provider_roles.py`:

| Role | Default provider |
|---|---|
| `judge1` | gemini |
| `judge2` | groq |
| `supreme_court` | gemini |
| `prompt_guard` | groq (Llama Prompt Guard 2 22M) |
| `front_desk` | gemini |

- `LLM_PROVIDER=mock`: all roles use the mock.
- `LLM_PROVIDER=vertex`: roles whose default is gemini run on Vertex AI. `judge2` and `prompt_guard` stay on groq.
- The Prompt Guard fails open: if it cannot score, the result is `skipped`.

Decision (2026-11-08): Groq is not used in this project. `judge2` and `prompt_guard` run on the project providers (Vertex, Muse, Adaption) instead. How they are remapped is worked out in T10 and T11 and declared here. `TODO(verify)`: behavior of the Prompt Guard under `LLM_PROVIDER=mock`.

## 7. Other findings

- Docker Desktop was stopped and was started for this task (engine 29.8.0).
- RabbitMQ failed to start with `eacces` on `/var/lib/rabbitmq/.erlang.cookie`. Cause (probable): the compose healthcheck runs `rabbitmq-diagnostics` as root during startup, creating a root-owned cookie before the server (user `rabbitmq`) reads it. Running the healthcheck as the `rabbitmq` user fixed it (section 8). A plain `docker run` of the same image works.
- The `migrate` service applies Alembic migrations and exits with code 0; the other services wait for it.
- The external `.env` is passed to all containers through `env_file`. It holds the external project's own keys. The chaos override sets `LLM_PROVIDER=mock`, so no paid call is made.

## 8. Configuration changes (none inside the external repository)

All changes live in a compose override file kept outside the external repository and passed with an extra `-f`. Compose files of the external repository were not edited.

| Change | Reason |
|---|---|
| Compose project name `swarmexp` | Separate volumes from the development stack |
| `container_name` set to `swarmexp_*` for all services | The base file fixes container names that already exist |
| MCP server published on 18080 | Host port 8080 is in use |
| RabbitMQ: no data volume | A volume is not needed for experiment runs |
| RabbitMQ healthcheck run as `gosu rabbitmq` | Fixes the cookie permission error |
| MCP server: bind-mount of a clients file over `/app/mcp_clients.json`, with `swarm-reader` and `swarm-privileged` added | Adds the two identities; tokens are random, generated locally and never committed |

Override file (paths shortened):

```yaml
services:
  postgres: {container_name: swarmexp_db}
  rabbitmq:
    container_name: swarmexp_mq
    volumes: !override []
    healthcheck:
      test: !override ["CMD-SHELL", "gosu rabbitmq rabbitmq-diagnostics -q check_port_connectivity"]
  migrate: {container_name: swarmexp_migrate}
  mcp_server:
    container_name: swarmexp_mcp_server
    ports: !override ["18080:8080"]
    volumes:
      - <absolute path>/mcp_clients_exp.json:/app/mcp_clients.json:ro
  worker: {container_name: swarmexp_worker}
  sweeper: {container_name: swarmexp_sweeper}
  gateway: {container_name: swarmexp_gateway}
```

Start command (from the external repository directory):

```
docker compose -p swarmexp -f docker-compose.yml -f docker-compose.chaos.yml -f <override file> up -d postgres rabbitmq migrate mcp_server worker sweeper gateway
```

A token hash is produced with `hashlib.sha256(token.encode()).hexdigest()`.

## 9. Remaining `TODO(verify)`

| Item | Needed by |
|---|---|
| Origin of the `unknown` / `DENIED_UNAUTHENTICATED` audit row at startup | T07 |
| Client-side shape of a denied MCP call | T07 |
| Prompt Guard behavior under `LLM_PROVIDER=mock` | T10 |
| Remapping `judge2` and `prompt_guard` from Groq to Vertex, Muse or Adaption | T10, T11 |
| Real-provider run of the claim pipeline (needs keys) | T11 |
| Model ids, prices and limits for Adaption, Muse, Modal and Vertex (`docs/MODELS.md`) | gate G1 |
