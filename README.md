
# JobShield AI 🛡️

**An AI-Powered Multi-Agent System for Detecting Fraudulent Job Postings**

JobShield AI is an intelligent job verification platform designed to identify potentially fraudulent job opportunities by analyzing company information, online presence, and recruitment communications.

It combines deterministic risk scoring with a CrewAI-powered multi-agent investigation system to provide evidence-based assessments and help job seekers make informed decisions.

---

## 🚀 Key Features

- **Company Verification:** Checks company registration information through the configured MCA/data.gov.in integration.
- **Website Investigation:** Examines company websites and their online presence.
- **Job Offer Analysis:** Detects suspicious language, misleading recruitment claims, and upfront payment requests.
- **Deterministic Risk Scoring:** Calculates the official risk score using predefined rules.
- **Multi-Agent Investigation:** Uses specialized AI agents to investigate and interpret collected evidence.
- **Fallback Verification:** Maintains core verification functionality even when AI agents or LLM providers fail.
- **Investigation Reports:** Generates explanations of findings and supporting evidence.
- **Database Integration:** Stores verification results using MongoDB.
- **Interactive Frontend:** Provides a React-based interface for submitting and viewing verification results.

---

## 🧠 System Architecture

JobShield AI uses two complementary layers:

1. **Deterministic Verification Layer**
2. **AI Multi-Agent Investigation Layer**

### 1. Deterministic Verification Layer

This layer is responsible for collecting evidence and calculating the official risk score.

It performs:

- Company registry lookups.
- Website and online-presence checks.
- Job offer and communication analysis.
- Rule-based red-flag detection.
- Risk score calculation.

The deterministic scoring engine ensures that the official risk score does not depend on an AI-generated opinion.

### 2. Multi-Agent Investigation Layer

The multi-agent system uses specialized agents to investigate different aspects of a job opportunity.

| Agent | Responsibility |
|---|---|
| Manager Agent | Coordinates the investigation and consolidates findings. |
| Registry Agent | Analyzes company registration evidence. |
| Web Presence Agent | Investigates the company's website and online presence. |
| Communication Agent | Analyzes job offers and recruitment messages for suspicious indicators. |
| Scoring Agent | Helps interpret and explain the detected findings. |

The deterministic scoring engine remains authoritative for the official risk score.

### Investigation Workflow

```text
             Job Offer / Company Details
                         |
                         v
                 Evidence Collection
                 /        |        \
                v         v         v
           Registry    Website   Communication
             Check      Check      Analysis
                \         |         /
                 \        |        /
                  v       v       v
               Deterministic Scoring
                         |
                         v
                Multi-Agent Investigation
                         |
                         v
                Consolidated AI Report
                         |
                         v
                 Verification Result
```

---

## 🔄 Fallback Mechanism

A major reliability feature of JobShield AI is its deterministic fallback mechanism.

Multi-agent systems depend on external LLM providers and orchestration frameworks. These services can fail due to API limits, network problems, timeouts, or provider outages.

Instead of allowing these failures to stop the entire verification process, JobShield AI can execute its core verification pipeline independently.

The fallback mechanism uses:

- Evidence collection tools.
- Company registry checks.
- Website investigation.
- Communication analysis.
- Deterministic risk scoring.

The function `run_verification()` in `backend/agents/coordinator.py` provides a way to execute this verification path without depending on the CrewAI multi-agent orchestration.

### Why Both Layers?

| Multi-Agent System | Fallback Mechanism |
|---|---|
| Provides contextual investigation. | Provides core verification functionality. |
| Interprets and connects evidence. | Collects evidence and applies predefined rules. |
| Generates detailed investigation reports. | Returns deterministic findings and risk scores. |
| Depends on AI orchestration and LLM availability. | Does not depend on the multi-agent workflow. |

This architecture improves reliability while retaining the benefits of AI-powered investigation.

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, FastAPI |
| AI Framework | CrewAI |
| LLM Providers | OpenRouter, Google Gemini |
| Database | MongoDB |
| Frontend | React, Vite |
| Company Verification | MCA / data.gov.in integration |
| Website Investigation | Web Search, WHOIS |
| Testing | Pytest |

