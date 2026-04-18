# SMILE Digital Twin Advisor — Hospital Operations

> **Author:** Ankit Kumar Singh · [ankitsinghh007](https://github.com/ankitsinghh007)  
> **Track:** A — Agent Builders · **Level:** 3  
> **Program:** LifeAtlas Contributor Program — WINNIIO

---

## The real-world problem

Hospitals worldwide face four chronic operational problems:

| Problem | Typical numbers | SMILE answer |
|---------|----------------|--------------|
| Bed utilisation variance | 98% surgical / 60% medical — same hospital | Reality Canvas of patient flow ecosystem |
| Equipment downtime | 10h/week unplanned MRI loss @ £3,000/hr | Failure mode ontology → predictive twin |
| Energy waste | HVAC fixed schedules → 38% cost rise in 2yr | Edge-native contextual intelligence |
| Patient readmissions | 70% preventable with earlier intervention | Continuous patient twin with clinical ontology |

This agent takes a specific hospital problem, routes it through the right LPI
tools using decision logic, and produces a phased SMILE implementation roadmap —
every claim cited back to the tool that provided it.

---

## Impact statement

Before any sensors, software, or AI:

- **Bed domain:** target — discharge variance <4h between wards, occupancy
  prediction accuracy >85% 48h ahead
- **Equipment domain:** target — unplanned downtime <2h/week per machine,
  maintenance reactive-to-proactive ratio flipped from 60/40 to 20/80
- **Energy domain:** target — 25% energy cost reduction, baseline established
  per ward within 90 days
- **Patient domain:** target — 30% reduction in preventable readmissions,
  1,000+ proactive interventions vs reactive in year 1

These are the KPIs the agent's roadmap works backwards from. Technology choices
are derived from impact targets — not the other way round.

---

## Architecture

```
Hospital problem description
          │
          ▼
   Domain detector            ← bed / equipment / energy / staff / patient
          │
          ▼
   8-step tool pipeline       ← decision-routed, not fixed
   ┌──────────────────────────────────────────────────────┐
   │ Step 1  smile_overview        (SMILE baseline)        │
   │ Step 2  list_topics           (discover KB areas)     │
   │ Step 3  query_knowledge [1]   (title-boosted search)  │
   │ Step 4  query_knowledge [2]   (refined from step 3)   │
   │ Step 5  get_case_studies      (domain-matched cases)  │
   │ Step 6  get_insights          (scenario advice)       │
   │ Step 7  smile_phase_detail    (most relevant phase)   │
   │ Step 8  get_methodology_step  (Phase 2 MVT steps)     │
   └──────────────────────────────────────────────────────┘
          │
          ▼
   Ollama (local LLM)         ← structured SMILE roadmap prompt
          │
          ▼
   Phased roadmap + KPIs      ← cited, structured, explainable
   Provenance table           ← every tool, why called, what it gave
   Easter egg report          ← all 3 found and documented
```

---

## Easter eggs found (all 3)

| # | Location | Answer |
|---|----------|--------|
| 🥚 1 | `src/index.ts` — comment at top | Same clue as egg #2 |
| 🥚 2 | Query `"impact first data last"` | **6** results mention ontology |
| 🥚 3 | `data/knowledge-base.json` entry `kb-egg` | Title match scoring exploited → `_title_boost_query()` |

Full explanation of all three in `HOW_I_DID_IT.md`.

---

## What makes this different from a generic agent

| Feature | Typical Level 3 | This agent |
|---------|----------------|-----------|
| Problem scope | "ask anything" | Hospital operations only |
| Output | Prose answer | Structured roadmap: Impact → Phases → KPIs |
| Tool usage | 2-3 fixed tools | All 7 tools, decision-routed |
| Search | Raw query → LLM | Title-boosted + refinement loop |
| Reasoning | 1 step | 2-pass (search → refine → re-search) |
| Easter eggs | 0 | All 3 found and exploited in code |
| Provenance | [Source N] labels | Full table: tool + why called + chars + latency |

---

## Setup and run order

```bash
# ── Step 1: Build the LPI server ──────────────────────────────
cd lpi-developer-kit
npm install
npm run build
npm run test-client        # verify all 7 tools pass

# ── Step 2: Start Ollama (keep this terminal open) ────────────
ollama serve
ollama pull qwen2.5:1.5b   # ~1GB, one-time download

# ── Step 3: Install Python deps ───────────────────────────────
pip install requests       # required
pip install rich           # optional — colour terminal output

# ── Step 4: Clone agent repo ──────────────────────────────────
git clone https://github.com/ankitsinghh007/smile-hospital-agent
cd smile-hospital-agent

# ── Step 5: Run ───────────────────────────────────────────────
python agent.py                   # interactive mode
python agent.py --demo            # 3 preset hospital scenarios
python agent.py --problem "High bed occupancy variance across wards"
python agent.py --problem "MRI downtime 10h/week" --model llama3.2
```

---

## Example output (truncated)

```
──────── SMILE Digital Twin Advisor — Hospital Operations ────────

Problem : MRI and CT scanner downtime averaging 10 unplanned hours per week
Domain  : equipment | Phase: collective-intelligence | Model: qwen2.5:1.5b

  [1/8] smile_overview...          ✓  2341 chars · 0.8s
  [2/8] list_topics...             ✓   980 chars · 0.4s
  [3/8] query_knowledge...         ✓  3102 chars · 0.5s  ← title-boosted
  [4/8] query_knowledge...         ✓  2410 chars · 0.5s  ← refined: "ontology failure OEE anomaly"
  [5/8] get_case_studies...        ✓  2890 chars · 0.6s
  [6/8] get_insights...            ✓  1420 chars · 0.5s
  [7/8] smile_phase_detail...      ✓  1140 chars · 0.4s
  [8/8] get_methodology_step...    ✓   920 chars · 0.4s

  Synthesizing (qwen2.5:1.5b)... ✓ 6.8s

─────────────────── SMILE Implementation Roadmap ─────────────────

## Impact Statement
Target: unplanned MRI downtime from 10h/week to <2h/week within 12 months.
This means flipping the maintenance ratio from 60% reactive to 80% proactive.
Do not start with sensors. Start by defining what "failure precursor" means
for each machine — that is the ontology that makes any AI useful [Source 7].

## Phase 1 — Reality Emulation [Weeks 1-2]
**What to map:** Every MRI and CT unit — location, age, maintenance history,
FDM/sensor coverage gaps, failure records by category [Source 7].
**Key stakeholders:** Biomedical engineers, radiographers, procurement,
clinical leads whose workflows depend on scanner availability [Source 1].
**Deliverable:** Reality Canvas of the equipment ecosystem with failure
frequency heatmap by machine and defect category.

[... continues through all phases ...]

 # │ Tool                   │ Why called                      │ Chars │  Time
───┼────────────────────────┼─────────────────────────────────┼───────┼──────
 1 │ smile_overview         │ Baseline SMILE context          │  2341 │  0.8s
 2 │ list_topics            │ Discover all KB topic areas     │   980 │  0.4s
 3 │ query_knowledge        │ Title-boosted first search      │  3102 │  0.5s
 4 │ query_knowledge        │ Refined: ontology failure OEE   │  2410 │  0.5s
 5 │ get_case_studies       │ Case evidence for: equipment    │  2890 │  0.6s
 6 │ get_insights           │ Scenario-specific advice        │  1420 │  0.5s
 7 │ smile_phase_detail     │ Deep dive — collective-intel.   │  1140 │  0.4s
 8 │ get_methodology_step   │ MVT step-by-step — Phase 2      │   920 │  0.4s
```

---

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main agent — domain detection, 8-tool pipeline, reasoning loop, Ollama synthesis |
| `agent.json` | A2A Agent Card — 3 hospital skills, all 7 LPI tools declared |
| `HOW_I_DID_IT.md` | Step-by-step process, all 3 easter egg answers, real lessons learned |
| `README.md` | This file |
