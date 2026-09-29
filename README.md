---
title: Evactive
emoji: 🚨
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Agentic-AI evacuation command center for industrial plants
---

# Evactive: AI-assisted emergency evacuation for industrial plants

Prototype command-center demo. Five sample plants, fire and flammable-gas hazards, a detector
network, simulated personnel, and a team of agents that detect, assess, decide, re-route and
communicate as the incident develops.

> Simulation only. Layouts, detectors and people are synthetic and not to scale.

**Stack:** Python (FastAPI, NumPy) simulation + agents · React (Vite) dashboard on a live
WebSocket · LLM via Hugging Face Inference Providers (or local Ollama) for situation reports,
bilingual (English/Hindi) PA announcements and operator Q&A.

---

## Run it locally

You need **Python 3.11+** (https://www.python.org/downloads/; on Windows tick *Add python.exe to
PATH* during install). Node.js is *not* needed: the dashboard is pre-built in `frontend/dist`.

**1. Get the code:** `git clone https://github.com/harsh-k03/Evactive.git`, or on GitHub click
**Code → Download ZIP** and unzip it.

**2. Install and start** (from inside the `Evactive` folder):

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

**3. Open http://localhost:8000.** Everything works without an API key: situation reports and PA
messages then come from built-in templates. To get AI-written text, add your own key (next section).
Stop the server with **Ctrl+C**.

Optional: keep the packages separate in a virtual environment. Before `pip install`, run
`python -m venv .venv`, then `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`
(macOS/Linux). With Anaconda: `conda create -n evactive python=3.11 -y`, then `conda activate evactive`.

### Turn on the LLM agents (optional but recommended)

Without an LLM, the agents still work; situation reports and PA messages use rule-based
templates (marked `template` in the UI). Two ways to add an LLM:

**Option A: Hugging Face API (nothing to download)**

1. Create a token at https://huggingface.co/settings/tokens (type *Fine-grained*, tick
   **Make calls to Inference Providers**).
2. In `backend/`, copy `.env.example` to `.env` and paste your token after `HF_TOKEN=`:
   - Windows (PowerShell): `copy .env.example .env`, then `notepad .env`
   - macOS / Linux: `cp .env.example .env`, then open `.env` in any editor

   `.env` is git-ignored: never commit your token.
3. Restart the server (Ctrl+C, then the `uvicorn` command again). The top-right pill turns green and shows the model in use (default
   `Qwen2.5-72B-Instruct`; falls back to Llama-3.3-70B or Gemma-3-27B if a model is unavailable).

Free accounts get a small monthly credit; check usage at https://huggingface.co/settings/billing.
Any chat model served by Inference Providers works: set `HF_MODEL` (comma-separated list, tried
in order). `python hf_check.py` (in `backend/`) shows what your token can do and which models answer.

**Option B: Ollama (local, free, offline)**

1. Install Ollama from https://ollama.com/download
2. `ollama pull qwen2.5:3b`
3. In `backend/.env` set `EVACTIVE_LLM_BACKEND=ollama` (with no `.env` file at all, Ollama is the
   default). Keep Ollama running, then restart the server.

### Troubleshooting

| Problem | Fix |
|---|---|
| `pip` or `uvicorn` "is not recognized" | Use `python -m pip ...` and `python -m uvicorn ...` as shown above (on Windows, `py` also works in place of `python`) |
| Port 8000 already in use | Pick another port, e.g. `--port 8010`, and open http://localhost:8010 |
| LLM pill (top right) stays red | Check that `backend/.env` holds your token, restart the server, then run `python hf_check.py` in `backend/` to see what the token can do |
| Error that a model is "not supported by any provider" | Enable providers at https://huggingface.co/settings/inference-providers or set `HF_MODEL` to another model; the app also tries fallback models by itself |
| Reports and PA messages are marked `template` | No LLM is connected. That is the built-in fallback; everything else works normally |

---

## Deploy

### Docker (your own machine, AWS EC2, any Docker host)

