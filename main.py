import disnake
from disnake.ext import commands
import asyncio
import os

# =========================
# CONFIGURAÇÃO
# =========================

TOKENS = [
    "tk",
    "tk",
    "tk"
]

PASTA_MUSICAS = "./music"

bots = []
servidores_ativos = {}  # guild_id -> bot_id

# =========================
# GERENCIADOR DE BOTS
# =========================

def get_bot_livre(guild_id):

    # se já tiver bot ativo neste servidor
    if guild_id in servidores_ativos:
        bot_id = servidores_ativos[guild_id]

        for b in bots:
            if b.user and b.user.id == bot_id:
                return b

    # procurar bot livre
    for b in bots:

        guild = b.get_guild(guild_id)

        if guild:

            vc = guild.voice_client

            if not vc:
                return b

    return None


# =========================
# AUTOCOMPLETE MÚSICAS
# =========================

async def autocompletar_musicas(inter, texto):

    if not os.path.exists(PASTA_MUSICAS):
        return []

    arquivos = [
        f for f in os.listdir(PASTA_MUSICAS)
        if f.endswith((".mp3", ".wav", ".ogg", ".m4a"))
    ]

    resultado = [f for f in arquivos if texto.lower() in f.lower()]

    return resultado[:25]


# =========================
# COG DE MÚSICA
# =========================

class SistemaMusica(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    # -------------------------
    # PLAY
    # -------------------------

    @commands.slash_command(description="Tocar música da pasta")
    async def play(
        self,
        inter: disnake.ApplicationCommandInteraction,
        musica: str = commands.Param(autocomplete=autocompletar_musicas)
    ):

        if not inter.author.voice:
            return await inter.response.send_message(
                "Entre em um canal de voz primeiro.",
                ephemeral=True
            )

        caminho = os.path.join(PASTA_MUSICAS, musica)

        if not os.path.exists(caminho):
            return await inter.response.send_message(
                "Música não encontrada.",
                ephemeral=True
            )

        bot_escolhido = get_bot_livre(inter.guild.id)

        if not bot_escolhido:
            return await inter.response.send_message(
                "❌ Todos os bots estão ocupados.",
                ephemeral=True
            )

        await inter.response.defer()

        guild = bot_escolhido.get_guild(inter.guild.id)
        membro = guild.get_member(inter.author.id)

        if not membro or not membro.voice:
            return await inter.edit_original_response(
                content="Erro ao encontrar seu canal de voz."
            )

        canal = membro.voice.channel

        vc = guild.voice_client

        if not vc:
            vc = await canal.connect()
            servidores_ativos[inter.guild.id] = bot_escolhido.user.id

        if vc.is_playing():
            vc.stop()

        audio = disnake.FFmpegPCMAudio(caminho)

        vc.play(audio)

        await inter.edit_original_response(
            content=f"🎵 **{musica}**\n🤖 Bot usado: **{bot_escolhido.user.name}**"
        )


    # -------------------------
    # ADICIONAR MÚSICA
    # -------------------------

    @commands.slash_command(description="Adicionar música ao bot")
    async def addmusic(
        self,
        inter: disnake.ApplicationCommandInteraction,
        arquivo: disnake.Attachment
    ):

        await inter.response.defer(ephemeral=True)

        if not arquivo.filename.endswith((".mp3", ".wav", ".ogg", ".m4a")):
            return await inter.edit_original_response(
                content="❌ Envie apenas arquivos de áudio."
            )

        if not os.path.exists(PASTA_MUSICAS):
            os.makedirs(PASTA_MUSICAS)

        caminho = os.path.join(PASTA_MUSICAS, arquivo.filename)

        await arquivo.save(caminho)

        await inter.edit_original_response(
            content=f"✅ Música **{arquivo.filename}** adicionada!"
        )

    @commands.slash_command(description="Parar música e desconectar o bot")
    async def stop(self, inter: disnake.ApplicationCommandInteraction):

        bot_usado = get_bot_livre(inter.guild.id)

        if not bot_usado:
            return await inter.response.send_message(
                "❌ Nenhum bot está ativo neste servidor.",
                ephemeral=True
            )

        guild = bot_usado.get_guild(inter.guild.id)

        vc = guild.voice_client

        if not vc:
            return await inter.response.send_message(
                "❌ O bot não está em um canal de voz.",
                ephemeral=True
            )

        if vc.is_playing():
            vc.stop()

        await vc.disconnect()

        if inter.guild.id in servidores_ativos:
            del servidores_ativos[inter.guild.id]

        await inter.response.send_message("🛑 Música parada e bot desconectado.")


# =========================
# INICIAR BOTS
# =========================

def criar_bot():

    bot = commands.Bot(
        command_prefix="!",
        intents=disnake.Intents.all(),
        command_sync_flags=commands.CommandSyncFlags.default()
    )

    bot.add_cog(SistemaMusica(bot))

    @bot.event
    async def on_ready():
        print(f"✅ {bot.user} online!")
    return bot


# =========================
# MAIN
# =========================

async def main():

    if not os.path.exists(PASTA_MUSICAS):
        os.makedirs(PASTA_MUSICAS)

    for token in TOKENS:

        bot = criar_bot()

        bots.append(bot)

    tasks = []

    for bot, token in zip(bots, TOKENS):
        tasks.append(bot.start(token))

    print(f"🚀 Iniciando {len(bots)} bots")

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())