import discord, asyncio, os, watcher, utils, time, aiohttp
from requests.models import StreamConsumedError
from discord.ext.commands.help import HelpCommand
from PIL import Image
from io import BytesIO
from discord.ext import commands, tasks
from utils import log, logErr
from riotwatcher import LolWatcher, ApiError
from riotwatcher._apis.league_of_legends.ChampionMasteryApiV4 import ChampionMasteryApiV4
from riotwatcher._apis.league_of_legends.SummonerApiV4 import SummonerApiV4
from riotwatcher._apis.league_of_legends.SpectatorApiV4 import SpectatorApiV4
from champs import get_champions_name
import mw
import url_check
from keep_alive import keep_alive

ky = utils.get_config().credentials['riot_api_key']
watcher2 = LolWatcher(ky)

class leaguebot:
    def __init__(self):
        
        # Get Token
        self.token = utils.get_config().credentials['bot_token_key']
        log("bot_token_key : {}".format(self.token[:4]+''.join('X' if c.isalpha() or c.isdigit() else c for c in self.token[4:])))

        # Bot Settings
        self.game = discord.Game("!help")
        self.prefix = "!"
        self.wt = watcher.watcher()
        self.lt = {}

os.chdir(os.path.dirname(os.path.abspath(__file__)))
setup = leaguebot()
bot = commands.Bot(
    command_prefix=setup.prefix, status=discord.Status.online, activity=setup.game
)
bot.remove_command("help")

# Bot events
@bot.event
async def on_ready():
    
    log("We have logged in as {}".format(bot.user))
    log("Guild List : {}".format(str(bot.guilds)))
    update_locale_data.start()
    setup.wt.load_summoner_list(bot.guilds)
    for guild in bot.guilds:
        setup.lt[guild.id] = True
    live_game_tracker.start()


@bot.event
async def on_guild_join(guild):
    
    log("League Bot joined new guild.", guild)
    
    setup.wt.load_summoner_list(bot.guilds)
    setup.lt[guild.id] = False

    try:
        channel = get_guild_channel(guild)

        await channel.send(
            embed=discord.Embed(title="League Bot is now ONLINE")
        )
    except discord.errors.Forbidden:
        logErr("(error code: 50013): Missing Permissions", guild)
        await guild.leave()
        return

    log("Restart live_game_tracker", guild)
    live_game_tracker.restart()


@bot.event
async def on_guild_remove(guild):
    
    log("League Bot was removed on this guild.", guild)
    
    setup.wt.delete_guild(guild.id)
    setup.wt.load_summoner_list(bot.guilds)
    del setup.lt[guild.id]
    
    log("Restart live_game_tracker", guild)
    live_game_tracker.restart()


# Bot commands
@bot.command()
async def help(ctx):
    
    await ctx.send(
        embed=discord.Embed(
            description="Bot Prefix: **!** \n To see all commands, type **!command** \n To see bot description, type **!description** ", color=0x00ff00
        )
    )


@bot.command()
async def command(ctx):

    embedVar = discord.Embed(title="All Commands", description="Prefix: ! ", color=0x00ff00)
    embedVar.add_field(name="!help", value="Get initial help", inline=False)
    embedVar.add_field(name="!command", value="See the list of commands", inline=False)
    embedVar.add_field(name="!description", value="See bot description", inline=False)
    embedVar.add_field(name="!l setup", value="Setup LoL live match tracker", inline=False)
    embedVar.add_field(name="!l add 'SummonerName'", value="Add a summoner to live-tracking list", inline=False)
    embedVar.add_field(name="!l remove 'SummonerName'", value="Remove a summoner from live-tracking list", inline=False)
    embedVar.add_field(name="!l list", value="Display the list of summoners currently being live-tracked", inline=False)
    embedVar.add_field(name="!l start", value="Start live match tracker", inline=False)
    embedVar.add_field(name="!l stop", value="Stop live match tracker", inline=False)
    embedVar.add_field(name="!l card 'region' 'SummonerName'", value="Share summoner card with channel \n ('region' options: **br1, eun1, euw1, jp1, kr, la1, la2, na1, oc1, tr1, ru**)", inline=False)
    embedVar.add_field(name="!s 'leagueName'", value="Display league schedule (LoL Esports) \n ('leagueName' options: **lec, lcs, lck, lpl, worlds, msi, tcl, lcl, cblol, lla, lco, ljl**)", inline=False)
    embedVar.add_field(name="!s wiki 'search'", value="Search for an esports element wiki \n ('search' is **any esports player, team, event, etc.**)", inline=False)

    await ctx.send(embed=embedVar)


