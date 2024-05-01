"""Tool-Interactive Reflection Agent Worker."""

import logging
import uuid
from typing import (
    Any,
    Callable,
    List,
    Optional,
    cast,
    Sequence,
    Protocol,
    runtime_checkable,
)

from llama_index.core.agent.types import (
    BaseAgentWorker,
    Task,
    TaskStep,
    TaskStepOutput,
)
from llama_index.core.bridge.pydantic import BaseModel, Field, PrivateAttr
from llama_index.core.agent.function_calling.step import FunctionCallingAgentWorker
from llama_index.core.callbacks import (
    CallbackManager,
    trace_method,
)
from llama_index.core.chat_engine.types import (
    AgentChatResponse,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.llms.llm import LLM
from llama_index.core.program.llm_prompt_program import BaseLLMFunctionProgram
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.objects.base import ObjectRetriever
from llama_index.core.tools import BaseTool, adapt_to_async_tool
from llama_index.core.tools import BaseTool, adapt_to_async_tool
from llama_index.core.tools.types import AsyncBaseTool
import llama_index.core.instrumentation as instrument

dispatcher = instrument.get_dispatcher(__name__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

CORRECT_PROMPT_TEMPLATE = """
You are responsible for correcting an input based on a provided critique.

Input:

{input_str}

Critique:

{critique}

Use the provided information to generate a corrected version of input.
"""

CORRECT_RESPONSE_FSTRING = "Here is a corrected version of the input.\n{correction}"

DEFAULT_MAX_ITERATIONS = 5


class Critique(BaseModel):
    """Data class for holding the critique response."""

    critique: str = Field(description="Provided critique.")
    is_sufficient: bool = Field(
        description="Whether or not the critique shows that the response is sufficient."
    )


class Correction(BaseModel):
    """Data class for holding the corrected input."""

    correction: str = Field(default_factory=str, description="Corrected input")


@runtime_checkable
class StoppingCallable(Protocol):
    def __call__(self, critique_str: str) -> bool:
        ...


class ToolInteractiveReflectionAgentWorker(BaseModel, BaseAgentWorker):
    """Tool-Interactive Reflection Agent Worker.

    This agent worker implements the CRITIC reflection framework.
    """

    callback_manager: CallbackManager = Field(default=CallbackManager([]))
    max_iterations: int = Field(default=DEFAULT_MAX_ITERATIONS)
    stopping_callable: Optional[StoppingCallable] = Field(
        default=None,
        description="Optional function that operates on critique string to see if no more corrections are needed.",
    )
    _critique_agent_worker: FunctionCallingAgentWorker = PrivateAttr()
    _critique_template: str = PrivateAttr()
    _correction_llm: LLM = PrivateAttr()
    _correction_program: BaseLLMFunctionProgram = PrivateAttr()
    _verbose: bool = PrivateAttr()
    _get_tools: Callable = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        critique_agent_worker: FunctionCallingAgentWorker,
        critique_template: str,
        tools: Sequence[BaseTool],
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        stopping_callable: Optional[StoppingCallable] = None,
        correction_llm: Optional[LLM] = None,
        callback_manager: Optional[CallbackManager] = None,
        verbose: bool = False,
        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
        **kwargs: Any,
    ) -> None:
        self._critique_agent_worker = critique_agent_worker
        self._critique_template = critique_template
        self._verbose = verbose
        self._correction_llm = correction_llm

        # define _correction_program
        try:
            from llama_index.program.openai import OpenAIPydanticProgram
        except ImportError:
            raise ImportError(
                "Missing OpenAIPydanticProgram. Please run `pip install llama-index-program-openai`."
            )
        self._correction_program = OpenAIPydanticProgram.from_defaults(
            Correction,
            prompt_template_str=CORRECT_PROMPT_TEMPLATE,
            llm=self._correction_llm,
        )

        # define _get_tools
        if len(tools) > 0 and tool_retriever is not None:
            raise ValueError("Cannot specify both tools and tool_retriever")
        elif len(tools) > 0:
            self._get_tools = lambda _: tools
        elif tool_retriever is not None:
            tool_retriever_c = cast(ObjectRetriever[BaseTool], tool_retriever)
            self._get_tools = lambda message: tool_retriever_c.retrieve(message)
        else:
            # no tools
            self._get_tools = lambda _: []

        super().__init__(
            callback_manager=callback_manager,
            max_iterations=max_iterations,
            stopping_callable=stopping_callable,
            **kwargs,
        )

    @classmethod
    def from_args(
        cls,
        critique_agent_worker: FunctionCallingAgentWorker,
        critique_template: str,
        correction_llm: Optional[LLM] = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        stopping_callable: Optional[StoppingCallable] = None,
        tools: Optional[Sequence[BaseTool]] = None,
        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
        callback_manager: Optional[CallbackManager] = None,
        verbose: bool = False,
        **kwargs: Any,
    ) -> "ToolInteractiveReflectionAgentWorker":
        """Convenience constructor method from set of of BaseTools (Optional)."""
        if correction_llm is None:
            try:
                from llama_index.llms.openai import OpenAI
            except ImportError:
                raise ImportError(
                    "Missing OpenAI LLMs. Please run `pip install llama-index-llms-openai`."
                )
            correction_llm = OpenAI(model="gpt-4-turbo-preview", temperature=0)

        return cls(
            critique_agent_worker=critique_agent_worker,
            critique_template=critique_template,
            correction_llm=correction_llm,
            tools=tools or [],
            tool_retriever=tool_retriever,
            max_iterations=max_iterations,
            stopping_callable=stopping_callable,
            callback_manager=callback_manager or CallbackManager([]),
            verbose=verbose,
            **kwargs,
        )

    def get_tools(self, input: str) -> List[AsyncBaseTool]:
        """Get tools."""
        return [adapt_to_async_tool(t) for t in self._get_tools(input)]

    def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:
        """Initialize step from task."""
        # temporary memory for new messages
        new_memory = ChatMemoryBuffer.from_defaults()

        # put current history in new memory
        messages = task.memory.get()
        for message in messages:
            new_memory.put(message)

        # initialize task state
        task_state = {
            "new_memory": new_memory,
            "sources": [],
        }
        task.extra_state.update(task_state)

        return TaskStep(
            task_id=task.task_id,
            step_id=str(uuid.uuid4()),
            input=task.input,
            step_state={"count": 0},
        )

    @dispatcher.span
    def _critique(self, input_str: str) -> AgentChatResponse:
        agent = self._critique_agent_worker.as_agent(verbose=True)
        critique = agent.chat(self._critique_template.format(input_str=input_str))
        if self._verbose:
            print(f"Critique: {critique.response}", flush=True)
        return critique

    @dispatcher.span
    def _correct(self, input_str: str, critique: str) -> ChatMessage:
        correction = self._correction_program(input_str=input_str, critique=critique)

        correct_response_str = CORRECT_RESPONSE_FSTRING.format(
            correction=correction.correction
        )
        if self._verbose:
            print(f"Correction: {correction.correction}", flush=True)
        return ChatMessage.from_str(correct_response_str, role="assistant")

    @dispatcher.span
    @trace_method("run_step")
    def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:
        """Run step."""
        state = step.step_state
        state["count"] += 1

        messages = task.extra_state["new_memory"].get()
        current_response = messages[-1].content
        # if reached max iters
        if state["count"] >= self.max_iterations:
            return AgentChatResponse(response=current_response), True

        # critique
        input_str = current_response.replace(
            "Here is a corrected version of the input.\n", ""
        )
        critique_response = self._critique(input_str=input_str)
        task.extra_state["sources"].extend(critique_response.sources)

        if self.stopping_callable:
            is_done = self.stopping_callable(critique_str=critique_response.response)

        critique_msg = ChatMessage(
            role=MessageRole.USER, content=critique_response.response
        )
        task.extra_state["new_memory"].put(critique_msg)

        # correct
        if is_done:
            agent_response = AgentChatResponse(
                response=current_response, sources=task.extra_state["sources"]
            )
            new_steps = []
        else:
            correct_msg = self._correct(
                input_str=input_str, critique=critique_response.response
            )
            agent_response = (
                AgentChatResponse(
                    response=str(correct_msg), sources=critique_response.sources
                ),
            )
            task.extra_state["new_memory"].put(correct_msg)

            if self.max_iterations == state["count"]:
                new_steps = []
            else:
                new_steps = [
                    step.get_next_step(
                        step_id=str(uuid.uuid4()),
                        # NOTE: input is unused
                        input=None,
                        step_state=state,
                    )
                ]

        return TaskStepOutput(
            output=agent_response,
            task_step=step,
            is_last=is_done | self.max_iterations == state["count"],
            next_steps=new_steps,
        )

    # Async Methods
    @dispatcher.span
    async def _acritique(self, input_str: str) -> AgentChatResponse:
        agent = self._critique_agent_worker.as_agent(verbose=True)
        critique = await agent.achat(
            self._critique_template.format(input_str=input_str)
        )
        if self._verbose:
            print(f"Critique: {critique.response}", flush=True)
        return critique

    @dispatcher.span
    async def _acorrect(self, input_str: str, critique: str) -> ChatMessage:
        correction = await self._correction_program.acall(
            input_str=input_str, critique=critique
        )

        correct_response_str = CORRECT_RESPONSE_FSTRING.format(
            correction=correction.correction
        )
        if self._verbose:
            print(f"Correction: {correction.correction}", flush=True)
        return ChatMessage.from_str(correct_response_str, role="assistant")

    @dispatcher.span
    @trace_method("run_step")
    async def arun_step(
        self, step: TaskStep, task: Task, **kwargs: Any
    ) -> TaskStepOutput:
        """Run step (async)."""
        state = step.step_state
        state["count"] += 1

        messages = task.extra_state["new_memory"].get()
        current_response = messages[-1].content
        # if reached max iters
        if state["count"] >= self.max_iterations:
            return AgentChatResponse(response=current_response), True

        # critique
        input_str = current_response.replace(
            "Here is a corrected version of the input.\n", ""
        )
        critique_response = await self._acritique(input_str=input_str)
        task.extra_state["sources"].extend(critique_response.sources)

        if self.stopping_callable:
            is_done = self.stopping_callable(critique_str=critique_response.response)

        critique_msg = ChatMessage(
            role=MessageRole.USER, content=critique_response.response
        )
        task.extra_state["new_memory"].put(critique_msg)

        # correct
        if is_done:
            agent_response = AgentChatResponse(
                response=current_response, sources=task.extra_state["sources"]
            )
            new_steps = []
        else:
            correct_msg = await self._acorrect(
                input_str=input_str, critique=critique_response.response
            )
            agent_response = (
                AgentChatResponse(
                    response=str(correct_msg), sources=critique_response.sources
                ),
            )
            task.extra_state["new_memory"].put(correct_msg)

            if self.max_iterations == state["count"]:
                new_steps = []
            else:
                new_steps = [
                    step.get_next_step(
                        step_id=str(uuid.uuid4()),
                        # NOTE: input is unused
                        input=None,
                        step_state=state,
                    )
                ]

        return TaskStepOutput(
            output=agent_response,
            task_step=step,
            is_last=is_done,
            next_steps=new_steps,
        )

    # Steam methods
    @dispatcher.span
    @trace_method("run_step")
    def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:
        """Run step (stream)."""
        raise NotImplementedError(
            "Stream not supported for tool-interactive reflection agent"
        )

    @dispatcher.span
    @trace_method("run_step")
    async def astream_step(
        self, step: TaskStep, task: Task, **kwargs: Any
    ) -> TaskStepOutput:
        """Run step (async stream)."""
        raise NotImplementedError(
            "Stream not supported for tool-interactive reflection agent"
        )

    def get_all_messages(self, task: Task) -> List[ChatMessage]:
        return (
            self.prefix_messages
            + task.memory.get()
            + task.extra_state["new_memory"].get_all()
        )

    def finalize_task(self, task: Task, **kwargs: Any) -> None:
        """Finalize task, after all the steps are completed."""
        # add new messages to memory
        task.memory.set(task.extra_state["new_memory"].get_all())
        # reset new memory
        task.extra_state["new_memory"].reset()
