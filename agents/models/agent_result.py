from dataclasses import dataclass, field


@dataclass
class AgentResult:

    agent_name: str
    answer: str

    tools_called: list = field(default_factory=list)

    raw_data: dict = field(default_factory=dict)

    confidence: float = 0.0

    issues_found: list = field(default_factory=list)

    reasoning: str = ""
