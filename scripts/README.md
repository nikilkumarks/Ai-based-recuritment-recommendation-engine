# Local helper scripts

Phase 0 uses Docker Compose as the primary runner. See the root README.

Optional host-side checks after Python/Node are installed:

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
ruff check .

# Frontend
cd ..\frontend
npm install
npm run lint
npm run typecheck
npm run build
```
