# Demo Video Walkthrough Script (<= 3 Minutes)

This document provides the exact sequence to record for `demo/walkthrough.mp4`.

---

## Prerequisites (Already Running)
- Docker Desktop is open.
- The containers `celesto_api` and `celesto_ledger` are healthy on port 8080:
  ```powershell
  docker compose ps
  ```

---

## 3-Minute Recording Sequence

### Scene 1: FastAPI Swagger UI (`http://localhost:8080/docs`) — 25s
1. Open your browser and navigate to:
   **`http://localhost:8080/docs`**
2. Show the interactive Swagger documentation with `/health`, `GET /api/runs`, and `POST /api/runs`.

### Scene 2: Health Check (`/health`) — 20s
1. In Swagger UI, expand `GET /health` -> Click **Try it out** -> **Execute**.
2. Show the response code `200` with response body:
   ```json
   {
     "status": "ok"
   }
   ```

### Scene 3: List Seeded Runs (`GET /api/runs`) — 25s
1. In Swagger UI, expand `GET /api/runs` -> Click **Try it out** -> **Execute**.
2. Show the seeded demo run in PostgreSQL:
   ```json
   {
     "run_id": "demo-seed-1",
     "sandbox_name": "sbx-seeddemo1",
     "problem_id": "problem-demo",
     "state": "deleted",
     "execution_target": "celesto_sandbox"
   }
   ```

### Scene 4: Create a New Run (`POST /api/runs`) — 30s
1. Expand `POST /api/runs` -> Click **Try it out**.
2. Paste the valid payload:
   ```json
   {
     "run_id": "demo-ui-run-001",
     "sandbox_name": "sbx-demouirun01",
     "problem_id": "demo-problem",
     "state": "running",
     "execution_target": "celesto_sandbox"
   }
   ```
3. Click **Execute** and show the `201 Created` response.
4. Execute `GET /api/runs` again to show both runs now persisted in PostgreSQL.

### Scene 5: Input Validation Error Handling — 25s
1. In `POST /api/runs`, change `"execution_target": "host"` or `"sandbox_name": "invalid-name"`.
2. Click **Execute**.
3. Show the `400 Bad Request` response code, demonstrating strict sandbox boundary enforcement.

### Scene 6: Containment Demonstration & Audit Log — 35s
1. Switch to terminal and run:
   ```powershell
   py -3 scripts/containment_test.py
   ```
2. Show the blocked malicious exfiltration command (`CommandBlockedError`).
3. Show the audit log:
   ```powershell
   Get-Content logs/commands.jsonl -Tail 5
   ```
4. Point out the `"decision": "block"` entry for the attempted secret exfiltration.

### Scene 7: Save Video File — 10s
1. Stop screen recording.
2. Save the video as:
   `demo/walkthrough.mp4`

---
*Note: Audio narration is optional. A screen recording clearly demonstrating the browser at `http://localhost:8080/docs` and the terminal commands satisfies all submission requirements.*
