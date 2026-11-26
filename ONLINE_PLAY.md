# Online play and free hosting

## Current online mode

`streamlit_app.py` is a playable multi-browser MVP backed by `cardgame/online.py`:

- Create a room and generate a private PIN for each named player.
- Each player connects from a separate browser using the room code, their name and PIN.
- The host starts the game; bidding starts left of the dealer and the dealer bids last.
- Each player sees only their own hand. The server-side room state contains all hands, but the UI only renders the connected player's hand.
- The app enforces turn order and follow-suit, calculates trick winners, and displays trump, bids, trick totals, played cards and scores.
- There is a bid-review phase in which players can correct their own bids, followed by host confirmation.
- There is a trick-review phase in which the host can correct trick totals; totals must still equal the number of tricks in the round.
- At game completion, the host can save the game into the same `data/game_history.csv` format used by the local modes.

The current repository uses SQLite with transactions. It supports multiple browser sessions connected to the same running app process. It is a functional prototype, not yet a hardened public multiplayer service: it does not have account authentication, robust session recovery, room expiry, rate limiting, or protection against an untrusted host.

## Free deployment

A no-cost starting combination is:

- **Streamlit Community Cloud** for hosting the Streamlit application.
- **Supabase Free** for shared PostgreSQL persistence once the local SQLite adapter is replaced.

Streamlit Community Cloud currently offers free app deployment. <https://docs.streamlit.io/deploy/streamlit-community-cloud> Supabase currently lists a $0 Free plan with a 500 MB database allowance, but free projects pause after one week of inactivity. <https://supabase.com/pricing> Free plans have usage limits and may change. A Streamlit deployment using the current local SQLite database can lose room state and CSV files when the app restarts or redeploys. It is suitable for local tests and short demonstrations, not durable online game history. For a game night where the room must survive restarts, move the room and history persistence to Supabase/Postgres before deploying.

## Deploy the Streamlit app for free

1. Push this project to a GitHub repository.
2. Create a Streamlit Community Cloud account and deploy `streamlit_app.py` from that repository.
3. Community Cloud reads `requirements.txt`, which includes Streamlit.
4. For persistent shared rooms, first implement the Supabase/Postgres adapter described above; do not deploy the SQLite version for games that must survive app restarts.

Streamlit documents the free Community Cloud deployment flow here: <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy>.

## Run locally

```bash
uv sync
uv pip install -r requirements-web.txt
uv run streamlit run streamlit_app.py
```

Open the displayed local URL in separate browser windows/devices. Create a room, share each player's PIN privately, and connect each player. The first listed player is the host.

## Before inviting the public

1. Replace SQLite with Supabase/Postgres and use server-side transactions for all state changes.
2. Add proper player authentication or expiring signed invite tokens; the six-character room code is not authentication.
3. Add database row-level security so each player can retrieve only their own hand.
4. Add session reconnect/recovery, room expiry, host handoff, rate limits and audit logs.
5. Add concurrency tests for simultaneous turns and unauthorized requests.
6. Store game history in the managed database or periodically export it; do not rely on Streamlit's local filesystem for persistence.

## Privacy note

The app's rendering layer only displays the connected player's hand, but the SQLite-backed prototype is not a security boundary against a malicious host or a compromised app server. Do not use real-money stakes or sensitive account data with this prototype.
