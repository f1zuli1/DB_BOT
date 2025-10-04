import discord
import random
import re
import os
from discord.ext import commands, tasks
from discord import ui, ButtonStyle, TextStyle
from collections import defaultdict
from logic import *
from logic import Pokemon
from logic import Wizard,Fighter
from logic import quiz_questions
from logic import DB_Manager
from logic import allowed_domains, warnings
from config import token, DATABASE


user_responses = {}
points = defaultdict(int)
manager = DB_Manager(DATABASE)
manager.create_tables()

# Bot için yetkileri/intents ayarlama
intents = discord.Intents.default()  # Varsayılan ayarların alınması
intents.messages = True              # Botun mesajları işlemesine izin verme
intents.message_content = True       # Botun mesaj içeriğini okumasına izin verme
intents.guilds = True                # Botun sunucularla çalışmasına izin verme

intents = discord.Intents.default()
intents.message_content = True
# Tanımlanmış bir komut önekine ve etkinleştirilmiş amaçlara sahip bir bot oluşturma
bot = commands.Bot(command_prefix=["!", "$"], intents=intents)

@bot.event
async def on_ready():
    print(f'Giriş yapıldı:  {bot.user.name}')

@bot.command()
async def start(ctx):
    await ctx.send("Merhaba! Ben bir sohbet yöneticisi botuyum!")

#-----------------TRANSLATE------------------------------------------------------------------------------------------------------------------------------

class PersistentView(discord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=None)
        self.owner = owner

    @discord.ui.button(label="Cevap al", style=discord.ButtonStyle.primary, custom_id="text_ans")
    async def text_ans_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        obj = TextAnalysis.memory[self.owner][-1]
        await interaction.response.send_message(obj.response, ephemeral=True)

    @discord.ui.button(label="Mesajı çevirin", style=discord.ButtonStyle.secondary, custom_id="text_translate")
    async def text_translate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        obj = TextAnalysis.memory[self.owner][-1]
        await interaction.response.send_message(obj.translation, ephemeral=True)

@bot.command(name="cevir")
async def start(ctx, *, text: str):
    TextAnalysis(text, ctx.author.name)
    view = PersistentView(ctx.author.name)
    await ctx.send("Mesajını aldım! Bununla ne yapmak istiyorsun?", view=view)

#------------------BAN---------------------------------------------------------------------------------------------------------------------------------
# Mesajda qadağan olunmuş link olub olmadığını yoxlayan funksiyası
def contains_unallowed_link(message_content):
    urls = re.findall(r'(https?://\S+)', message_content)
    for url in urls:
        if not any(domain in url for domain in allowed_domains):
            return True
    return False

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Botun öz mesajlarına reaksiya vermə

    if contains_unallowed_link(message.content):
        user_id = message.author.id

        # Əgər istifadəçi artıq xəbərdarlıq alıbsa, ban et
        if warnings.get(user_id, 0) >= 1:
            try:
                await message.author.ban(reason="Shared a banned link for the second time")
                await message.channel.send(f"{message.author}He was banned for sharing a banned link for the second time.")
                warnings.pop(user_id, None)  # İstifadəçini dictionary-dən sil
            except Exception as e:
                await message.channel.send(f"Unable to ban: {e}")
        else:
            # Birinci xəbərdarlıq
            warnings[user_id] = 1
            await message.channel.send(f"{message.author}, You shared a banned link! Next time you will be banned.")

    await bot.process_commands(message)

#--------------QUIZ-----------------------------------------------------------------------------------------------------------------------------------------

# Start quiz komutu
@bot.command(name="startquiz")
async def start_quiz(ctx):
    user_id = ctx.author.id
    if user_id in user_responses:
        await ctx.send("Zaten bir quiz başlattınız!")
        return

    user_responses[user_id] = 0  # Kullanıcı için quiz başlangıcı
    points[user_id] = 0          # Puanı sıfırla
    await send_question(ctx, user_id)

async def send_question(ctx_or_interaction, user_id):
    question = quiz_questions[user_responses[user_id]]
    buttons = question.gen_buttons()
    view = discord.ui.View()
    for button in buttons:
        view.add_item(button)

    if isinstance(ctx_or_interaction, commands.Context):
        await ctx_or_interaction.send(question.text, view=view)
    else:
        await ctx_or_interaction.followup.send(question.text, view=view)
#question
@bot.event
async def on_interaction(interaction):
    user_id = interaction.user.id
    if user_id not in user_responses:
        # Eğer etkileşim daha önce yanıtlandıysa followup ile gönder
        if interaction.response.is_done():
            await interaction.followup.send("Lütfen !startquiz komutunu yazarak testi başlatın", ephemeral=True)
        else:
            await interaction.response.send_message("Lütfen !startquiz komutunu yazarak testi başlatın", ephemeral=True)
        return

    custom_id = interaction.data.get("custom_id")
    if not custom_id:
        return

    if custom_id.startswith("correct"):
        await interaction.response.send_message("Doğru cevap!", ephemeral=True)
        points[user_id] += 1
    elif custom_id.startswith("wrong"):
        await interaction.response.send_message("Yanlış cevap!", ephemeral=True)

    user_responses[user_id] += 1
    if user_responses[user_id] > len(quiz_questions) - 1:
        await interaction.followup.send(f"Tebrikler sınav bitti! Toplam Puanınız: {points[user_id]}")
    else:
        await send_question(interaction, user_id)

