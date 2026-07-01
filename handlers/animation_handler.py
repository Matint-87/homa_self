import asyncio
from telethon import events

def register_animation_handlers(client):
    """ثبت ۱۰ هندلر انیمیشن متحرک و فوق‌العاده خفن ایموجی روی سلف‌بات"""

    # ۱. دستور *قلب (تغییر رنگ قلب‌ها در جای خود)
    @client.on(events.NewMessage(pattern=r'^\*قلب$'))
    async def heart_colors(event):
        if not event.out: return
        frames = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💖", "💝", "❤️"]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.3)
            except: break

    # ۲. دستور *متحرک (بزرگ شدن و جلو آمدن قلب از عقب)
    @client.on(events.NewMessage(pattern=r'^\*متحرک$'))
    async def heart_zoom(event):
        if not event.out: return
        frames = [
            "🖤🖤🖤🖤🖤\n🖤🖤❤️🖤🖤\n🖤🖤🖤🖤🖤",
            "🖤🖤🖤🖤🖤\n🖤❤️‍🔥❤️❤️‍🔥🖤\n🖤🖤🖤🖤🖤",
            "🖤🖤🖤🖤🖤\n🖤✨💖✨🖤\n🖤🖤🖤🖤🖤",
            "🖤🖤🖤🖤🖤\n🖤🌟💝🌟🖤\n🖤🖤🖤🖤🖤",
            "❤️‍🔥❤️‍🔥❤️‍🔥❤️‍🔥❤️‍🔥\n❤️‍🔥💓💘💓❤️‍🔥\n❤️‍🔥❤️‍🔥❤️‍🔥❤️‍🔥❤️‍🔥",
            "💥💥💥💥💥\n💥❤️‍🔥❤️💥\n💥💥💥💥💥",
            "❤️"
        ]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.4)
            except: break

    # ۳. دستور *باران (باریدن باران و رعد و برق و رنگین‌کمان)
    @client.on(events.NewMessage(pattern=r'^\*باران$'))
    async def rain_animation(event):
        if not event.out: return
        frames = ["☁️", "☁️\n💧", "🌧️\n💧 💧", "⛈️\n⚡ 💧 💧", "🌧️\n💧 💧 💧", "🌤️\n🌈"]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.5)
            except: break

    # ۴. دستور *لودینگ (حالت بارگذاری متحرک رنگین‌کمانی)
    @client.on(events.NewMessage(pattern=r'^\*لودینگ$'))
    async def loading_animation(event):
        if not event.out: return
        frames = [
            "[⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜] 0%",
            "[🟥⬜⬜⬜⬜⬜⬜⬜⬜⬜] 10%",
            "[🟥🟧⬜⬜⬜⬜⬜⬜⬜⬜] 25%",
            "[🟥🟧🟨⬜⬜⬜⬜⬜⬜⬜] 40%",
            "[🟥🟧🟨🟩⬜⬜⬜⬜⬜⬜] 55%",
            "[🟥🟧🟨🟩🟦⬜⬜⬜⬜] 70%",
            "[🟥🟧🟨🟩🟦🟪⬜⬜⬜] 85%",
            "[🟥🟧🟨🟩🟦🟪💖⬜⬜] 95%",
            "[🟥🟧🟨🟩🟦🟪💖💝✅] 100%\n\n✨ **بارگذاری با موفقیت انجام شد!**"
        ]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.3)
            except: break

    # ۵. دستور *موشک (شلیک موشک به سمت فضا)
    @client.on(events.NewMessage(pattern=r'^\*موشک$'))
    async def rocket_animation(event):
        if not event.out: return
        frames = ["🌍\n\n\n\n🚀", "🌍\n\n\n🚀\n🔥", "🌍\n\n🚀\n⚡\n🔥", "🌍\n🚀\n✨\n⚡", "🚀\n✨\n\n🌌", "🛸\n\n\n🌌"]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.4)
            except: break

    # ۶. دستور *تایپ (شبیه‌ساز خفن افکت هکر زنده)
    @client.on(events.NewMessage(pattern=r'^\*تایپ$'))
    async def typewriter_animation(event):
        if not event.out: return
        text = "Hello... I am Self-Bot! ⚙️\nSystem updated successfully. 💻"
        current = ""
        for char in text:
            try:
                current += char
                # اضافه کردن کاراکتر چشمک‌زن هکری در انتها
                await event.edit(f"🧬 {current} ▒")
                await asyncio.sleep(0.1)
            except: break
        try: await event.edit(f"🧬 {text} ✅")
        except: pass

    # ۷. دستور *ماشین (کورس مسابقه‌ای و دریفت متحرک)
    @client.on(events.NewMessage(pattern=r'^\*ماشین$'))
    async def car_animation(event):
        if not event.out: return
        frames = [
            "🏁 🏎️💨            🏢",
            "🏁   🏎️💨          🏢",
            "🏁     🏎️💨        🏢",
            "🏁       🏎️💨      🏢",
            "🏁         💥🏎️💨  🏢",
            "🏁           🔥💥  🏢",
            "🏆🥇 **FINISH!**"
        ]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.4)
            except: break

    # ۸. دستور *هک (شبیه‌ساز فیک نفوذ امنیتی برای کل‌کل)
    @client.on(events.NewMessage(pattern=r'^\*هک$'))
    async def hack_animation(event):
        if not event.out: return
        frames = [
            "📡 Connecting to main frame...",
            "📡 Connecting to main frame... [OK]",
            "🔓 Bypassing Telegram Firewalls...",
            "🔓 Bypassing Telegram Firewalls... 50%",
            "🔓 Bypassing Telegram Firewalls... 100%",
            "💉 Injecting Exploit Packets...",
            "💥 System Overloaded!",
            "☠️ **TARGET HACKED BY HOMA SELF** ☠️"
        ]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.5)
            except: break

    # ۹. دستور *جادو (پرتاب جادو و تبدیل شدن به خرگوش)
    @client.on(events.NewMessage(pattern=r'^\*جادو$'))
    async def magic_animation(event):
        if not event.out: return
        frames = [
            "🧙‍♂️ 🪄     🎩",
            "🧙‍♂️  ✨    🎩",
            "🧙‍♂️   ✨   🎩",
            "🧙‍♂️    ✨  🎩",
            "🧙‍♂️     💥🎩",
            "🧙‍♂️     💨🎩",
            "🧙‍♂️        🐇 ✨"
        ]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.4)
            except: break

    # ۱۰. دستور *گربه (انیمیشن راه رفتن گربه کیوت)
    @client.on(events.NewMessage(pattern=r'^\*گربه$'))
    async def cat_animation(event):
        if not event.out: return
        frames = [
            "🐈      🐾",
            " 🐈     🐾",
            "  🐈    🐾",
            "   🐈   🐾",
            "    🐈  🐾",
            "     🐈 🐾",
            "      🐈🐾",
            "😻🐾 **Meow!**"
        ]
        for frame in frames:
            try:
                await event.edit(frame)
                await asyncio.sleep(0.3)
            except: break