@bot.command()
async def description(ctx):

    await ctx.send(" ```Hi, League Bot here! I create sharable summoner cards, track live games and provide esports data! Thanks for choosing me for your channel!``` ")    


@bot.command()
async def s(ctx, *args):
    
    log("{0.author} : {0.message.content}".format(ctx), ctx.guild)

    if not args:
        await ctx.send(
            embed=discord.Embed(
                title="Check available commands by typing **!command**"
            )
        )
        return

    if args[0] == "lec" and len(args) == 1:
        depotDict = mw.run("LEC")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "lec")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2F1592516184297_LEC-01-FullonDark.png")
        schCard.set_footer(text="Watch live at twitch.tv/lec", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/55a32fc5-8def-421a-841f-7693786781b0-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "lcs" and len(args) == 1:
        depotDict = mw.run("LCS")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "lcs")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2FLCSNew-01-FullonDark.png")
        schCard.set_footer(text="Watch live at twitch.tv/lcs", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/3ab30b90-63a3-4d24-941c-995806ecc511-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "lck" and len(args) == 1:
        depotDict = mw.run("LCK")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "lck")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2Flck-color-on-black.png")
        schCard.set_footer(text="Watch live at twitch.tv/lck", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/04b097ac-9a71-409e-b30e-570175b39caf-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "lpl" and len(args) == 1:
        depotDict = mw.run("LPL")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "lpl")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2F1592516115322_LPL-01-FullonDark.png")
        schCard.set_footer(text="Watch live at twitch.tv/lpl", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/a5b6fd5c-9aeb-4af2-b1eb-26077fd4f44b-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "tcl" and len(args) == 1:
        depotDict = mw.run("TCL")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "tcl")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=https%3A%2F%2Flolstatic-a.akamaihd.net%2Fesports-assets%2Fproduction%2Fleague%2Fturkiye-sampiyonluk-ligi-8r9ofb9.png")
        schCard.set_footer(text="Watch live at twitch.tv/riotgamesturkish", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/ee7b821c-d8ea-4dd4-9dc7-8240a51cd675-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "cblol" and len(args) == 1:
        depotDict = mw.run("CBLOL")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "cblol")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2Fcblol-logo-symbol-offwhite.png")
        await ctx.send(embed=schCard)

    elif args[0] == "lla" and len(args) == 1:
        depotDict = mw.run("LLA")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "lla")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2F1592516315279_LLA-01-FullonDark.png")
        schCard.set_footer(text="Watch live at twitch.tv/lla", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/430e325e-50c8-4688-8019-9aa6504c04f6-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "lco" and len(args) == 1:
        depotDict = mw.run("LCO")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "lco")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2Flco-color-white.png")
        schCard.set_footer(text="Watch live at twitch.tv/lco", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/a197a8b9-ea12-41c3-aa14-90092235b1e9-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "ljl" and len(args) == 1:
        depotDict = mw.run("LJL")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "ljl")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2F1592516354053_LJL-01-FullonDark.png")
        schCard.set_footer(text="Watch live at twitch.tv/riotgamesjp", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/5265df94-fc97-4263-aec3-44cb9f4cdbad-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "lcl" and len(args) == 1:
        depotDict = mw.run("LCL")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "lcl")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2F1593016885758_LCL-01-FullonDark.png")
        schCard.set_footer(text="Watch live at twitch.tv/riotgamesru", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/5f338718-f9d9-458e-b1fa-99db45f2a7c5-profile_image-70x70.png")
        await ctx.send(embed=schCard)

    elif args[0] == "worlds" and len(args) == 1:
        depotDict = mw.run("Worlds")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "worlds")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2F1592594612171_WorldsDarkBG.png")
        await ctx.send(embed=schCard)

    elif args[0] == "msi" and len(args) == 1:
        depotDict = mw.run("MSI")
        croppedDict = crop_dict(depotDict)
        schCard = form_embed_card(croppedDict, "msi")
        schCard.set_thumbnail(url="https://am-a.akamaihd.net/image?resize=120:&f=http%3A%2F%2Fstatic.lolesports.com%2Fleagues%2F1592594634248_MSIDarkBG.png")
        await ctx.send(embed=schCard)

    searched = " ".join(args[1:])
    word_list = searched.split()
    no_of_words = len(word_list)    
    if no_of_words == 1:
        searchedUrl = "https://lol.fandom.com/wiki/" + searched
    elif no_of_words > 1:
        searchedUrl = "https://lol.fandom.com/wiki/" + searched.replace(" ", "_")    

    if args[0] == "wiki" and len(args) > 1:
        if url_check.is_valid(searchedUrl):
            embedWiki = discord.Embed(title=searched, url=searchedUrl,description="Click on the title to view your wiki request!", color=discord.Color.blue())
        else:
            embedWiki = discord.Embed(title="The page you are looking for doesn't exist :(", description="Please check the spelling and capital letters again. Also make sure that your search term is esports-related.", color=discord.Color.red())

        await ctx.send(embed=embedWiki)                      


