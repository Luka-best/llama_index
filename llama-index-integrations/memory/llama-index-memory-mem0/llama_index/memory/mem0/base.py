from typing import Dict, List, Optional, Union, Any
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.memory.types import BaseMemory
from llama_index.memory.mem0.utils import convert_memory_to_system_message
from mem0 import MemoryClient, Memory
from pydantic import BaseModel, Field, ValidationError, model_validator, SerializeAsAny, PrivateAttr
from llama_index.core.base.llms.types import ChatMessage, MessageRole

class BaseMem0(BaseMemory):
    """Base class for Mem0"""
    _client: Optional[Union[MemoryClient, Memory]] = PrivateAttr(default=None)

    class Config:
        arbitrary_types_allowed = True 

    def __init__(self, **data):
        super().__init__(**data)
        self._client = data.get('client')

    #TODO: Return type
    def add(self, messages: Union[str, List[Dict[str, str]]], **kwargs) -> Optional[Any]:
        if self._client is None:
            raise ValueError("Client is not initialized")
        response = self._client.add(messages=messages, **kwargs)
        return response
    
    #TODO: Return type
    def search(self, query: str, **kwargs) -> Optional[Any]:
        if self._client is None:
            raise ValueError("Client is not initialized")
        response = self._client.search(query=query, **kwargs)
        return response
    
    #TODO: Add more apis from client

class Mem0Context(BaseModel):
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None

    @model_validator(mode="after")
    def check_at_least_one_assigned(cls, values):
        if not any(getattr(values, field) for field in ['user_id', 'agent_id', 'run_id']):
            raise ValueError("At least one of 'user_id', 'agent_id', or 'run_id' must be assigned.")
        return values
    
    def get_context(self) -> Dict[str, Optional[str]]:
        return {
            key: value for key, value in self.__dict__.items()
            if value is not None
        }
    
    class Config:
        validate_assignment = True

class Mem0ComposableMemory(BaseMem0):
    chat_history: SerializeAsAny[BaseMemory] = Field(description="Primary memory source for chat agent.")
    _context: Optional[Mem0Context] = PrivateAttr(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self._context = data.get('context')

    @classmethod
    def class_name(cls) -> str:
        """Class name."""
        return "Mem0ComposableMemory"
    
    #TODO: Not functional yet. 
    @classmethod 
    def from_defaults(cls, **kwargs: Any) -> "Mem0ComposableMemory":
        raise NotImplementedError("Use either from_client or from_config")
    
    @classmethod
    def from_client(
        cls,
        context_dict: Dict[str, Any],
        chat_history: Optional[BaseMemory] = None,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        **kwargs: Any,
    ) :
        if kwargs:
            raise ValueError(f"Unexpected kwargs: {kwargs}")
        
        chat_history = chat_history or ChatMemoryBuffer.from_defaults()

        try:
            context = Mem0Context(**context_dict)
        except ValidationError as e:
            raise ValidationError(f"Context validation error: {e}")

        client = MemoryClient(api_key=api_key, host=host, organization=organization, project=project)
        return cls(
            chat_history=chat_history, 
            context=context, 
            client=client
        )
    
    @classmethod
    def from_config(
        cls,
        context_dict: Dict[str, Any], 
        confif_dict: Dict[str, Any],
        chat_history: Optional[BaseMemory] = None,
        **kwargs: Any,
    ):
        if kwargs:
            raise ValueError(f"Unexpected kwargs: {kwargs}")

        chat_history = chat_history or ChatMemoryBuffer.from_defaults()

        try:
            context = Mem0Context(**context_dict)
        except Exception as e:
            raise ValidationError(f"Context validation error: {e}")

        client = Memory.from_config(config_dict=confif_dict)
        return cls(
            chat_history=chat_history, 
            context=context, 
            client=client
        )
    
    def get(self, input: Optional[str] = None, **kwargs: Any) -> List[ChatMessage]:
        messages = self.chat_history.get(input=input, **kwargs)
        if input is None:
            # Iterate through messages from last to first
            for message in reversed(messages):
                if message.role == MessageRole.USER:
                    _recent_user_message = message
                    break
            else:
                raise ValueError("No input and user message found in chat history.")
            input = str(_recent_user_message.content)

        #TODO: Add support for more kwargs, for api and oss
        search_results = self.search(query=input, **self._context.get_context())
        if isinstance(self._client, Memory):
            search_results = search_results['results']
        system_message = convert_memory_to_system_message(search_results)
        
        # If system message is present
        if len(messages) > 0 and messages[0].role == MessageRole.SYSTEM:
            #TODO: What if users provide system_message or prefix_message, or system_message in chat_history becaomes old enough?
            assert messages[0].content is not None
            system_message = convert_memory_to_system_message(response=search_results, existing_system_message=messages[0])
        messages.insert(0, system_message)
        return messages

    def get_all(self) -> List[ChatMessage]:
        """Returns all chat history."""
        return self.chat_history.get_all()

    def _add_user_msg_to_memory(self, message: ChatMessage) -> None:
        """Only add new user message to client memory."""
        if message.role == MessageRole.USER:
            self.add(
                messages=str(message.content),
                **self._context.get_context()
            )

    def put(self, message: ChatMessage) -> None:
        """Add message to chat history. Add user message to client memory."""
        self._add_user_msg_to_memory(message)
        self.chat_history.put(message)

    def set(self, messages: List[ChatMessage]) -> None:
        """Set chat history. Add new user message to client memory."""
        initial_chat_len = len(self.chat_history.get_all())
        #Insert only new chat messages
        for message in messages[initial_chat_len:]:
            self._add_user_msg_to_memory(message)
        self.chat_history.set(messages)

    def reset(self) -> None:
        """Only reset chat history"""
        #TODO: Context specific reset is missing in client.
        self.chat_history.reset()




    

    
    