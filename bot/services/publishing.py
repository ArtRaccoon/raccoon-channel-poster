import json
import logging
from json import JSONDecodeError

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.services.channels import get_channel_signature
from bot.services.posts import CAPTION_LIMIT, add_publish_log, set_post_status

logger = logging.getLogger(__name__)

RIGHTS_ERROR = 'Не удалось опубликовать. Проверьте, что бот всё ещё администратор канала и имеет право публиковать сообщения.'
NETWORK_ERROR = 'Сетевая ошибка при публикации. Попробуйте позже.'
CAPTION_SIGNATURE_ERROR = 'Подпись вместе с текстом превышает лимит Telegram 1024 символа для фото.'
GENERIC_ERROR = 'Не удалось опубликовать пост. Попробуйте позже или проверьте настройки канала.'


def build_post_text_with_signature(text: str | None, signature: str | None) -> str:
    base = text or ''
    sign = (signature or '').strip()
    if not sign:
        return base
    if not base.strip():
        return sign
    return f'{base}\n\n{sign}'


def build_url_buttons_markup(buttons_json: str | None) -> InlineKeyboardMarkup | None:
    if not buttons_json:
        return None
    try:
        buttons = json.loads(buttons_json)
    except (JSONDecodeError, TypeError):
        return None
    rows = []
    for button in buttons[:8]:
        text = str(button.get('text', '')).strip() if isinstance(button, dict) else ''
        url = str(button.get('url', '')).strip() if isinstance(button, dict) else ''
        if text and (url.startswith('http://') or url.startswith('https://')):
            rows.append([InlineKeyboardButton(text=text, url=url)])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def classify_publish_error(exc: Exception) -> str:
    if isinstance(exc, TelegramForbiddenError):
        return RIGHTS_ERROR
    if isinstance(exc, TelegramBadRequest):
        lower = str(exc).lower()
        rights_markers = ('not enough rights', 'have no rights', 'chat not found', 'bot was kicked', 'forbidden')
        if any(marker in lower for marker in rights_markers):
            return RIGHTS_ERROR
    if isinstance(exc, (TelegramNetworkError, TimeoutError, ConnectionError, OSError)):
        return NETWORK_ERROR
    return GENERIC_ERROR


async def _post_signature(db_path: str, post: tuple) -> str | None:
    return await get_channel_signature(db_path, post[1], post[2])


async def render_post_preview(bot, chat_id: int, post: tuple, db_path: str) -> None:
    signature = await _post_signature(db_path, post)
    text = build_post_text_with_signature(post[3], signature)
    markup = build_url_buttons_markup(post[10])
    if post[5] == 'photo':
        if text and len(text) > CAPTION_LIMIT:
            raise ValueError(CAPTION_SIGNATURE_ERROR)
        await bot.send_photo(chat_id=chat_id, photo=post[4], caption=text or None, reply_markup=markup)
    else:
        await bot.send_message(chat_id=chat_id, text=text or ' ', reply_markup=markup)


async def publish_post(db_path: str, bot, post: tuple) -> tuple[bool, str]:
    try:
        signature = await _post_signature(db_path, post)
        text = build_post_text_with_signature(post[3], signature)
        markup = build_url_buttons_markup(post[10])
        if post[5] == 'photo':
            if text and len(text) > CAPTION_LIMIT:
                raise ValueError(CAPTION_SIGNATURE_ERROR)
            await bot.send_photo(chat_id=post[2], photo=post[4], caption=text or None, reply_markup=markup)
        else:
            await bot.send_message(chat_id=post[2], text=text or '', reply_markup=markup)
        await set_post_status(db_path, post[0], 'published')
        await add_publish_log(db_path, post[1], post[2], post[0], 'success')
        return True, 'Пост опубликован.'
    except ValueError as exc:
        logger.exception('Publish validation error for post_id=%s', post[0])
        await set_post_status(db_path, post[0], 'failed')
        await add_publish_log(db_path, post[1], post[2] or '', post[0], 'error', str(exc))
        return False, str(exc)
    except Exception as exc:
        logger.exception('Publish error for post_id=%s', post[0])
        await set_post_status(db_path, post[0], 'failed')
        await add_publish_log(db_path, post[1], post[2] or '', post[0], 'error', str(exc))
        return False, classify_publish_error(exc)
