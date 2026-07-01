import asyncio
from telethon import events
from telethon.tl.types import ChannelParticipantsAdmins

async def get_all_members(client, chat):
    """گرفتن همه اعضای گروه"""
    members = []
    try:
        async for member in client.iter_participants(chat):
            if member and not member.bot:
                members.append(member)
    except Exception as e:
        print(f"Error fetching members: {e}")
    return members

async def get_admins(client, chat):
    """گرفتن لیست ادمین‌ها با روش سازگار با انواع گروه‌ها"""
    admins = []
    try:
        async for admin in client.iter_participants(chat, filter=ChannelParticipantsAdmins()):
            if admin and not admin.bot:
                admins.append(admin)
    except:
        try:
            async for member in client.iter_participants(chat):
                if not member.bot and member.participant:
                    if hasattr(member.participant, 'admin_rights') or type(member.participant).__name__ in ['ChatParticipantAdmin', 'ChatParticipantCreator']:
                        admins.append(member)
        except Exception as e:
            print(f"Error fetching admins: {e}")
    return admins


def register_tagger(bot):
    """ثبت هندلرهای تگ روی ربات"""

    @bot.on(events.NewMessage(pattern=r'^\*(تگ اعضا|تگ همه|تگ ادمین|تگ مدیرا)(.*)'))
    async def tag_handler(event):
        if not event.is_group:
            return

        sender_id = event.sender_id
        message_text = event.message.text
        chat = await event.get_chat()

        # ۱. بررسی ادمین بودن فرستنده پیام
        if event.out:
            is_admin = True
        else:
            try:
                permissions = await bot.get_permissions(event.chat_id, sender_id)
                is_admin = permissions.is_admin
            except Exception:
                is_admin = False

        # ----------------------------------------------------
        # ❌ سناریوی کاربر عادی: هدایت دستور و تگ کردن ادمین‌ها علیه او
        # ----------------------------------------------------
        if not is_admin:
            # ربات لیست ادمین‌ها را می‌گیرد تا آن‌ها را روی پیام کاربر عادی تگ کند
            admins = await get_admins(bot, chat)
            if not admins:
                return
                
            mention_text = "⚠️ **گزارش تخلف کاربر عادی:**\n"
            mention_text += f"کاربر [{event.sender.first_name}](tg://user?id={sender_id}) قصد استفاده از دستورات عمومی تگ را داشت.\n\n"
            mention_text += "🔔 **فراخوان ادمین‌ها جهت بررسی:**\n"
            
            for admin in admins:
                mention_text += f"@{admin.username} " if admin.username else f"密 [{admin.first_name}](tg://user?id={admin.id}) "
                
            # ارسال تگ ادمین‌ها به صورت ریپلای روی پیام شخص متخلف
            await event.reply(mention_text)
            return

        # ----------------------------------------------------
        #  سناریوی ادمین یا خودت: اجرای دقیق و درست دستور
        # ----------------------------------------------------
        
        # الف) اجرای دستور تگ اعضا / همه برای ادمین
        if message_text.startswith('*تگ اعضا') or message_text.startswith('*تگ همه'):
            status_msg = await event.reply("🔄 در حال دریافت لیست اعضا...")
            members = await get_all_members(bot, chat)
            await status_msg.delete()
            
            text = message_text.replace('*تگ اعضا', '').replace('*تگ همه', '').strip()
            mention_text = ""
            for member in members:
                mention_text += f"@{member.username} " if member.username else f"[{member.first_name}](tg://user?id={member.id}) "
                if len(mention_text) > 600:
                    await event.respond(f"{text}\n\n{mention_text}" if text else mention_text)
                    mention_text = ""
                    await asyncio.sleep(4.0)
            if mention_text:
                await event.respond(f"{text}\n\n{mention_text}" if text else mention_text)

        # ب) اجرای دستور تگ ادمین / مدیرا برای ادمین
        elif message_text.startswith('*تگ ادمین') or message_text.startswith('*تگ مدیرا'):
            status_msg = await event.reply("🔄 در حال دریافت لیست ادمین‌ها...")
            admins = await get_admins(bot, chat)
            await status_msg.delete()
            
            text = message_text.replace('*تگ ادمین', '').replace('*تگ مدیرا', '').strip()
            mention_text = ""
            for admin in admins:
                mention_text += f"@{admin.username} " if admin.username else f"[{admin.first_name}](tg://user?id={admin.id}) "
                if len(mention_text) > 600:
                    await event.respond(f"{text}\n\n{mention_text}" if text else mention_text)
                    mention_text = ""
                    await asyncio.sleep(3.0)
            if mention_text:
                await event.respond(f"{text}\n\n{mention_text}" if text else mention_text)

    @bot.on(events.NewMessage(pattern=r'^\*راهنمای تگ$'))
    async def help_handler(event):
        if not event.out:
            return
            
        help_text = """
🎯 **راهنمای هوشمند دستورات تگ**

**دستورات اصلی (فقط برای شما و ادمین‌ها):**
• `*تگ اعضا [پیام]` - تگ تمام اعضای گروه
• `*تگ همه [پیام]` - تگ تمام اعضا
• `*تگ ادمین [پیام]` - تگ تمام ادمین‌ها
• `*تگ مدیرا [پیام]` - تگ تمام ادمین‌ها

**سیستم ضد نفوذ:**
🔸 اگر کاربران عادی از این دستورات استفاده کنند، ربات کل ادمین‌های گروه را روی پیام آن‌ها ریپلای و تگ می‌کند تا ادمین‌ها مطلع شوند.
"""
        await event.reply(help_text)