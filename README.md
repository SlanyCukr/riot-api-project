# League Analysis - Analyze Player, Detect Smurfs & More

A League of Legends player analysis platform that identifies potential smurf accounts using advanced algorithms and Riot API data.

## 🎯 What It Does

- **🔍 Player Analysis**: Analyzes 9 factors to detect likely smurf accounts
- **⚖️ Matchmaking Analysis**: Analyzes average win rates of teammates vs opponents
- **📊 Player Analytics**: Match history, performance stats, and rank tracking
- **⚡ Real-time Monitoring**: Automated background jobs for continuous updates
- **🌍 Multi-Region Support**: Works on all major Riot API regions

## 🚀 Quick Start

### Prerequisites

- Docker Engine with Compose v2
- Riot API Key from [Riot Developer Portal](https://developer.riotgames.com/)

### 1. Setup

```bash
git clone <repository-url>
cd riot-api-project
cp .env.example .env
# Edit .env with database credentials and JWT secret
# Riot API key will be set via web UI after startup
```

### 2. Start Development

```bash
docker compose up -d                    # Start services with hot reload
```

### 3. Access the App

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Hot reload is automatic:** Changes to Python files auto-restart the backend via `uvicorn --reload`. Changes to TypeScript/JSX files hot reload the frontend via `next dev`. No manual restart needed!

## 🎯 Key Features

### Player Analysis Algorithm

Analyzes players using 9 weighted factors:

| Factor                  | Weight | What It Checks               |
| ----------------------- | ------ | ---------------------------- |
| Rank Discrepancy        | 20%    | Performance vs rank mismatch |
| Win Rate Analysis       | 18%    | High win rates over time     |
| Performance Trends      | 15%    | KDA consistency patterns     |
| Win Rate Trends         | 10%    | Improvement patterns         |
| Role Performance        | 9%     | Multi-role versatility       |
| Rank Progression        | 9%     | Fast climbing detection      |
| Account Level           | 8%     | Low account level            |
| Performance Consistency | 8%     | Variance analysis            |
| KDA Analysis            | 3%     | Kill/death ratios            |

**Confidence Levels:**

- 🔴 **High (80%+)**: Very likely smurf
- 🟡 **Medium (60-79%)**: Probable smurf
- 🟢 **Low (40-59%)**: Possible smurf

### Web Interface

- **Player Analysis**: Search players and run analysis
- **Matchmaking Analysis**: Analyze matchmaking fairness for tracked players
- **Tracked Players**: Monitor players automatically
- **Background Jobs**: View system status and job history

## 🏗️ Tech Stack

**Backend**

- Python 3.13 + FastAPI + PostgreSQL
- SQLAlchemy + Pydantic for type safety
- APScheduler for background jobs

**Frontend**

- Next.js 16 + React 19 + TypeScript
- shadcn/ui + Tailwind CSS
- TanStack Query for data fetching

**Infrastructure**

- Docker + Docker Compose + Docker Bake
- Modern multi-stage builds with BuildKit
- Multi-environment support (dev/prod)

## 🛠️ Development

Both frontend and backend support automatic hot reload via volume mounts—just save files, no restart needed:

```bash
docker compose up -d                                # Start services
docker compose logs -f                              # View all logs
docker compose logs -f backend                      # View backend logs only
docker compose exec backend uv run alembic current  # Check migration status
docker compose down                                 # Stop services
```

**How hot reload works:**

- **Backend**: `uvicorn --reload` watches Python files and auto-restarts on changes
- **Frontend**: `next dev` watches TypeScript/JSX files and hot reloads on changes
- **Two-way sync**: Volume mounts (`./backend:/app`, `./frontend:/app`) sync code changes to containers and generated files (like Alembic migrations) back to host

**When to rebuild containers:**

- Dependency changes (`pyproject.toml`, `package.json`)
- Dockerfile modifications
- System package changes

For detailed build info and production deployment, see **`docker/AGENTS.md`** and **`scripts/AGENTS.md`**.

## 📊 Background Jobs

The system runs two automated jobs:

1. **Tracked Player Updater** (every 2 minutes)

   - Fetches new matches for monitored players
   - Updates ranks and statistics

2. **Player Analyzer** (continuous)
   - Runs player analysis on players with 20+ matches
   - Stores analysis results with confidence scores

Monitor jobs at: http://localhost:3000/jobs

## 🔧 API Endpoints

### Players

- `GET /api/v1/players/search` - Search by Riot ID or summoner name
- `POST /api/v1/players/{puuid}/track` - Add player to tracking
- `DELETE /api/v1/players/{puuid}/track` - Remove from tracking

### Matches & Analysis

- `GET /api/v1/matches/player/{puuid}` - Get match history
- `POST /api/v1/player-analysis/analyze` - Run player analysis
- `GET /api/v1/player-analysis/{puuid}/latest` - Get latest analysis
- `POST /api/v1/matchmaking-analysis/start` - Start matchmaking analysis
- `GET /api/v1/matchmaking-analysis/player/{puuid}` - Get latest matchmaking analysis

**Full API docs**: http://localhost:8000/docs

## ⚙️ Configuration

Key environment variables in `.env`:

```bash
# Application Configuration
POSTGRES_DB=riot_api_db
POSTGRES_USER=riot_api_user
POSTGRES_PASSWORD=secure_pass         # Database password
JWT_SECRET_KEY=<generate-64-char-hex> # JWT signing secret (run: python -c 'import secrets; print(secrets.token_hex(32))')
```

**Notes**:

- **Riot API Key**: Stored in database only, not in `.env`. Set via web UI at http://localhost:3000/settings after first startup.
- **Region/Platform**: Hardcoded to europe/eun1 in backend code
- **Database URL**: Automatically constructed from POSTGRES\_\* variables

**⚠️ Important**: Development API keys expire every 24 hours. Update your key via the settings page when expired.

## 🗂️ Project Structure

```
riot-api-project/
├── backend/app/               # FastAPI application (feature-based)
│   ├── core/                  # Infrastructure (database, config, Riot API client)
│   └── features/              # Domain features
│       ├── auth/              # User authentication and authorization
│       ├── players/           # Player management (search, tracking, rank info)
│       ├── matches/           # Match data and statistics
│       ├── player_analysis/   # Player analysis algorithms
│       ├── matchmaking_analysis/  # Matchmaking fairness evaluation
│       ├── jobs/              # Background job scheduling
│       └── settings/          # System configuration
├── frontend/                  # Next.js application (feature-based)
│   ├── app/                   # Pages (App Router)
│   ├── features/              # Feature modules
│   │   ├── auth/              # Authentication components and context
│   │   ├── players/           # Player components, hooks, utilities
│   │   ├── matches/           # Match components
│   │   ├── player-analysis/   # Analysis components
│   │   ├── matchmaking/       # Matchmaking analysis components
│   │   ├── jobs/              # Job management components
│   │   └── settings/          # Settings components
│   ├── components/            # Shared layout components and shadcn/ui
│   └── lib/core/              # Core utilities (API client, schemas, validations)
├── docker/                    # Docker configuration
├── scripts/                   # Development scripts
└── AGENTS.md                  # Project quick reference (CLAUDE.md → AGENTS.md)
```

## 🧪 Testing

```bash
# Backend tests
docker compose exec backend uv run pytest

# Frontend linting
docker compose exec frontend npm run lint
```

## 🔒 Rate Limiting

The application respects Riot API rate limits:

- 20 requests per second
- 100 requests per 2 minutes

Built-in backoff and retry mechanisms handle rate limits automatically.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is for educational and research purposes. Please ensure compliance with Riot Games' API Terms of Service.

## ⚠️ Disclaimer

This project is not affiliated with or endorsed by Riot Games. All League of Legends-related content is property of Riot Games, Inc.

---

**Built with ❤️ for the League of Legends community**
