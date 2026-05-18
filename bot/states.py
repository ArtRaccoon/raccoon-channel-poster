from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    main_menu = State()
    settings_menu = State()
