from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from config import supabase
from utils import db_execute

# create table user_profiles (
#   client_id bigint primary key, -- آیدی اکانت تلگرام کاربر
#   first_name text,
#   last_name text,
#   updated_at timestamp with time zone default timezone('utc'::text, now())
# );

# تعریف دیکشنری فونت‌ها در همان فایل هندلر
FONTS = {
    "1": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ۰۱۲۳۴۵۶۷۸۹", "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"),
    "2": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝖏𝗐𝗑𝗒𝗓𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹"),
    "3": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"),
    "4": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ"),
    "5": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝔄𝔅𝔆𝔇𝔈𝔉𝔊𝔗𝔉𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔𝔕𝔖𝔗𝔘𝔙𝔚𝔛𝔜𝔗"),
    "6": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"),
    "7": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ"),
    "8": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅"),
    "9": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝔄𝔅𝔆𝔇𝔈𝔉𝔊𝔗𝔉𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔𝔕𝔖𝔗𝔘𝔙𝔚𝔛𝔜𝔗𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"),
    "10": str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", "卂乃匚ᗪ乇千Ꮆ卄丨ﾌҜㄥ爪几ㄖ卩Ɋ尺丂ㄒㄩᐯ山乂ㄚ乙卂乃匚ᗪ乇千Ꮆ卄丨ﾌҜㄥ爪几ㄖ卩Ɋ尺丂ㄒㄩᐯ山乂ㄚ乙"),
}

def register_profile_handler(client):
    
    # دیتابیس برای ذخیره نام اصلی
    async def get_or_set_orig_name(client_id, first=None, last=None):
        if first is not None or last is not None:
            await db_execute(supabase.table("user_profiles").upsert({
                "client_id": client_id, "first_name": first, "last_name": last
            }))
        res = await db_execute(supabase.table("user_profiles").select("*").eq("client_id", client_id))
        if res.data:
            return res.data[0]
        me = await client.get_me()
        await get_or_set_orig_name(client_id, me.first_name, me.last_name)
        return {"first_name": me.first_name, "last_name": me.last_name}

    @client.on(events.NewMessage(outgoing=True, pattern=r'^\*(نام|فامیلی|فونت نام|تنظیم پروفایل)'))
    async def profile_handler(event):
        text = event.raw_text
        me = await client.get_me()
        tr = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

        # 1. تغییر نام اصلی
        if text.startswith('*نام '):
            new_name = text.replace('*نام ', '').strip()
            current = await get_or_set_orig_name(me.id)
            await get_or_set_orig_name(me.id, new_name, current.get("last_name", ""))
            await client(UpdateProfileRequest(first_name=new_name))
            await event.edit(f"✅ نام اصلی به **{new_name}** تغییر کرد.")

        # 2. تغییر فامیلی اصلی
        elif text.startswith('*فامیلی '):
            new_last = text.replace('*فامیلی ', '').strip()
            current = await get_or_set_orig_name(me.id)
            await get_or_set_orig_name(me.id, current.get("first_name", ""), new_last)
            await client(UpdateProfileRequest(last_name=new_last))
            await event.edit(f"✅ فامیلی به **{new_last}** تغییر کرد.")

        # 3. تغییر عکس پروفایل
        elif text == '*تنظیم پروفایل':
            if event.is_reply:
                reply = await event.get_reply_message()
                if reply.media:
                    await event.edit("⏳ در حال آپلود...")
                    photo = await client.download_media(reply)
                    file = await client.upload_file(photo)
                    await client(UploadProfilePhotoRequest(file=file))
                    await event.edit("✅ عکس پروفایل با موفقیت تغییر کرد.")
                else:
                    await event.edit("❌ ریپلای حاوی عکس نیست.")

        # 4. اعمال فونت روی نام و فامیلی
        elif text.startswith('*فونت نام '):
            font_id = text.replace('*فونت نام ', '').strip().translate(tr)
            if font_id in FONTS:
                data = await get_or_set_orig_name(me.id)
                n = (data.get("first_name") or "").translate(FONTS[font_id])
                l = (data.get("last_name") or "").translate(FONTS[font_id])
                
                await client(UpdateProfileRequest(first_name=n, last_name=l))
                await event.edit(f"✅ استایل {font_id} روی پروفایل اعمال شد.")
            else:
                await event.edit("❌ فونت معتبر نیست (1 تا 10).")