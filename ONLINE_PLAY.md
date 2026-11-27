# Online play and free hosting

## Current online mode

`streamlit_app.py` is a playable multi-browser MVP backed by `cardgame/online.py`:

- Create a room and optionally generate a private PIN for each named player.
- Each player connects from a separate browser using the room code, their name and PIN.
- The host starts the game; bidding starts left of the dealer and the dealer bids last.
- Each player sees only their own hand. The server-side room state contains all hands, but the UI only renders the connected player's hand.
- The app enforces turn order and follow-suit, calculates trick winners, and displays trump, bids, trick totals, played cards and scores.
- There is a bid-review phase in which players can correct their own bids, followed by host confirmation.
- There is a trick-review phase in which the host can correct trick totals; totals must still equal the number of tricks in the round.
- At game completion, the host can save the game into the same `data/game_history.csv` format used by the local modes.

The app uses SQLite transactions (Python standard library) for live room state and CSV for player identities and game history. Streamlit fragments refresh the shared game view every three seconds. The SQLite room database records every bid, correction, card play and scoring transition, so a player can reconnect after a browser refresh or server restart if the data directory is restored.

For a public Streamlit deployment, the app can back up its SQLite and CSV files to a **separate private GitHub repository**. This is an optional durable storage adapter implemented with Python's standard library; it does not require Supabase, Postgres or another Python package. A backup is committed after each room-state mutation and after player/history CSV changes. The private repository must be created separately and must not be the public source-code repository.

## Free deployment

A low-dependency deployment is:

- **Streamlit Community Cloud** for hosting the Streamlit application.
- **SQLite + CSV** for the app's local data format.
- **A separate private GitHub repository** as the optional durable backup target.

Streamlit Community Cloud supports free app deployment. <https://docs.streamlit.io/deploy/streamlit-community-cloud>. Its app filesystem should not be treated as durable storage: without an external backup, room state and CSV files may disappear after a restart or redeploy. The private backup adapter restores data on startup and uploads a fresh snapshot after every room mutation and CSV update. This is crash/restart recovery, not a high-availability multi-region database: it depends on GitHub availability, API limits, and a single active app instance. For larger traffic or simultaneous multi-instance hosting, use a transactional managed database instead.

## Deploy the Streamlit app for free

1. Push this project to a GitHub repository.
2. Create a Streamlit Community Cloud account and deploy `streamlit_app.py` from that repository.
3. Community Cloud reads `requirements.txt`, which includes Streamlit.
4. For persistent shared rooms, create a separate **private** GitHub repository for backups and configure the Streamlit secrets below before inviting players.

Streamlit documents the free Community Cloud deployment flow here: <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy>.

## Run locally

```bash
uv sync --no-default-groups --group online
uv run --no-sync streamlit run streamlit_app.py
```

For local backup testing, set `FARMERS_BRIDGE_BACKUP_REPO`, `FARMERS_BRIDGE_BACKUP_TOKEN`
and optionally `FARMERS_BRIDGE_BACKUP_BRANCH` as environment variables. The same adapter works
locally and on Streamlit.

Open the displayed local URL in separate browser windows/devices. Create a room, optionally share each player's PIN privately, and connect each player. The first listed player is the host.


## Recovery behaviour

- **In person:** local JSON checkpoint after every completed round. Resume from the last completed round after restarting the program.
- **Pygame:** local JSON checkpoint after every card play and trick. It restores hands, bids, trick leader and a partially played trick.
- **Online:** SQLite transaction after every state change. Reconnect with the same room code and username/PIN. With private backup configured, the database and CSVs are restored after a Streamlit restart/redeploy.
- If the process stops during manual bid/trick entry, that unfinished input phase must be re-entered; the last completed round remains saved.

The GitHub backup is intended for one running Streamlit app instance and small game-night datasets. It is not a high-availability database: it depends on GitHub availability, API limits and a single active app instance. Add stronger authentication, room expiry, host handoff, rate limits and concurrency tests before exposing the app widely.

## Privacy note

The app's rendering layer only displays the connected player's hand, but the SQLite-backed prototype is not a security boundary against a malicious host or a compromised app server. Do not use real-money stakes or sensitive account data with this prototype.


## Lobby joining

The host creates a room with their own username and the number of player seats.
Each remaining player joins with the room code and enters their own username; if
PINs are enabled, each joining player chooses their own PIN. The lobby shows
registered players and the remaining open seats, and the host cannot start until
all seats are filled. Use pseudonymous usernames rather than real names.
