class WorkflowError(Exception):
    """Base exception for workflow state machine violations."""
    pass

class WorkflowTransitionError(WorkflowError):
    """Raised when an invalid status transition is requested."""
    pass

class UnauthorizedWorkflowActionError(WorkflowError):
    """Raised when an actor lacks authority for a state transition."""
    pass

class CoordinationConflictWarning(WorkflowError):
    """Advisory warning when a unilateral action conflicts with an active joint coordination."""
    pass
