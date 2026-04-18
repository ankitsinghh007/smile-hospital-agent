#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  SMILE Digital Twin Advisor — Hospital Operations
  LPI Developer Kit · Level 3 · Track A: Agent Builders
  Author : Ankit Kumar Singh (ankitsinghh007)
  Repo   : https://github.com/ankitsinghh007/smile-hospital-agent
═══════════════════════════════════════════════════════════════════

Real-world problem:
  Hospitals struggle with bed utilisation variance, reactive equipment
  maintenance, energy waste from occupancy-blind HVAC, and patient
  readmissions from quarterly-only monitoring.

  This agent takes a hospital operations problem, routes it to the
  right LPI tools, and produces a SMILE implementation roadmap with
  every claim cited to the source tool that provided it.

What makes this different:
  1. Domain-specific problem framing (hospital operations only)
  2. Decision routing — tools selected based on detected domain
  3. Multi-step reasoning — query_knowledge called twice:
     first with title-boost, second refined from first result
  4. Title-boost search exploits Easter egg #3 (documented below)
  5. All 7 LPI tools used across the 8-step pipeline
  6. Structured output: Impact → Phases → KPIs → Pitfalls → Sources
  7. Full provenance table with WHY each tool was called

Easter eggs found (all 3):
  Egg 1: src/index.ts — comment at top of file
  Egg 2: query "impact first data last" -> 6 results mention ontology
  Egg 3: knowledge-base.json entry kb-egg — title match weighting
         exploited in _title_boost_query() below

Requirements:
  node >=18 + npm run build  (in lpi-developer-kit folder)
  ollama serve + ollama pull qwen2.5:1.5b
  pip install requests rich  (rich is optional)

Run order:
  Terminal 1: cd lpi-developer-kit && node dist/src/index.js
  Terminal 2: ollama serve
  Terminal 3: python agent.py --demo
              python agent.py --problem "your hospital problem"
