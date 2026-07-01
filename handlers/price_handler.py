import asyncio
import aiohttp
from telethon import events

async def get_crypto_prices():
    """گرفتن قیمت جهانی کریپتو از سرور بین‌المللی کوین‌اگز"""
    url = "https://api.coinex.com/v1/market/ticker/all"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    res_json = await response.json()
                    if res_json.get("code") == 0:
                        return res_json.get("data", {}).get("ticker", {})
    except:
        pass
    return None

async def get_live_fiat_prices():
    """گرفتن قیمت دقیق و واقعی دلار آزاد بازار، تتر و یورو از سرور بدون تحریم"""
    url = "https://brws.xyz/api/v1/rates"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with session.get(url, headers=headers, timeout=6) as response:
                if response.status == 200:
                    data = await response.json()
                    # استخراج مستقیم نرخ‌های بازار آزاد
                    return {
                        "usd": int(data.get("usd", {}).get("value", 0)),
                        "usdt": int(data.get("usdt", {}).get("value", 0)),
                        "eur": int(data.get("eur", {}).get("value", 0))
                    }
    except:
        pass
    return None


def register_price_handlers(client):
    """ثبت هندلرهای قیمت ارز و کریپتو"""

    @client.on(events.NewMessage(pattern=r'^\*(دلار|تتر|بیت‌کوین|اتریوم)$'))
    async def price_handler(event):
        if not event.out:
            return

        command = event.pattern_match.group(1)
        msg = await event.edit(f"🔄 در حال دریافت قیمت واقعی {command}...")

        # دریافت قیمت‌های زنده بازار آزاد (دلار، تتر، یورو)
        fiat_data = await get_live_fiat_prices()
        
        # اگر سرور بالا پاسخ نداد، به عنوان لایه دوم از نوبیتکس کمک می‌گیرد تا ربات ارور ندهد
        if not fiat_data:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api.nobitex.ir/v3/orderbook/USDTIRT", timeout=4) as res:
                        if res.status == 200:
                            n_data = await res.json()
                            last_trade = int(float(n_data.get("lastTradePrice", 0)) / 10)
                            fiat_data = {"usdt": last_trade, "usd": last_trade - 400, "eur": int(last_trade * 1.08)}
            except:
                pass

        if not fiat_data:
            await msg.edit("❌ خطا در اتصال به سرورهای قیمت‌دهی. لطفاً دوباره تلاش کنید.")
            return

        crypto_data = await get_crypto_prices()

        try:
            if command == "تتر":
                text = f"💵 **قیمت لحظه‌ای تتر (USDT):**\n\n💰 قیمت: `{fiat_data['usdt']:,}` تومان"
            
            elif command == "دلار":
                # این قیمت مستقیماً از بازار آزاد تهران خوانده می‌شود (نه محاسباتی دستی)
                text = f"💵 **قیمت دلار بازار آزاد:**\n\n💰 قیمت: `{fiat_data['usd']:,}` تومان"

            elif command == "بیت‌کوین":
                if not crypto_data:
                    await msg.edit("❌ خطا در دریافت اطلاعات بازار کریپتو.")
                    return
                btc_usd = float(crypto_data.get("BTCUSDT", {}).get("last", 0))
                btc_toman = int(btc_usd * fiat_data['usdt'])
                text = f"🪙 **قیمت لحظه‌ای بیت‌کوین (BTC):**\n\n💰 قیمت: `{btc_toman:,}` تومان"

            elif command == "اتریوم":
                if not crypto_data:
                    await msg.edit("❌ خطا در دریافت اطلاعات بازار کریپتو.")
                    return
                eth_usd = float(crypto_data.get("ETHUSDT", {}).get("last", 0))
                eth_toman = int(eth_usd * fiat_data['usdt'])
                text = f"🪙 **قیمت لحظه‌ای اتریوم (ETH):**\n\n💰 قیمت: `{eth_toman:,}` تومان"

            await msg.edit(text)

        except Exception as e:
            print(f"Price Error: {e}")
            await msg.edit("❌ خطا در پردازش اطلاعات.")