# Admin Web UI - Frontend Dev Guide

This doc targets frontend developers building the admin web interface for the Gatcha Monster Generator. It focuses on the admin API and expected workflows.

## 1. Quick pointers

- Base URL (local): http://localhost:8000
- Admin API prefix: /api/v1/admin
- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
- Auth: none enforced in code (plan UI assuming no auth for now)

## 2. Core concepts

### 2.1 Monster lifecycle states

Values (enum):
- GENERATED
- DEFECTIVE
- CORRECTED
- PENDING_REVIEW
- APPROVED
- TRANSMITTED
- REJECTED

Typical flow:
- GENERATED -> (valid) -> PENDING_REVIEW
- DEFECTIVE -> (corrected) -> CORRECTED -> PENDING_REVIEW
- PENDING_REVIEW -> APPROVED or REJECTED
- APPROVED -> TRANSMITTED

### 2.2 Review actions

Values (enum):
- approve
- reject
- correct
- transmit

Note: for the admin review endpoint, only approve/reject are accepted by the backend.

## 3. Admin API (lifecycle endpoints)

### 3.1 List monsters

GET /api/v1/admin/monsters

Query params:
- state: optional, MonsterState
- limit: 1-200 (default 50)
- offset: >= 0 (default 0)
- sort_by: string (default created_at)
- order: asc|desc (default desc)

Response: array of MonsterSummary

MonsterSummary fields:
- monster_id (string)
- filename (string)
- name (string)
- element (string)
- rank (string)
- state (MonsterState)
- created_at (ISO datetime)
- updated_at (ISO datetime)
- is_valid (bool)
- review_notes (string|null)

Important: backend currently ignores sort_by/order, so do not rely on server-side sorting yet.

### 3.2 Monster detail

GET /api/v1/admin/monsters/{monster_id}

Response: MonsterDetail
- metadata (MonsterMetadata)
- monster_data (object)
- image_url (string|null)
- validation_report (object|null)

MonsterMetadata (key fields):
- monster_id, filename, state, created_at, updated_at
- generation_prompt
- is_valid, validation_errors
- reviewed_by, review_date, review_notes
- transmitted_at, transmission_attempts, last_transmission_error
- history: [{ from_state, to_state, timestamp, actor, note }]

### 3.3 Monster history

GET /api/v1/admin/monsters/{monster_id}/history

Response:
- monster_id
- current_state
- history: list of transitions (from_state, to_state, timestamp, actor, note)

### 3.4 Review (approve / reject)

POST /api/v1/admin/monsters/{monster_id}/review

Body:
- action: "approve" | "reject"
- notes: string|null (max 1000)
- corrected_data: object|null

Rules:
- Monster must be in PENDING_REVIEW
- If corrected_data is provided, backend validates it and can return 400 if invalid

Response (success):
- status: "success"
- monster_id
- new_state
- message

### 3.5 Correct a defective monster

POST /api/v1/admin/monsters/{monster_id}/correct

Body:
- corrected_data: object
- notes: string|null

Rules:
- Monster must be in DEFECTIVE
- corrected_data must pass validation
- Backend auto-transitions DEFECTIVE -> CORRECTED -> PENDING_REVIEW

Response (success):
- status: "success"
- monster_id
- new_state
- message

### 3.6 Dashboard stats

GET /api/v1/admin/dashboard/stats

Response: DashboardStats
- total_monsters (int)
- by_state (object: { state: count })
- transmission_rate (float 0..1)
- avg_review_time_hours (float|null)
- recent_activity: list of { monster_id, monster_name, transition, timestamp, actor }

## 4. Legacy admin endpoints (defective JSONs)

These endpoints operate on JSON files and are kept for backward compatibility. Prefer the lifecycle endpoints above for the new admin UI, but you may still expose a "Legacy Defectives" tab if needed.

### 4.1 List defective JSONs

GET /api/v1/admin/defective

Response: array of
- filename
- created_at
- status
- error_count
- monster_name

### 4.2 Defective detail

GET /api/v1/admin/defective/{filename}

Response:
- filename
- created_at
- status
- monster_data (object)
- validation_errors: [{ field, error_type, message }]
- notes

### 4.3 Validate a defective JSON

POST /api/v1/admin/defective/{filename}/validate

Response:
- filename
- is_valid (bool)
- validation: { is_valid, errors, warnings, ... }

### 4.4 Update (no approval)

PUT /api/v1/admin/defective/{filename}/update

Body:
- corrected_data (object)
- notes (string)

Response:
- status: "updated"
- message
- path

### 4.5 Approve

POST /api/v1/admin/defective/{filename}/approve

Body:
- corrected_data (object)
- notes (string)

Response:
- status: "approved" | "rejected"
- message or reason
- new_path (when approved)
- errors (when rejected)

### 4.6 Reject

POST /api/v1/admin/defective/{filename}/reject

Body:
- reason (string)

Response:
- status: "rejected"
- message
- reason

### 4.7 Validation rules

GET /api/v1/admin/validation-rules

Use this for form constraints (enum values, stat limits, max lengths).

Response:
- valid_stats: ["ATK", "DEF", "HP", "VIT"]
- valid_elements: ["FIRE", "WATER", "WIND", "EARTH"]
- valid_ranks: ["COMMON", "RARE", "EPIC", "LEGENDARY"]
- stat_limits: { stat: { min, max } }
- skill_limits: { stat: { min, max } }
- lvl_max
- max_card_description_length

## 5. UI screens and behavior

### 5.1 Dashboard

- KPIs: total monsters, transmission rate, avg review time
- State distribution chart using by_state
- Recent activity list using recent_activity

### 5.2 Monsters list

- Filters: state
- Pagination: limit/offset
- Columns: name, element, rank, state, created_at, is_valid
- Actions: open detail

### 5.3 Monster detail

- Tabs: summary, data, validation, history
- Show image_url (if present) and metadata
- Show validation_report if is_valid is false
- Actions when state is PENDING_REVIEW: Approve / Reject
- Action when state is DEFECTIVE: Correct and send to review

### 5.4 Edit/correction UX

- Use validation-rules endpoint for client-side constraints
- Provide JSON editor and structured form view
- Validate locally before sending corrected_data

## 6. Error handling

- Typical errors: 400 (invalid state or invalid corrected_data), 404 (not found), 500 (server error)
- FastAPI error shape: { "detail": "..." } in most cases
- Legacy approve may return 200 with status="rejected" + errors (not 4xx)

## 7. Example calls (curl)

List monsters:
```bash
curl "http://localhost:8000/api/v1/admin/monsters?state=PENDING_REVIEW&limit=20&offset=0"
```

Approve:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/monsters/UUID/review" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve","notes":"looks good"}'
```

Reject:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/monsters/UUID/review" \
  -H "Content-Type: application/json" \
  -d '{"action":"reject","notes":"missing stats"}'
```

Correct defective:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/monsters/UUID/correct" \
  -H "Content-Type: application/json" \
  -d '{"corrected_data": {"nom":"...","element":"FIRE","rang":"COMMON","stats":{"hp":1,"atk":1,"def":1,"vit":1},"description_carte":"...","description_visuelle":"...","skills":[]},"notes":"fixed enums"}'
```
