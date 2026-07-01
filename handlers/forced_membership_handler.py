import asyncio

from telethon import events
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest

from config import supabase

SETTINGS_TABLE = "forced_membership_settings"
CHANNELS_TABLE = "forced_membership_channels"

_my_id_cache = {}


async def _get_my_id(client):
    key = id(client)
    if key not in _my_id_cache:
        me = await client.get_me()
        _my_id_cache[key] = me.id
    return _my_id_cache[key]


# ---------------- Supabase: توابع sync که با to_thread صدا زده میشن ----------------

def _select_enabled_sync(user_id: int):
    res = supabase.table(SETTINGS_TABLE).select("enabled").eq("user_id", user_id).limit(1).execute()
    if res.data:
        return bool(res.data[0].get("enabled", False))
    return False


def _set_enabled_sync(user_id: int, enabled: bool):
    supabase.table(SETTINGS_TABLE).upsert(
        {"user_id": user_id, "enabled": enabled}, on_conflict="user_id"
    ).execute()


def _add_channel_sync(user_id: int, channel: str):
    supabase.table(CHANNELS_TABLE).upsert(
        {"user_id": user_id, "channel": channel}, on_conflict="user_id,channel"
    ).execute()


def _remove_channel_sync(user_id: int, channel: str):
    supabase.table(CHANNELS_TABLE).delete().eq("user_id", user_id).eq("channel", channel).execute()


def _list_channels_sync(user_id: int):
    res = supabase.table(CHANNELS_TABLE).select("channel").eq("user_id", user_id).execute()
    return [row["channel"] for row in res.data] if res.data else []


def _clear_channels_sync(user_id: int):
    supabase.table(CHANNELS_TABLE).delete().eq("user_id", user_id).execute()


# ---------------- نسخه‌های async (برای استفاده داخل هندلرها) ----------------

async def _get_enabled(user_id):
    return await asyncio.to_thread(_select_enabled_sync, user_id)


async def _set_enabled(user_id, enabled):
    await asyncio.to_thread(_set_enabled_sync, user_id, enabled)


async def _add_channel(user_id, channel):
    await asyncio.to_thread(_add_channel_sync, user_id, channel)


async def _remove_channel(user_id, channel):
    await asyncio.to_thread(_remove_channel_sync, user_id, channel)


async def _list_channels(user_id):
    return await asyncio.to_thread(_list_channels_sync, user_id)


async def _clear_channels(user_id):
    await asyncio.to_thread(_clear_channels_sync, user_id)


def _normalize_channel(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        raw = raw.replace("https://t.me/", "")
    if not raw.startswith("@"):
        raw = "@" + raw
    return raw


async def _is_member(client, channel: str, user) -> bool:
    try:
        entity = await client.get_entity(channel)
        await client(GetParticipantRequest(entity, user))
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        # اگه نتونستیم چک کنیم (مثلا دسترسی نداریم)، به نفع کاربر فرض می‌کنیم عضوه
        # تا کسی به‌اشتباه بلاک نشه.
        return True


def forced_membership_handler (client):
    """این تابع رو با کلاینت Telethon خودت صدا بزن تا قابلیت عضویت اجباری فعال بشه."""

    # ---------- دستورات کنترلی ----------

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*تنظیم عضویت\s+(\S+)$"))
    async def _set_channel(event):
        channel = _normalize_channel(event.pattern_match.group(1))
        user_id = await _get_my_id(client)
        await _add_channel(user_id, channel)
        await event.edit(f"✅ کانال/گروه {channel} به لیست عضویت اجباری اضافه شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*حذف عضویت\s+(\S+)$"))
    async def _del_channel(event):
        channel = _normalize_channel(event.pattern_match.group(1))
        user_id = await _get_my_id(client)
        await _remove_channel(user_id, channel)
        await event.edit(f"🗑 کانال/گروه {channel} از لیست عضویت اجباری حذف شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*لیست عضویت اجباری$"))
    async def _list_cmd(event):
        user_id = await _get_my_id(client)
        channels = await _list_channels(user_id)
        if not channels:
            await event.edit("📭 لیست عضویت اجباری خالیه.")
            return
        text = "\n".join(f"➖ {c}" for c in channels)
        await event.edit(f"📋 لیست عضویت اجباری:\n{text}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*پاکسازی عضویت اجباری$"))
    async def _clear_cmd(event):
        user_id = await _get_my_id(client)
        await _clear_channels(user_id)
        await event.edit("🧹 لیست عضویت اجباری پاک شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*عضویت اجباری روشن$"))
    async def _enable_cmd(event):
        user_id = await _get_my_id(client)
        await _set_enabled(user_id, True)
        await event.edit("✅ عضویت اجباری فعال شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*عضویت اجباری خاموش$"))
    async def _disable_cmd(event):
        user_id = await _get_my_id(client)
        await _set_enabled(user_id, False)
        await event.edit("⛔️ عضویت اجباری غیرفعال شد.")

    # ---------- چک کردن پیام‌های خصوصی ورودی ----------

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def _check_membership(event):
        user_id = await _get_my_id(client)

        enabled = await _get_enabled(user_id)
        if not enabled:
            return

        channels = await _list_channels(user_id)
        if not channels:
            return

        sender = await event.get_sender()
        if sender is None or sender.bot:
            return

        missing = []
        for channel in channels:
            is_member = await _is_member(client, channel, sender)
            if not is_member:
                missing.append(channel)

        if not missing:
            return

        try:
            await event.delete()  # فقط از دید خودِ اکانت تو پاک میشه (محدودیت تلگرام)
        except Exception:
            pass

        channel_list = "\n".join(f"➖ {c}" for c in missing)
        try:
            await event.respond(
                "⚠️ برای ارسال پیام به من، اول باید عضو موارد زیر بشی:\n"
                f"{channel_list}\n\n"
                "بعد از عضویت، دوباره پیام بده."
            )
        except Exception:
            pass

    return (
        _set_channel,
        _del_channel,
        _list_cmd,
        _clear_cmd,
        _enable_cmd,
        _disable_cmd,
        _check_membership,
    )