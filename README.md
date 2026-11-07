# Transformer Health Historian

An AI agent that remembers every oil test, maintenance job, overload, failure and engineer verdict for each
distribution transformer, and uses that memory to judge new dissolved gas analysis (DGA) results.
Memory is powered by [Hindsight](https://github.com/vectorize-io/hindsight).

## The problem

DISCOMs test transformer oil (DGA) every few months and interpret it with generic IEEE C57.104 rules. Those
rules raise many false alarms and miss slow, unit-specific faults. The context that explains a reading
(maintenance work, overloads, a sister unit's failure) sits in scattered registers and in engineers' memory.
Warning signs get ignored or missed until a failure costing ₹30–40 lakh.

## How Hindsight memory is used

| Operation | What we do with it |
|---|---|
| **Retain** | Every DGA result, maintenance job, loading event, failure report and engineer verdict is stored in one fleet memory bank (`dga-historian`), with its real date. |
| **Recall** | Before analysing a new reading, the agent recalls that transformer's history and fleet-wide lessons (failures, confirmed false alarms). |
| **Reflect** | "Fleet risk summary" asks Hindsight to reason over the whole bank and rank transformers by risk. |
| **Learning** | When an engineer records a verdict (confirmed fault / false alarm), it is retained. Next time a similar pattern appears, the agent uses it. |

Without memory, the agent can only apply generic rules. With memory, it judges each transformer against its
own baseline and connects gas changes to events like OLTC work by a specific contractor.

## Architecture

```
Engineer (Streamlit UI)
   │  new DGA reading / question / verdict
   ▼
HistorianAgent (core.py)
   ├── retain ──► Hindsight memory bank (self-hosted, per-fleet)
   ├── recall ◄── transformer history + fleet lessons
   └── LLM (Groq: openai/gpt-oss-120b) ──► Risk + Why (cites records) + Action
```

## Run it

We use the open-source, self-hosted Hindsight server on a laptop. Hindsight Cloud also works if you set the URL in `.env`.

```bash
pip install -r requirements.txt
pip install hindsight-api
```

**Terminal 1: memory server**
```powershell
copy start-hindsight.example.ps1 start-hindsight.ps1   # then add your Groq key inside
powershell -ExecutionPolicy Bypass -File .\start-hindsight.ps1
```

**Terminal 2: app**
```bash
copy .env.example .env      # then add your Groq key
python -m streamlit run app.py
```

In the app, click **Load demo history** once, then wait about 30 seconds.

## Demo script (3 minutes)

1. **Before.** Turn **Hindsight memory OFF**. Select **T-3** and enter the reading H2 70, CH4 26, C2H6 18, C2H4 24,
   C2H2 4, CO 310, CO2 2450. The agent gives a generic "resample" style answer.
2. **After.** Turn memory **ON** and click **Compare**. The memory agent links the acetylene to last month's OLTC overhaul
   by Shree Electricals. It recalls that T-1 showed the same pattern 6 weeks before failing in 2024 and recommends an
   OLTC inspection now.
3. **It also prevents false alarms.** Select **T-5** and enter H2 31, CH4 18, C2H6 15, C2H4 10, C2H2 7, CO 280,
   CO2 2200. The agent recalls the 2025 OLTC gasket leak (confirmed false alarm) and the new seepage note. It advises
   fixing the gasket and resampling, not an emergency outage.
4. **It learns.** Record a verdict for T-3: "CONFIRMED FAULT — diverter contacts misaligned". Ask "What is the
   pattern with Shree Electricals OLTC work?" and the agent now cites two cases.
5. **Fleet view.** Click **Fleet risk summary (reflect)**.

## Data

All data in `seed_data.py` is synthetic but realistic (11 kV fleet, 5 transformers, 2023–2026).

## Team

- **Ayush A N Grampurohit**: Hindsight memory integration (retain / recall / reflect), agent logic and backend (`core.py`)
- **Bhoomi Kahallikeri**: Streamlit user interface, before/after Compare view and demo flow (`app.py`)
- **Yashaswini R Kareppanavar**: Domain research on transformer DGA, IEEE C57.104-2019 and the need statement
- **Varsha S Mudakavi**: Synthetic fleet data design: DGA readings, maintenance, failure and verdict records (`seed_data.py`)
- **Prajwal Bevoor**: Testing, local Hindsight server setup, documentation and demo video
