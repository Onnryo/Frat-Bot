import asyncio
import discord
import os
import json
import requests
import _thread
import urllib.request
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup as bs
import ast
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from discord.ext import commands

SYMBOL = "$"
privileged = ["Onryo#6072", "j_smitty01#1195", "The27Club#9594"]
server_usernames = {"Onryo#6072": "onryo",
	"j_smitty01#1195": "j_smitty01",
	"The27Club#9594": "seancavi"}
headers = {}

if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')

def init_settings(server):
	settings = {
		"spongemock": True,
		"owo": 0,
	}
	save_settings(server, settings)
	return

def get_settings(server):
	return json.load(open("settings/" + server + ".json"))

def save_settings(server, settings):
	with open('settings/' + server + ".json", 'w') as outfile:
		json.dump(settings, outfile)
	return

def update_settings(server):
	settings = get_settings(server)
	keys = settings.keys()
	if "spongemock" not in keys:
		settings["spongemock"] = True
	if "owo" not in keys:
		settings["owo"] = 0
	save_settings(server, settings)

class VoiceEntry:
	def __init__(self, message, player):
		self.requester = message.author
		self.channel = message.channel
		self.player = player

	def __str__(self):
		fmt = '*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}'
		duration = self.player.duration
		if duration:
			fmt = fmt + ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
		return fmt.format(self.player, self.requester)

class VoiceState:
	def __init__(self, bot):
		self.current = None
		self.voice = None
		self.bot = bot
		self.play_next_song = asyncio.Event()
		self.songs = asyncio.Queue()
		self.skip_votes = set() # a set of user_ids that voted
		self.audio_player = self.bot.loop.create_task(self.audio_player_task())

	def is_playing(self):
		if self.voice is None or self.current is None:
			return False

		player = self.current.player
		return not player.is_done()

	@property
	def player(self):
		return self.current.player

	def skip(self):
		self.skip_votes.clear()
		if self.is_playing():
			self.player.stop()

	def toggle_next(self):
		self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

	async def audio_player_task(self):
		while True:
			self.play_next_song.clear()
			self.current = await self.songs.get()
			await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
			self.current.player.start()
			await self.play_next_song.wait()

class Sound:
	def __init__ (self, bot):
		self.bot = bot
		self.voice_states = {}

	def get_voice_state(self, server):
		state = self.voice_states.get(server.id)
		if state is None:
			state = VoiceState(self.bot)
			self.voice_states[server.id] = state
		return state

	async def create_voice_client(self, channel):
		voice = await self.bot.join_voice_channel(channel)
		state = self.get_voice_state(channel.server)
		state.voice = voice

	def __unload(self):
		for state in self.voice_states.values():
			try:
				state.audio_player.cancel()
				if state.voice:
					self.bot.loop.create_task(state.voice.disconnect())
			except:
				pass

	@commands.command(pass_context=True, no_pm=True)
	async def summon(self, ctx):
		summoned_channel = ctx.message.author.voice_channel
		if summoned_channel is None:
			msg = "You have to be in a voice channel to use this command."
			await self.bot.send_message(ctx.message.channel, msg)
			return False
		state = self.get_voice_state(ctx.message.server)
		if state.voice is None:
			state.voice = await self.bot.join_voice_channel(summoned_channel)
		else:
			await state.voice.move_to(summoned_channel)
		return True

	@commands.command(pass_context=True, no_pm=True)
	async def sound(self, ctx):
		try:
			params = ctx.message.content.split(" ")[1:]
		except:
			params = []
		if len(params) > 0:
			if params[0] == "list":
				sounds = os.listdir("sound/")
				sounds.sort()
				for i in range(0, len(sounds)):
					sounds[i] = ".".join(sounds[i].split('.')[:-1])
				msg = "\n".join(str(s) for s in sounds)
				await self.bot.send_message(ctx.message.channel, msg)
				return
			else:
				sounds = os.listdir("sound/")
				sounds.sort()
				for i in range(0, len(sounds)):
					sounds[i] = ".".join(sounds[i].split('.')[:-1])
				if params[0] not in sounds:
					msg = "You want me to play wot?"
					await self.bot.send_message(ctx.message.channel, msg)
					return
				else:
					sound_path = "sound/" + params[0] + ".mp3"
					state = self.get_voice_state(ctx.message.server)
					if state.voice is None:
						success = await ctx.invoke(self.summon)
						if not success:
							return
					player = state.voice.create_ffmpeg_player(sound_path)
					player.start()

	@commands.command(pass_context=True, no_pm=True)
	async def banish(self, ctx):
		server = ctx.message.server
		state = self.get_voice_state(server)
		if state.is_playing():
			player = state.player
			player.stop()
		try:
			state.audio_player.cancel()
			del self.voice_states[server.id]
			await state.voice.disconnect()
		except:
			pass

