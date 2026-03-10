# Repository Structure

Target structure for long-term maintainability (current state after refactor):

```text
prizmbet-v2/
├── .github/                 # CI/CD workflows
├── assets/                  # Brand/static media not required in root
│   ├── branding/
│   └── legacy-root/
├── backend/                 # Backend services and domain logic
│   ├── api/
│   ├── bot/
│   ├── db/
│   ├── parsers/
│   └── utils/
├── config/                  # SQL schema snapshots and config artifacts
├── docs/                    # Active product/engineering docs
│   └── legacy/              # Archived notes and historical docs
├── frontend/                # Static web client and assets
├── infra/                   # Infrastructure-oriented files (reserved)
├── mobile/
│   └── android/             # Android client (moved from prizmbet_android)
├── scripts/                 # Helpers, one-off tools, local ops scripts
│   └── frontend/
├── supabase/
│   └── migrations/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── package.json
├── README.md
└── requirements.txt
```

## Conventions

- Keep root minimal and product-focused.
- Keep active documentation only in `docs/`.
- Put temporary or one-off operational scripts in `scripts/`.
- Preserve business logic in `backend/` and `frontend/` unless migration is planned.