@bot.command()
async def l(ctx, *args):

    log("{0.author} : {0.message.content}".format(ctx), ctx.guild)

    if not args:
        await ctx.send(
            embed=discord.Embed(
                title="Check available commands by typing **!command**"
            )
        )
        return

    if args[0] == "setup" and len(args) > 0:

        def check_confirm(m):
            return m.content == "y" or m.content == "n" and m.channel == ctx.channel

        def select_region(m):
            regions = ["br1", "eun1", "euw1", "jp1", "kr", "la1", "la2", "na1", "oc1", "tr1", "ru"]
            return m.content in regions and m.channel == ctx.channel

        await ctx.send(
            embed=discord.Embed(
                title="Type 'y' to start setup",
                description="'y' : Yes 'n' : No",
            ).set_author(name="Live tracker Setup")
        )
        try:
            confirm = await bot.wait_for("message", timeout=30.0, check=check_confirm)
        except asyncio.TimeoutError:
            await ctx.send(embed=discord.Embed(title="Timeout : Try again."))
            return
        if confirm.content == "n":
            return

        setup.wt.delete_guild(ctx.guild.id)

        await ctx.send(
            embed=discord.Embed(
                title="Choose your League Of Legends region",
                description="'br1', 'eun1', 'euw1', 'jp1', 'kr', 'la1', 'la2', 'na1', 'oc1', 'tr1', 'ru'",
            ).set_author(name="Live tracker Setup")
        )
        try:
            region = await bot.wait_for("message", timeout=30.0, check=select_region)
        except asyncio.TimeoutError:
            await ctx.send(embed=discord.Embed(title="Timeout : Try again."))
            return
        await ctx.send(
            embed=discord.Embed(
                title="Confirm this setup?",
                description="region : " + region.content + "\n'y' : Yes 'n' : No",
            ).set_author(name="Live tracker Setup")
        )
        try:
            confirm = await bot.wait_for("message", timeout=30.0, check=check_confirm)
        except asyncio.TimeoutError:
            await ctx.send(embed=discord.Embed(title="Timeout : Try again."))
            return
        if confirm.content == "n":
            return

        setup.wt.setup(region.content, ctx.guild)
        setup.wt.load_summoner_list(bot.guilds)
        setup.lt[ctx.guild.id] = True
        try:
            live_game_tracker.start()
        except RuntimeError:
            live_game_tracker.restart()

        await ctx.send(
            embed=discord.Embed(title="Live tracker was setup successfully.")
        )
        return

    if not setup.wt.is_setup_already(ctx.guild):
        await ctx.send(
            embed=discord.Embed(title="'!l setup'").set_author(
                name="You have to setup League Bot first!"
            )
        )
        return

    rg = "".join(args[1])
    name = " ".join(args[2:])
    locale = get_locale(ctx.guild)

    if args[0] == "add" and len(args) > 1:
        d = setup.wt.edit_summoner_list(ctx.guild, True, name)
        await ctx.send(embed=discord.Embed(title=d))

    elif args[0] == "remove" and len(args) > 1:
        d = setup.wt.edit_summoner_list(ctx.guild, False, name)
        await ctx.send(embed=discord.Embed(title=d))

    elif args[0] == "card" and len(args) > 1:
        try:
            summonerName = name
            summonerRegion = rg
            summoner = watcher2.summoner.by_name(summonerRegion, summonerName)
            stats = watcher2.league.by_summoner(summonerRegion, summoner['id'])
            summoner_champs = watcher2.champion_mastery.by_summoner(summonerRegion, summoner['id'])

            summonerIconId = summoner['profileIconId']
            summonerLevel = summoner['summonerLevel']

            region_without_number = (summonerRegion[:-1]).upper()

            embedCard = discord.Embed(title= "(" + region_without_number + ")", description="", color=discord.Color.blue())
  
            summonerNameForUrl = summonerName.replace(" ", "+")
            embedCard.set_author(name=summonerName + " (" + str(summonerLevel) + ")", url= "https://" + region_without_number.lower() + ".op.gg/summoner/userName=" + summonerNameForUrl, icon_url="http://ddragon.leagueoflegends.com/cdn/11.15.1/img/profileicon/" + str(summonerIconId) + ".png")

            try:
                tier_soloq = stats[0]['tier']
                rank_soloq = stats[0]['rank']
                lp_soloq = stats[0]['leaguePoints']
                wins_soloq = (int) (stats[0]['wins'])
                losses_soloq = (int) (stats[0]['losses'])
                winrate_soloq = (int) ((wins_soloq / (wins_soloq + losses_soloq)) * 100)

                embedCard.add_field(name="Rank (Solo/Duo): ", value=str(tier_soloq) + "-" + str(rank_soloq) + "   " + str(lp_soloq) + " LP  -  Win Rate: %" + str(winrate_soloq), inline=False)
            except:
                embedCard.add_field(name="Rank (Solo/Duo): ", value="No data found!", inline=False)

            try:
                tier_flex = stats[1]['tier']
                rank_flex = stats[1]['rank']
                lp_flex = stats[1]['leaguePoints']
                wins_flex = (int) (stats[1]['wins'])
                losses_flex = (int) (stats[1]['losses'])
                winrate_flex = (int) ((wins_flex / (wins_flex + losses_flex)) * 100)

                embedCard.add_field(name="Rank (Flex 5v5): ", value=str(tier_flex) + "-" + str(rank_flex) + "   " + str(lp_flex) + " LP  -  Win Rate: %" + str(winrate_flex), inline=False)
            except:
                embedCard.add_field(name="Rank (Flex 5v5): ", value="No data found!", inline=False) 

            favChamps = [get_champions_name(summoner_champs[0]['championId']), get_champions_name(summoner_champs[1]['championId']), get_champions_name(summoner_champs[2]['championId'])]
            favChampsStr = ">>> " + favChamps[0] + "\n" + favChamps[1] + "\n" + favChamps[2]
            embedCard.add_field(name="Most Played: ", value=favChampsStr, inline=False)
    
            await ctx.send(embed=embedCard)
        except ApiError:
            await ctx.send("Summoner not found!") 
        except:
            await ctx.send("Something went wrong!")

    elif args[0] == "start" and len(args) == 1:
        setup.wt.init_riot_api()

        if setup.lt[ctx.guild.id] is True:
            await ctx.send(
                embed=discord.Embed(title=locale['tracker_started_already'])
            )
            return
        elif setup.wt.riot_api_status() == 403:
            await ctx.send(
                embed=discord.Embed(
                    title=locale['tracker_failed']
                )
            )
            return
        try:
            live_game_tracker.start()
        except RuntimeError:
            live_game_tracker.restart()

        setup.lt[ctx.guild.id] = True

        log("live_game_tracker was started", ctx.guild)
        
        await ctx.send(embed=discord.Embed(title=locale['tracker_started']))

    elif args[0] == "stop" and len(args) == 1:
        if setup.lt[ctx.guild.id] is False:
            await ctx.send(
                embed=discord.Embed(title=locale['tracker_stopped_already'])
            )
            return
        setup.lt[ctx.guild.id] = False

        log("live_game_tracker was stopped", ctx.guild)

        await ctx.send(embed=discord.Embed(title=locale['tracker_stopped']))

    elif args[0] == "list" and len(args) == 1:
        region = setup.wt.guild_region[ctx.guild.id]
        names = ""
        for name in setup.wt.get_summoner_list(ctx.guild.id):
            names += name + "\n"
        await ctx.send(
            embed=discord.Embed(
                title=locale['region'] + " : " + region, description=names
            ).set_author(name=locale['tracker_list'])
        )

    else:
        await ctx.send(
            embed=discord.Embed(
                title="Check available commands by typing **!command**"
            )
        )


