"""
Agent logic: Hindsight memory (retain / recall / reflect) + an LLM (Groq, OpenAI-compatible).
Kept separate from the UI so it can be tested and reused.
"""

import time
from concurrent.futures import ThreadPoolExecutor


class HindsightWorker:
    """Runs every Hindsight call on ONE dedicated thread.

    The Hindsight Python client keeps an async connection that belongs to the thread that created it.
    Streamlit runs each rerun (every button click) on a different thread, so a shared client crashes with
    "Timeout context manager should be used inside a task". Pinning all calls to one thread avoids that.
    """

    def __init__(self, base_url, api_key, timeout=60.0):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hindsight")
        self._base_url, self._api_key, self._timeout = base_url, api_key, timeout
        self._client = None

    def _client_here(self):
        if self._client is None:  # created inside the worker thread
            from hindsight_client import Hindsight
            self._client = Hindsight(base_url=self._base_url, api_key=self._api_key, timeout=self._timeout)
        return self._client

    def _run(self, method, **kwargs):
        return self._executor.submit(lambda: getattr(self._client_here(), method)(**kwargs)).result()

    def create_bank(self, **kwargs):
        return self._run("create_bank", **kwargs)

    def retain(self, **kwargs):
        return self._run("retain", **kwargs)

    def recall(self, **kwargs):
        return self._run("recall", **kwargs)

    def reflect(self, **kwargs):
        return self._run("reflect", **kwargs)


def friendly_error(e):
    """Turn Hindsight/HTTP errors into a message a beginner can act on."""
    msg = str(e)
    if "402" in msg or "Insufficient credits" in msg:
        return ("Hindsight says: insufficient credits. Add the MEMHACK99 promo code in Billing at "
                "ui.hindsight.vectorize.io (same organization as your API key), then try again.")
    if "401" in msg or "403" in msg or "Unauthorized" in msg:
        return "Hindsight rejected the API key. Copy it again into .env (no spaces), save, and restart the app."
    if "404" in msg:
        return "Memory bank not found. Click 'Load demo history' to create it."
    return f"Hindsight error: {msg[:300]}"


GASES = [("h2", "H2"), ("ch4", "CH4"), ("c2h6", "C2H6"), ("c2h4", "C2H4"),
         ("c2h2", "C2H2"), ("co", "CO"), ("co2", "CO2")]

SYSTEM_WITH_MEMORY = """You are a transformer health analyst for an Indian electricity distribution company (DISCOM).
You interpret dissolved gas analysis (DGA) of 33/11 kV power transformers.

You are given PAST RECORDS recalled from the fleet's memory: earlier DGA results, maintenance work,
loading events, failures and engineer verdicts. Use them:
- Compare a new reading with THAT transformer's own baseline and trend, not only generic limits.
- Link gas changes to events around them (OLTC work, overloads, leaks, contractors).
- Use lessons from other transformers: a pattern that preceded a failure is a warning; a pattern that
  engineers confirmed as a false alarm should lower concern, if the evidence matches.
- Always name the specific past record(s) you rely on, with dates.

Answer format (short, plain English, for a busy substation engineer):
Risk: LOW / MEDIUM / HIGH
Why: 2-4 bullet points citing records
Action: one clear next step with a time frame
Do not invent records or numbers that are not in the PAST RECORDS or the question."""

SYSTEM_WITHOUT_MEMORY = """You are a transformer DGA analyst. You have NO history of this transformer or fleet.
Judge the reading only with general DGA practice (IEEE C57.104-2019 style status and Duval-type reasoning).
Do not invent table values you are unsure of.

Answer format (short):
Risk: LOW / MEDIUM / HIGH
Why: 2-3 bullet points
Action: one next step"""


def format_reading(tx_id, tx_name, sample_date, gases):
    parts = ", ".join(f"{label} {gases[key]:g}" for key, label in GASES)
    return f"{tx_id} ({tx_name}) DGA sample on {sample_date}: {parts} ppm."


