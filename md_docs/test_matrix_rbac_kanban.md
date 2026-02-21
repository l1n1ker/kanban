# RBAC + Kanban Test Matrix (Pairwise + Critical)

## Scope
- Roles: `admin`, `head`, `curator`, `executor`
- Context: own pocket/project vs foreign pocket/project
- Task states: `Создана` (unassigned/assigned), `В работе`, `Приостановлена`, `Завершена`
- Operations: `claim`, `assign`, `start`, `pause`, `resume`, `complete`, `edit`, `read`

## Critical Scenarios
| ID | Actor | Context | Action | Expected |
|---|---|---|---|---|
| M01 | curator_1 | own pocket P1 | create project | 200 |
| M02 | curator_1 | foreign pocket P2 | create project | 403 |
| M03 | curator_1 | own project PR1A | create task | 200 |
| M04 | curator_1 | foreign project PR2A | create task | 403 |
| M05 | curator_1 | own task | update task | 200 |
| M06 | curator_1 | foreign task | update task | 403 |
| M07 | curator_1 | any | read foreign task | 200 (read-all) |
| M08 | executor | queue task | claim | 403 |
| M09 | curator_1 | queue task in own project | claim | 200 + assigned + started |
| M10 | curator_1 | queue task in own project | assign exec_01 | 200 + status `Создана` |
| M11 | curator_1 | queue task in foreign project | assign | 403 |
| M12 | executor | queue task | assign | 403 |
| M13 | curator_1 | `Создана` assigned | start | 200 |
| M14 | curator_1 | `Создана` unassigned | start | 409 |
| M15 | curator_1 | `В работе` | pause | 200 |
| M16 | curator_1 | `Приостановлена` | resume | 200 |
| M17 | curator_1 | `В работе`/`Приостановлена` | complete | 200 |
| M18 | curator_2 | task owned by curator_1 pocket | pause/resume/complete | 403 |
| M19 | head | any pocket/project/task write action | allowed by role + business rules |
| M20 | admin | any pocket/project/task write action | allowed |
| M21 | executor | project/pocket edit | 403 |
| M22 | Kanban | queue grouping | only `Создана` + no executor |
| M23 | Kanban | created grouping | only `Создана` + executor |
| M24 | Kanban | claim from queue (curator+) | card moves to `В работе` |
| M25 | Kanban | assign from queue (curator+) | card moves to `Создана` |

## Pairwise Extension
- Add pairwise combinations of:
  - actor role (`admin/head/curator/executor`)
  - ownership (`own/foreign`)
  - task state (`queue/created/in_progress/paused/done`)
  - operation (`claim/assign/start/pause/resume/complete/edit/read`)
- Keep expected code mapping:
  - `200`: allowed
  - `403`: RBAC/ownership denied
  - `409`: conflict/invalid transition (`already assigned`, `cannot start without executor`)
  - `400/422`: validation

## Manual UI Checklist
1. Queue column contains only unassigned `Создана`.
2. Created column contains only assigned `Создана`.
3. `👤+` appears in queue for curator+ and performs claim.
4. `👥` appears in queue for curator+ and performs assign without start.
5. `▶` not shown for unassigned cards.
6. Error dialogs show API conflict details.
