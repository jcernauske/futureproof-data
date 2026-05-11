# FutureProof

### **An RPG-style career engine for the "17-year-old planning for college in the middle of AI-transformation"—powered by Gemma 4, grounded in federal data, and built to run 100% offline.**

------

## **The Problem: The "45-Minute" Trap**

The American School Counselor Association recommends a 250:1 student-to-counselor ratio. In many states, that number triples. The result? **The average public school student receives just 45 minutes of college guidance over their entire four-year high school career.** In those 45 minutes, a 17-year-old is expected to make a $100,000 decision.

A private-school senior buys their way out of this trap with a $400-an-hour counselor. A first-generation applicant gets a marketing pamphlet. The pamphlet shows graduation gowns; it does not show **AI automation exposure**, **wage ceilings**, or **debt-to-earnings ratios**.

## **The Solution: FutureProof**

FutureProof fills the gap between the pamphlet and the private counselor. It translates dense federal labor data into the visual language of the RPGs and strategy games students already master.

It replaces "brochure vibes" with a data-honest gauntlet. A student types a major, faces five "Boss Fights," and walks away with a ultra-specific questions to ask college admissions.

**Not a dream. A plan.**

------

## 🛠 Principles

FutureProof is a **grounded system**, not a chatbot. We split the labor between deterministic logic and generative reasoning to trend hallucination on high-stakes stats to 0%.

| **Task**                     | **Engine**             | **The "Handshake"**                                          |
| ---------------------------- | ---------------------- | ------------------------------------------------------------ |
| **Scoring (ERN, ROI, etc.)** | **DuckDB (Gold Zone)** | Every stat is pulled from a governed local database. **Gemma cannot "invent" a salary.** |
| **Intent Resolution**        | **Gemma 4**            | Maps messy text (e.g., *"I want to work with music but make money"*) to the correct federal CIP/SOC codes. |
| **The "Reroll"**             | **Gemma 4**            | Narrates how adding a specific skill (e.g., *"Spanish Fluency"*) flips a Boss Fight from **LOSE** to **DRAW**. |
| **The Receipts**             | **System-Wide**        | Every number in the UI has a "Receipt" link showing how the numbers were derived. |

------

## 🛠 Technical Specifications & Architecture

To ensure the **Advisory Equity** mission is met with **Ground Truth** accuracy, FutureProof utilizes a hybrid deterministic-generative architecture. This bypasses the "Black Box" hallucination risks common in standard educational AI.

### **1. The Sovereign Data Lake (Ground Truth)**

- **Engine:** Local **DuckDB** instance running **Gold Zone** labor statistics.
- **Data Source:** Integration of Federal labor data, wage-growth curves, and regional cost-of-living indices.
- **Deterministic Visualization:** The **Build Stat Pentagon** and **Future Map** nodes are rendered directly from database queries, ensuring the UI reflects reality, not model "vibes."

### **2. Reasoning Engine (Gemma 4)**

- **Models Supported:** * **Cloud Mode:** `Gemma-2-27b` via OpenRouter (High-fidelity cross-domain reasoning).
  - **Local Mode:** `Gemma-2-4b` (quantized) via **Ollama** (Privacy-first, zero-cost inference).
- **Native Function Calling:** FutureProof utilizes Gemma’s native tool-use capabilities to trigger database lookups, PDF generation, and "Boss Fight" logic based on real-time user state.
- **Context Management:** Leverages the 128k context window to maintain a "Long-Memory" career profile, allowing for deep comparative analysis between multiple career builds.

### **3. Privacy & Digital Equity Protocol**

- **Offline-First:** Toggleable environment configuration for 100% air-gapped operation.
- **Zero-Harvesting:** All PII (Personal Identifiable Information) remains in the local browser state or the local LLM instance.
- **Inference Parity:** The "Quiet Defiance" logic is maintained across both 27b and 4b scales, ensuring a student’s location or internet speed doesn't dictate the quality of their advice.

### **4. Tech Stack**