```bash
docker build -t evactive .
docker run -p 7860:7860 -e HF_TOKEN=hf_xxx evactive
```

Then open http://localhost:7860 (or the server's address). Leave out `-e HF_TOKEN=...` to run with
templates only. On a server, `-p 80:7860 --restart always` serves it on the normal web port and
restarts it after reboots.

### Hugging Face Spaces

The header at the top of this README is the Space config (`sdk: docker`, port 7860). Note that
Docker Spaces now need a Hugging Face PRO account.

1. Create a Space at https://huggingface.co/new-space → SDK **Docker** → template **Blank**.
2. In the Space: **Settings → Variables and secrets → New secret**: `HF_TOKEN` = your token.
3. Upload the repo files (web upload, `git push`, or `huggingface_hub.upload_folder`).
   Do **not** upload `backend/.env`.

> One shared simulation per server: everyone who opens the URL sees and controls the same run.

---

## Using the dashboard

| Control | What it does |
|---|---|
| Plant + scenario dropdowns, **Load/Reset** | Pick one of 5 plants and one of its 5 scripted incidents (or free play) |
| **Run / Pause / Step**, 1x-8x | Simulation clock (1 tick = 1 simulated second) |
| **+ Fire / + Gas leak** then click the map | Start a hazard anywhere, live |
| Wind sliders | Change wind direction/speed; outdoor gas and smoke drift with it |
| Operator override | Manual site/zone evacuation, manual ESD (gas isolation) |
| Ask Evactive | Ask the LLM about the live situation |
| Bottom tabs | Agent activity log, detector readings, personnel muster roll |

Hover over any person, detector or cell for details. Click a person in the Personnel tab
to highlight their route.

### The five sample plants

| Plant | What makes it hard to evacuate |
|---|---|
| Float Glass Plant | Long linear hall, outdoor gas station upwind of an assembly point |
| Glass Processing Unit | Everyone shares one central corridor; canteen and clean room have single doors; single-leaf fire door at one end |
| Pharma API Plant | Clean room reachable only through a gowning airlock (two single doors in series); solvent tank farm |
| High-Bay Warehouse | 1-cell rack aisles that dead-end at a wall; fire wall with only two openings; exits mostly on the dock side |
| Auto Components Plant | Two buildings joined by a narrow connector; crowded canteen at shift change; conveyor maze in assembly |

Each plant has 5 scripted scenarios. Pick the plant in the first dropdown, the scenario in the
second, then **Load/Reset** and **Run**.

### Good demo scenarios

1. **Float Glass - Natural gas PRS leak, wind toward South Lawn**: the gas cloud drifts onto AP3, which is
   closed automatically and everyone is re-routed to AP1/AP2.
2. **Float Glass - Warehouse fire**: the loading-dock exit E5 gets blocked and AP2 is closed; routes change live.
3. **Float Glass - Fuel gas leak at furnace burner -> ignition**: ALERT -> zone evacuation -> ESD -> site
   evacuation -> ignition 100 s in.
4. **Glass Processing - Canteen kitchen fire during lunch**: queues form at the single canteen door
   and in the shared corridor (orange rings).
5. **Pharma - Clean room fire**: the emergency exit is blocked, 14 packers leave through the airlock.
6. **Free play**: set wind, drop a gas leak upwind of an assembly point and watch.

---

## How it works

```
 detectors ──> Detection ──> Assessment ──> Commander ──> Routing ──> (people move) ──> Accountability ──> Comms
   (sim)        debounce     hazard picture   escalation     cost-to-safety           muster roll        PA (EN/HI)
                alarms       + LLM sitrep     ladder, ESD    field, exits/APs         ALL CLEAR          + SMS (LLM)
```

