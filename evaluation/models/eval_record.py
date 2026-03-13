from dataclasses import dataclass


@dataclass
class EvalRecord:
    # Question
    question_id : str;  question    : str;  complexity : str
    category    : str;  expected    : str
    # Baseline
    bl_answer       : str   = "";  bl_time         : float = 0.0
    bl_score        : int   = -1;  bl_reasoning    : str   = ""
    bl_hallucination: str   = "";  bl_issues       : str   = ""
    # Single agent
    sa_answer       : str   = "";  sa_tools        : str   = ""
    sa_tool_count   : int   = 0;   sa_iters        : int   = 0
    sa_time         : float = 0.0; sa_score        : int   = -1
    sa_reasoning    : str   = "";  sa_hallucination: str   = ""
    sa_issues       : str   = ""
    # Multi agent
    ma_answer       : str   = "";  ma_tools        : str   = ""
    ma_tool_count   : int   = 0;   ma_time         : float = 0.0
    ma_confidence   : str   = "";  ma_critic_issues: int   = 0
    ma_agents       : str   = "";  ma_architecture : str   = ""
    ma_score        : int   = -1;  ma_reasoning    : str   = ""
    ma_hallucination: str   = "";  ma_issues       : str   = ""