- **Frontend:** Vite + React + Tailwind (Minimalist/Functional Design).
- **Data Visualization:** D3.js (Future Map) and SVG-based radar plotting.
- **Backend Inference:** Ollama API / OpenRouter SDK.

## ✨ Features

- **The Five-Stat Pentagon:** Computed from College Scorecard, BLS, O*NET, and a three-signal AI-exposure composite.
  - **ERN** (Earning Power) | **ROI** (Payback) | **RES** (AI Resilience) | **GRW** (Growth) | **AURA** (Brand)
- **The Gauntlet:** Five RPG-style boss fights—Fight AI, Fight Loans, Fight the Market, Fight Burnout, Fight the Ceiling.
- **Structural Honesty:** No fake trophies. If the data shows a path is risky, you see a **LOSE** state. You win through "Skills" and "Rerolls."
- **The Counselor Script:** Generates a lightweight PDF export. The student brings this to the admissions office to ask: *"Your brochure says X, but the federal data says my ROI is a DRAW. How does your curriculum fix this?"*
- **100% Offline:** Ships with a 50MB DuckDB Gold zone. Run it in a school lab with the Wi-Fi off.

------

## 🚀 Quickstart (Local-First)

Total setup time is roughly 5 minutes (plus model download).

### Prerequisites

- **Ollama** running locally (`localhost:11434`)
- **Python 3.11+** and **Node.js 20+**
- **8GB RAM Minimum**

### 1. Pull the Model

Bash

```
# This is the effective 4.5B variant optimized for school-owned laptops
ollama pull gemma4:e4b
```

### 2. Install & Run

Bash

```
git clone https://github.com/jcernauske/futureproof.git
cd futureproof

# Install Pipeline & Backend
uv sync
( cd backend && pip install -e "." && playwright install chromium )

# Start Services
# Terminal A: Backend
( cd backend && python -m uvicorn app.main:app )

# Terminal B: Frontend
( cd frontend && npm install && npm run dev )
```

Visit `http://localhost:5173`. **Turn off your Wi-Fi to verify the local-first "Handshake."**

------

## 📊 Methodology: Data-Honest Scoring

FutureProof doesn't sell "Victory." We use a conservative **15-year ROI window** to reflect the reality of modern loan repayment.

$$ROI = \frac{\sum_{t=1}^{15} (MedianSalary \times 1.03^t)}{4 \times StickerPrice}$$

- **Gold Zone Data:** We ship the pre-processed Gold tables in `/data`. No scraping or API keys required for the judge to verify scores.
- **AI Resilience (RES):** A three-signal composite blending Karpathy’s Index, the Anthropic Economic Index, and a Gemma-rescored signal.

------

## 🤖 Why Gemma 4?

Gemma 4 is the "Reasoning Bridge" across five fragmented federal taxonomies that were never designed to fit together.

- **Function Calling:** Gemma calls ten governed MCP-style tools to fetch school and career data.
- **Structured JSON:** Ensures every "Skill" and "Reroll" narrated by Gemma is product-safe and testable.
- **Digital Equity:** By supporting the `gemma4:e4b` variant on Ollama, we turn inference from a metered cloud bill into a fixed local hardware cost.

------

## 🛠 Technical Depth & Reproducibility

- **Grounded Reasoning:** Gemma explains scores; it does not invent them.
- **Observability:** All local Gemma calls are logged in the backend for judge inspection.
- **Hardware Compatibility:**
  - **M2 Mac:** 14 tok/s (Fast)
  - **Old Windows Laptop (No GPU):** 3-4 tok/s (Functional)

------

## ⚖️ Safety & Responsible AI

- **Not Financial Advice:** FutureProof is a career exploration tool, not a substitute for a licensed counselor.
- **Privacy:** No login. No PII. No tracking. Running via Ollama ensures student data never leaves the building.

------

**Team:** Jeff Cernauske | **Tracks:** Main, Future of Education, Digital Equity, Ollama Special Track.