class Spongemock:
	def __init__(self, bot, text=""):
		self.bot = bot
		self.text = text

	@commands.command(pass_context=True, no_pm=True)
	async def spongemock(self, ctx):
		i = 0
		async for message in self.bot.logs_from(ctx.message.channel, limit=10):
			if i == 1:
				self.text = message.content
				break
			i += 1
		if len(self.text) < 50:
			self.create_image()
			await self.bot.send_file(ctx.message.channel, 'spongemock/out.jpg')
			return
		else:
			msg = ''
			b = False
			for c in self.text.lower():
				msg += c.upper() if b else c.lower()
				if c.isalpha():
					b = not b
			await self.bot.send_message(ctx.message.channel, msg)
			return

	def create_image(self):
		msg = ''
		b = False
		for c in self.text.lower():
			msg += c.upper() if b else c.lower()
			if c.isalpha():
				b = not b
		img = Image.open('spongemock/template.jpg')
		draw = ImageDraw.Draw(img)
		font = ImageFont.truetype('spongemock/bluefish.otf', 100)
		W, H = (981, 692)
		w, h = draw.textsize(msg, font=font)
		if w > W:
			for i in range(20, len(msg)):
				if msg[i] == ' ':
					msg2 = msg[i:]
					msg = msg[:i]
					break
			w, h = draw.textsize(msg, font=font)
			w2, h2 = draw.textsize(msg2, font=font)
			draw.text(((W-w)/2, H-h-h2-15), msg, (255,255,255), font=font)
			draw.text(((W-w2)/2, H-h2-10), msg2, (255,255,255), font=font)
		else:
			draw.text(((W-w)/2,H-h-10), msg, (255,255,255), font=font)
		img.save('spongemock/out.jpg')

	async def auto(self, message):
		self.create_image()
		await self.bot.send_file(message.channel, 'spongemock/out.jpg')
		return

class Torrents:
	def __init__(self, bot):
		self.bot = bot
		self.results = {}

	async def get_results(self, ctx):
		try:
			query = " ".join(ctx.message.content.split(' ')[1:])
			base = "https://thepiratebay.org/search/"
			url = base + query.replace(" ", "%20")
			request = urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'})).read()
			soup = bs(request, "html.parser")
			trs = soup.find("table", id="searchResult").find_all("tr")[1:]
			self.results[ctx.message.server.id] = []
			for tr in trs:
				#name, size, seeders, leachers, magnet, href
				item = []
				item.append(tr.find("a", class_="detLink").text)
				item.append(tr.find("font", class_="detDesc").text.split(", ")[1].split(" ")[1].replace(" ", " "))
				item.append(tr.find_all("td")[2].text)
				item.append(tr.find_all("td")[3].text)
				item.append(tr.find("a", title="Download this torrent using magnet")["href"])
				item.append(tr.find("a", class_="detLink")["href"])
				self.results[ctx.message.server.id].append(item)
			msg = "```"
			count = 0
			for result in self.results[ctx.message.server.id]:
				if count == 10:
					break
				msg = msg + str(count + 1) + ".\t" + result[0] + '\tSize: ' + result[1] + '\tSeeders: ' + result[2] + '\tLeachers: ' + result[3] + '\n'
				count = count + 1
			msg = msg[:-1]
			msg = msg + "```"
			await self.bot.say(msg)
		except Exception as e:
			#raise e
			print(e)
			await self.bot.say("fuck")

	@commands.command(pass_context=True, no_pm=True)
	async def search(self, ctx):
		if str(ctx.message.author) in privileged and len(ctx.message.content.split()) == 1:
			await self.bot.say("Search for wot?")
			return
		if str(ctx.message.author) in privileged:
			await self.get_results(ctx)

	@commands.command(pass_context=True, no_pm=True)
	async def description(self, ctx):
		if str(ctx.message.author) in privileged and len(ctx.message.content.split()) == 1:
			await self.bot.say("Description of what?")
			return
		num = int(ctx.message.content.split()[1])
		if num <= 0 or num > len(self.results[ctx.message.server.id]):
			await self.bot.say("Enter a valid number.")
			return
		if str(ctx.message.author) in privileged:
			url = "https://thepiratebay.org" + self.results[ctx.message.server.id][num-1][5]
			request = urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'})).read()
			soup = bs(request, "html.parser")
			name = self.results[ctx.message.server.id][num-1][0]
			desc = soup.find("pre").text
			await self.bot.say("```" + name + ":\n" + desc + "```")

	@commands.command(pass_context=True, no_pm=True)
	async def download(self, ctx):
		if str(ctx.message.author) in privileged and len(ctx.message.content.split()) == 1:
			await self.bot.say("Download wot?")
			return
		num = int(ctx.message.content.split()[1])
		if num <= 0 or num > len(self.results[ctx.message.server.id]):
			await self.bot.say("Enter a valid number.")
			return
		if str(ctx.message.author) in privileged:
			url = "http://localhost:1025/torrent/add"
			payload = {"torrenttype": "misc",
				"user": server_usernames[str(ctx.message.author)],
				"uri": self.results[ctx.message.server.id][num-1][4]}
			r = requests.post(url, data=json.dumps(payload), headers=headers)
			await self.bot.say("Downloading " + self.results[ctx.message.server.id][num-1][0] + ".  It will be placed in your ftp folder once it is finished.")

	@commands.command(pass_context=True, no_pm=True)
	async def status(self, ctx):
		if str(ctx.message.author) in privileged:
			url = "http://localhost:1025/torrent"
			r = requests.get(url, headers=headers)
			data = r.json()
			if len(data) == 0:
				await self.bot.say("``` ```")
			else:
				msg = "```"
				for show in data:
					msg = msg + show["Name"] + " - " + show["Progress"] + "\n"
				msg = msg[:-1]
				msg = msg + "```"
				await self.bot.say(msg)

