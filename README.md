# Grafana test automation: Python, pytest-playwright, Appium, Allure, AI

Targets **Grafana 13.2.2**. UI + API + mobile-web tests, data-driven from **CSV and SQLite**, Allure reporting with
traces and video, AI failure triage, an **AI-analysed HTML report**, Docker and scheduled GitHub Actions.

## Project layout
```
ai/                LLM client, failure analyzer, exploratory agent, Allure parser + AI report generator
allure-results/    raw Allure results (generated)
extensions/        pytest plugins: fixtures (api, browser, mobile) and hooks
logs/              pytest.log and the AI report (generated)
page_objects/      Page Objects, components/ (reusable widgets), mobile/ (Appium screens)
tests/             ui/  api/  mobile/  ai/  unit/   and  data/ (csv/, seed.sql, test_data.db)
traces/            Playwright traces kept per retention policy (generated)
utils/             settings, Grafana API client, builders, data loader, DB seeding, run_suite ...
videos/            recorded videos kept per retention policy (generated)
workflows/         Jenkinsfile (the GitHub workflow must live in .github/workflows/)
config.json  requirements.txt  README.md  .gitignore
conftest.py  pytest.ini  Dockerfile  docker-compose.yml  .dockerignore     (tool-required root files)
```

## Setup (Windows / PowerShell)
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned      # once
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
copy .env.example .env                                    # optional: API key, overrides
```
Configuration: `config.json`; environment variables / `.env` override it (see `.env.example`). Never commit the API key.

## Running
```powershell
pytest -m unit                  # framework self-tests, no Grafana needed
pytest -m api                   # API tests, no browser
pytest -m smoke --headed        # watch the UI
pytest --browser firefox        # or repeat --browser for several
pytest -n 4                     # parallel
python -m utils.run_suite       # pytest + AI report in one go (what Docker/CI use)
allure serve allure-results     # needs Allure CLI + Java:  scoop install allure
```

## Data-driven testing: CSV and SQLite
```python
load_cases("login_invalid")                                                      # tests/data/csv/login_invalid.csv
load_cases("dashboards_view", source="sqlite", json_columns=("panels",))         # view in tests/data/test_data.db
```
* Each row needs an `id` (becomes the test id). CSV values are strings; SQLite keeps real types.
* The database is built from `tests/data/seed.sql` automatically and rebuilt when that file changes
  (`python -m utils.db_seed --force` to rebuild manually). Tests open it read-only.
* Tables/views used must expose an `id` column. Table names are validated against SQL injection.

## AI report from Allure results
```powershell
python -m ai.generate_report                    # reads allure-results, writes logs/ai_report.html
python -m ai.generate_report --no-ai            # rule-based only, no API call
```
Contains: verdict and risk, KPIs, pass-rate chart, breakdown per feature and browser, failures grouped by root cause
with suggested fixes, prioritised improvements, slowest tests. With an AI provider configured (see *Staying on the free tier*)
a model writes the analysis; without one (or if the call fails) it falls back to rule-based analysis, so it always renders.

## Docker
```powershell
docker compose up --build --abort-on-container-exit      # clean Grafana 13.2.2 + test runner
docker compose run --rm -e BASE_URL=http://host.docker.internal:3000 tests   # against YOUR running Grafana
docker build -t grafana-tests --build-arg BROWSERS=chromium .                  # smaller image
```
The default run excludes mobile and AI tests (`-m "not mobile and not ai"`); they have their own compose profiles, below.

### Mobile tests in Docker (emulator on your machine)
A container cannot host an Android emulator, so Appium and the emulator run on your Windows host and the tests run in Docker.
```
 Docker: mobile-tests --(HTTP)--> host Appium :4723 --> emulator --(http://10.0.2.2:3000)--> Grafana (published by compose)
```
One-time host setup:
1. Android Studio -> Device Manager -> create a device with a **Google APIs / Google Play** system image (it needs Chrome).
2. Set `ANDROID_HOME` (e.g. `C:\Users\<you>\AppData\Local\Android\Sdk`) and `JAVA_HOME`; add `platform-tools` to PATH.
3. `npm i -g appium` then `appium driver install uiautomator2`.

Each session (three terminals):
```powershell
# 1) start the emulator from Android Studio (or: emulator -avd <name>) and wait for the home screen
# 2) Appium (leave running; allow it through Windows Firewall when prompted)
appium --allow-insecure=uiautomator2:chromedriver_autodownload
# 3) check everything, then run
python -m utils.mobile_check
docker compose --profile mobile run --rm mobile-tests
```
Notes: stop a locally running Grafana first (compose publishes its own on port 3000), or use your own with
`docker compose --profile mobile run --rm --no-deps -e BASE_URL=http://host.docker.internal:3000 mobile-tests`.
With several devices connected set `MOBILE_UDID`. If Appium is unreachable this service **fails** (it does not skip).

### AI tests in Docker
```powershell
# in .env:  AI_PROVIDER=github  +  GITHUB_TOKEN=...      (or AI_PROVIDER=ollama, see below)
docker compose --profile ai run --rm ai-tests
```
Set `AI_FAILURE_ANALYSIS=true` in `.env` for AI root-cause notes on failed UI tests during normal runs.

## Staying on the free tier
Nothing in this project bills you by default: **`AI_PROVIDER` is `none`**, so no AI request is ever made and the report uses
rule-based analysis. To switch AI on at zero cost choose one provider:

| Provider | Cost | Setup |
|---|---|---|
| `github` | Free tier (rate-limited per model/day) | In Actions it uses the built-in `GITHUB_TOKEN`, no secret needed. Locally put a personal access token with the Models permission in `.env` as `GITHUB_TOKEN`. |
| `ollama` | Free, runs on your PC | Install Ollama, `ollama pull llama3.1:8b` (about 8 GB RAM). Docker containers reach it automatically via `host.docker.internal`. |
| `anthropic` | **Paid, pay-as-you-go** | Only if you set `AI_PROVIDER=anthropic` and an API key. Not needed for anything in this project. |

Safeguards: `AI_MAX_CALLS` (default 10) caps AI calls per process; do **not** enable paid inference in your GitHub Models
settings (it is opt-in, free usage never converts to paid on its own). Small local models write weaker analysis and may return
invalid JSON; the report then falls back to rule-based text. Failure details (messages, page structure) are sent to the provider
you choose; with `ollama` they never leave your machine.

Other costs, all free for a course project: Grafana OSS, Playwright, Appium, Android Studio, Allure, Docker Desktop (personal/education use).
GitHub Actions: free for public repositories; private repositories get a monthly allowance of minutes and artifact storage
(check current limits), so keep `retention-days` low and use `workflow_dispatch` for heavy runs.

## CI/CD
**GitHub Actions** (`.github/workflows/tests.yml`): runs on a **weekday 05:00 UTC schedule**, on push/PR, and manually
(Actions tab -> Run workflow). It starts Grafana 13.2.2 as a service, builds the Docker image (cached), runs the suite on
chromium / firefox / webkit (plus an `ai-tests` job), uploads results, then a `report` job merges all browsers into one `ai-report` artifact.
AI analysis in CI uses **GitHub Models** (free tier) with the built-in `GITHUB_TOKEN`, no secret to create.
Change the schedule by editing the `cron:` line. **Jenkins**: `workflows/Jenkinsfile` (cron trigger included).

## Design patterns
Page Object, Component Object, Facade (API client), Builder, Factory, Singleton config, Strategy (CSV/SQLite sources),
Dependency Injection (fixtures), Unit of Work (cleanup stack), Decorator (`@step`), Command and Adapter (AI agent).

## Notes
* Selectors are written for Grafana 13.x conventions and need verifying against your instance; run
  `python -m utils.inspect_page` to see the real ones, then fix them in `page_objects/` only.
* Appium (Android emulator) setup is unchanged; run `pytest -m mobile` with the Appium server up.