#--------------POKEMON-----------------------------------------------------------------------------------------------------------------------------------------------

# '!go' komutu
@bot.command()
async def go(ctx):
    author = ctx.author.name  # Komutu çağıran kullanıcının adını alır
    if author not in Pokemon.pokemons:  # Bu kullanıcı için zaten bir Pokémon olup olmadığını kontrol ederiz
        chance = random.randint(1, 3)  # 1 ile 3 arasında rastgele bir sayı oluştururuz
        # Rastgele sayıya göre bir Pokémon nesnesi oluştururuz
        if chance == 1:
            pokemon = Pokemon(author)  # Standart bir Pokémon oluştururuz
        elif chance == 2:
            pokemon = Wizard(author)  # Wizard türünde bir Pokémon oluştururuz
        elif chance == 3:
            pokemon = Fighter(author)  # Fighter türünde bir Pokémon oluştururuz
        await ctx.send(await pokemon.infopokemon())  # Pokémon hakkında bilgi gönderilmesi
        image_url = await pokemon.show_img()  # Pokémon resminin URL'sini alma
        if image_url:
            name=await pokemon.get_name()
            color=discord.Color.orange()
            embed = discord.Embed(color=color,title=name.upper())
            boy=pokemon.height/10
            kilo=pokemon.weight/10
            hp=pokemon.hp
            power=pokemon.power
            embed.add_field(name="Kilo",value=kilo,inline=True)
            embed.add_field(name="Boy",value=boy,inline=True)
            embed.add_field(name="",value="",inline=False) 
            embed.add_field(name="Hp",value=hp,inline=True)
            embed.add_field(name="Power",value=power,inline=True)   # Gömülü mesajı oluşturma
            embed.set_image(url=image_url)  # Pokémon'un görüntüsünün ayarlanması
            await ctx.send(embed=embed)  # Görüntü içeren gömülü bir mesaj gönderme
        else:
            await ctx.send("Pokémonun görüntüsü yüklenemedi!")
    else:
        await ctx.send("Zaten kendi Pokémonunuzu oluşturdunuz!")  # Bir Pokémon'un daha önce oluşturulup oluşturulmadığını gösteren bir mesaj



@bot.command()
async def attack(ctx):
    target = ctx.message.mentions[0] if ctx.message.mentions else None  # Mesajda belirtilen kullanıcıyı alırız
    if target:  # Kullanıcının belirtilip belirtilmediğini kontrol ederiz
        # Hem saldırganın hem de hedefin Pokémon sahibi olup olmadığını kontrol ederiz
        if target.name in Pokemon.pokemons and ctx.author.name in Pokemon.pokemons:
            enemy = Pokemon.pokemons[target.name]  # Hedefin Pokémon'unu alırız
            attacker = Pokemon.pokemons[ctx.author.name]  # Saldırganın Pokémon'unu alırız
            result = await attacker.attack(enemy)  # Saldırıyı gerçekleştirir ve sonucu alırız
            await ctx.send(result)  # Saldırı sonucunu göndeririz
        else:
            await ctx.send("Savaş için her iki tarafın da Pokémon sahibi olması gerekir!")  # Katılımcılardan birinin Pokémon'u yoksa bilgilendiririz
    else:
        await ctx.send("Saldırmak istediğiniz kullanıcıyı etiketleyerek belirtin.")  # Saldırmak için kullanıcıyı etiketleyerek belirtmesini isteriz
# Botun çalıştırılması


@bot.command()
async def infopokemon(ctx):
    author = ctx.author.name
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        await ctx.send(await pokemon.info())
    else:
        await ctx.send("Pokémon'un yok!")


@bot.command()
async def feed(ctx):
    author = ctx.author.name
    if author in Pokemon.pokemons:
        pokemon = Pokemon.pokemons[author]
        await ctx.send(await pokemon.feed())
    else:
        await ctx.send("Pokémon'un yok!")

#------------- MODAL ---------------------------------------------------------------------------------------------------------------------------------------

# Modal pencere tanımlama
class TestModal(ui.Modal, title='Create Profil'):
    field_1 = ui.TextInput(label='Ad')
    field_2 = ui.TextInput(label='Soyad', style=TextStyle.paragraph)
    field_3 = ui.TextInput(label='Dogum Tarixi', placeholder="DD/MM/YY")

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        ad = self.field_1.value
        soyad = self.field_2.value
        dogum_tarixi = self.field_3.value

        manager.insert_profile(user_id, ad, soyad, dogum_tarixi)
        await interaction.response.send_message("Profiliniz kaydedildi!", ephemeral=True)

# Buton tanımlama
class TestButton(ui.Button):
    def __init__(self, label="Profil", style=ButtonStyle.blurple, row=0):
        super().__init__(label=label, style=style, row=row)

    async def callback(self, interaction: discord.Interaction):
        # Sadece modalı göster
        await interaction.response.send_modal(TestModal())

