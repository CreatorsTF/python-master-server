import a2s
import requests
import json
import time
import socket
from colorama import Fore
import sys
import signal
from discord_webhook import DiscordWebhook, DiscordEmbed

#webhook = DiscordWebhook(url='https://canary.discord.com/api/webhooks/874855141075984435/q_YE9jAoQN8fwdOh9n2a4cLg8sCXfPSllEK8a6wd-3sD0goyfJesTaJDgsYMF2_Zo_M9')
#
## create embed object for webhook
## you can set the color as a decimal (color=242424) or hex (color='03b2f8') number
#embed = DiscordEmbed(title='Python Master Server', description='{}', color='00ffbf')
#embed.add_embed_field(name='{}', value='{}')
#webhook.add_embed(embed)
#response = webhook.execute()

# Creators.TF Master Server
# Written by ZoNiCaL.
# Purpose: Updates the Creators.TF database with the latest website information.

# Currently, we only care about a few providers in our network, that being
# Creators.TF, Balance Mod, Silly Events servers, and Creators.TF Vanilla+.
# For now, we don't have a way to grab providers dynamically, so we'll just
# hardcode them until we decide to flesh out providers more.
providers = [ 15, 1756, 11919, 78132 ]

# time to sleep after running thru all providers
sleeptime = 10;

# Custom exception class to diagnose problems that specifically happen with the
# Creators.TF API. This could help diagnose problems later if needed.
# ^^^ ??? what??
class CreatorsTFAPIError(BaseException):
    pass

# Import a config file that has our Master API key. This allows the website to
# recognise us when we make requests.
masterKey = ""

try:
    config = json.load(open("config.json", 'r'))
    masterKey = config["key"]
except Exception as e:
    print(f"Failed to load config and grab API key: {e}")
    quit()

while True:
    # Grab our server list with an HTTP request.
    for provider in providers:
        requestURL = f"https://creators.tf/api/IServers/GServerList?provider={provider}"
        # Make an API request to the website.
        try:
            req = requests.get(requestURL, timeout=5)    # Return a JSON object which we can iterate over.
            serverList = req.json()

            #print(f"{serverList}")

            # If the API returned something that wasn't a SUCCESS, something wen't wrong
            # on the website-end, so we'll just skip this provider for now.
            if serverList["result"] != "SUCCESS":
                raise CreatorsTFAPIError(f"[{req.status_code}] API (GServerList) returned non-SUCCESS code.")

        # If we run into some sort of error making a request, we'll just skip this provider.
        except BaseException as e:
            print(f"[FAIL] Request failed for provider {provider}: {e}")
            continue

        serversToSend = []

        # Loop through all the returned servers and request information for them.
        for server in serverList["servers"]:
            serverstr = str(server['ip']) + ":" + str(server['port'])
            try:
                serverID = server["id"]
                timeout = 2.0
                a2sInfoRequest = a2s.info((server["ip"], server["port"]), timeout)

                # Construct a JSON object with all of our server information.
                info = {
                    "hostname":         a2sInfoRequest.server_name,
                    "online":           a2sInfoRequest.player_count,
                    "maxplayers":       a2sInfoRequest.max_players,
                    "map":              a2sInfoRequest.map_name,
                    "keywords":         a2sInfoRequest.keywords,
                    "bots":             a2sInfoRequest.bot_count,
                    "game":             a2sInfoRequest.game,
                    "appid":            a2sInfoRequest.app_id,
                    "version":          a2sInfoRequest.version,
                    "passworded":       a2sInfoRequest.password_protected,
                    "vac_secure":       a2sInfoRequest.vac_enabled,
                    "sourcetv_port":    a2sInfoRequest.stv_port,
                    "sourcetv_name":    a2sInfoRequest.stv_name,
                }

                # This could totally have more support for more data later like
                # actual players. If we consider doing a "recent activity" feature,
                # we could return other player info.

                #Construct an object that we'll send to the database soon:
                serverToSend = {
                    "id": serverID,
                    "datapack": info
                }

                # Add to our final list:
                serversToSend.append(serverToSend)

                print(Fore.GREEN + f"[SUCCESS] {serverstr}: {a2sInfoRequest.server_name}, {a2sInfoRequest.player_count}/{a2sInfoRequest.max_players}" + Fore.RESET)

            except socket.timeout:
                print(Fore.RED + f"[TIMEOUT] {serverstr}" + Fore.RESET)
            except ConnectionRefusedError:
                print(Fore.RED + f"[REFUSED] {serverstr}" + Fore.RESET)
            except socket.gaierror:
                print(Fore.RED + f"[NOSERVER] {serverstr}" + Fore.RESET)
            except OSError:
                print(Fore.RED + f"[OSERROR] {serverstr}" + Fore.RESET)

        # We've now got a list of servers for this provider. Create a request to the
        # website API that updates server information in the database.
        requestURL = f"https://creators.tf/api/IServers/GHeartbeat"
        # Make an API request to the website.
        try:
            req = requests.post(requestURL,
                data={ "servers": serversToSend, "key": masterKey })
            resp = req.json()   # Return a JSON object which we can iterate over.

            # If the API returned something that wasn't a SUCCESS, something wen't wrong
            # on the website-end, so we'll just skip this provider for now.
            if resp["result"] != "SUCCESS":
                raise CreatorsTFAPIError(f"[{req.status_code}] API (GHeartbeat) returned non-SUCCESS code.")

            print(f"Successfully updated provider {provider}")
        except BaseException as e:
            print(e)
            continue

    # stupid bad code
    seconds = "";
    if sleeptime != 1:
        seconds = "s"

    print(Fore.MAGENTA + f"Sleeping for {int(sleeptime)} second{seconds}..."  + Fore.RESET)
    time.sleep(int(sleeptime));


os._exit(1)