@tasks.loop(minutes=30.0)
async def update_locale_data():
    setup.wt.update_locale_data()
    log("Data Dragon maps and queues data was updated")


@tasks.loop(seconds=60.0)
async def live_game_tracker():
    if setup.wt.riot_api_status() == 403:
        logErr("403 Forbidden, Riot API token key was expired or It might be Riot API server error")
        return

    setup.wt.update_ddragon_data()

    tasks = [process_per_guild_async(guild) for guild in bot.guilds]
    await asyncio.wait(tasks)


async def process_per_guild_async(guild):
    if setup.lt[guild.id] is False:
        return
    
    setup.wt.remove_ended_match(guild)
    locale = get_locale(guild)
    channel = get_guild_channel(guild)

    summoners = await setup.wt.search_summoner_from_list(guild, setup.wt.get_summoner_list(guild.id))
    result = await setup.wt.search_live_match(guild, summoners)

    for id_ in result:
        await process_live_match_async(guild, id_, locale, channel)
        await asyncio.sleep(60.0)

async def process_live_match_async(guild, id_, locale, channel):
    embed = discord.Embed(
        title=locale['match_found'],
        description=locale['loading'],
        colour=discord.Colour.green(),
    )
    await channel.send(embed=embed, delete_after=1.0)
    await send_match_data_async(guild, id_, channel)


