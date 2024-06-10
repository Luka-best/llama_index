import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    TYPE_CHECKING,
)

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
    LLMMetadata,
    MessageRole,
)
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.callbacks import CallbackManager
from llama_index.core.constants import DEFAULT_TEMPERATURE
from llama_index.core.llms.callbacks import (
    llm_chat_callback,
    llm_completion_callback,
)
from llama_index.core.base.llms.generic_utils import (
    achat_to_completion_decorator,
    astream_chat_to_completion_decorator,
    chat_to_completion_decorator,
    stream_chat_to_completion_decorator,
)
from llama_index.core.llms.function_calling import FunctionCallingLLM, ToolSelection
from llama_index.core.types import BaseOutputParser, PydanticProgramMode
from llama_index.llms.bedrock_converse.utils import FUNCTION_CALLING_MODELS

if TYPE_CHECKING:
    from llama_index.core.chat_engine.types import AgentChatResponse
    from llama_index.core.tools.types import BaseTool


class BedrockConverse(FunctionCallingLLM):
    """
    Bedrock Converse LLM.

    Examples:
        `pip install llama-index-llms-bedrock-converse`

        ```python
        from llama_index.llms.bedrock_converse import BedrockConverse

        llm = BedrockConverse(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            aws_access_key_id="AWS Access Key ID to use",
            aws_secret_access_key="AWS Secret Access Key to use",
            aws_session_token="AWS Session Token to use",
            aws_region_name="AWS Region to use, eg. us-east-1",
        )

        resp = llm.complete("Paul Graham is ")
        print(resp)
        ```
    """

    model: str = Field(description="The modelId of the Bedrock model to use.")
    temperature: float = Field(
        default=DEFAULT_TEMPERATURE,
        description="The temperature to use for sampling.",
        gte=0.0,
        lte=1.0,
    )
    max_tokens: int = Field(description="The maximum number of tokens to generate.")
    context_size: int = Field("The maximum number of tokens available for input.")
    profile_name: Optional[str] = Field(
        description="The name of aws profile to use. If not given, then the default profile is used."
    )
    aws_access_key_id: Optional[str] = Field(
        description="AWS Access Key ID to use", exclude=True
    )
    aws_secret_access_key: Optional[str] = Field(
        description="AWS Secret Access Key to use", exclude=True
    )
    aws_session_token: Optional[str] = Field(
        description="AWS Session Token to use", exclude=True
    )
    region_name: Optional[str] = Field(
        description="AWS region name to use. Uses region configured in AWS CLI if not passed",
        exclude=True,
    )
    botocore_session: Optional[Any] = Field(
        description="Use this Botocore session instead of creating a new default one.",
        exclude=True,
    )
    botocore_config: Optional[Any] = Field(
        description="Custom configuration object to use instead of the default generated one.",
        exclude=True,
    )
    max_retries: int = Field(
        default=10, description="The maximum number of API retries.", gt=0
    )
    timeout: float = Field(
        default=60.0,
        description="The timeout for the Bedrock API request in seconds. It will be used for both connect and read timeouts.",
    )
    additional_kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs for the bedrock invokeModel request.",
    )

    _client: Any = PrivateAttr()
    _aclient: Any = PrivateAttr()

    def __init__(
        self,
        model: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: Optional[int] = 512,
        context_size: Optional[int] = None,
        profile_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        region_name: Optional[str] = None,
        botocore_session: Optional[Any] = None,
        client: Optional[Any] = None,
        timeout: Optional[float] = 60.0,
        max_retries: Optional[int] = 10,
        botocore_config: Optional[Any] = None,
        additional_kwargs: Optional[Dict[str, Any]] = None,
        callback_manager: Optional[CallbackManager] = None,
        system_prompt: Optional[str] = None,
        messages_to_prompt: Optional[Callable[[Sequence[ChatMessage]], str]] = None,
        completion_to_prompt: Optional[Callable[[str], str]] = None,
        pydantic_program_mode: PydanticProgramMode = PydanticProgramMode.DEFAULT,
        output_parser: Optional[BaseOutputParser] = None,
    ) -> None:
        additional_kwargs = additional_kwargs or {}
        callback_manager = callback_manager or CallbackManager([])

        if context_size is None and model not in FUNCTION_CALLING_MODELS:
            raise ValueError(
                "`context_size` argument not provided and"
                "model provided refers to a non-foundation model."
                " Please specify the context_size"
            )

        session_kwargs = {
            "profile_name": profile_name,
            "region_name": region_name,
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "aws_session_token": aws_session_token,
            "botocore_session": botocore_session,
        }
        config = None
        try:
            import boto3
            from botocore.config import Config

            config = (
                Config(
                    retries={"max_attempts": max_retries, "mode": "standard"},
                    connect_timeout=timeout,
                    read_timeout=timeout,
                )
                if botocore_config is None
                else botocore_config
            )
            session = boto3.Session(**session_kwargs)
        except ImportError:
            raise ImportError(
                "boto3 package not found, install with" "'pip install boto3'"
            )

        # Prior to general availability, custom boto3 wheel files were
        # distributed that used the bedrock service to invokeModel.
        # This check prevents any services still using those wheel files
        # from breaking
        if client is not None:
            self._client = client
        elif "bedrock-runtime" in session.get_available_services():
            self._client = session.client("bedrock-runtime", config=config)
        else:
            self._client = session.client("bedrock", config=config)

        super().__init__(
            temperature=temperature,
            max_tokens=max_tokens,
            additional_kwargs=additional_kwargs,
            timeout=timeout,
            max_retries=max_retries,
            model=model,
            callback_manager=callback_manager,
            system_prompt=system_prompt,
            messages_to_prompt=messages_to_prompt,
            completion_to_prompt=completion_to_prompt,
            pydantic_program_mode=pydantic_program_mode,
            output_parser=output_parser,
        )

    @classmethod
    def class_name(cls) -> str:
        return "Bedrock_Converse_LLM"

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_size,
            num_output=self.max_tokens,
            is_chat_model=True,
            model_name=self.model,
            is_function_calling_model=True,
        )

    # TODO might need to implement this
    # @property
    # def tokenizer(self) -> Tokenizer:
    #     return self._client.get_tokenizer()

    @property
    def _model_kwargs(self) -> Dict[str, Any]:
        base_kwargs = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        return {
            **base_kwargs,
            **self.additional_kwargs,
        }

    def _get_all_kwargs(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            **self._model_kwargs,
            **kwargs,
        }

    def _get_content_and_tool_calls(
        self, response: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        tool_calls = []
        content = ""
        for message in response["message"]:
            for content_block in message["content"]:
                if text := content_block.get("text", None):
                    content += text
                if tool_usage := content_block.get("toolUse", None):
                    tool_calls.append(tool_usage)

        return content, tool_calls

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        anthropic_messages, system_prompt = messages_to_anthropic_messages(messages)
        all_kwargs = self._get_all_kwargs(**kwargs)

        response = self._client.beta.tools.messages.create(
            messages=anthropic_messages,
            stream=False,
            system=system_prompt,
            **all_kwargs,
        )

        content, tool_calls = self._get_content_and_tool_calls(response)

        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=content,
                additional_kwargs={"tool_calls": tool_calls},
            ),
            raw=dict(response),
        )

    @llm_completion_callback()
    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        complete_fn = chat_to_completion_decorator(self.chat)
        return complete_fn(prompt, **kwargs)

    @llm_chat_callback()
    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        anthropic_messages, system_prompt = messages_to_anthropic_messages(messages)
        all_kwargs = self._get_all_kwargs(**kwargs)

        response = self._client.messages.create(
            messages=anthropic_messages, system=system_prompt, stream=True, **all_kwargs
        )

        def gen() -> ChatResponseGen:
            content = ""
            role = MessageRole.ASSISTANT
            for r in response:
                if isinstance(r, ContentBlockDeltaEvent):
                    content_delta = r.delta.text
                    content += content_delta
                    yield ChatResponse(
                        message=ChatMessage(role=role, content=content),
                        delta=content_delta,
                        raw=r,
                    )

        return gen()

    @llm_completion_callback()
    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseGen:
        stream_complete_fn = stream_chat_to_completion_decorator(self.stream_chat)
        return stream_complete_fn(prompt, **kwargs)

    @llm_chat_callback()
    async def achat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponse:
        anthropic_messages, system_prompt = messages_to_anthropic_messages(messages)
        all_kwargs = self._get_all_kwargs(**kwargs)

        response = await self._aclient.beta.tools.messages.create(
            messages=anthropic_messages,
            system=system_prompt,
            stream=False,
            **all_kwargs,
        )

        content, tool_calls = self._get_content_and_tool_calls(response)

        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=content,
                additional_kwargs={"tool_calls": tool_calls},
            ),
            raw=dict(response),
        )

    @llm_completion_callback()
    async def acomplete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        acomplete_fn = achat_to_completion_decorator(self.achat)
        return await acomplete_fn(prompt, **kwargs)

    @llm_chat_callback()
    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        anthropic_messages, system_prompt = messages_to_anthropic_messages(messages)
        all_kwargs = self._get_all_kwargs(**kwargs)

        response = await self._aclient.messages.create(
            messages=anthropic_messages, system=system_prompt, stream=True, **all_kwargs
        )

        async def gen() -> ChatResponseAsyncGen:
            content = ""
            role = MessageRole.ASSISTANT
            async for r in response:
                if isinstance(r, ContentBlockDeltaEvent):
                    content_delta = r.delta.text
                    content += content_delta
                    yield ChatResponse(
                        message=ChatMessage(role=role, content=content),
                        delta=content_delta,
                        raw=r,
                    )

        return gen()

    @llm_completion_callback()
    async def astream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseAsyncGen:
        astream_complete_fn = astream_chat_to_completion_decorator(self.astream_chat)
        return await astream_complete_fn(prompt, **kwargs)

    def chat_with_tools(
        self,
        tools: List["BaseTool"],
        user_msg: Optional[Union[str, ChatMessage]] = None,
        chat_history: Optional[List[ChatMessage]] = None,
        verbose: bool = False,
        allow_parallel_tool_calls: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Predict and call the tool."""
        chat_history = chat_history or []

        if isinstance(user_msg, str):
            user_msg = ChatMessage(role=MessageRole.USER, content=user_msg)
            chat_history.append(user_msg)

        tool_dicts = []
        for tool in tools:
            tool_dicts.append(
                {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "input_schema": tool.metadata.get_parameters_dict(),
                }
            )

        response = self.chat(chat_history, tools=tool_dicts, **kwargs)

        if not allow_parallel_tool_calls:
            force_single_tool_call(response)

        return response

    async def achat_with_tools(
        self,
        tools: List["BaseTool"],
        user_msg: Optional[Union[str, ChatMessage]] = None,
        chat_history: Optional[List[ChatMessage]] = None,
        verbose: bool = False,
        allow_parallel_tool_calls: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Predict and call the tool."""
        chat_history = chat_history or []

        if isinstance(user_msg, str):
            user_msg = ChatMessage(role=MessageRole.USER, content=user_msg)
            chat_history.append(user_msg)

        tool_dicts = []
        for tool in tools:
            tool_dicts.append(
                {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "input_schema": tool.metadata.get_parameters_dict(),
                }
            )

        response = await self.achat(chat_history, tools=tool_dicts, **kwargs)

        if not allow_parallel_tool_calls:
            force_single_tool_call(response)

        return response

    def get_tool_calls_from_response(
        self,
        response: "AgentChatResponse",
        error_on_no_tool_call: bool = True,
        **kwargs: Any,
    ) -> List[ToolSelection]:
        """Predict and call the tool."""
        tool_calls = response.message.additional_kwargs.get("tool_calls", [])

        if len(tool_calls) < 1:
            if error_on_no_tool_call:
                raise ValueError(
                    f"Expected at least one tool call, but got {len(tool_calls)} tool calls."
                )
            else:
                return []

        tool_selections = []
        for tool_call in tool_calls:
            if (
                "input" not in tool_call
                or "id" not in tool_call
                or "name" not in tool_call
            ):
                raise ValueError("Invalid tool call.")
            if tool_call["type"] != "tool_use":
                raise ValueError("Invalid tool type. Unsupported by Anthropic")
            argument_dict = (
                json.loads(tool_call["input"])
                if isinstance(tool_call["input"], str)
                else tool_call["input"]
            )

            tool_selections.append(
                ToolSelection(
                    tool_id=tool_call["id"],
                    tool_name=tool_call["name"],
                    tool_kwargs=argument_dict,
                )
            )

        return tool_selections
