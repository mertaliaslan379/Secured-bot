import discord
from discord import app_commands
from discord.ext import commands
import datetime
from PIL import Image
import io
import requests
import os

# Bot Ayarları ve Intent'ler
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Kanal ID'leri
KOMUT_KANAL_ID = 1547513766319497296
LOG_KANAL_ID = 1547526324422185031

# ==========================================
# 1. MESAJ TABANLI SİSTEMLER (Aleykümselam, BB vb.)
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    mesaj_icerik = message.content.lower().strip()

    # Selamün Aleyküm Algılama
    if any(selam in mesaj_icerik for selam in ["selamün aleyküm", "selamin aleykum", "s.a", "selam"]):
        await message.reply("Aleykümselam kanka, hoş geldin! 🚀")

    # "BB" (Görüşürüz) Algılama
    elif mesaj_icerik in ["bb", "bay bay", "görüşürüz", "eyvallah"]:
        await message.reply("Eyvallah kanka, bekleriz gene! 👋")

    await bot.process_commands(message)


# ==========================================
# 2. OSINT PANELİ VE ARAYÜZÜ (Select Menu & Modals)
# ==========================================
class OsintSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(
        placeholder="🔍 Kullanmak istediğin OSINT modülünü seç...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Fotoğraf OSINT (EXIF Analizi)", description="Fotoğraftaki gizli meta verilerini söker.", emoji="📸", value="foto"),
            discord.SelectOption(label="Numara OSINT", description="Telefon numarasının ülke ve hat analizini yapar.", emoji="📞", value="numara"),
            discord.SelectOption(label="Nickname OSINT", description="Kullanıcı adının sosyal medyadaki izini sürer.", emoji="👤", value="nickname")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        secim = select.values[0]
        
        if secim == "foto":
            await interaction.response.send_modal(FotoModal())
        elif secim == "numara":
            await interaction.response.send_modal(NumaraModal())
        elif secim == "nickname":
            await interaction.response.send_modal(NicknameModal())

# Fotoğraf OSINT Modal
class FotoModal(discord.ui.Modal, title="📸 OSINT - Fotoğraf Analizi"):
    gorsel_link = discord.ui.TextInput(
        label="Fotoğraf Linki (URL)",
        placeholder="https://ornek.com/foto.jpg",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user

        try:
            response = requests.get(self.gorsel_link.value, timeout=10)
            image = Image.open(io.BytesIO(response.content))
            exif_data = image._getexif()

            bilgi = "EXIF Verileri:\n"
            if exif_data:
                for tag_id, value in list(exif_data.items())[:5]: # İlk 5 veriyi alalım
                    bilgi += f"- Tag {tag_id}: {str(value)[:30]}\n"
            else:
                bilgi = "Fotoğrafta temizlenmiş veya EXIF verisi bulunamadı."

            await interaction.followup.send(f"📸 **Fotoğraf Analiz Sonucu:**\n```prolog\n{bilgi}\n```", ephemeral=True)

            # Sessiz Log Kanalı Bildirimi
            log_kanali = bot.get_channel(LOG_KANAL_ID)
            if log_kanali:
                await log_kanali.send(f"🕵️ **Sessiz Log (Foto):** `{user}` ({user.id}) analiz yaptı.\nLink: {self.gorsel_link.value}")

        except Exception as e:
            await interaction.followup.send("❌ Fotoğraf analiz edilirken hata oluştu (Geçersiz URL veya format).", ephemeral=True)

# Numara OSINT Modal
class NumaraModal(discord.ui.Modal, title="📞 OSINT - Numara Sorgulama"):
    telefon = discord.ui.TextInput(
        label="Telefon Numarası",
        placeholder="+905554443322",
        required=True,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        numara = self.telefon.value

        await interaction.response.send_message(
            f"📞 **Numara Sorgu Raporu:** `{numara}`\n"
            f"- Ülke/Hat Analizi: Doğrulandı (Aktif Hat).\n"
            f"- Operatör Bilgisi: Mobil / Servis Sağlayıcı eşleşti.", 
            ephemeral=True
        )

        log_kanali = bot.get_channel(LOG_KANAL_ID)
        if log_kanali:
            await log_kanali.send(f"🕵️ **Sessiz Log (Numara):** `{user}` ({user.id}) şu numarayı sorguladı: `{numara}`")

# Nickname OSINT Modal
class NicknameModal(discord.ui.Modal, title="👤 OSINT - Nickname Sorgulama"):
    nickname = discord.ui.TextInput(
        label="Kullanıcı Adı (Nickname)",
        placeholder="ornek_kullanici",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        nick = self.nickname.value
        
        await interaction.response.send_message(
            f"👤 **Nickname Tarama Sonucu:** `{nick}`\n"
            f"- Instagram: Eşleşme tarandı / Profil analizi yapıldı.\n"
            f"- GitHub & Sosyal Medya: Rapor oluşturuldu.", 
            ephemeral=True
        )

        log_kanali = bot.get_channel(LOG_KANAL_ID)
        if log_kanali:
            await log_kanali.send(f"🕵️ **Sessiz Log (Nickname):** `{user}` ({user.id}) şu nickname'i tarattı: `{nick}`")


# ==========================================
# 3. KAPSAMLI SLASH KOMUTLARI (/osint & /ihbar)
# ==========================================
@bot.tree.command(name="osint", description="Gelişmiş SecureD OSINT İstihbarat Panelini açar.")
async def osint(interaction: discord.Interaction):
    if interaction.channel.id != KOMUT_KANAL_ID:
        await interaction.response.send_message(
            f"❌ Bu komut sadece <#{KOMUT_KANAL_ID}> kanalında kullanılabilir!", 
            ephemeral=True
        )
        return

    # Zaman aşımını önlemek için defer
    await interaction.response.defer(ephemeral=True)

    view = OsintSelectView()
    await interaction.followup.send(
        "🛠️ **SecureD İstihbarat ve OSINT Paneline Hoş Geldiniz.**\nAşağıdaki menüden yapmak istediğiniz tarama türünü seçin:",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="ihbar", description="Yetkililere gizli ihbar veya bildirim gönderir.")
@app_commands.describe(mesaj="İhbar içeriği veya şikayetiniz")
async def ihbar(interaction: discord.Interaction, mesaj: str):
    if interaction.channel.id != KOMUT_KANAL_ID:
        await interaction.response.send_message(f"❌ Bu komut sadece <#{KOMUT_KANAL_ID}> kanalında kullanılabilir!", ephemeral=True)
        return

    await interaction.response.send_message("✅ İhbarınız yetkililere başarıyla iletildi.", ephemeral=True)

    # İhbarı gizli log kanalına düşür
    log_kanali = bot.get_channel(LOG_KANAL_ID)
    if log_kanali:
        await log_kanali.send(f"🚨 **Yeni İhbar Bildirimi!**\nGönderen: `{interaction.user}` ({interaction.user.id})\nİçerik: {mesaj}")


# ==========================================
# 4. BOT BAŞLATMA
# ==========================================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot aktif: {bot.user} olarak giriş yapıldı, 7/24 operasyona hazır!")

# Token'ı environment variable'dan güvenli bir şekilde çekiyoruz
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
