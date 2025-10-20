# League Eye Spy - Analyze Player, Detect Smurfs & More

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
# Edit .env with your Riot API key
```

### 2. Start Development

```bash
./scripts/dev.sh
```

### 3. Access the App

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

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

- Next.js 15 + React 19 + TypeScript
- shadcn/ui + Tailwind CSS
- TanStack Query for data fetching

**Infrastructure**

- Docker + Docker Compose + Docker Bake
- Modern multi-stage builds with BuildKit
- Multi-environment support (dev/prod)

## 🛠️ Development

Both frontend and backend support hot reload—just save files, no restart needed:

```bash
./scripts/dev.sh                # Start with hot reload
./scripts/dev.sh --build        # Rebuild containers
./scripts/dev.sh --reset-db     # Reset database (⚠️ wipes data)
./scripts/dev.sh --down         # Stop services
```

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
- `GET /api/v1/player-analysis/player/{puuid}/latest` - Get latest analysis
- `POST /api/v1/matchmaking-analysis/start` - Start matchmaking analysis
- `GET /api/v1/matchmaking-analysis/{puuid}/latest` - Get latest matchmaking analysis

**Full API docs**: http://localhost:8000/docs

## ⚙️ Configuration

Key environment variables in `.env`:

```bash
RIOT_API_KEY=your_api_key      # Required: Get from Riot Developer Portal
RIOT_REGION=europe             # Your region
RIOT_PLATFORM=eun1             # Your platform
POSTGRES_PASSWORD=secure_pass  # Database password
JOB_SCHEDULER_ENABLED=true     # Enable background jobs
MAX_TRACKED_PLAYERS=10         # Max players to track
```

**⚠️ Important**: Development API keys expire every 24 hours. Update your key in `.env` and restart services when expired.

## 🗂️ Project Structure

```
riot-api-project/
├── backend/app/               # FastAPI application
│   ├── api/                   # API endpoints
│   ├── services/              # Business logic
│   ├── riot_api/              # Riot API integration
│   ├── models/                # Database models
│   └── jobs/                  # Background jobs
├── frontend/                  # Next.js application
│   ├── app/                   # Pages (App Router)
│   ├── components/            # React components
│   └── lib/                   # Utilities and API client
├── docker/                    # Docker configuration
├── scripts/                   # Development scripts
└── CLAUDE.md                  # Project quick reference
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
