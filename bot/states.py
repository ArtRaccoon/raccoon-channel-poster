from aiogram.fsm.state import State, StatesGroup


class AddChannelState(StatesGroup):
    waiting_channel_ref = State()


class CreatePostState(StatesGroup):
    waiting_content = State()
    waiting_channel = State()
    waiting_edit_text = State()
    waiting_schedule_at = State()
    waiting_buttons = State()
    waiting_replace_photo = State()
    waiting_search_query = State()


class ChannelSignatureState(StatesGroup):
    waiting_signature = State()
