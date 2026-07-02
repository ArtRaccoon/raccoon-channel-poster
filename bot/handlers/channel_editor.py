from __future__ import annotations

import logging
from html import escape

from aiogram import Router
from aiogram.types import Message
from aiogram.utils.text_decorations import html_decoration

from bot.services.channels import get_active_channel_by_chat_id
from bot.services.edit_logs import add_edit_log
from bot.services.link_injector import CAPTION_LIMIT, TEXT_LIMIT, append_links_block_checked

router = Router()
logger = logging.getLogger(__name__)

PROCESSED_MEDIA_GROUPS: set[str] = set()
CAPTION_MEDIA_FIELDS = ('photo', 'video', 'animation', 'document', 'audio', 'voice')


def _supports_caption(message: Message) -> bool:
    return any(getattr(message, field, None) for field in CAPTION_MEDIA_FIELDS)


def _message_text_html(message: Message) -> str:
    text = message.text or ''
    entities = message.entities or []
    if entities:
        return html_decoration.unparse(text, entities)
    return escape(text)


def _message_caption_html(message: Message) -> str:
    caption = message.caption or ''
    entities = message.caption_entities or []
    if entities:
        return html_decoration.unparse(caption, entities)
    return escape(caption)


async def _notify_owner(bot, owner_id: int | None, text: str) -> None:
    if owner_id is None:
        return
    try:
        await bot.send_message(owner_id, text)
    except Exception as exc:  # best-effort notification only
        logger.warning('Failed to notify owner_id=%s: %s', owner_id, exc)


@router.channel_post()
async def inject_links_into_channel_post(message: Message, bot, config) -> None:
    if message.from_user and message.from_user.id == bot.id:
        return

    channel_id = str(message.chat.id)
    message_id = message.message_id
    channel = await get_active_channel_by_chat_id(config.database_path, channel_id)
    if not channel:
        return

    owner_id = channel['owner_telegram_id']
    if not channel.get('auto_edit_enabled', True):
        await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'skipped_auto_disabled')
        return

    links_block = channel.get('links_block') or ''
    if not links_block.strip():
        await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'skipped_no_links')
        return

    if message.text:
        result = append_links_block_checked(message.text, links_block, original_html=_message_text_html(message), limit=TEXT_LIMIT)
        if not result.changed:
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, result.reason or 'skipped')
            if result.reason == 'error_limit':
                logger.warning('Text limit exceeded for channel_id=%s message_id=%s', channel_id, message_id)
                await _notify_owner(bot, owner_id, 'Не удалось добавить ссылки: превышен лимит текста.')
            return
        try:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=message_id, text=result.text, parse_mode='HTML')
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'success')
        except Exception as exc:
            logger.exception('Telegram edit_message_text failed for channel_id=%s message_id=%s', channel_id, message_id)
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'error_telegram', str(exc))
        return

    if message.caption:
        result = append_links_block_checked(message.caption, links_block, original_html=_message_caption_html(message), limit=CAPTION_LIMIT)
        if not result.changed:
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, result.reason or 'skipped')
            if result.reason == 'error_limit':
                logger.warning('Caption limit exceeded for channel_id=%s message_id=%s', channel_id, message_id)
                await _notify_owner(bot, owner_id, 'Не удалось добавить ссылки: превышен лимит caption.')
            return
        try:
            await bot.edit_message_caption(chat_id=message.chat.id, message_id=message_id, caption=result.text, parse_mode='HTML')
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'success')
        except Exception as exc:
            logger.exception('Telegram edit_message_caption failed for channel_id=%s message_id=%s', channel_id, message_id)
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'error_telegram', str(exc))
        return

    if _supports_caption(message):
        if message.media_group_id:
            media_group_key = f'{message.chat.id}:{message.media_group_id}'
            if media_group_key in PROCESSED_MEDIA_GROUPS:
                await add_edit_log(
                    config.database_path,
                    owner_id,
                    channel_id,
                    message_id,
                    'skipped_media_group_already_processed',
                )
                return
            PROCESSED_MEDIA_GROUPS.add(media_group_key)

        result = append_links_block_checked('', links_block, original_html='', limit=CAPTION_LIMIT)
        if not result.changed:
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, result.reason or 'skipped')
            if result.reason == 'error_limit':
                logger.warning('Caption limit exceeded for channel_id=%s message_id=%s', channel_id, message_id)
                await _notify_owner(bot, owner_id, 'Не удалось добавить ссылки: превышен лимит caption.')
            return
        try:
            await bot.edit_message_caption(chat_id=message.chat.id, message_id=message_id, caption=result.text, parse_mode='HTML')
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'success')
        except Exception as exc:
            logger.exception('Telegram edit_message_caption failed for channel_id=%s message_id=%s', channel_id, message_id)
            await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'error_telegram', str(exc))
        return

    logger.info('Unsupported channel post without text/caption: channel_id=%s message_id=%s', channel_id, message_id)
    await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'skipped_unsupported_media')
