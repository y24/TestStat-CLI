# Agent Instructions

## Development Servers

**Do not start development servers.** The user keeps both servers running manually.

- Backend: `uvicorn app.main:app --host 0.0.0.0 --port 18000` (in `teststat-server/`)
- Frontend: `npm run dev` (in `teststat-frontend/`, served at `http://localhost:5173/tstat/`)

If a server needs to be restarted due to a port conflict or crash, ask the user to do it.
Code changes to the backend require a manual server restart to take effect (no `--reload`).
