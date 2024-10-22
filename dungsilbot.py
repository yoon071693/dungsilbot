import os 
import logging
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

# 로그 설정
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!!', intents=intents)

queue = []
current_song = None
allowed_channel_id = 1170880422230630470  # 허용된 채널 ID를 저장하는 변수

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

async def join_voice_channel(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
    else:
        msg = await ctx.send(embed=discord.Embed(
            title='🚫 오류',
            description='먼저 음성 채널에 연결해 주세요.',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()

async def play_next(ctx):
    global queue, current_song
    if queue:
        next_song = queue.pop(0)
        title, url = next_song
        voice_client = ctx.voice_client

        try:
            if voice_client.is_playing():
                voice_client.stop()
            voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
            current_song = title
            msg = await ctx.send(embed=discord.Embed(
                title='▶️ 노래를 재생합니다',
                description=f'{title}',
                color=0xF6CEF5
            ))
            await asyncio.sleep(5)
            await msg.delete()
            logging.info(f"Playback started: {title}")

            def after_playing(error):
                if error:
                    logging.error(f"Playback error: {error}")
                asyncio.create_task(play_next(ctx))

            voice_client.source = discord.PCMVolumeTransformer(voice_client.source)
            voice_client.source.after = after_playing
        except Exception as e:
            msg = await ctx.send(embed=discord.Embed(
                title='🚫 오류',
                description=f'노래 재생 중 오류 발생: {e}',
                color=0xF6CEF5
            ))
            await asyncio.sleep(5)
            await msg.delete()
            logging.error(f"Playback error: {e}")

@bot.command()
async def 재생(ctx, *, query):
    if allowed_channel_id is None or ctx.channel.id != allowed_channel_id:
        return

    await join_voice_channel(ctx)

    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'default_search': 'auto',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': '%(id)s.%(ext)s',
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        if 'entries' in info:
            info = info['entries'][0]
        else:
            msg = await ctx.send(embed=discord.Embed(
                title='🚫 오류',
                description='검색 결과를 찾을 수 없습니다.',
                color=0xF6CEF5
            ))
            await asyncio.sleep(5)
            await msg.delete()
            return

        formats = info.get('formats', [])
        url = None
        for format in formats:
            if format.get('acodec') != 'none':
                url = format.get('url')
                break

        if not url:
            msg = await ctx.send(embed=discord.Embed(
                title='🚫 오류',
                description='오디오 URL을 찾을 수 없습니다.',
                color=0xF6CEF5
            ))
            await asyncio.sleep(5)
            await msg.delete()
            return

        title = info['title']
        logging.info(f"Playing URL: {url}")

    voice_client = ctx.voice_client
    if not voice_client.is_playing():
        try:
            voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))

            current_song = title
            msg = await ctx.send(embed=discord.Embed(
                title='▶️ 노래를 재생합니다',
                description=f'{title}',
                color=0xF6CEF5
            ))
            await asyncio.sleep(5)
            await msg.delete()
            logging.info(f"Playback started: {title}")

            def after_playing(error):
                if error:
                    logging.error(f"Playback error: {error}")
                asyncio.create_task(play_next(ctx))

            voice_client.source = discord.PCMVolumeTransformer(voice_client.source)
            voice_client.source.after = after_playing
        except Exception as e:
            msg = await ctx.send(embed=discord.Embed(
                title='🚫 오류',
                description=f'노래 재생 중 오류 발생: {e}',
                color=0xF6CEF5
            ))
            await asyncio.sleep(5)
            await msg.delete()
            logging.error(f"Playback error: {e}")
    else:
        queue.append((title, url))
        msg = await ctx.send(embed=discord.Embed(
            title='🎵 대기열에 추가되었습니다',
            description=f'{title}',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()

@bot.command()
async def 종료(ctx):
    if allowed_channel_id is None or ctx.channel.id != allowed_channel_id:
        return

    voice_client = ctx.voice_client
    if voice_client:
        if voice_client.is_playing():
            voice_client.stop()
        
        await voice_client.disconnect()
        msg = await ctx.send(embed=discord.Embed(
            title='👋 종료',
            description='노래를 종료하고 음성 채팅방에서 나갔습니다.',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()
        logging.info("Disconnected from voice channel")
    else:
        msg = await ctx.send(embed=discord.Embed(
            title='연결된 음성 채팅방 없음',
            description='현재 연결된 음성 채팅방이 없습니다.',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()

@bot.command()
async def 스킵(ctx):
    if allowed_channel_id is None or ctx.channel.id != allowed_channel_id:
        return

    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        msg = await ctx.send(embed=discord.Embed(
            title='⏭️ 스킵',
            description='현재 재생 중인 노래를 스킵했습니다.',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()
        logging.info("Playback skipped")

        await play_next(ctx)
    else:
        msg = await ctx.send(embed=discord.Embed(
            title='😌 휴식',
            description='현재 재생 중인 노래가 없습니다.',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()

@bot.command()
async def 대기(ctx):
    if allowed_channel_id is None or ctx.channel.id != allowed_channel_id:
        return

    if queue:
        # 대기열의 각 곡에 번호를 붙이기
        queue_list = '\n'.join([f"{i+1}. {title}" for i, (title, _) in enumerate(queue)])
        msg = await ctx.send(embed=discord.Embed(
            title='📋 대기 중인 곡',
            description=queue_list,
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()
    else:
        msg = await ctx.send(embed=discord.Embed(
            title='📋 대기 중인 곡',
            description='대기 중인 곡이 없습니다.',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()

@bot.command()
async def 채널설정(ctx, channel: discord.TextChannel):
    if not ctx.message.author.guild_permissions.administrator:
        msg = await ctx.send(embed=discord.Embed(
            title='🚫 오류',
            description='이 명령어를 사용할 권한이 없습니다.',
            color=0xF6CEF5
        ))
        await asyncio.sleep(5)
        await msg.delete()
        return

    global allowed_channel_id
    allowed_channel_id = channel.id
    msg = await ctx.send(embed=discord.Embed(
        title='✅ 채널 설정',
        description=f'명령어를 사용할 수 있는 채널이 {channel.mention}으로 설정되었습니다.',
        color=0xF6CEF5
    ))
    await asyncio.sleep(5)
    await msg.delete()

async def periodic_message(channel):
    while True:
        # 메시지를 보냅니다.
        message = await channel.send("🎵둥실이 열일중🎵")
        
        # 3분 후에 메시지를 삭제합니다.
        await asyncio.sleep(180)  # 3분(180초) 대기
        await message.delete()

        # 4분 대기 후 다시 메시지를 보냅니다.
        await asyncio.sleep(240)  # 4분(240초) 대기


bot.run(os.getenv('DISCORD_TOKEN'))