---

## 📁 Project Structure

```text
jobshield-ai/
│
├── backend/
│   ├── agents/
│   │   ├── coordinator.py
│   │   ├── manager_agent.py
│   │   ├── registry_agent.py
│   │   ├── web_presence_agent.py
│   │   ├── communication_agent.py
│   │   └── scoring_agent.py
│   │
│   ├── crews/
│   │   ├── verification_crew.py
│   │   └── hierarchical_crew.py
│   │
│   ├── tools/
│   │   ├── registry/
│   │   │   └── mca_lookup_tool.py
│   │   └── web_presence/
│   │       └── search_presence_tool.py
│   │
│   ├── api/
│   │   └── main.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   └── tests/
│
├── frontend/
│   └── React Application
│
├── .env
├── requirements.txt
└── README.md
```

---

## ⚙️ Getting Started

### Prerequisites

Make sure you have installed:

- Python 3.12
- Node.js and npm
- MongoDB or MongoDB Atlas
- Required API keys for the configured LLM and external services

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd jobshield-ai
```

### 2. Create a Virtual Environment

```bash
python3.12 -m venv .venv
```

Activate it:

**macOS / Linux**

```bash
source .venv/bin/activate
```

### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

If your requirements file is inside `backend/`, run:

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the appropriate project directory.

Configure the required credentials and settings, including:

```env
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

MONGO_URI=your_mongodb_connection_string

DATA_GOV_API_KEY=your_data_gov_api_key
DATA_GOV_BASE_URL=your_data_gov_api_endpoint
MCA_RESOURCE_IDS=your_resource_ids
```

Additional configuration may be required depending on the enabled integrations.

**Important:** Never commit your `.env` file or expose API keys publicly.

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

## ▶️ Running the Application

### Start the Backend

From the project root:

```bash
PYTHONPATH=backend uvicorn api.main:app --reload
```

The backend will typically be available at:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

### Start the Frontend

Open another terminal:

```bash
cd frontend
npm run dev
```

Open the local URL provided by Vite.

---

## 🧪 Running the Fallback Verification Independently

JobShield AI allows you to execute the deterministic verification pipeline without running the multi-agent orchestration.

From the project root:

```bash
PYTHONPATH=backend python
```

Then:

```python
from agents.coordinator import run_verification

result = run_verification(
    company_name="Example Company",
    website="https://example.com",
    offer_text="Paste the job offer or recruitment message here."
)

print(result)
```

Check `backend/agents/coordinator.py` for the exact function signature and required parameters in your current version.

This directly executes `run_verification()` and does not require the frontend.

---

## 🧪 Running Tests

Run the backend test suite from the project root:

```bash
PYTHONPATH=backend python -m pytest -v backend/tests/
```

To run an individual test file:

```bash
PYTHONPATH=backend python -m pytest -v backend/tests/test_verification_crew.py
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Checks backend availability. |
| POST | `/api/verify` | Submits a job opportunity for verification. |

For detailed API documentation, access:

```text
http://127.0.0.1:8000/docs
```

---

## 🔐 Risk Scoring and Reliability

JobShield AI follows several important principles:

- The official risk score is calculated using deterministic rules.
- AI-generated reports cannot independently modify the official score.
- API failures must not automatically increase the risk score.
- A company not being found in a registry is not proof of fraud.
- A registry record does not automatically prove that the returned legal entity is associated with the recruiter or brand in a job offer.
- Investigation findings should be supported by actual evidence.

---

## ⚠️ Limitations

- External APIs and LLM providers may experience outages or rate limits.
- Registry data may be incomplete or unavailable.
- Similar company names may belong to different legal entities.
- AI-generated reports may contain errors and should be checked against the underlying evidence.
- Risk scores depend on the configured rules and available evidence.

JobShield AI is intended to assist with job-opportunity assessment, not replace independent verification or human judgment.

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a feature branch.
3. Implement your changes.
4. Add or update tests.
5. Submit a pull request.

---

## 📌 Project Goal

**JobShield AI — Helping job seekers identify suspicious opportunities through evidence-based verification and AI-powered investigation.**