"""

import json
import subprocess
import sys
import os
import time
import requests
import argparse
from typing import Optional

# Plain text output only
RICH = False

# ═══════════════════════════════════════════════════════════════
# CONFIG — edit OLLAMA_MODEL if you have a different model pulled
# ═══════════════════════════════════════════════════════════════

# Path resolution — works for both layouts:
#   Layout A: lifeatlas-project/lpi-developer-kit/  (sibling of smile-hospital-agent)
#   Layout B: any location, as long as lpi-developer-kit is sibling folder
_AGENT_DIR  = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.abspath(os.path.join(_AGENT_DIR, ".."))

# lpi-developer-kit is a sibling folder of smile-hospital-agent
_LPI_ROOT      = os.path.join(_PARENT_DIR, "lpi-developer-kit")
_LPI_INDEX     = os.path.join(_LPI_ROOT, "dist", "src", "index.js")

# On Windows, subprocess needs shell=True or a string command — use string
import platform as _platform
_IS_WINDOWS = _platform.system() == "Windows"

if _IS_WINDOWS:
    LPI_SERVER_CMD = f'node "{_LPI_INDEX}"'
else:
    LPI_SERVER_CMD = ["node", _LPI_INDEX]

LPI_SERVER_CWD = _LPI_ROOT
OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "qwen2.5:1.5b"

# ═══════════════════════════════════════════════════════════════
# EASTER EGG DOCUMENTATION (all 3 found)
# ═══════════════════════════════════════════════════════════════
#
# Egg 1 — src/index.ts, comment at top of file:
#   "Easter egg #2: Query query_knowledge with the exact phrase
#    impact first data last and count how many results mention
#    ontology. Put the number in your HOW_I_DID_IT.md."
#
# Egg 2 — Answer to the above:
#   Query "impact first data last" returns 39 results.
#   Of those, 6 mention "ontology" in title/content/tags:
#   kb-011, kb-003, kb-022, kb-047, kb-049, kb-063
#   ANSWER = 6
#
# Egg 3 — data/knowledge-base.json, entry id "kb-egg":
#   Title: "The Hidden Principle"
#   Content reveals: search scores by term matches across
#   title+content+tags as one blob. Short titles with exact
#   keyword matches score disproportionately high.
#   EXPLOIT: _title_boost_query() prepends nouns that appear
#   verbatim in KB entry titles, pushing relevant entries to #1.

EASTER_EGGS = {
    "Egg 1 location":  "src/index.ts — comment at top of file",
    "Egg 2 query":     "impact first data last",
    "Egg 2 answer":    "6 results mention ontology",
    "Egg 3 location":  "data/knowledge-base.json — entry kb-egg",
    "Egg 3 exploit":   "_title_boost_query() in agent.py",
}

# ═══════════════════════════════════════════════════════════════
# TITLE-BOOST SEARCH  (Easter egg #3 exploit)
# ═══════════════════════════════════════════════════════════════

_TITLE_KEYWORDS = {
    "bed":       ["patient", "flow", "occupancy", "healthcare", "admission"],
    "equipment": ["maintenance", "predictive", "OEE", "downtime", "failure"],
    "staff":     ["workforce", "readiness", "organisational", "change"],
    "energy":    ["energy", "edge", "sustainability", "smart-buildings"],
    "patient":   ["patient", "chronic", "health", "CGM", "readmission"],
    "general":   ["ontology", "MVT", "impact", "interoperability", "edge"],
}

def _title_boost_query(problem: str, domain: str) -> str:
    """
    Exploit: LPI search scores term matches across title+content+tags.
    Prepending nouns that appear verbatim in KB titles pushes those
    entries to rank #1. See kb-egg in knowledge-base.json.
    """
    boosts = _TITLE_KEYWORDS.get(domain, []) + _TITLE_KEYWORDS["general"]
    combined = problem + " " + " ".join(boosts)
    seen, out = set(), []
    for w in combined.split():
        if w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return " ".join(out)[:450]

# ═══════════════════════════════════════════════════════════════
# DOMAIN DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_domain(problem: str) -> str:
    p = problem.lower()
    if any(w in p for w in ["bed", "occupancy", "ward", "admission", "discharge", "flow", "capacity"]):
        return "bed"
    if any(w in p for w in ["equipment", "device", "maintenance", "downtime", "mri", "ct", "ventilator", "scanner"]):
        return "equipment"
    if any(w in p for w in ["staff", "nurse", "doctor", "schedule", "shift", "workforce", "rota"]):
        return "staff"
    if any(w in p for w in ["energy", "hvac", "heating", "carbon", "emission", "electricity", "power"]):
        return "energy"
    if any(w in p for w in ["patient", "readmission", "chronic", "diabetes", "disease", "monitoring"]):
        return "patient"
    return "general"

_DOMAIN_PHASE = {
    "bed":       "reality-emulation",
    "equipment": "collective-intelligence",
    "staff":     "concurrent-engineering",
    "energy":    "contextual-intelligence",
    "patient":   "collective-intelligence",
    "general":   "reality-emulation",
}

_DOMAIN_CASES = {
    "bed":       "hospital patient flow healthcare",
    "equipment": "predictive maintenance manufacturing downtime",
    "staff":     "workforce organisational change management",
    "energy":    "energy smart buildings HVAC sustainability",
    "patient":   "patient chronic disease healthcare digital twin",
    "general":   "hospital healthcare digital twin",
}

# ═══════════════════════════════════════════════════════════════
# MCP CLIENT — modelled exactly on the reference examples/agent.py
# ═══════════════════════════════════════════════════════════════

class MCPClient:
    """
    Persistent MCP session over subprocess stdio.
    Follows the EXACT same handshake pattern as examples/agent.py
    in the lpi-developer-kit repo.
    """

    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self._id = 0

    def start(self):
        # Verify the LPI server file exists before trying to launch
        if not os.path.isfile(_LPI_INDEX):
            raise FileNotFoundError(
                f"LPI server not found at:\n  {_LPI_INDEX}\n"
                f"Fix: cd lpi-developer-kit && npm run build"
            )

        self.proc = subprocess.Popen(
            LPI_SERVER_CMD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=LPI_SERVER_CWD,
            shell=_IS_WINDOWS,   # Windows requires shell=True for string commands
        )

        # ── Step 1: initialize request (matches examples/agent.py exactly) ──
        init_req = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smile-hospital-agent", "version": "1.0.0"},
            },
        }
        self.proc.stdin.write(json.dumps(init_req) + "\n")
        self.proc.stdin.flush()
        self.proc.stdout.readline()  # consume init response

        # ── Step 2: initialized notification ──────────────────────────────
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self.proc.stdin.write(json.dumps(notif) + "\n")
        self.proc.stdin.flush()

    def call(self, tool: str, args: dict = None) -> tuple[str, float]:
        """Call one LPI tool. Returns (text_result, elapsed_seconds)."""
        self._id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args or {}},
        }
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()

        t0 = time.time()
        line = self.proc.stdout.readline()
        elapsed = time.time() - t0

        if not line:
            return f"[ERROR] no response from {tool}", elapsed

        try:
            resp = json.loads(line)
        except json.JSONDecodeError:
            return f"[ERROR] bad JSON from {tool}", elapsed

        if "result" in resp and "content" in resp["result"]:
            return resp["result"]["content"][0].get("text", ""), elapsed
        if "error" in resp:
            return f"[ERROR] {resp['error'].get('message', 'unknown')}", elapsed
        return "[ERROR] unexpected format", elapsed

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                pass

# ═══════════════════════════════════════════════════════════════
# PROVENANCE LEDGER
# ═══════════════════════════════════════════════════════════════

class Provenance:
    def __init__(self):
        self.entries: list[dict] = []

    def record(self, step: int, tool: str, args: dict,
               result: str, elapsed: float, reason: str):
        self.entries.append({
            "step": step, "tool": tool, "args": args,
            "chars": len(result), "elapsed": round(elapsed, 2),
            "reason": reason,
            "ok": not result.startswith("[ERROR]"),
        })

    def print_table(self):
        print("\n>>> Provenance (tools called)")
        print(f"{'#':<3} {'Tool':<24} {'Why called':<34} {'Chars':>6}")
        print("-" * 70)
        for e in self.entries:
            print(f"{e['step']:<3} {e['tool']:<24} {e['reason']:<34} {e['chars']:>6}")
        print("-" * 70)

# ═══════════════════════════════════════════════════════════════
# OLLAMA
# ═══════════════════════════════════════════════════════════════

def query_ollama(prompt: str, model: str) -> str:
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 900},
            },
            timeout=180,
        )
        r.raise_for_status()
        return r.json().get("response", "[No response from model]").strip()
    except requests.ConnectionError:
        return "[ERROR] Cannot connect to Ollama. Make sure ollama serve is running."
    except requests.Timeout:
        return "[ERROR] Ollama timed out. Try a smaller model with --model qwen2.5:1.5b"
    except Exception as e:
        return f"[ERROR] Ollama: {e}"

# ═══════════════════════════════════════════════════════════════
# REFINEMENT LOOP — step 4 uses terms found in step 3 result
# ═══════════════════════════════════════════════════════════════

def _refine_terms(first_result: str, domain: str) -> str:
    signals = {
        "bed":       ["ontology", "patient", "flow", "KPI", "discharge", "stakeholder"],
        "equipment": ["ontology", "failure", "OEE", "anomaly", "CMMS", "precursor"],
        "staff":     ["readiness", "change", "adoption", "skill", "organisational"],
        "energy":    ["edge", "self-learning", "occupancy", "CO2", "sensor"],
        "patient":   ["CGM", "ontology", "clinical", "consent", "intervention"],
        "general":   ["ontology", "MVT", "impact", "interoperability", "edge"],
    }
    words = signals.get(domain, signals["general"])
    text = first_result.lower()
    found = [w for w in words if w.lower() in text] or words[:3]
    return " ".join(found[:4])

# ═══════════════════════════════════════════════════════════════
# MAIN ADVISOR PIPELINE
# ═══════════════════════════════════════════════════════════════

def run_advisor(problem: str, model: str) -> None:
    domain      = detect_domain(problem)
    phase_focus = _DOMAIN_PHASE[domain]
    case_q      = _DOMAIN_CASES[domain]
    boosted_q   = _title_boost_query(problem, domain)

    prov = Provenance()
    mcp  = MCPClient()

    print("\nSmile Hospital Twin")
    print(f"Problem : {problem}")
    print(f"Domain  : {domain} | Phase: {phase_focus} | Model: {model}\n")

    # ── Start MCP session ────────────────────────────────────
    try:
        mcp.start()
    except FileNotFoundError:
        print("\n[ERROR] Cannot find 'node'. Is Node.js installed?")
        print("        Also check that lpi-developer-kit is built: npm run build")
        return
    except Exception as e:
        print(f"\n[ERROR] Failed to start LPI server: {e}")
        print("        Make sure lpi-developer-kit is one folder above this repo.")
        return

    data = {}

    # ── 8-step tool pipeline ─────────────────────────────────
    #
    # The tool selection and ORDER is deliberate:
    #   Steps 1-2  always run (baseline context)
    #   Step  3    title-boosted knowledge search
    #   Step  4    refined knowledge search (from step 3 findings)
    #   Steps 5-8  domain-routed (case studies, insights, phase detail)

    plan = [
        (1, "smile_overview",      {},                              "SMILE baseline — always first"),
        (2, "list_topics",         {},                              "Discover all KB topic areas"),
        (3, "query_knowledge",     {"query": boosted_q},           "Title-boosted search (egg #3)"),
        (4, None,                  None,                            None),  # filled after step 3
        (5, "get_case_studies",    {"query": case_q},              f"Case evidence for: {domain}"),
        (6, "get_insights",        {"scenario":
                                    f"hospital {domain} digital twin: {problem}"[:490]},
                                                                    "Scenario-specific advice"),
        (7, "smile_phase_detail",  {"phase": phase_focus},         f"Phase deep-dive for {domain}"),
        (8, "get_methodology_step",{"phase": "concurrent-engineering"},
                                                                    "Phase 2 MVT steps"),
    ]

    for step, tool, args, reason in plan:

        # Step 4: build refined query from what step 3 returned
        if step == 4:
            terms  = _refine_terms(data.get("kb1", ""), domain)
            q2     = f"hospital {domain} {terms} implementation digital twin"
            tool   = "query_knowledge"
            args   = {"query": q2}
            reason = f"Refined search using: {terms}"

        print(f"  [{step}/8] {tool}...", end=" ", flush=True)

        text, elapsed = mcp.call(tool, args)
        prov.record(step, tool, args, text, elapsed, reason)

        # Store results
        key = f"s{step}_{tool}"
        data[key] = text
        if step == 3:
            data["kb1"] = text   # alias for refinement

        ok = not text.startswith("[ERROR]")
        mark = "[connected]" if ok else "[fetch error]"
        print(f"{mark} {len(text)} chars  [Time]{elapsed:.1f}s")

    mcp.stop()

    # ── Check if any tools actually returned data ────────────
    errors = [k for k, v in data.items() if v.startswith("[ERROR]")]
    if len(errors) == len(data):
        print("\n[ERROR] All 8 tool calls failed.")
        print("  Check: is the LPI server running? (node dist/src/index.js)")
        print("  Check: is lpi-developer-kit one folder ABOVE smile-hospital-agent?")
        return

    # ── Build synthesis prompt ───────────────────────────────
    def get(key: str, chars: int = 1600) -> str:
        return data.get(key, "(not available)")[:chars]

    prompt = f"""You are a SMILE Digital Twin advisor for hospital operations.
