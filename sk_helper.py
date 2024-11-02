from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import OpenAIChatPromptExecutionSettings
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from openai import AsyncOpenAI
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatHistory
CHAT_SERVICE_ID = 'chat'
HOST_NAME = 'your_chat_agent'
class SKHelper:
    def __init__(self, chat_profile, chat_settings):
        self.chat_profile = chat_profile
        self.chat_settings = chat_settings
        self.kernel = sk.Kernel()

    async def setup_chat_agent(self):
        #set up sk chat agent
        await self.add_chat_services()
        settings:OpenAIChatPromptExecutionSettings = self.kernel.get_prompt_execution_settings_from_service_id(CHAT_SERVICE_ID, ChatCompletionClientBase)
        settings.stream = True
        settings.temperature = self.chat_settings.get('temperature')
        instructions = self.chat_settings.get('instructions')
        chat_agent = ChatCompletionAgent(
            service_id=CHAT_SERVICE_ID,
            kernel=self.kernel,
            name=HOST_NAME,
            execution_settings=settings,
            instructions=instructions
        )
        self.agent = chat_agent
        pass

    async def invoke_chat_agent(self, chat_history):
        
        chat_history = ChatHistory.model_validate({'messages': chat_history})
        return self.agent.invoke_stream(chat_history)
        #invoke sk chat agent
        

    async def add_chat_services(self):

        #add necessary services to chat
        client = AsyncOpenAI()
        self.chat_service = OpenAIChatCompletion(
            service_id=CHAT_SERVICE_ID,
            ai_model_id=self.chat_settings.get('model'),
            async_client=client
        )
        self.kernel.add_service(self.chat_service, overwrite=True)
        
