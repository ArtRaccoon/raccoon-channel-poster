from aiogram import Router

from .channels import router as channels_router
from .create_post import router as create_post_router
from .drafts import router as drafts_router
from .menu import router as menu_router
from .settings import router as settings_router
from .start import router as start_router
from .statistics import router as statistics_router


def get_routers() -> list[Router]:
    return [
        start_router,
        menu_router,
        settings_router,
        channels_router,
        create_post_router,
        drafts_router,
        statistics_router,
    ]
