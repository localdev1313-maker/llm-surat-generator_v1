import sys
import logging
from app.config import settings
from app.services.telegram_bot import create_telegram_bot

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    print("=" * 60)
    print("🤖 Bot Telegram Layanan Penyusunan Surat Elektronik Otomatis Terintegrasi AI")
    print("=" * 60)
    
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN.strip() == "":
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN belum dikonfigurasi!")
        print("💡 Silakan ikuti langkah berikut:")
        print("   1. Dapatkan Bot Token dari @BotFather di Telegram.")
        print("   2. Buat file .env di folder backend/ (atau salin dari .env.example).")
        print("   3. Isi TELEGRAM_BOT_TOKEN=<token_anda> pada file .env tersebut.")
        print("   4. Jalankan kembali: python run_bot.py\n")
        sys.exit(1)

    bot_app = create_telegram_bot()
    print("✅ Bot siap melayani pembuatan surat dari jarak jauh!")
    print("👉 Buka bot di aplikasi Telegram Anda dan ketik /start")
    print("Tekan Ctrl + C untuk menghentikan bot.\n")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

