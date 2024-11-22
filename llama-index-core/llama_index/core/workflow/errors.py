class WorkflowValidationError(Exception):
    pass


class WorkflowTimeoutError(Exception):
    pass


class WorkflowRuntimeError(Exception):
    pass


class WorkflowDone(Exception):
    pass


class WorkflowCancelledByUser(Exception):
    pass


class RunIdMismatchError(Exception):
    pass


class MissingWorkflowRunIdError(Exception):
    pass
