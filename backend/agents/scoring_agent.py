
"""
agents/scoring_agent.py

CrewAI agent for explaining JobShield AI risk scores.
The actual score is calculated deterministically by score_risk().
"""

from crewai import Agent, Task
from crewai.tools import tool

from backend.tools.scoring.red_flag_scorer_tool import score_risk
from backend.utils.llm import get_llm


@tool("Calculate deterministic job fraud risk score")
def calculate_job_risk_score(findings_json: str) -> str:
    """Calculate a risk score from a JSON array of structured findings.

    Each finding should contain a rule_id and severity (high, medium, low).
    Optional fields include evidence and recommendation.
    """
    import json

    try:
        findings = json.loads(findings_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({
            "status": "invalid_input",
            "error": "Input must be a valid JSON array of findings",
        })

    result = score_risk(findings)
    return json.dumps(result, ensure_ascii=False)


def create_scoring_agent() -> Agent:
    """Create the risk-scoring explanation agent."""
    return Agent(
        role="Job Risk Assessment Analyst",
        goal=(
            "Explain risk scores and their supporting evidence accurately, "
            "without treating a score as definitive proof of fraud."
        ),
        backstory=(
            "You interpret deterministic risk-scoring results. The scoring "
            "tool is the authority for numeric scores and risk levels. "
            "You never change the returned score, invent findings, or treat "
            "missing evidence and tool failures as fraud indicators."
        ),
        tools=[calculate_job_risk_score],
        llm=get_llm(temperature=0.1),
        verbose=True,
        allow_delegation=False,
    )


def create_scoring_task(agent: Agent, findings: list[dict]) -> Task:
    """Create a task to score and explain structured findings."""
    import json

    findings_json = json.dumps(findings, ensure_ascii=False)

    return Task(
        description=(
            "Calculate and explain the risk associated with these findings. "
            "Pass the exact findings to the deterministic scoring tool. "
            "Preserve the tool's numeric score and risk level exactly. "
            "Do not add findings or count tool/API errors as risk indicators.\n\n"
            f"Findings JSON:\n{findings_json}"
        ),
        expected_output=(
            "The deterministic risk score, risk level, findings considered, "
            "points assigned, ignored findings, and the scoring disclaimer. "
            "The numeric result must match the tool output exactly."
        ),
        agent=agent,
    )
