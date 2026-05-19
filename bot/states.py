from aiogram.fsm.state import State, StatesGroup


class AddChannelState(StatesGroup):
    waiting_channel_ref = State()


class CreatePostState(StatesGroup):
    waiting_content = State()
    waiting_channel = State()
    waiting_edit_text = State()
    waiting_schedule_at = State()
    waiting_buttons = State()
    waiting_replace_media = State()
    waiting_search_query = State()
    waiting_signature = State()
    waiting_channel_buttons = State()
    waiting_channel_timezone = State()
    waiting_template_title = State()
    waiting_template_text = State()
    waiting_schedule_rule = State()

    waiting_batch_channel = State()
    waiting_batch_schedule_text = State()
    waiting_batch_content = State()
    waiting_batch_review = State()
    waiting_settings_schedule_text = State()
    waiting_settings_signature_text = State()
