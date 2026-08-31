import enum


class AutomationMode(str, enum.Enum):
    """Per content profile (spec section 52).

    MANUAL: every step is human-triggered; the autonomous cycle refuses to
    run at all.
    SEMI_AUTOMATIC: the autonomous cycle runs research through QA, then
    stops at AWAITING_APPROVAL/QA_FAILED for a human to approve/reject.
    AUTONOMOUS: the cycle also auto-approves and auto-publishes, but only
    when the QA gate passes (see can_auto_publish in
    app/services/autonomous.py) -- never unconditionally.
    """

    MANUAL = "manual"
    SEMI_AUTOMATIC = "semi_automatic"
    AUTONOMOUS = "autonomous"