# Buton içeren görünüm
class TestView(ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TestButton(label="Profil"))
# --------------------- Modal ve Buton --------------------------
# --------------------- Komutlar ---------------------

@bot.command()
async def infocommand(ctx):
    await ctx.send("""
Kullanabileceğiniz komutlar şunlardır:

!new_project - yeni bir proje eklemek
!projects - tüm projelerinizi listelemek
!update_projects - proje verilerini güncellemek
!skills - belirli bir projeye beceri eklemek
!delete - bir projeyi silmek
!createprofil - profil oluşturmak
!profil - profili görüntülemek
!deleteprofil - profili silmek
!go - pokemon karti olusturmak
!feed - pokemonun canini artirmak
!attack - rakibin pokemona saldirmak
!cevir - yazdiginiz cumleyi ingilizceye ceviriyor
!startquiz - quizi baslatiyor
acikartirma - acik artirmayi baslatir
			   
-------------------------- $ --------------------------------------

$duel @kullanıcı - bir kullanıcıya satranç düellosu teklif etmek
$game @kullanıcı - duel komutunun kısayolu
$challenge @kullanıcı - duel komutunun kısayolu
$move [taş] [hedef] - bir taşı hedef kareye götürmek
$m [taş] [hedef] - move komutunun kısayolu
$castle [kale] - rok yapmak
$concede - oyunu bırakmak (pes etmek)
$draw - beraberlik teklif etmek
$accept - düello veya beraberlik teklifini kabul etmek
$refuse - düello veya beraberlik teklifini reddetmek
👁️ - göz emojisine tıklayarak oyunu izleyici olarak takip etmek
BAN - http ile baslayan mesaj atarsaniz sizi banliyor
                   
/ping	Botun ping dəyərini göstərir
/checkers	Yeni bir oyun başlatır
/movepiece move:3E 4D	Taxtadan bir fiquru seçib hərəkət etdirir (3E → 4D kimi)
/checkeryourself	Bot özü ilə oyun oynayır (AI vs AI)
/stats	RAM istifadəsini göstərir
""")

#---------------------- Profil ----------------------------------------

#-----  !craeteprofil ---------
@bot.command()
async def createprofil(ctx):
    await ctx.send("Bu düğmeye basarak profil oluşturabilirsiniz:", view=TestView())

#------- !profil ---------------
@bot.command()
async def profil(ctx):
    user_id = ctx.author.id
    profile = manager.get_profile(user_id)
    if profile:
        ad, soyad, dogum_tarixi = profile
        await ctx.send(f"ID: {user_id}\nAd: {ad}\nSoyad: {soyad}\nDogum Tarihi: {dogum_tarixi}")
    else:
        await ctx.send("Henüz bir profil oluşturmadınız. !createprofil komutunu kullanın.")

#------- !deleteprofil --------
@bot.command()
async def deleteprofil(ctx, user_id: int):
    profile = manager.get_profile(user_id)
    if profile:
        manager.delete_profile(user_id)
        await ctx.send(f"{user_id} ID’li profil başarıyla silindi.")
    else:
        await ctx.send(f"{user_id} ID’li profili bulamadım.")
        
#--------- Project ----------------------------------------------------------------

@bot.command(name='new_project')
async def new_project(ctx):
    await ctx.send("Lütfen projenin adını girin!")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    name = await bot.wait_for('message', check=check)
    data = [ctx.author.id, name.content]
    await ctx.send("Lütfen projeye ait bağlantıyı gönderin!")
    link = await bot.wait_for('message', check=check)
    data.append(link.content)

    statuses = [x[0] for x in manager.get_statuses()]
    await ctx.send("Lütfen projenin mevcut durumunu girin!", delete_after=60.0)
    await ctx.send("\n".join(statuses), delete_after=60.0)
    
    status = await bot.wait_for('message', check=check)
    if status.content not in statuses:
        await ctx.send("Seçtiğiniz durum listede bulunmuyor. Lütfen tekrar deneyin!", delete_after=60.0)
        return

    status_id = manager.get_status_id(status.content)
    data.append(status_id)
    manager.insert_project([tuple(data)])
    await ctx.send("Proje kaydedildi")

@bot.command(name='projects')
async def get_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "\n".join([f"Project name: {x[2]} \nLink: {x[4]}\n" for x in projects])
        await ctx.send(text)
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

