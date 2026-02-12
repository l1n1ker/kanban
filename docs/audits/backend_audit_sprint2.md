@backend/__init__.py
@backend/db.py
@backend/models.py
@backend/rbac.py
@backend/logging.py
@backend/repositories.py
@backend/services.py
@backend/api.py

Audit backend code against the project documentation in md_docs/:
- architecture.md
- db_schema.md
- workflow.md
- tasks_rules.md
- wip_rules.md
- ui_structure.md
- README.md

For each file, check the following:

1. **Architecture Consistency**
   - Models match db_schema.md
   - All entities and fields are implemented correctly
   - No entities outside schema

2. **RBAC and Permissions**
   - Centralized authorization logic is used
   - Executor cannot change statuses
   - Curator and higher roles have correct rights
   - admin role access is consistent with docs

3. **Separation of Concerns**
   - db.py only manages connection/initialization
   - models.py defines data structures
   - repositories.py handles data CRUD only
   - services.py implements business rules + RBAC
   - logging.py logs changes correctly
   - api.py only exposes services

4. **Logging**
   - action_log entries are recorded for all necessary actions
   - timestamp and user_id are stored
   - old/new values are human-readable

5. **WIP Calculation**
   - WIP logic is in services layer
   - No WIP storage in DB tables

6. **Tests and Error Handling**
   - Methods validate inputs
   - Errors are raised for unauthorized actions
   - DAOs avoid SQL injection

7. **Documentation Consistency**
   - Comments correspond to md_docs descriptions
   - No missing or mismatched fields/actions

Provide the audit result file by file in Markdown format:
- summary per file: pass/fail
- list of issues per file with references to md_docs sections
- recommendations to fix each issue (one line each)
