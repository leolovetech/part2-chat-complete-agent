import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.data.storage_clients.azure import AzureStorageClient
from dotenv import load_dotenv
import chainlit as cl
import os
load_dotenv()
from sk_helper import SKHelper
import logging as logger

storage_client = AzureStorageClient(account_url=os.getenv("AZURE_STORAGE_URL"), container=os.getenv("AZURE_STORAGE_CONTAINER_NAME"), credential=os.getenv("AZURE_STORAGE_KEY"))
cl_data._data_layer = SQLAlchemyDataLayer(conninfo=os.getenv("SQLALCHEMY_CONNECTION_STRING"), storage_provider=storage_client)




@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None


#start when loaded chat
@cl.on_chat_start
async def start():
    # AG_Helper(cl.user_session.get("chat_profile"), cl.user_session.get("chat_settings"))
    assert cl_data._data_layer is not None, "Data layer is not set"
    await load_chat_settings()
    await setup_sk_helper()

@cl.on_message
async def on_message(message: cl.Message):
    
    ai_message = await cl.Message(content="", author="assistant").send()
    await ai_message.send()

    sk_helper = cl.user_session.get("sk_helper") #type: SKHelper
    if not sk_helper:
        ai_message.content = "No chat agent setup"
        await ai_message.update()
        return
    chat_history = cl.chat_context.to_openai()
    
    if len(chat_history) > 1:
        chat_history.pop()
    async for chunk in await sk_helper.invoke_chat_agent(chat_history):
        await ai_message.stream_token(chunk.content if chunk.content is not None else "")
    await ai_message.update()


@cl.on_chat_resume
async def on_chat_resume():
    await load_chat_settings()
    await setup_sk_helper()
    logger.info(f"chat resumed: {cl.user_session.get('chat_settings')}")

@cl.on_chat_end
async def on_chat_end():
    pass

@cl.on_stop
async def on_stop():
    pass

@cl.set_chat_profiles
async def set_chat_profiles(current_user: cl.User):
    if current_user.metadata.get("role") == "admin":
        return [
            cl.ChatProfile(name="Admin", markdown_description="Admin profile", icon="👨‍💻"),
            cl.ChatProfile(name="User", markdown_description="User profile", icon="👤")
        ]
    else:
        return [
            cl.ChatProfile(name="User", markdown_description="User profile", icon="👤")
        ]
    

async def load_chat_settings():
    from chainlit.input_widget import TextInput, Select, Slider, Tags
    #todo load chat settings from db and set to user_session
    chat_settings = cl.user_session.get("chat_settings")
    logger.info(f"chat_settings: {chat_settings}")
    init_model = "gpt-4o"
    init_temperature = 0.7
    init_instructions = "You are a helpful bot"
    init_tags = []

    if chat_settings:
        init_model = chat_settings.get("model") if chat_settings.get("model") else "gpt-4o"
        init_temperature = chat_settings.get("temperature") if chat_settings.get("temperature") else 0.7
        init_instructions = chat_settings.get("instructions") if chat_settings.get("instructions") else "You are a helpful bot"
        init_tags = chat_settings.get("tags") if chat_settings.get("tags") else []

    settings = await cl.ChatSettings(
        [
            TextInput(
                id="instructions",
                label="Instructions",
                multiline=True,
                placeholder="Enter your instructions here",
                initial=init_instructions
            ),
            Select(
                id="model", 
                label="Model",
                initial_value=init_model,
                values=["gpt-4o", "gpt-4o-mini"]
            ),
            Slider(
                id="temperature",
                label="Temperature",
                initial=init_temperature,
                min=0.0,
                max=1.0,
                step=0.1
            ),
            Tags(
                id="tags",
                label="Tags",
                initial=init_tags,
                values=init_tags
            )
        ]).send()
    cl.user_session.set("chat_settings", settings)

@cl.on_settings_update
async def on_settings_update(settings):
    logger.info(f"settings update: {settings}")
    cl.user_session.set("chat_settings", settings)
    await setup_sk_helper()

async def setup_sk_helper():
    chat_settings = cl.user_session.get("chat_settings")
    chat_profile = cl.user_session.get("chat_profile")
    sk_helper = SKHelper(chat_profile, chat_settings)
    await sk_helper.add_chat_services()
    await sk_helper.setup_chat_agent()
    cl.user_session.set("sk_helper", sk_helper)
