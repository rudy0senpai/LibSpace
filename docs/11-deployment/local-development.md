# Local Development
**Status:** Planned. To be verified once the foundation exists.

Intended setup:
1. Install Node.js, Python and PostgreSQL (or use Docker Compose).
2. Copy `.env.example` to `.env` and fill values (never commit `.env`).
3. Create the PostgreSQL database (`mitrc_libsphere`) and run migrations, then seed demo data.
4. Run the FastAPI backend and the Vite dev server (default frontend origin `http://localhost:5173`).
5. Run backend, integration and E2E tests.

`scripts/setup.sh`, `seed_database.py`, `backup_database.sh` will automate parts of this.