@bot.command(name='skills')
async def skills(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send('Bir beceri eklemek istediğiniz projeyi seçin')
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('Bu projeye sahip değilsiniz, lütfen tekrar deneyin! Beceri eklemek istediğiniz projeyi seçin')
            return

        skills = [x[1] for x in manager.get_skills()]
        await ctx.send('Bir beceri seçin')
        await ctx.send("\n".join(skills))

        skill = await bot.wait_for('message', check=check)
        if skill.content not in skills:
            await ctx.send('Görünüşe göre seçtiğiniz beceri listede yok! Lütfen tekrar deneyin! Bir beceri seçin')
            return

        manager.insert_skill(user_id, project_name.content, skill.content)
        await ctx.send(f'{skill.content} becerisi {project_name.content} projesine eklendi')
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

@bot.command(name='delete_project')
async def delete_project(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Silmek istediğiniz projeyi seçin")
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('Bu projeye sahip değilsiniz, lütfen tekrar deneyin!')
            return

        project_id = manager.get_project_id(project_name.content, user_id)
        manager.delete_project(user_id, project_id)
        await ctx.send(f'{project_name.content} projesi veri tabanından silindi!')
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

@bot.command(name='update_projects')
async def update_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Güncellemek istediğiniz projeyi seçin")
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send("Bir hata oldu! Lütfen güncellemek istediğiniz projeyi tekrar seçin:")
            return

        await ctx.send("Projede neyi değiştirmek istersiniz?")
        attributes = {'Proje adı': 'project_name', 'Açıklama': 'description', 'Proje bağlantısı': 'url', 'Proje durumu': 'status_id'}
        await ctx.send("\n".join(attributes.keys()))

        attribute = await bot.wait_for('message', check=check)
        if attribute.content not in attributes:
            await ctx.send("Hata oluştu! Lütfen tekrar deneyin!")
            return

        if attribute.content == 'Durum':
            statuses = manager.get_statuses()
            await ctx.send("Projeniz için yeni bir durum seçin")
            await ctx.send("\n".join([x[0] for x in statuses]))
            update_info = await bot.wait_for('message', check=check)
            if update_info.content not in [x[0] for x in statuses]:
                await ctx.send("Yanlış durum seçildi, lütfen tekrar deneyin!")
                return
            update_info = manager.get_status_id(update_info.content)
        else:
            await ctx.send(f"{attribute.content} için yeni bir değer girin")
            update_info = await bot.wait_for('message', check=check)
            update_info = update_info.content

        manager.update_projects(attributes[attribute.content], (update_info, project_name.content, user_id))
        await ctx.send("Tüm işlemler tamamlandı! Proje güncellendi!")
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

#----------------------------- CHESS.BOT -----------------------------------------------

# -*- coding: utf-8 -*-
"""
Created on Wed Jan  6 05:15:48 2021

@author: Gortaf
"""

import os
import discord
import asyncio
import time
import datetime
import random
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from dotenv import load_dotenv
from discord.ext import commands

# from discord_slash import SlashCommand, SlashContext

from ChessPieces import Pawn, Rook, Knight, Bishop, Queen, King

load_dotenv()

intents = discord.Intents.default()
intents.members = True
bot.remove_command('help')

# =============================================================================
# Initialise some variables & global data at launch
# =============================================================================
@bot.event
async def on_ready():
	bot.startTime = time.time()
	bot.startDateTime = datetime.datetime.now()

	print(f"Online as {bot.user.name} at {bot.startDateTime}")
	bot.serv_dic = {}
	bot.duel_ids = {}
	bot.spectate_msgs = {}

	await bot.change_presence(activity = discord.Game("$duel @someone"))

	# A dictionnary of all the bot's custom emotes (correspondes to the pieces)
	# 0 for white, 1 for black pieces
	bot.emotes = {
		"pawn": ["<:pawn_white:798140768379863090>","<:pawn_black:798140768379863060>"],
		"rook": ["<:rook_white:798140768166084609>","<:rook_black:798140768438583296>"],
		"bishop": ["<:bishop_white:798140767801311243>","<:bishop_black:798140768102514699>"],
		"knight": ["<:knight_white:798140768383926272>","<:knight_black:798140768204095508>"],
		"queen": ["<:queen_white:798140768476725278>","<:queen_black:798140768442384404>"],
		"king": ["<:king_white:798140768165429278>","<:king_black:798140768187449395>"]
		}

# =============================================================================
# Displays a message when the bot joins a server
# =============================================================================
@bot.event
async def on_guild_join(guild):
	for channel in guild.text_channels:
		if channel.permissions_for(guild.me).send_messages:
			msg = "Thank you for adding me to this server!"

			# Checking for missing perms
			missing_perms = []
			if not channel.permissions_for(guild.me).manage_messages:
				missing_perms.append("-Manage Messages")

			if not channel.permissions_for(guild.me).attach_files:
				missing_perms.append("-Attach Files")

			if not channel.permissions_for(guild.me).manage_channels:
				missing_perms.append("-Manage Channels")

			if not channel.permissions_for(guild.me).manage_roles:
				missing_perms.append("-Manage Roles")

			if not channel.permissions_for(guild.me).external_emojis:
				missing_perms.append("-Using External Emojis")

			if not channel.permissions_for(guild.me).add_reactions:
				missing_perms.append("-Add Reactions")

			if len(missing_perms) != 0:
				to_add = '\n'.join(missing_perms)
				msg += f"\nI appear to be missing the following permissions, please add them before using the $duel command:\n{to_add}"
				msg += "\n\nYou can also have me rejoin through that link to ensure I get the proper permissions: https://discord.com/oauth2/authorize?bot_id=797085070422441984&scope=bot&permissions=268807248"
			await channel.send(msg)
			break


# =============================================================================
# The coroutine that runs the actual duel
# =============================================================================
async def game_on(ctx,duel_channel, duelist, victim, duel_msg):

	def command_check(message):
		return message.channel == duel_channel and message.author != bot.user

	async def endgame():
		await asyncio.sleep(60)
		await duel_channel.delete()

	async def get_piece(idt):
		if white == turnset:
			for piece in white_pieces:
				if piece.idt.lower() == idt.lower():
					return piece
			else:
				return None

		elif black == turnset:
			for piece in black_pieces:
				if piece.idt.lower() == idt.lower():
					return piece

			else:
				return None

	board = [[{"color": None, "piece": None} for i in range(8)] for i in range(8)]

	# Filling the board's color
	col = "W"
	for line in board:
		for cell in line:
			cell["color"] = col

			# Swap the next cell color
			if col == "W":
				col = "B"
			elif col == "B":
				col = "W"

	# Filling the board with pieces
	# White Pawns
	for x in range(len(board[1])):
		board[1][x]["piece"] = Pawn("W",x,1,f"P{x+1}")

	# Black Pawns
	for x in range(len(board[6])):
		board[6][x]["piece"] = Pawn("B",x,6,f"P{x+1}")

	# Rooks
	board[0][0]["piece"] = Rook("W",0,0,"R1")
	board[0][7]["piece"] = Rook("W",7,0,"R2")
	board[7][0]["piece"] = Rook("B",0,7,"R1")
	board[7][7]["piece"] = Rook("B",7,7,"R2")

	# Knights
	board[0][1]["piece"] = Knight("W",1,0,"K1")
	board[0][6]["piece"] = Knight("W",6,0,"K2")
	board[7][1]["piece"] = Knight("B",1,7,"K1")
	board[7][6]["piece"] = Knight("B",6,7,"K2")

	# Bishops
	board[0][2]["piece"] = Bishop("W",2,0,"B1")
	board[0][5]["piece"] = Bishop("W",5,0,"B2")
	board[7][2]["piece"] = Bishop("B",2,7,"B1")
	board[7][5]["piece"] = Bishop("B",5,7,"B2")

	# Queens
	board[0][3]["piece"] = Queen("W",3,0,"Q")
	board[7][3]["piece"] = Queen("B",3,7,"Q")

	# Kings
	board[0][4]["piece"] = King("W",4,0,"K")
	white_king = board[0][4]["piece"]
	board[7][4]["piece"] = King("B",4,7,"K")
	black_king = board[7][4]["piece"]

	# Randomly decides who is white and who is black
	if random.randint(0,1):
		white = duelist
		black = victim

	else:
		white = victim
		black = duelist

	# Initialising stuff
	turnset = white
	winner = None
	old_x = None
	old_y = None
	move_x = None
	move_y = None
	old_piece = None
	castled_rook = False
	white_queen_nb= 1
	black_queen_nb = 1
	white_taken = {"pawn":0,"rook":0,"bishop":0,"knight":0,"queen":0,"king":0}
	black_taken = {"pawn":0,"rook":0,"bishop":0,"knight":0,"queen":0,"king":0}


	msg = f"Here's how you play chess with {ctx.guild.me.mention}:\n```\n"
	msg += "When it's your turn, move your piece with:  $move [piece name] [destination coordinates]\n"
	msg += "For exemple, to move the 3rd Pawn (P3) to the f4 cell, use $move P3 f4\n(note that you can use $m instead of $move, and that the piece's names and positions aren't caps sensitive)\n\n"
	msg += "Castling is done with $castle [castling rook].\nFor exemple, to castle using the R1 rook, use $castle R1\n\n"
	msg += "You can concede anytime with $concede, even if it's not your turn. You can also ask your opponent to declare the game a draw with $draw (they will have to accept).\nTo win, you have to take the king (not just checkmate it)."
	msg += "\n\nWhile I will not register illegal moves, I also won't stop you from putting your king in danger :)\n\n"
	msg += "If someone doesn't take their turn within 10 minutes, the game times out, and the other player is declared winner.\n```"
	await duel_channel.send(msg)

	while True:  # Turns will continue until a King is taken

		if winner == None:

			# Constructing the list of taken pieces as emotes
			white_toadd = ""
			black_toadd = ""
			for taken_piece,nb in white_taken.items():
				if nb == 0:
					continue
				white_toadd += f"  {bot.emotes[taken_piece][1]}\\*{nb}"

			for taken_piece,nb in black_taken.items():
				if nb == 0:
					continue
				black_toadd += f"  {bot.emotes[taken_piece][0]}\\*{nb}"

			turn_msg = f"**White:** {white.name}  -{white_toadd}\n**Black:** {black.name}  -{black_toadd}"

			if old_x != None and old_y != None:
				turn_msg+=f"\nLast turn: **{old_piece.idt}** moved (*{chr(old_x+97)}{old_y+1}* → *{chr(move_x+97)}{move_y+1}*)"
				if castled_rook:
					castled_rook = False
					turn_msg+=" **-castling-**"

			turn_msg += f"\nWaiting for a play from: {turnset.mention}"
		else:
			turn_msg = f"**White:** {white.name}\n**Black:** {black.name}\n**{winner.name} WINS!**"

		# Checks if either king is in check
		if winner == None:
			white_check = white_king.is_in_check(board)
			black_check = black_king.is_in_check(board)

		if white_check[0]:
			turn_msg += "\n**⚠️---THE WHITE KING IS IN CHECK---⚠️**\n"
		if black_check[0]:
			turn_msg += "\n**⚠️---THE BLACK KING IS IN CHECK---⚠️**\n"

		# Initalising the list of pieces of both players
		white_pieces = []
		black_pieces = []

		# Using PIL to construct the chessboard
		board_img = Image.open("Ressources/ChessBoard.png")
		start_x = 22
		start_y = 1200
		cell_size = 162
		offset = cell_size//4

		# Loading the font for the pieces ID
		font = ImageFont.truetype("Ressources/F25_font.ttf", 31)
		draw = ImageDraw.Draw(board_img)

		for i in range(8):
			for j in range(8):

				# Calculating this cell's absolute coordinates (in px)
				point_coords = (start_x + j*cell_size+offset, start_y- i*cell_size-offset)
				piece = board[i][j]["piece"]

				# Skipping empty cells
				if piece == None:
					continue
				else:

					# putting the piece into the piece list
					if piece.color == "W":
						white_pieces.append(piece)
					elif piece.color == "B":
						black_pieces.append(piece)

					# Getting the corresponding piece file
					piece_filepath = "Ressources/Pieces/"+piece.file
					piece_img = Image.open(piece_filepath)


				# pasting the piece into the board
				board_img.paste(piece_img,point_coords,piece_img)
				piece_img.close()

				# Adding the text
				point_coords = list(point_coords)
				point_coords[0] = point_coords[0] - (offset//3)
				point_coords = tuple(point_coords)

				# The text is black, or red if the piece is threatening a king
				color = "black"
				if piece in white_check[1] or piece in black_check[1]:
					color = "red"

				draw.text(point_coords,piece.idt,font=font,fill=color)

		# If there was a move last turn, draw a line representing it
		if old_x != None and old_y != None:
			old_px = (start_x+old_x*cell_size+int(2.6*offset),start_y-old_y*cell_size+(offset//1.1))
			new_px = (start_x+move_x*cell_size+int(2.6*offset),start_y-move_y*cell_size+(offset//1.1))

			draw.line(old_px + new_px, fill = "red", width=5)

		# Saving the image
		randname = random.randint(100,9999999)
		board_img.save(str(randname)+".png")
		board_img.close()

		# Sending updated board & updated turn message, then deleting the image
		turn_sent = await duel_channel.send(content=turn_msg, file=discord.File(str(randname)+".png"))
		os.remove(str(randname)+".png")

		if winner != None:
			await duel_channel.send(f"{winner.name} wins the game!\n(This channel will be deleted in 1 minute)")
			await endgame()
			return

		end_turn = True
		while True and end_turn:

			try:
				reply = await bot.wait_for("message", check=command_check, timeout = 600)

			except asyncio.TimeoutError:
				await duel_channel.send(f"{turnset.mention} didn't play in time (10min). Game canceled.\n(This channel will be deleted in 1 minute)")
				await endgame()
				return


			from_player = reply.author == white or reply.author == black
			if "$concede" in reply.content and from_player:
				await duel_channel.send(f"**{reply.author.name} has conceded!**\n(This channel will be deleted in 1 minute)")
				await endgame()
				return

			exited_draw = False
			if "$draw" == reply.content and from_player:
				bot_msg = await duel_channel.send(f"{reply.author.name} wants to declare this game a draw.\nType $accept to accept\nType $refuse to refuse")

				# Waiting for an answer
				while True:
					try:
						reply_draw = await bot.wait_for("message", check=command_check, timeout = 180)

					except asyncio.TimeoutError:
						bot_reply = await duel_channel.send("No reply was given in time. Draw request canceled.")
						exited_draw = True
						break

					# The draw request was accepted. Ending the match
					if reply_draw.content == "$accept":
						await duel_channel.send("**This match has been declared a draw!**\n(This channel will be deleted in 1 minute)")
						await endgame()
						return

					elif reply_draw.content == "$refuse":
						bot_reply = await duel_channel.send("Draw request refused. The match continues!")
						exited_draw = True
						break

					else:
						tmp = await reply_draw.channel.fetch_message(reply_draw.id)
						await tmp.add_reaction("💬")
						await tmp.delete(delay = 15)

			# Returns at the start of the loop & cleans the draw message
			if exited_draw:
				await reply.delete(delay = 2)
				await reply_draw.delete(delay = 2)
				await bot_reply.add_reaction("❌")
				await bot_reply.delete(delay = 10)
				await bot_msg.delete(delay = 2)

				continue

			# If there is no commands, then this is a chat message (15sec lifespan)
			mv_cmd = "$move" not in reply.content and "$m " not in reply.content
			if mv_cmd and "$castle" not in reply.content and "$draw" not in reply.content:
				tmp = await reply.channel.fetch_message(reply.id)
				await tmp.add_reaction("💬")
				await tmp.delete(delay = 15)
				continue

			if reply.author == turnset:
				elements = reply.content.split(" ")

				# Easy way to avoid problems between commands argument number
				if len(elements)<3:
					elements.append(None)
					elements.append(None)

				# Finding the piece in question (if it exists)
				piece = await get_piece(elements[1])
				if piece == None:
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue

				if "$castle" in reply.content:

					# Only Rooks can castle
					if type(piece) == Rook:
						king = await get_piece("K")

						# Can't castle if K or R has moved
						if piece.can_castle and king.can_castle:
							castle_check = piece.castling(king.x, king.y, board)

							# Can't castle if there's anything in the path
							# Also can't castle if king is in check
							if castle_check[0] and not king.in_check:

								# Results depend on the type of castling
								if castle_check[1] == "big":
									k_mod = -2
									r_mod = 3

								elif castle_check[1] == "small":
									k_mod = 2
									r_mod = -2

								# Moving the Rook
								old_x = piece.x
								old_y = piece.y
								board[piece.y][piece.x+r_mod]["piece"] = piece
								board[old_y][old_x]["piece"] = None
								piece.x = piece.x + r_mod
								piece.can_castle = False

								# Moving the king
								old_x = king.x
								old_y = king.y
								board[king.y][king.x+k_mod]["piece"] = king
								board[old_y][old_x]["piece"] = None
								king.x = king.x + k_mod
								king.can_castle = False

								# Updates the move coords for the movement line
								move_x = king.x
								move_y = king.y
								old_piece = king
								castled_rook = True

								# This turn ends
								end_turn = False
								continue

					# Castling failed
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue


				try:
					move_x = ord(elements[2][0].lower())-97
					move_y = int(elements[2][1])-1

				except Exception as e:
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue

				old_x = piece.x
				old_y = piece.y

				# Attempts to move the piece
				if piece.move(move_x, move_y, board):

					old_piece = piece
					cur_piece = board[move_y][move_x]["piece"]

					if cur_piece != None:
						if turnset == white:
							white_taken[cur_piece.piece_type] += 1

						else:
							black_taken[cur_piece.piece_type] += 1


					# If a king is taken, the game ends
					if board[move_y][move_x]["piece"] != None and board[move_y][move_x]["piece"].idt == "K":
						winner = turnset

					board[move_y][move_x]["piece"] = piece
					board[old_y][old_x]["piece"] = None

					# If a pawn gets to the end of the board, it becomes a queen
					if "P" in piece.idt and ((piece.y == 0 and piece.color == "B") or (piece.y == 7 and piece.color == "W")):

						# Avoids new queens having the same id
						if turnset == white:
							to_add = white_queen_nb
							white_queen_nb +=1

						else:
							to_add = black_queen_nb
							black_queen_nb +=1

						board[move_y][move_x]["piece"] = Queen(piece.color,piece.x,piece.y,f"Q{to_add}")


					break

				else:
					tmp = await reply.channel.fetch_message(reply.id)
					await tmp.add_reaction("👎")
					await tmp.delete(delay =2)
					continue
			else:
				tmp = await reply.channel.fetch_message(reply.id)
				await tmp.add_reaction("🤨")
				await tmp.delete(delay =2)
				continue

		# Deleting the messages
		tmp = await reply.channel.fetch_message(reply.id)
		await tmp.delete()
		tmp = await turn_sent.channel.fetch_message(turn_sent.id)
		await tmp.delete()

		# next turn
		if turnset == white:
			turnset = black
		elif turnset == black:
			turnset = white

		end_turn = False



# =============================================================================
# The $duel command is used to start a game
# =============================================================================
@bot.command(pass_context=True, aliases = ["game","challenge"])
async def duel(ctx, victim_str=None, *args):

	# Called to verify if a message is a reply to a duel request
	def accept_check(message):
		return (message.content == "$accept" or message.content == "$refuse") and message.author == victim

	if ctx.guild == None:
		await ctx.send("You can only use the duel command in a server.")
		return

	if not victim_str:
		await ctx.send("You need to specify the user you wish to duel.")
		return

	if len(ctx.message.mentions) == 0:
		await ctx.send(f"Cannot find user \"{victim_str.strip('@')}\".")
		return

	# The User objects of the 2 participants
	duelist = ctx.author
	victim = ctx.message.mentions[0]

	if victim == ctx.author:
		await ctx.send("You can't challenge yourself...")
		return

	if victim == bot.user:
		await ctx.send("You cannot challenge me (for your own good).")
		return

	await ctx.send(f"{duelist.mention} has challenged you, {victim.mention}, in a game of chess. Will you accept the duel?\n\nType \"$accept\" to accept the duel.\nType \"$refuse\" to refuse the duel.")

	try:
		reply = await bot.wait_for("message", check=accept_check, timeout = 600)

	except asyncio.TimeoutError:
		await ctx.send(f"{duelist.mention}'s challenge request has expired. {victim.mention} didn't accept in time.")
		return

	if reply.content == "$refuse":
		await ctx.send(f"{victim.mention} has refused {duelist.mention}'s challenge.")
		return

	# If we're here, both parties are ready for the duel
	# Generating duel ID
	duel_id = random.randint(10000, 99999)
	while duel_id in bot.duel_ids.keys():
		duel_id = random.randint(10000, 99999)

	bot.duel_ids[duel_id] = ctx.guild.id

	# Creating duel channel
	overwrites = {
		ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
		duelist: discord.PermissionOverwrite(read_messages=True, send_messages=True),
		victim:  discord.PermissionOverwrite(read_messages=True, send_messages=True)

		}

	if "public" in args:
		overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(send_messages=False)

	else:
		overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(read_messages=False)

	duel_channel = await ctx.guild.create_text_channel(f"chess-{duel_id}", overwrites=overwrites, category=ctx.channel.category)

	# Adding duel entry
	if ctx.guild.id not in bot.serv_dic.keys():
		bot.serv_dic[ctx.guild.id] = {}

	bot.serv_dic[ctx.guild.id][duel_id] = {
		"duel_channel": duel_channel,
		"duelist": duelist,
		"victim": victim,
		"start_time": datetime.datetime.now()
		}

	# Sending the duel message
	msg = f"{victim.mention} has accepted {duelist.mention}'s duel!\nThe duel will take place in {duel_channel.mention}."
	if "private" not in args and "public" not in args:
		msg += "\n\n Everyone can react with 👁️ to this message to gain access to the duel channel as a spectateor."
	duel_msg = await ctx.send(msg)

	# If the game is private, no spectateing is allowed
	if "private" not in args and "public" not in args:
		await duel_msg.add_reaction("👁️")

		# Storing the message to allow spectateors to join
		bot.spectate_msgs[duel_msg.id] = duel_channel

	await game_on(ctx, duel_channel, duelist, victim, duel_msg)
	del bot.spectate_msgs[duel_msg.id]

# =============================================================================
# Fake commands (avoids raising useless errors)
# =============================================================================
@bot.command(pass_context=False)
async def accept(ctx):
	pass
@bot.command(pass_context=False)
async def refuse(ctx):
	pass
@bot.command(pass_context=False)
async def move(ctx):
	pass
@bot.command(pass_context=False)
async def m(ctx):
	pass
@bot.command(pass_context=False)
async def castle(ctx):
	pass
@bot.command(pass_context=False)
async def draw(ctx):
	pass
@bot.command(pass_context=False)
async def concede(ctx):
	pass

# =============================================================================
# Reads reaction for spectateor mode
# =============================================================================
@bot.event
async def on_raw_reaction_add(payload):

	if payload.message_id in bot.spectate_msgs.keys() and payload.emoji.name == "👁️" and payload.user_id != bot.user.id:
		await bot.spectate_msgs[payload.message_id].set_permissions(payload.member, read_messages=True, send_messages=False)

@bot.event
async def on_raw_reaction_remove(payload):

	pass  # Doesn't work currently. the payload of this function doesn't include the member.
# 	if payload.message_id in bot.spectate_msgs.keys() and payload.emoji.name == "👁️" and payload.user_id != bot.user.id:
# 		await bot.spectate_msgs[payload.message_id].set_permissions(message.auth, read_messages=False, send_messages=False)

#--------------------------------- Acik artirma -----------------------------------------------------------------------------------------------------------
#  Kullanıcı kaydı için bir komut
@bot.command()
async def acikartirma(ctx):
    user_id = ctx.author.id
    if user_id in manager.get_users():
        await ctx.send("Zaten kayıtlısınız!")
    else:
        manager.add_user(user_id, ctx.author.name)
        await ctx.send("""Merhaba! Hoş geldiniz! Başarılı bir şekilde kaydoldunuz! Her dakika yeni resimler alacaksınız ve bunları elde etme şansınız olacak! Bunu yapmak için “Al!” butonuna tıklamanız gerekiyor! Sadece “Al!” butonuna tıklayan ilk üç kullanıcı resmi alacaktır! =)""")

# Derecelendirme komutu.
@bot.command()
async def rating(ctx):
    res = manager.get_rating()
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    await ctx.send(f"```\n{res}\n```")

# Resim göndermek için zamanlanmış bir görev
@tasks.loop(minutes=1)
async def send_message():
    for user_id in manager.get_users():
        prize = manager.get_random_prize()
        if not prize:
            print("Kullanılabilir ödül yok, bu tur atlanıyor.")
            continue  # ödül kalmadıysa bu kullanıcı için gönderim yapılmaz

        prize_id, img = prize[:2]
        manager.hide_img(img)
        user = await bot.fetch_user(user_id)
        if user:
            await send_image(user, f'hidden_img/{img}', prize_id)
        manager.mark_prize_used(prize_id)

async def send_image(user, image_path, prize_id):
    with open(image_path, 'rb') as img:
        file = discord.File(img)
        button = discord.ui.Button(label="Al!", custom_id=str(prize_id))
        view = discord.ui.View()
        view.add_item(button)
        await user.send(file=file, view=view)

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        user_id = interaction.user.id

        if manager.get_winners_count(custom_id) < 3:
            res = manager.add_winner(user_id, custom_id)
            if res:
                img = manager.get_prize_img(custom_id)
                with open(f'img/{img}', 'rb') as photo:
                    file = discord.File(photo)
                    await interaction.response.send_message(file=file, content="Tebrikler, resmi aldınız!")
            else:
                await interaction.response.send_message(content="Bu resme zaten sahipsiniz!", ephemeral=True)
        else:
            await interaction.response.send_message(content="Maalesef, bu resmi bir başkası çoktan aldı...", ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    if not send_message.is_running():
        send_message.start()

bot.run(token)