class Meme:
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True, no_pm=True)
	async def meme(self, ctx):
		if len(ctx.message.content.split()) == 1:
			await self.bot.say("https://www.youtube.com/playlist?list=PLUwWkZ_MqmzFUpFBSCiuA9lFirIdhS-Yy")

class Plex:
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True, no_pm=True)
	async def plex(self, ctx):
		if str(ctx.message.author) in privileged and len(ctx.message.content.split()) == 1:
			await self.bot.say("Url:\thttp://69.247.112.45:32400 / http://192.168.1.16:32400\nUsername:\tonryobot@gmail.com\nPassword:\tTrey1997$")
			return

class Learn:
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True, no_pm=True)
	async def learn(self, ctx):
		try:
			params = ctx.message.content.split(" ")[1:]
		except:
			print(e)
			params = []
		if len(params) == 0:
			await self.bot.say("Please specify type of file and name.")
			return
		elif len(params) == 1:
			await self.bot.say("Please specify name of file.")
			return
		else:
			url = ctx.message.attachments[0]["url"]
			ext = url.split(".")[-1]
			path = "sound/" + params[1] + "." + ext
			if params[0] == "sound":
				r = requests.get(url)
				with open(path, 'wb') as f:
					f.write(r.content)
				await self.bot.say("I learned how to say " + params[1] + "!")
			else:
				await self.bot.say("Does it look like I know what a " + params[0] + " is?")
		#await self.bot.say(ctx.message.attachments[0]["url"])

class Settings:
	def __init__ (self, bot):
		self.bot = bot

	@commands.command(pass_context=True, no_pm=True)
	async def toggle(self, ctx):
		server = ctx.message.server.id
		channel = ctx.message.channel
		try:
			params = ctx.message.content.split(" ")[1:]
		except:
			params = []
		if len(params) > 0:
			if params[0] == "spongemock":
				settings = get_settings(server)
				sm = settings["spongemock"]
				settings["spongemock"] = not sm
				save_settings(server, settings)
				if sm:
					msg = "Spongemock is disabled"
				else:
					msg = "sPoNgEmOcK iS eNaBlEd"
			else:
				msg = "You want me to toggle wot?"
		else:
			msg = "You want me to toggle wot?"
		await self.bot.send_message(channel, msg)

	@commands.command(pass_context=True, no_pm=True, description = "Owo Score", help="Displays how many times owo has been said.")
	async def owo(self, ctx):
		await self.bot.say("OwO Score: " + str(get_settings(ctx.message.server.id)["owo"]))

	def check(self, msg):
		return msg.author == self.bot.user

	@commands.command(pass_context=True, no_pm=True)
	async def purge(self, ctx):
		await self.bot.purge_from(ctx.message.channel, check=self.check, limit=1000)
		
		

bot = commands.Bot(command_prefix=commands.when_mentioned_or(SYMBOL), description='Every frat needs a helper.')
bot.add_cog(Settings(bot))
bot.add_cog(Spongemock(bot))
bot.add_cog(Sound(bot))
bot.add_cog(Learn(bot))
bot.add_cog(Plex(bot))
bot.add_cog(Torrents(bot))
bot.add_cog(Meme(bot))

@bot.event
async def on_message(message):
	spongemock = ['snu', 'sigma nu', 'frat', 'party', 'meeting', 'chapter', 'library']
	if message.content[0] != SYMBOL and message.author != bot.user and ("owo" in message.content.lower() or "0w0" in message.content.lower()):
		settings = get_settings(message.server.id)
		owo = settings["owo"]
		settings["owo"] = owo + 1
		save_settings(message.server.id, settings)
	if get_settings(message.server.id)["spongemock"] and (":snu:" not in message.content) and any(x in message.content.lower() for x in spongemock) and len(message.content) <= 50:
		sm = Spongemock(bot, text=message.content)
		await sm.auto(message)
	await bot.process_commands(message)

@bot.event
async def on_ready():
	global headers
	print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))
	try:
		url = "http://localhost:1025/authenticate"
		payload = {"username": "onryo",
			"password": "asdf"}
		r = requests.post(url, data=json.dumps(payload))
		headers = {"authorization": "bearer " + str(json.loads(r.text)["token"])}
	except:
		pass
	for server in bot.servers:
		if not os.path.isfile("settings/" + server.id + ".json"):
			init_settings(server.id)
		update_settings(server.id)

bot.run('NDI4MDExMjI2NzExMTk1NjYw.DZs4nA.qEXDIQLSwAerzo0UKP0vdAmQHLM')
