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

# =========================
# GERENCIADOR DE BOTS
# =========================

def get_bot_livre(guild_id, canal_id):

    # se já tem bot neste canal, reutiliza
    for b in bots:

        guild = b.get_guild(guild_id)
        if not guild:
            continue

        vc = guild.voice_client

        if vc and vc.channel and vc.channel.id == canal_id:
            return b

    # procurar bot livre
    for b in bots:

        guild = b.get_guild(guild_id)
        if not guild:
            continue

        vc = guild.voice_client

        if not vc or not vc.is_connected():
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
        musica: str = commands.Param(autocomplete=autocompletar_musicas),
        loop: bool = commands.Param(default=False, description="Ativar modo 24/7 (Loop infinito)?")
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

        canal_usuario = inter.author.voice.channel

        bot_escolhido = get_bot_livre(
            inter.guild.id,
            canal_usuario.id
        )

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

        if vc.is_playing():
            vc.stop()

        # ==========================================
        # A MÁGICA DO 24/7
        # ==========================================
        # Se 'loop' for True, o FFmpeg repete o arquivo infinitamente
        opcoes_iniciais = "-stream_loop -1" if loop else ""
        audio = disnake.FFmpegPCMAudio(caminho, before_options=opcoes_iniciais)

        def depois_tocar(error):
            # O bot SÓ vai se desconectar se não estiver no modo 24/7
            if not loop:
                fut = asyncio.run_coroutine_threadsafe(
                    vc.disconnect(),
                    bot_escolhido.loop
                )
                try:
                    fut.result()
                except:
                    pass

        vc.play(audio, after=depois_tocar)

        texto_loop = "\n🔄 **Modo 24/7 Ativado!**" if loop else ""
        await inter.edit_original_response(
            content=f"🎵 **{musica}**\n🤖 Bot usado: **{bot_escolhido.user.name}**{texto_loop}"
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
