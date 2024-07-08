import discord
from discord.ext import commands
import asyncio
import os
import yt_dlp as youtube_dl
from dotenv import load_dotenv

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


queue = []


@bot.event
async def on_ready():
    print(f'Bot {bot.user} jest gotowy!')


@bot.command(name='play', help='Odtwarza muzykę z YouTube')
async def play(ctx, url):
    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop)
        queue.append(player)
        await ctx.send(f'Dodano do kolejki: {player.title}')

        if ctx.voice_client is None:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                await channel.connect()
            else:
                await ctx.send("Musisz być na kanale głosowym, aby użyć tej komendy.")
                return

        if not ctx.voice_client.is_playing():
            await play_next(ctx)


async def play_next(ctx):
    if queue:
        player = queue.pop(0)
        ctx.voice_client.play(player, after=lambda e: bot.loop.create_task(play_next(ctx)))
        await ctx.send(f'Odgrywam: {player.title}')
    else:
        await ctx.voice_client.disconnect()


@bot.command(name='stop', help='Zatrzymuje odtwarzanie muzyki')
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    queue.clear()
    await voice_client.disconnect()
    await ctx.send('Muzyka zatrzymana.')


@bot.command(name='skip', help='Pomija aktualnie odtwarzany utwór')
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send('Pomijanie utworu...')


# Komendy dodające określone piosenki do kolejki
@bot.command(name='norbi', help='Dodaje do kolejki piosenkę "Norbiego"')
async def add_norbi(ctx):
    url = 'https://www.youtube.com/watch?v=u1I9ITfzqFs'
    await add_song(ctx, url)


@bot.command(name='panek', help='Dodaje do kolejki piosenkę "Panka"')
async def add_panek(ctx):
    url = 'https://www.youtube.com/watch?v=GAZU62dMhkg'
    await add_song(ctx, url)


@bot.command(name='wirus', help='Dodaje do kolejki piosenkę "Wirusa"')
async def add_wirus(ctx):
    url = 'https://www.youtube.com/watch?v=M9XbJxKSTlk'
    await add_song(ctx, url)


@bot.command(name='filip', help='Dodaje do kolejki piosenkę "Filipa"')
async def add_filip(ctx):
    url = 'https://www.youtube.com/watch?v=_UpJBdXrYjo'
    await add_song(ctx, url)


@bot.command(name='chwaster', help='Dodaje do kolejki piosenkę "Chwastera"')
async def add_chwaster(ctx):
    url = 'https://www.youtube.com/watch?v=SzzERnsKMFg'
    await add_song(ctx, url)


@bot.command(name='stasiak', help='Dodaje do kolejki piosenkę "Stasiaka"')
async def add_stasiak(ctx):
    url = 'https://www.youtube.com/watch?v=EssaGhC29zo'
    await add_song(ctx, url)


@bot.command(name='przemek', help='Dodaje do kolejki piosenkę "Przemka"')
async def add_przemek(ctx):
    url = 'https://www.youtube.com/watch?v=PSg7Zs5vlBQ'
    await add_song(ctx, url)


@bot.command(name='gamala', help='Dodaje do kolejki piosenkę "Gamali"')
async def add_gamala(ctx):
    url = 'https://youtu.be/bpOSxM0rNPM?si=QKxKQ_2R4R3yd4iO'
    await add_song(ctx, url)


async def add_song(ctx, url):
    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop)
        queue.append(player)
        await ctx.send(f'Dodano do kolejki: {player.title}')

        if ctx.voice_client is None:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                await channel.connect()
            else:
                await ctx.send("Musisz być na kanale głosowym, aby użyć tej komendy.")
                return

        if not ctx.voice_client.is_playing():
            await play_next(ctx)
# Uruchomienie bota

bot.run(DISCORD_BOT_TOKEN)