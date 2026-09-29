# Environment Variables
**Status:** Planned. Never commit real secrets; `.env` must be in `.gitignore`.

```text
DATABASE_URL=postgresql://username:password@localhost:5432/mitrc_libsphere
JWT_SECRET=change_me
CORS_ORIGINS=http://localhost:5173
UPLOAD_DIRECTORY=uploads/
```
Files: root `.env.example`, `backend/.env.example`. Values above are placeholders, not real credentials.
