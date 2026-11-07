"""
Synthetic but realistic history for a small 11 kV distribution fleet.
Every record is retained into Hindsight memory when you click "Load demo history".
All values are made up for the demo; gas values are in ppm.
"""

TRANSFORMERS = {
    "T-1": "Gokul Road 33/11 kV substation, 10 MVA, 2009 make (replaced after 2024 failure)",
    "T-2": "Dharwad Industrial Area 33/11 kV, 12.5 MVA, 2012 make",
    "T-3": "Navanagar 33/11 kV substation, 10 MVA, 2011 make",
    "T-4": "Vidyanagar 33/11 kV substation, 8 MVA, 2016 make",
    "T-5": "Unkal 33/11 kV substation, 8 MVA, 2010 make",
}

# (content, ISO timestamp, context)
SEED_RECORDS = [
    # ---------- T-1: the failure story the agent should learn from ----------
    ("T-1 (Gokul Road, 10 MVA) DGA sample: H2 38, CH4 22, C2H6 18, C2H4 12, C2H2 0, CO 310, CO2 2450 ppm. "
     "Engineer remark: healthy, routine.", "2023-07-14T10:00:00Z", "DGA lab result"),
    ("T-1 (Gokul Road) DGA sample: H2 41, CH4 24, C2H6 19, C2H4 13, C2H2 0, CO 330, CO2 2600 ppm. "
     "Engineer remark: no change from baseline.", "2023-12-05T10:00:00Z", "DGA lab result"),
    ("T-1 (Gokul Road) OLTC (on-load tap changer) overhaul done by contractor Shree Electricals. "
     "Diverter contacts replaced.", "2024-02-02T10:00:00Z", "maintenance record"),
    ("T-1 (Gokul Road) DGA sample: H2 85, CH4 30, C2H6 20, C2H4 30, C2H2 5, CO 340, CO2 2700 ppm. "
     "Engineer remark: acetylene appeared but low, no action taken, resample at next cycle.",
     "2024-03-15T10:00:00Z", "DGA lab result"),
    ("T-1 (Gokul Road) FAILED: Buchholz trip followed by internal arcing in OLTC diverter switch. "
     "9 days outage, about Rs 38 lakh repair and transformer replacement. Root cause: diverter contacts "
     "misaligned during the February 2024 overhaul by Shree Electricals. Lesson: acetylene appearing "
     "within weeks of OLTC work means inspect the OLTC immediately, do not wait for next sample.",
     "2024-04-28T10:00:00Z", "failure report"),

    # ---------- T-3: same pattern starting now (the risk the agent must catch) ----------
    ("T-3 (Navanagar, 10 MVA) DGA sample: H2 35, CH4 20, C2H6 16, C2H4 10, C2H2 0, CO 290, CO2 2300 ppm. "
     "Engineer remark: healthy.", "2025-11-20T10:00:00Z", "DGA lab result"),
    ("T-3 (Navanagar) DGA sample: H2 37, CH4 21, C2H6 17, C2H4 11, C2H2 0, CO 300, CO2 2380 ppm. "
     "Engineer remark: stable.", "2026-06-12T10:00:00Z", "DGA lab result"),
    ("T-3 (Navanagar) OLTC overhaul done by contractor Shree Electricals. Diverter contacts replaced.",
     "2026-09-20T10:00:00Z", "maintenance record"),

    # ---------- T-5: a benign pattern (the false alarm the agent must calm) ----------
    ("T-5 (Unkal, 8 MVA) DGA sample: H2 30, CH4 18, C2H6 15, C2H4 9, C2H2 0, CO 280, CO2 2200 ppm. "
     "Engineer remark: healthy.", "2024-11-10T10:00:00Z", "DGA lab result"),
    ("T-5 (Unkal) DGA sample: H2 34, CH4 19, C2H6 15, C2H4 10, C2H2 6, CO 285, CO2 2250 ppm. "
     "Engineer remark: sudden acetylene, flagged as possible arcing.", "2025-03-08T10:00:00Z", "DGA lab result"),
    ("T-5 (Unkal) Investigation: OLTC compartment gasket seepage found; OLTC oil (which normally contains "
     "acetylene from switching) was leaking into the main tank. Internal inspection found no arcing. "
     "Gasket replaced, main tank oil filtered. Verdict: FALSE ALARM, contamination from OLTC leak, not an "
     "internal fault. Lesson: on T-5, acetylene with no rise in H2 or C2H4 plus OLTC seepage = leak, not fault.",
     "2025-03-25T10:00:00Z", "engineer verdict"),
    ("T-5 (Unkal) DGA sample after gasket repair and filtration: H2 28, CH4 17, C2H6 14, C2H4 9, C2H2 0, "
     "CO 270, CO2 2150 ppm. Engineer remark: back to baseline.", "2025-06-15T10:00:00Z", "DGA lab result"),
    ("T-5 (Unkal) Patrol note: oil seepage again visible at OLTC compartment gasket.",
     "2026-10-22T10:00:00Z", "inspection note"),

    # ---------- T-2: thermal / overload story ----------
    ("T-2 (Dharwad Industrial, 12.5 MVA) DGA sample: H2 45, CH4 40, C2H6 35, C2H4 20, C2H2 0, CO 450, "
     "CO2 3600 ppm. Engineer remark: normal for industrial loading.", "2025-12-02T10:00:00Z", "DGA lab result"),
    ("T-2 (Dharwad Industrial) ran at 112-118% load for about 3 weeks in May 2026 due to a feeder transfer "
     "while T-6 was under repair. Top oil temperature reached 92 C.", "2026-05-25T10:00:00Z", "loading event"),
    ("T-2 (Dharwad Industrial) DGA sample: H2 60, CH4 65, C2H6 55, C2H4 38, C2H2 0, CO 720, CO2 5200 ppm. "
     "Engineer remark: CO and CO2 up after overload, paper insulation ageing suspected, keep load under 100%.",
     "2026-06-20T10:00:00Z", "DGA lab result"),

    # ---------- T-4: steady healthy unit ----------
    ("T-4 (Vidyanagar, 8 MVA) DGA sample: H2 25, CH4 12, C2H6 10, C2H4 6, C2H2 0, CO 200, CO2 1800 ppm. "
     "Engineer remark: healthy.", "2025-08-18T10:00:00Z", "DGA lab result"),
    ("T-4 (Vidyanagar) DGA sample: H2 26, CH4 13, C2H6 11, C2H4 6, C2H2 0, CO 210, CO2 1850 ppm. "
     "Engineer remark: healthy, stable trend.", "2026-08-21T10:00:00Z", "DGA lab result"),
]

# Readings to type in during the live demo (shown in the README demo script)
DEMO_READINGS = {
    "T-3": dict(h2=70, ch4=26, c2h6=18, c2h4=24, c2h2=4, co=310, co2=2450),   # should alarm: same as T-1
    "T-5": dict(h2=31, ch4=18, c2h6=15, c2h4=10, c2h2=7, co=280, co2=2200),   # should calm: same as T-5 2025
}