async def send_match_data_async(guild, id_, channel):
    st = time.time()
    content = await setup.wt.load_live_match_data(guild, id_)
    print("loaded in : ", time.time() - st)    
    if type(content) is Image.Image:
        with BytesIO() as image_binary:
            content.save(image_binary, "PNG")
            image_binary.seek(0)
            await channel.send(
                file=discord.File(fp=image_binary, filename="image.png")
            )
    elif type(content) is str:
        await channel.send(content=content)


def get_locale(guild):
    config = utils.get_locale_config()
    locale = config.locale['na1']
    region = setup.wt.get_guild_region(guild)

    if region in config.locale:
        locale = config.locale[region]

    return locale

def get_guild_channel(guild):
    if guild.system_channel is None:
        return guild.text_channels[0]
    else:
        return guild.system_channel

def crop_dict(dict):
    initialLength = len(dict)
    newDict = {}
    if initialLength >= 6:
        for k in range(6):
            newDict[k] = dict[(initialLength - (k+1))]
    else:
        for i in range(len(initialLength)):
            newDict[i] = dict[(initialLength - (i+1))]

    return newDict

def form_embed_card(latestDict, leagueName):
    embedSchedule = discord.Embed(title=str(leagueName).upper() + " Schedule", url="https://lolesports.com/schedule?leagues=" + str(leagueName), description="(most recent & upcoming matches)", color=0x03e8fc)

    for n in range(len(latestDict)):
        matchup = latestDict[len(latestDict) - (n+1)]
        if matchup["winner"] == 'None':
            embedSchedule.add_field(name=matchup["team1"] + " vs " + matchup["team2"], value="Details: \n" + matchup["date"] + " " + matchup["time"] + matchup["timezone"] + "\n" +  "BO" + str(matchup["bestof"]), inline=False)
        else:
            embedSchedule.add_field(name=matchup["team1"] + " vs " + matchup["team2"], value="Details: \n" + matchup["date"] + " " + matchup["time"] + matchup["timezone"] + "\n" +  "BO" + str(matchup["bestof"]) + "\n" + "**Winner:** ||" + matchup["winner"] + " (" + matchup["score"] + ")" + "||", inline=False)        

    return embedSchedule                

if __name__ == "__main__":
    
    keep_alive()
    bot.run(setup.token)