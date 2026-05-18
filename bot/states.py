from aiogram.fsm.state import State, StatesGroup


class AddChannelState(StatesGroup):
    waiting_channel_ref = State()


class CreatePostState(StatesGroup):
    waiting_text = State()
    waiting_channel = State()
    waiting_action = State()