class HistorianAgent:
    def __init__(self, hs, llm, bank_id, model, transformers):
        self.hs = hs                  # hindsight_client.Hindsight
        self.llm = llm                # openai.OpenAI pointed at Groq
        self.bank_id = bank_id
        self.model = model
        self.transformers = transformers

    # ---------------- memory ----------------
    def ensure_bank(self):
        try:
            self.hs.create_bank(bank_id=self.bank_id, name="Transformer Health Historian")
        except Exception:
            pass  # already exists, or the API auto-creates banks on first retain

    def remember(self, content, context, timestamp=None):
        if timestamp:
            # Put the date inside the text too, so the LLM can order events correctly after recall
            content = f"[{timestamp[:10]}] {content}"
        kwargs = dict(bank_id=self.bank_id, content=content, context=context)
        if timestamp:
            kwargs["timestamp"] = timestamp
        self.hs.retain(**kwargs)

    def recall(self, query, limit=8):
        res = self.hs.recall(bank_id=self.bank_id, query=query)
        items = getattr(res, "results", res) or []
        return [getattr(r, "text", str(r)) for r in items][:limit]

    def seed(self, records, progress=None):
        self.ensure_bank()
        for i, (content, ts, ctx) in enumerate(records, 1):
            self.remember(content, ctx, ts)
            if progress:
                progress(i, len(records))

    # ---------------- recording new facts ----------------
    def record_reading(self, tx_id, sample_date, gases):
        text = format_reading(tx_id, self.transformers.get(tx_id, ""), sample_date, gases)
        self.remember(text, "DGA lab result", f"{sample_date}T10:00:00Z")
        return text

    def record_event(self, tx_id, event_date, kind, details):
        text = f"{tx_id} ({self.transformers.get(tx_id, '')}) {kind} on {event_date}: {details}"
        self.remember(text, kind, f"{event_date}T10:00:00Z")
        return text

    def record_verdict(self, tx_id, verdict_date, verdict, notes):
        # This is how the agent learns: engineers' confirmed outcomes become memory.
        text = (f"{tx_id} ({self.transformers.get(tx_id, '')}) engineer verdict on {verdict_date}: "
                f"{verdict}. {notes}")
        self.remember(text, "engineer verdict", f"{verdict_date}T10:00:00Z")
        return text

    # ---------------- thinking ----------------
    def _chat(self, system, user, retries=2):
        last_err = None
        for attempt in range(retries + 1):
            try:
                reply = self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    temperature=0.2,
                )
                return reply.choices[0].message.content.strip()
            except Exception as e:  # Groq rate limits / tool-call hiccups: retry, never crash the demo
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        return f"(The language model did not respond: {last_err}. Please try again.)"

    def ask(self, question, tx_id=None, use_memory=True):
        """Returns (answer, memories_used)."""
        memories = []
        if use_memory:
            query = f"{tx_id} {question}" if tx_id else question
            memories = self.recall(query)
            # Also pull fleet-wide lessons (failures and verdicts) so cross-transformer learning shows up
            for m in self.recall("failure root cause lesson engineer verdict false alarm OLTC", limit=4):
                if m not in memories:
                    memories.append(m)
            records = "\n".join(f"- {m}" for m in memories) or "(none found)"
            user = f"PAST RECORDS:\n{records}\n\nTRANSFORMER: {tx_id or 'not specified'}\nQUESTION:\n{question}"
            answer = self._chat(SYSTEM_WITH_MEMORY, user)
            # Keep the analysis itself as memory so later sessions know what was advised
            self.remember(f"Agent analysis for {tx_id or 'fleet'}: Q: {question} | A: {answer[:600]}",
                          "agent analysis")
        else:
            answer = self._chat(SYSTEM_WITHOUT_MEMORY, f"TRANSFORMER: {tx_id}\nQUESTION:\n{question}")
        return answer, memories

    def fleet_summary(self):
        q = ("Which transformers in the fleet are at highest risk right now and why? "
             "Rank them and give one action each.")
        try:
            ans = self.hs.reflect(bank_id=self.bank_id, query=q)
            return getattr(ans, "text", str(ans))
        except Exception as e:
            return f"(Reflect failed: {e})"