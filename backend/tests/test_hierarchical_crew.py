
from crewai import Task

from crews.hierarchical_crew import create_hierarchical_crew


def main() -> None:
    """Run a real CrewAI hierarchical investigation smoke test."""
    crew = create_hierarchical_crew()

    task = Task(
        description=(
            "Investigate the following sample case using the appropriate "
            "specialists. Review the evidence and decide whether additional "
            "investigation is necessary.\n\n"
            "{investigation_input}\n\n"
            "Important rules:\n"
            "- Delegate only when a specialist can provide useful evidence.\n"
            "- Do not treat missing company records as proof of fraud.\n"
            "- Do not invent tool results or company matches.\n"
            "- The deterministic finding UPFRONT_PAYMENT has high severity.\n"
            "- No numeric risk score was supplied. Do not invent one.\n"
            "- Distinguish verified evidence from uncertainty."
        ),
        expected_output=(
            "An evidence-based report containing the investigation summary, "
            "specialists consulted, evidence obtained, existing findings, "
            "missing information, and practical recommendations."
        ),
    )

    # Replace the default task with this smoke-test task.
    crew.tasks = [task]

    investigation_input = (
        "Sample case for testing manager delegation.\n"
        "Company: Example Technologies Pvt Ltd\n"
        "CIN: Not provided\n"
        "Website: Not provided\n"
        "Offer text: Pay a refundable registration fee before an interview.\n"
        "Initial deterministic finding: UPFRONT_PAYMENT (high severity).\n"
        "Numeric risk score: Not supplied.\n"
        "No real company lookup results have been supplied."
    )

    result = crew.kickoff(
        inputs={"investigation_input": investigation_input}
    )

    print("\n========== HIERARCHICAL CREW RESULT ==========")
    print(result)


if __name__ == "__main__":
    main()