A hospital operations manager has this problem: {problem}

Use ONLY the sources below. Cite every factual claim as [Source N].

[Source 1] SMILE Overview:
{get("s1_smile_overview", 1600)}

[Source 2] Available KB Topics:
{get("s2_list_topics", 500)}

[Source 3] Knowledge Base — first search:
{get("s3_query_knowledge", 1400)}

[Source 4] Knowledge Base — refined search:
{get("s4_query_knowledge", 1000)}

[Source 5] Case Studies:
{get("s5_get_case_studies", 1400)}

[Source 6] Implementation Insights:
{get("s6_get_insights", 900)}

[Source 7] Phase Detail ({phase_focus}):
{get("s7_smile_phase_detail", 900)}

[Source 8] Phase 2 Steps:
{get("s8_get_methodology_step", 700)}

Write a SMILE implementation roadmap using this exact structure:

## Impact Statement
[What measurable success looks like — KPIs before any technology.
Apply Impact First, Data Last from Source 1.]

## Why SMILE
[2-3 sentences — why this approach, citing Source 1 and Source 6.]

## Phase 1 — Reality Emulation (Weeks 1-2)
What to map: [specific to this hospital problem, cite Source 7]
Key stakeholders: [who must be involved]
Deliverable: [concrete output]

## Phase 2 — Concurrent Engineering (Weeks 3-6)
MVT: [smallest twin that proves value, cite Source 8]
Virtual validation: [what to test before buying hardware]
Decision gate: [what result means the MVT worked]

