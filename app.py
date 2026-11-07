"""
Transformer Health Historian - Streamlit UI
Run:  streamlit run app.py
"""

import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from core import GASES, HindsightWorker, HistorianAgent, friendly_error
from seed_data import SEED_RECORDS, TRANSFORMERS

load_dotenv()
st.set_page_config(page_title="Transformer Health Historian", page_icon="⚡", layout="wide")

# ---------------- setup ----------------
missing = [k for k in ("HINDSIGHT_API_KEY", "GROQ_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"Missing in .env: {', '.join(missing)}. Copy .env.example to .env and add your keys.")
    st.stop()


@st.cache_resource
def get_agent():
    hs = HindsightWorker(base_url=os.getenv("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io"),
                         api_key=os.getenv("HINDSIGHT_API_KEY"))
    llm = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
    agent = HistorianAgent(hs, llm,
                           bank_id=os.getenv("HINDSIGHT_BANK_ID", "dga-historian"),
                           model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
                           transformers=TRANSFORMERS)
    agent.ensure_bank()
    return agent


agent = get_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []   # each: {role, content, memories, mode}

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("⚡ Fleet")
    tx_id = st.selectbox("Transformer", list(TRANSFORMERS),
                         format_func=lambda t: f"{t} · {TRANSFORMERS[t].split(',')[0]}")
    st.caption(TRANSFORMERS[tx_id])
    use_memory = st.toggle("Hindsight memory", value=True,
                           help="Turn off to see the same agent with no memory (before/after demo).")

    st.divider()
    with st.form("reading_form", clear_on_submit=True):
        st.subheader("🧪 New DGA reading")
        sample_date = st.date_input("Sample date", value=date.today())
        cols = st.columns(2)
        gases = {}
        for i, (key, label) in enumerate(GASES):
            gases[key] = cols[i % 2].number_input(f"{label} (ppm)", min_value=0.0, step=1.0, key=f"g_{key}")
        submit_reading = st.form_submit_button("Save & analyse", use_container_width=True)

    with st.expander("🛠 Log maintenance / loading event"):
        with st.form("event_form", clear_on_submit=True):
            ev_date = st.date_input("Date", value=date.today(), key="ev_date")
            ev_kind = st.selectbox("Type", ["maintenance record", "loading event", "inspection note", "failure report"])
            ev_details = st.text_area("Details", placeholder="e.g. OLTC overhaul by Shree Electricals, contacts replaced")
            submit_event = st.form_submit_button("Save event")

    with st.expander("✅ Record engineer verdict (agent learns)"):
        with st.form("verdict_form", clear_on_submit=True):
            v_date = st.date_input("Date", value=date.today(), key="v_date")
            verdict = st.selectbox("Outcome", ["CONFIRMED FAULT", "FALSE ALARM", "MONITORING - no conclusion yet"])
            v_notes = st.text_area("What was found", placeholder="e.g. Internal inspection found OLTC gasket leak, no arcing")
            submit_verdict = st.form_submit_button("Save verdict")

    st.divider()
    if st.button("📥 Load demo history (run once)", use_container_width=True):
        bar = st.progress(0.0, text="Retaining records into Hindsight…")
        try:
            agent.seed(SEED_RECORDS, progress=lambda i, n: bar.progress(i / n, text=f"Retained {i}/{n}"))
            st.success("Done. Wait ~30-60 s: Hindsight processes memories in the background.")
        except Exception as e:
            st.error(friendly_error(e))
    if st.button("🗑 Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---------------- main area ----------------
st.title("Transformer Health Historian")
st.caption("A DGA analyst that remembers every oil test, maintenance job, failure and engineer verdict "
           "for each transformer, powered by Hindsight memory.")

top = st.columns([1, 1, 2])
compare_clicked = top[0].button("⚖️ Compare: with vs without memory", use_container_width=True)
summary_clicked = top[1].button("🧠 Fleet risk summary (reflect)", use_container_width=True)
top[2].markdown(f"**Mode:** {'🟢 Memory ON' if use_memory else '⚪ Memory OFF'} · **Selected:** {tx_id}")


def add(role, content, memories=None, mode=None):
    st.session_state.messages.append(dict(role=role, content=content, memories=memories or [], mode=mode))


def run_question(question):
    add("user", question)
    with st.spinner("Recalling history and analysing…" if use_memory else "Analysing…"):
        try:
            answer, memories = agent.ask(question, tx_id, use_memory=use_memory)
        except Exception as e:
            answer, memories = f"⚠️ {friendly_error(e)}", []
    add("assistant", answer, memories, "memory" if use_memory else "no-memory")


def safe(action):
    """Run a memory write; show a friendly message instead of a red crash."""
    try:
        return action()
    except Exception as e:
        st.error(friendly_error(e))
        return None


# Handle sidebar actions
if submit_reading:
    if sum(gases.values()) == 0:
        st.sidebar.warning("Enter at least one gas value.")
    else:
        text = safe(lambda: agent.record_reading(tx_id, sample_date.isoformat(), gases))
        if text:
            run_question(f"New DGA result just came in. {text} Is this transformer at risk? What should we do?")
if submit_event and ev_details.strip():
    text = safe(lambda: agent.record_event(tx_id, ev_date.isoformat(), ev_kind, ev_details.strip()))
    if text:
        add("assistant", f"📝 Saved to memory: {text}", mode="note")
if submit_verdict and v_notes.strip():
    text = safe(lambda: agent.record_verdict(tx_id, v_date.isoformat(), verdict, v_notes.strip()))
    if text:
        add("assistant", f"✅ Verdict saved. I will use this next time: {text}", mode="note")
if summary_clicked:
    with st.spinner("Reflecting over the whole fleet's memory…"):
        add("assistant", "**Fleet risk summary**\n\n" + agent.fleet_summary(), mode="reflect")

# Compare view: same last question, two agents side by side
if compare_clicked:
    last_q = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"), None)
    if not last_q:
        st.info("Add a DGA reading or ask a question first, then click Compare.")
    else:
        left, right = st.columns(2)
        with st.spinner("Running both agents on the same question…"):
            plain, _ = agent.ask(last_q, tx_id, use_memory=False)
            try:
                smart, mems = agent.ask(last_q, tx_id, use_memory=True)
            except Exception as e:
                smart, mems = f"⚠️ {friendly_error(e)}", []
        with left:
            st.subheader("⚪ Without memory")
            st.markdown(plain)
        with right:
            st.subheader("🟢 With Hindsight memory")
            st.markdown(smart)
            with st.expander(f"Memories used ({len(mems)})"):
                for m in mems:
                    st.markdown(f"- {m}")
        st.divider()

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="⚡" if msg["role"] == "assistant" else None):
        if msg["mode"] == "no-memory":
            st.caption("⚪ answered without memory")
        st.markdown(msg["content"])
        if msg["memories"]:
            with st.expander(f"🧠 Memories used ({len(msg['memories'])})"):
                for m in msg["memories"]:
                    st.markdown(f"- {m}")

# Chat input
if prompt := st.chat_input(f"Ask about {tx_id} or the fleet, e.g. 'Why did T-1 fail?'"):
    run_question(prompt)
    st.rerun()