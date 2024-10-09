from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union
from zhipuai import ZhipuAI as ZhipuAIClient
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    ChatResponseAsyncGen,
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
    LLMMetadata,
    MessageRole,
)
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.constants import DEFAULT_CONTEXT_WINDOW, DEFAULT_NUM_OUTPUTS
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.base.llms.generic_utils import (
    chat_to_completion_decorator,
    achat_to_completion_decorator,
    stream_chat_to_completion_decorator,
    astream_chat_to_completion_decorator,
)
from llama_index.core.tools import ToolSelection

if TYPE_CHECKING:
    from llama_index.core.tools.types import BaseTool

DEFAULT_REQUEST_TIMEOUT = 30.0
SUCCESS = "SUCCESS"
FAILED = "FAILED"


def force_single_tool_call(response: ChatResponse) -> None:
    tool_calls = response.message.additional_kwargs.get("tool_calls", [])
    if len(tool_calls) > 1:
        response.message.additional_kwargs["tool_calls"] = [tool_calls[0]]


def async_llm_generate(item):
    try:
        return next(item)
    except StopIteration:
        return None


class ZhipuAI(FunctionCallingLLM):
    """ZhipuAI LLM.

    Visit https://open.bigmodel.cn to get more information about ZhipuAI.

    Examples:
        `pip install llama-index-llms-zhipuai`

        ```python
        from llama_index.llms.zhipuai import zhipuai

        llm = ZhipuAI(model="glm-4", request_timeout=60.0)

        response = llm.complete("What is the capital of France?")
        print(response)
        ```
    """

    model: str = Field(description="The ZhipuAI model to use.")
    api_key: Optional[str] = Field(
        default=None,
        description="The API key to use for the ZhipuAI API.",
    )
    temperature: float = Field(
        default=0.95,
        description="The temperature to use for sampling.",
        ge=0.0,
        le=1.0,
    )
    max_tokens: int = Field(
        default=1024,
        description="The maximum number of tokens for model output.",
        gt=0,
    )
    timeout: float = Field(
        default=DEFAULT_REQUEST_TIMEOUT,
        description="The timeout for making http request to ZhipuAI API server",
    )
    is_function_calling_model: bool = Field(
        default=True,
        description="Whether the model is a function calling model.",
    )
    _client: Optional[ZhipuAIClient] = PrivateAttr()

    def __init__(
        self,
        model: str,
        temperature: float = 0.95,
        max_tokens: int = 1024,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
        client: Optional[ZhipuAIClient] = None,
        is_function_calling_model: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            is_function_calling_model=is_function_calling_model,
            **kwargs,
        )

        self._client = client

    @classmethod
    def class_name(cls) -> str:
        return "ZhipuAI_llm"

    @property
    def metadata(self) -> LLMMetadata:
        """LLM metadata."""
        return LLMMetadata(
            context_window=self.context_window,
            num_output=DEFAULT_NUM_OUTPUTS,
            model_name=self.model,
            is_chat_model=True,
            is_function_calling_model=self.is_function_calling_model,
        )

    @property
    def client(self) -> ZhipuAIClient:
        if self._client is None:
            self._client = ZhipuAIClient(api_key=self.api_key)
        return self._client

    @property
    def _model_kwargs(self) -> Dict[str, Any]:
        base_kwargs = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        return base_kwargs

    def _convert_to_llm_messages(self, messages: Sequence[ChatMessage]) -> Dict:
        return [
            {
                "role": message.role.value,
                "content": message.content or "",
            }
            for message in messages
        ]

    def _prepare_chat_with_tools(
        self,
        tools: List["BaseTool"],
        user_msg: Optional[Union[str, ChatMessage]] = None,
        chat_history: Optional[List[ChatMessage]] = None,
        verbose: bool = False,
        allow_parallel_tool_calls: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        tool_specs = [
            tool.metadata.to_openai_tool(skip_length_check=True) for tool in tools
        ]

        if isinstance(user_msg, str):
            user_msg = ChatMessage(role=MessageRole.USER, content=user_msg)

        messages = chat_history or []
        if user_msg:
            messages.append(user_msg)

        return {
            "messages": messages,
            "tools": tool_specs or None,
        }

    def _validate_chat_with_tools_response(
        self,
        response: ChatResponse,
        tools: List["BaseTool"],
        allow_parallel_tool_calls: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Validate the response from chat_with_tools."""
        if not allow_parallel_tool_calls:
            force_single_tool_call(response)
        return response

    def get_tool_calls_from_response(
        self,
        response: "ChatResponse",
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
            return []

        tool_selections = []
        for tool_call in tool_calls:
            tool_selections.append(
                ToolSelection(
                    tool_id=tool_call["function"]["id"],
                    tool_name=tool_call["function"]["name"],
                    tool_kwargs=tool_call["function"]["arguments"],
                )
            )

        return tool_selections

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        messages_dict = self._convert_to_llm_messages(messages)
        raw_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages_dict,
            stream=False,
            tools=kwargs.get("tools", None),
            tool_choice=kwargs.get("tool_choice", None),
            timeout=self.timeout,
            extra_body=self._model_kwargs,
        )
        tool_calls = raw_response.choices[0].message.tool_calls or []
        return ChatResponse(
            message=ChatMessage(
                content=raw_response.choices[0].message.content,
                role=raw_response.choices[0].message.role,
                additional_kwargs={"tool_calls": tool_calls},
            ),
            raw=raw_response,
        )

    @llm_chat_callback()
    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        messages_dict = self._convert_to_llm_messages(messages)

        def gen() -> ChatResponseGen:
            raw_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_dict,
                stream=True,
                tools=kwargs.get("tools", None),
                tool_choice=kwargs.get("tool_choice", None),
                timeout=self.timeout,
                extra_body=self._model_kwargs,
            )
            response_txt = ""
            for chunk in raw_response:
                if chunk.choices[0].delta.content is None:
                    continue
                response_txt += chunk.choices[0].delta.content
                tool_calls = chunk.choices[0].delta.tool_calls
                yield ChatResponse(
                    message=ChatMessage(
                        content=response_txt,
                        role=chunk.choices[0].delta.role,
                        additional_kwargs={"tool_calls": tool_calls},
                    ),
                    delta=chunk.choices[0].delta.content,
                    raw=chunk,
                )

        return gen()

    @llm_chat_callback()
    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        messages_dict = self._convert_to_llm_messages(messages)

        async def gen() -> ChatResponseAsyncGen:
            raw_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_dict,
                stream=True,
                tools=kwargs.get("tools", None),
                tool_choice=kwargs.get("tool_choice", None),
                timeout=self.timeout,
                extra_body=self._model_kwargs,
            )
            response_txt = ""
            while True:
                chunk = await asyncio.to_thread(async_llm_generate, raw_response)
                if not chunk:
                    break
                if chunk.choices[0].delta.content is None:
                    continue
                response_txt += chunk.choices[0].delta.content
                tool_calls = chunk.choices[0].delta.tool_calls
                yield ChatResponse(
                    message=ChatMessage(
                        content=response_txt,
                        role=chunk.choices[0].delta.role,
                        additional_kwargs={"tool_calls": tool_calls},
                    ),
                    delta=chunk.choices[0].delta.content,
                    raw=chunk,
                )

        return gen()

    @llm_chat_callback()
    async def achat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        messages_dict = self._convert_to_llm_messages(messages)
        raw_response = self.client.chat.asyncCompletions.create(
            model=self.model,
            messages=messages_dict,
            tools=kwargs.get("tools", None),
            tool_choice=kwargs.get("tool_choice", None),
            timeout=self.timeout,
            extra_body=self._model_kwargs,
        )
        task_id = raw_response.id
        task_status = raw_response.task_status
        get_count = 0
        while task_status not in [SUCCESS, FAILED] and get_count < 40:
            task_result = self.client.chat.asyncCompletions.retrieve_completion_result(
                task_id
            )
            raw_response = task_result
            task_status = raw_response.task_status
            get_count += 1
            await asyncio.sleep(1)
        tool_calls = raw_response.choices[0].message.tool_calls or []
        return ChatResponse(
            message=ChatMessage(
                content=raw_response.choices[0].message.content,
                role=raw_response.choices[0].message.role,
                additional_kwargs={"tool_calls": tool_calls},
            ),
            raw=raw_response,
        )

    @llm_completion_callback()
    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        return chat_to_completion_decorator(self.chat)(prompt, **kwargs)

    @llm_completion_callback()
    async def acomplete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        return await achat_to_completion_decorator(self.achat)(prompt, **kwargs)

    @llm_completion_callback()
    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseGen:
        return stream_chat_to_completion_decorator(self.stream_chat)(prompt, **kwargs)

    @llm_completion_callback()
    async def astream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseAsyncGen:
        return await astream_chat_to_completion_decorator(self.astream_chat)(
            prompt, **kwargs
        )


llm = ZhipuAI(
    model="glm-4", api_key="4ac5cc2a83a729bce408b66085cd919a.llwq2XV8ongDR0IN"
)


import asyncio

# response_x = llm.complete("你是谁")
# print(response_x)
# response = asyncio.run(llm.acomplete("你是谁"))
# response = asyncio.run(llm.astream_complete("你是谁"))
# print(response)
message = [ChatMessage(content="who are you")]
# # print(message)
# # response = asyncio.run(llm.astream_chat(message))
# # print(type(response))


async def main():
    async for x in await llm.astream_chat(message):
        print(x)


asyncio.run(main())
