from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

from bot.services.channels import get_active_channel_by_chat_id
from bot.services.edit_logs import add_edit_log
from bot.services.link_injector import CAPTION_LIMIT, TEXT_LIMIT, append_links_block_checked

router = Router()
logger = logging.getLogger(__name__)


async def _notify_owner(bot, owner_id: int | None, text: str) -> None:
    if owner_id is None:
        return
    try:
        await bot.send_message(owner_id, text)
    except Exception as exc:  # best-effort notification only
        logger.warning('Failed to notify owner_id=%s: %s', owner_id, exc)


@router.channel_post()
async def inject_links_into_channel_post(message: Message, bot, config) -> None:
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
        result = append_links_block_checked(message.text, links_block, limit=TEXT_LIMIT)
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
        result = append_links_block_checked(message.caption, links_block, limit=CAPTION_LIMIT)
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
    await add_edit_log(config.database_path, owner_id, channel_id, message_id, 'skipped_no_text_or_caption')
