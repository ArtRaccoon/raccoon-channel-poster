import json
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiohttp import ClientError
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError

from bot.services.channels import get_channel_settings
from bot.services.posts import CAPTION_LIMIT, TEXT_LIMIT, add_publish_log, get_post, set_post_status


def build_post_text_with_signature(text: str | None, signature: str | None) -> str:
    base = (text or '').strip()
    sign = (signature or '').strip()
    if base and sign:
        return f'{base}\n\n{sign}'
    return base or sign


def build_url_buttons_markup(buttons_json: str | None) -> InlineKeyboardMarkup | None:
    if not buttons_json:
        return None
    data = json.loads(buttons_json)
    rows = [[InlineKeyboardButton(text=item['text'], url=item['url'])] for item in data if item.get('text') and item.get('url')]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def validate_post_before_publish(post: tuple, signature: str | None) -> str | None:
    full_text = build_post_text_with_signature(post[3], signature)
    if post[5] in ('photo', 'album') and len(full_text) > CAPTION_LIMIT:
        return 'Подпись вместе с текстом превышает лимит Telegram 1024 символа для фото.'
    if post[5] == 'text' and len(full_text) > TEXT_LIMIT:
        return 'Текст поста превышает лимит Telegram 4096 символов.'
    return None


def classify_publish_error(exc: Exception) -> str:
    if isinstance(exc, (TelegramForbiddenError, TelegramBadRequest)):
        return 'Не удалось опубликовать. Проверьте, что бот всё ещё администратор канала и имеет право публиковать сообщения.'
    if isinstance(exc, (TelegramNetworkError, ClientError)):
        return 'Сетевая ошибка при публикации. Попробуйте позже.'
    return 'Не удалось опубликовать пост. Попробуйте позже или проверьте настройки канала.'


async def render_post_preview(bot, user_id: int, post: tuple, channel: dict[str, Any] | None):
    signature = channel.get('signature') if channel else None
    full_text = build_post_text_with_signature(post[3], signature)
    buttons_json = post[10] or (channel.get('default_buttons_json') if channel else None)
    markup = build_url_buttons_markup(buttons_json)
    error = validate_post_before_publish(post, signature)
    if error:
        return False, error
    if post[5] == 'photo':
        await bot.send_photo(user_id, post[4], caption=full_text or None, reply_markup=markup)
    elif post[5] == 'album' and post[11]:
        media_items = json.loads(post[11])
        album = []
        for i, item in enumerate(media_items):
            album.append(InputMediaPhoto(media=item['file_id'], caption=full_text if i == 0 else None))
        await bot.send_media_group(user_id, album)
        if markup:
            await bot.send_message(user_id, 'URL-кнопки для альбома:', reply_markup=markup)
    else:
        await bot.send_message(user_id, full_text or '-', reply_markup=markup)
    return True, None


async def publish_post(bot, db_path: str, post_id: int) -> tuple[bool, str]:
    post = await get_post(db_path, post_id)
    channel = await get_channel_settings(db_path, post[1], post[2]) if post and post[2] else None
    signature = channel.get('signature') if channel else None
    full_text = build_post_text_with_signature(post[3], signature)
    buttons_json = post[10] or (channel.get('default_buttons_json') if channel else None)
    markup = build_url_buttons_markup(buttons_json)
    error = validate_post_before_publish(post, signature)
    if error:
        await set_post_status(db_path, post_id, 'failed')
        await add_publish_log(db_path, post[1], post[2] or '', post_id, 'error', error)
        return False, error
    try:
        if post[5] == 'photo':
            await bot.send_photo(post[2], post[4], caption=full_text or None, reply_markup=markup)
        elif post[5] == 'album' and post[11]:
            media_items = json.loads(post[11])
            album = [InputMediaPhoto(media=i['file_id'], caption=full_text if idx == 0 else None) for idx, i in enumerate(media_items)]
            await bot.send_media_group(post[2], album)
            if markup:
                await bot.send_message(post[2], 'Ссылки:', reply_markup=markup)
        else:
            await bot.send_message(post[2], full_text or '-', reply_markup=markup)
        await set_post_status(db_path, post_id, 'published')
        await add_publish_log(db_path, post[1], post[2], post_id, 'success')
        return True, 'ok'
    except Exception as exc:
        await set_post_status(db_path, post_id, 'failed')
        await add_publish_log(db_path, post[1], post[2] or '', post_id, 'error', str(exc))
        return False, classify_publish_error(exc)