| Agent | Role | Uses LLM? |
|---|---|---|
| Detection | Watches every detector, debounces (2 s), raises A1/A2 gas, flame, smoke alarms | No |
| Assessment | Fuses alarms with the hazard picture per zone; writes situation reports | Yes (sitrep) |
| Commander | Escalation policy: ALERT -> zone evacuation -> site evacuation; triggers ESD | No |
| Routing | Watches exits & assembly points; re-plans every evacuee's route each second | No |
| Accountability | Muster roll, trapped/injured tracking, ALL CLEAR | No |
| Comms | PA announcements (English + Hindi) and SMS to supervisors | Yes |

**Design principle:** safety-critical decisions (alarm thresholds, escalation, routing) are
deterministic and auditable. The LLM writes reports and messages and answers questions; it
never decides a route or an evacuation. If the LLM is down or slow, everything keeps working
on templates.

**Routing:** one reverse multi-source Dijkstra from all *safe* assembly points gives a
cost-to-safety value for every cell. Cell cost rises with smoke, gas %LEL and closeness to
fire; burning cells are impassable. Every person walks downhill on that field, so re-planning
for all people costs one Dijkstra. Congestion is modelled (max 3 people per 2 m cell).

**Crowds and bottlenecks:** a 2 m cell holds up to 3 people; a 1-cell-wide doorway is treated as a
~1 m single-leaf door (one person at a time), wider openings as double doors (2 per cell). Walking
speed drops as density rises. The route cost includes current crowding, so new arrivals are spread
across exits instead of piling onto one, and each evacuee stays committed to their assembly point
unless another is clearly (15%+) better. People stalled for 2+ seconds form a queue; queues of 3+
show as orange rings on the map, queues of 5+ are logged by the Routing agent, and the worst queue
is reported in the ALL CLEAR summary.

**Hazards:** fire is a fuel-driven cellular automaton (walls stop it); smoke and gas diffuse
through open cells, drift with wind outdoors and dilute over time; gas leaks ramp up and stop
~40 s after ESD. Demo-grade models, not CFD.

**Thresholds used:** gas A1 20% LEL, A2 40% LEL; exit blocked at 40% LEL / 60% smoke / fire at
exit; assembly point closed at 10% LEL / 20% smoke / fire within ~12 m.

---

## Project layout

```
backend/
  app/
    main.py            FastAPI: REST commands, WebSocket stream, serves dashboard
    engine.py          simulation engine: tick loop, people movement, frames
    layouts.py         float glass plant + registry of all plants
    plants/            the other four sample plants  <- copy one to add a new plant
    sim/               grid, hazards, sensors, routing, workers
    agents/            the six agents + LLM client (Hugging Face / Ollama)
  hf_check.py          diagnoses Hugging Face token / model availability
  requirements.txt
  .env.example         copy to .env for local LLM settings (git-ignored)
frontend/
  src/                 React dashboard (Vite)
  dist/                pre-built dashboard served by FastAPI
Dockerfile             container for Hugging Face Spaces / any Docker host
```

## Editing the dashboard (only if you change UI code)

Install Node.js LTS, then:

```bash
cd frontend
npm install
npm run dev      # live-reload UI at http://localhost:5173 (backend must be running)
npm run build    # rebuild dist/ so the backend serves the new UI (commit dist/ afterwards)
```

## API quick reference

`POST /api/sim/reset {scenario_id}` · `/api/sim/play` · `/api/sim/pause` · `/api/sim/step` ·
`/api/sim/speed {speed}` · `/api/hazard {type: fire|leak, x, y}` · `/api/wind {from_deg, speed_mps}` ·
`/api/evacuate {scope: "site"|zone_id}` · `/api/isolate` · `/api/ask {question}` ·
`GET /api/state` · `WS /ws`. Interactive docs at http://localhost:8000/docs (while the server is running).

## Known limitations

- Hazard models are demo-grade (cellular-automaton fire, grid diffusion for gas/smoke), not CFD.
- No sprinklers or firefighting are modelled, so long-running fires keep growing and can close
  assembly points late in a run.
- Detectors are simulated; in a real deployment the hazard picture would come from the detector
  network (and CCTV) instead of the simulator.