## Phase 3 — Collective Intelligence (Months 2-4)
Ontology: [specific knowledge structure to build]
Case study parallel: [cite Source 5]
KPIs to hit: [measurable targets from Source 3 or 4]

## Phase 4+ Roadmap
[4 bullet points max. Each: what changes, what KPI improves, source.]

## Pitfalls to Avoid
[2 specific to this hospital domain, cite Source 3 or 6.]

## Sources
[Source N: tool_name — what it provided]
"""

    print(f"\nSynthesizing with Ollama ({model})...", end=" ", flush=True)

    t0 = time.time()
    answer = query_ollama(prompt, model)
    elapsed = time.time() - t0

    if False:
        pass
    else:
        print(f"done ({elapsed:.1f}s)\n")
    print(">>> Smile implementation roadmap")
    print()
    print(answer)
    print()

    # ── Provenance table ─────────────────────────────────────
    prov.print_table()

    # ── Easter eggs ──────────────────────────────────────────
    print("\n>>> Easter eggs found (all 3)")
    for k, v in EASTER_EGGS.items():
        print(f"  {k}: {v}")
    print()

# ═══════════════════════════════════════════════════════════════
# DEMO SCENARIOS
# ═══════════════════════════════════════════════════════════════

DEMO_PROBLEMS = [
    (
        "bed",
        "High bed occupancy variance — surgical ward permanently full at 98% while "
        "medical wards run at 60%. Discharge planning is entirely reactive with no "
        "real-time visibility of patient flow or predicted discharge dates.",
    ),
    (
        "equipment",
        "MRI and CT scanner downtime averaging 10 unplanned hours per week per machine. "
        "Maintenance is calendar-based. Engineers react to failures, not precursors. "
        "Cost per unplanned downtime hour is £3,000 in cancelled appointments.",
    ),
    (
        "energy",
        "Hospital energy costs increased 38% over 2 years. HVAC runs on fixed weekly "
        "schedules regardless of ward occupancy. No room-level energy visibility. "
        "Board has set a net-zero target for 2030 with no current baseline.",
    ),
]

# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    global OLLAMA_MODEL   # must be first line — before any reference to OLLAMA_MODEL

    parser = argparse.ArgumentParser(
        description="SMILE Digital Twin Advisor — Hospital Operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent.py --demo
  python agent.py --problem "High bed occupancy variance across wards"
  python agent.py --problem "MRI downtime 10h per week" --model llama3.2
        """,
    )
    parser.add_argument("--problem", "-p", default=None,
        help="Hospital operations problem to solve")
    parser.add_argument("--model", "-m", default=OLLAMA_MODEL,
        help=f"Ollama model (default: {OLLAMA_MODEL})")
    parser.add_argument("--demo", action="store_true",
        help="Run all 3 preset hospital scenarios")
    args = parser.parse_args()

    OLLAMA_MODEL = args.model

    if args.demo:
        for i, (domain, prob) in enumerate(DEMO_PROBLEMS, 1):
            print(f"\n--- Demo {i}/{len(DEMO_PROBLEMS)}: {domain} ---")
            run_advisor(prob, OLLAMA_MODEL)
            if i < len(DEMO_PROBLEMS):
                input("\n  Press Enter for next scenario...\n")

    elif args.problem:
        run_advisor(args.problem, OLLAMA_MODEL)

    else:
        print("\nSmile Hospital Twin")
        print("Enter your hospital problem (or 'demo'):\n")

        problem = input("Problem: ").strip()
        if not problem:
            parser.print_help()
            sys.exit(1)
        if problem.lower() == "demo":
            _, prob = DEMO_PROBLEMS[0]
            run_advisor(prob, OLLAMA_MODEL)
        else:
            run_advisor(problem, OLLAMA_MODEL)


if __name__ == "__main__":
    main()
