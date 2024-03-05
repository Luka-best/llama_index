from llama_index.core.instrumentation.dispatcher import Dispatcher, Manager
from llama_index.core.instrumentation.event_handlers import NullEventHandler
from llama_index.core.instrumentation.span_handlers import NullSpanHandler

root_dispatcher: Dispatcher = Dispatcher(
    name="root",
    event_handlers=[NullEventHandler()],
    span_handler=NullSpanHandler(),
    propagate=False,
)

root_manager: Manager = Manager(root_dispatcher)


def get_dispatcher(name: str = "root") -> Dispatcher:
    """Module method that should be used for creating a new Dispatcher."""
    if name in root_manager.dispatchers:
        return root_manager.dispatchers[name]

    candidate_parent_name = ".".join(name.split(".")[:-1])
    if candidate_parent_name in root_manager.dispatchers:
        parent_name = candidate_parent_name
    else:
        parent_name = "root"

    return Dispatcher(
        name=name, root=root_dispatcher, parent_name=parent_name, manager=root_manager
    )
