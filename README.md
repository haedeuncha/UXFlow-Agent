# UXFlow Agent

## Run

```powershell
python -m uvicorn app.main:app --port 8000
```

Open Swagger at `http://127.0.0.1:8000/docs`.

## Swagger submission check

Start the server with the single command above, then open Swagger and execute
the following requests in order. No additional port is required.

1. `GET /api/health` — confirms that the API is running.
2. `GET /api/figma/status` — confirms only whether `FIGMA_ACCESS_TOKEN` is set;
   it never returns the token.
3. `GET /api/contracts` — shows the JSON Schema for each Agent handoff.
4. `POST /api/designs/plan` — enter a service brief and confirm the page plan.
5. `POST /api/designs/recommend-components` — paste the `PagePlan` response to
   receive approved `shadcn/ui` and `Lucide` recommendations.
6. `POST /api/designs/review` — paste the plan and recommendation responses to
   check the six five-star UX conditions.
7. `POST /api/designs/run?mode=plan_only` — runs the full safe workflow and
   returns a saved `run_id`; Figma is explicitly recorded as `skipped`.
8. `GET /api/designs/{run_id}` — replace `{run_id}` with the value from step 7
   to verify the ordered Agent trace.

`mode=build_figma` is opt-in. Until a user explicitly connects a Figma
integration, it safely returns `figma_not_connected` and preserves the approved
plan and error trace instead of pretending that a Figma file was created.

## Example request body

Use this body for the plan and run endpoints:

```json
{
  "service_name": "여행 예약 서비스",
  "target_users": ["여행자"],
  "primary_user_goal": "예약 요청 완료",
  "required_features": ["검색", "상세 보기", "예약 요청"],
  "platforms": ["web", "mobile"]
}
```
