# Hexcrawl Explorer Architecture & Design

## Scope & Goals
- Describe the Hex Map Explorer platform (Flask server + Obsidian client) with emphasis on the Obsidian Hexcrawl plugin.
- Capture how terrain generation, session orchestration, and content authoring align to support tabletop exploration.
- Provide implementation anchors so future contributors can navigate key files quickly.

## Runtime Context
- Default deployment runs the Flask backend locally with SQLAlchemy/SQLite persistence and optional Ollama access for flavour text (`app.py`, `models.py`, `generation/ollama_client.py`).
- Obsidian plugin bundles to `main.js` but sources live in `obsidian-hexcrawl-plugin/src`, compiled via esbuild with axios-driven HTTP calls.
- Communication is HTTPS-friendly: Flask enables CORS for Obsidian desktop origins and the plugin sends cookie + JWT credentials (`app.py`, `obsidian-hexcrawl-plugin/src/main.ts`).

## Backend Architecture
- **Web façade** – Flask app wires blueprints, SocketIO logging, optional Talisman security, and CORS; endpoints under `/api` manage map lifecycle, movement approvals, and content export (`app.py`).
- **Authentication service** – Blueprint handles registration, login, JWT token issuance, and profile updates, with rate-limiting hooks and lockout tracking (`auth.py`).
- **Game engine** – `HexMap` manages cube-coordinate tiles, terrain assignment, travel rules, and exploration triggers while `GenerationManager` streams Ollama descriptions asynchronously (`core/map.py`, `generation/manager.py`).
- **Persistence** – `User`, `GameSession`, and `LoginAttempt` tables store credentials, map snapshots, and audit trails; sessions reference JSON columns for hex data and player states (`models.py`).
- **Master control** – Dedicated endpoints let Game Masters seed worlds, paint terrain, approve movement queues, and push generated maps into live sessions (`app.py`).

## Domain & Data Model
- Hex tiles track terrain, biome, elevation, description, exploration flags, and neighbour relations; conversions between cube and offset coordinates appear in both server and plugin (`core/map.py`, `obsidian-hexcrawl-plugin/src/main.ts`).
- Player state ties to session IDs with per-hex coordinates plus party metadata; movement pipeline relies on queued requests when approval mode is active (`app.py`).
- AI description cache preserves generated text per terrain/coordinate pair to minimise Ollama calls (`generation/ollama_client.py`).

## HTTP API Surface (Selected)
- `POST /api/new_game` – creates or resumes a session, primes initial hex ring, and returns map data (`app.py`).
- `GET /api/get_map` – pulls explored map for a session (`app.py`).
- `POST /api/move` – executes immediate moves (`app.py`).
- Movement approval lifecycle – `POST /api/request_move`, `GET /api/check_movement_status`, `POST /api/approve_movement`, `POST /api/decline_movement` (`app.py`).
- Master endpoints – seed control, terrain painting, session syncing (`app.py`).
- Auth endpoints – JWT issuance and profile management (`auth.py`).

## Obsidian Plugin Architecture
- **Core plugin class** – loads settings, initialises axios client with JWT restoration, registers ribbon icons/commands, orchestrates sessions, note sync, and exports (`obsidian-hexcrawl-plugin/src/main.ts`).
- **Settings tab** – surfaces server URL, note folder, grid toggles, auto-login, and connection testing inside Obsidian settings (`obsidian-hexcrawl-plugin/src/main.ts`).
- **AuthView** – handles login, registration, profile update flows, plus session join/leave UX (`obsidian-hexcrawl-plugin/src/authView.ts`).
- **HexcrawlView (player)** – builds the canvas map, refresh controls, info panels, and modal movement requests (`obsidian-hexcrawl-plugin/src/hexcrawlView.ts`).
- **MasterView (GM)** – richer workspace with terrain brush controls, movement approval queue, player list, teleportation, seed management, and export features (`obsidian-hexcrawl-plugin/src/masterView.ts`).
- **CustomHexMap renderer** – encapsulates canvas drawing, pan/zoom, coordinate conversions, brush preview overlays, and callbacks for interaction (`obsidian-hexcrawl-plugin/src/customHexMap.ts`).
- **Type contracts** – align plugin state with backend expectations, including `HexcrawlSettings`, `AuthState`, `HexData`, `MapData` (`obsidian-hexcrawl-plugin/src/types.ts`).

## Plugin Data Flows
1. **Login sequence** – Auth view posts credentials to `/api/auth/login`, stores JWT, refreshes user state, and optionally auto-joins last session.
2. **Session bootstrap** – `createNewGame` or join stores `currentSessionId`, fetches map data, and feeds `CustomHexMap` for rendering.
3. **Player move** – UI computes cube offsets, posts to `/api/move` (or queues request), reloads map, and repaints canvas.
4. **Movement approvals** – Players submit requests; GM view polls approvals, then approves/declines and refreshes players + queue.
5. **Hex note sync** – `syncCurrentHexToNote` ensures folder, optionally requests AI text, and writes markdown with neighbour backlinks.
6. **Master terrain editing** – Brush mode paints batch hexes, queues saves to `/api/master/update_terrain`, and refreshes the map.

## Security & Session Handling
- JWT tokens include 24-hour expiry and are decoded server-side for request context; server falls back to Flask-Login session if token missing (`auth.py`).
- Plugin caches base64 token when “remember me” is set and rehydrates headers on reload (`obsidian-hexcrawl-plugin/src/main.ts`).
- Movement approvals enforce GM authority by matching request `creator_id` with authenticated user; plugin hides master view behind `user.isGameMaster` (`app.py`, `obsidian-hexcrawl-plugin/src/main.ts`).
- CORS allows Obsidian desktop origins and localhost ports while keeping credentialed requests secure (`app.py`).

## Dependencies & Integrations
- **Python** – Flask, Flask-Login, SQLAlchemy, Marshmallow, Flask-SocketIO, JWT, Ollama client, plus Pygame tooling.
- **TypeScript** – Obsidian plugin API, axios, node-forge, express mock, Obsidian community interfaces.
- **Optional** – Ollama model `qwen2.5:3b` for AI descriptions (`generation/ollama_client.py`).

## Extensibility & Next Steps
1. Consolidate terrain logic between backend generators and plugin brush palette to avoid drift (`core/map.py`, `obsidian-hexcrawl-plugin/src/masterView.ts`).
2. Introduce websocket push for movement approvals to replace polling while reusing SocketIO.
3. Extract `CustomHexMap` into a shared package for reuse across GUI and plugin.
4. Harden token storage by encrypting `savedToken` before base64 encoding and revisit local REST API scaffold if exposing vault automation.

Natural follow-on work: verify master terrain updates persist across reloads, exercise plugin commands inside Obsidian sandbox, and add automated tests around axios client auth refresh behaviour.
