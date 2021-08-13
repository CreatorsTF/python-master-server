import a2s
import requests
import json
import time
import socket
from colorama import Fore
import sys
import signal

#import logging
#import sys

#root = logging.getLogger()
#root.setLevel(logging.DEBUG)

#handler = logging.StreamHandler(sys.stdout)
#handler.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#handler.setFormatter(formatter)
#root.addHandler(handler)

#from discord_webhook import DiscordWebhook, DiscordEmbed

#try:
#    config = json.load(open("config.json", 'r'))
#    webhook = config["webhook"]
#except Exception as e:
#    print(f"Failed to load config and grab Discord URL: {e}")

#webhook = DiscordWebhook(url={}.format(webhook))
#
## create embed object for webhook
## you can set the color as a decimal (color=242424) or hex (color='03b2f8') number
#embed = DiscordEmbed(title='Python Master Server', description='{}', color='00ffbf')
#embed.add_embed_field(name='{}', value='{}')
#webhook.add_embed(embed)
#response = webhook.execute()

# Creators.TF Master Server
# Written by ZoNiCaL.
# edited by sapphonie
# Purpose: Updates the Creators.TF database with the latest website information.

# Currently, we only care about a few providers in our network, that being
# Creators.TF, Balance Mod, Silly Events servers, and Creators.TF Vanilla+.
# For now, we don't have a way to grab providers dynamically, so we'll just
# hardcode them until we decide to flesh out providers more.
providers = [ 15, 1756, 11919, 78132 ]

# time to sleep after running thru all providers
sleeptime = 10

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

def GrabServersForProvider(providerID):
    requestURL = f"https://creators.tf/api/IServers/GServerList?provider={providerID}"
    # Make an API request to the website.
    try:
        req = requests.get(requestURL, timeout=5)    # Return a JSON object which we can iterate over.
        serverList = req.json()

        # If the API returned something that wasn't a SUCCESS, something wen't wrong
        # on the website-end, so we'll just skip this provider for now.
        if serverList["result"] != "SUCCESS":
            raise CreatorsTFAPIError(f"[{req.status_code}] API (GServerList) returned non-SUCCESS code.")

    # If we run into some sort of error making a request, we'll just skip this provider.
    except BaseException as e:
        print(f"[FAIL] Request failed for provider {providerID}: {e}")
    
    return serverList["servers"]

# This function queries our server with A2S and returns a dict with all of the server information.
def QueryServer(serverID, serverInfo):
    try:
        timeout = 3
        a2sInfoRequest = a2s.info(serverInfo, timeout)

        # Construct a JSON object with all of our server information.
        info = {
            "name":             a2sInfoRequest.server_name,
            "players":           a2sInfoRequest.player_count,
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
            "datapack": {
                "info": info
            }
        }

        # Woo! Success! Log it.
        print(Fore.GREEN + f"[SUCCESS] {serverInfo}: {a2sInfoRequest.server_name}, {a2sInfoRequest.player_count}/{a2sInfoRequest.max_players}" + Fore.RESET)
        return serverToSend

    except socket.timeout:
        print(Fore.RED + f"[TIMEOUT] {serverInfo}" + Fore.RESET)
    except ConnectionRefusedError:
        print(Fore.RED + f"[REFUSED] {serverInfo}" + Fore.RESET)
    except socket.gaierror:
        print(Fore.RED + f"[NOSERVER] {serverInfo}" + Fore.RESET)
    except OSError:
        print(Fore.RED + f"[OSERROR] {serverInfo}" + Fore.RESET)

def SendServersToHeartbeat(servers):
    print(Fore.YELLOW + f"[PENDING] Sending block of {len(servers)} servers to api/IServers/GHeartbeat..."  + Fore.RESET)

    # We've now got a list of servers to send. Create a request to the
    # website API that updates server information in the database.
    requestURL = f"https://creators.tf/api/IServers/GHeartbeat"

    # Create our JSON payload:
    payload = {
        "key": masterKey,
        "servers": servers
    }

    # Make an API request to the website.
    try:
        req = requests.post(requestURL,
            json=payload, headers={"Content-Type": "application/json"})
        resp = req.json()   # Return a JSON object which we can iterate over.
        print(resp)

        # If the API returned something that wasn't a SUCCESS, something wen't wrong
        # on the website-end, so we'll just skip this provider for now.
        if resp["result"] != "SUCCESS":
            raise CreatorsTFAPIError(f"[{req.status_code}] API (GHeartbeat) returned non-SUCCESS code.")

    except BaseException as e:
        print(e)

    print(Fore.GREEN + f"[SUCCESS] Sent! Block of {len(servers)} servers arrived to api/IServers/GHeartbeat..."  + Fore.RESET)

def MasterServer():
    while True:
        # Grab our server list with an HTTP request.
        for provider in providers: 
            servers = GrabServersForProvider(provider)

            # We now have a list of servers. We're going to create blocks where we'll query
            # a block of servers and ship them off in a request. By default, we'll have
            # five servers in a block that we'll send off in a list. If we happen to have
            # less than five servers in a block because we've reached the end of a list for
            # a provider, that's alright, we'll send them anyways.
            serverBlock = []

            for server in servers:
                # Take a second to breathe so we don't spam our servers too much.
                time.sleep(2.0)

                # Okay, now lets send a query to the server asking for information.
                result = QueryServer(server["id"], (server["ip"], server["port"]))

                # Do we have a block of five servers we can ship off?
                if (len(serverBlock) <= 5): # No? Append the list.
                    if result != None:
                        serverBlock.append(result)
                else: # We already have a block of five servers, ship it off.
                    SendServersToHeartbeat(serverBlock)
                    serverBlock.clear()

                    # Add this server to the list afterwards as well.
                    if result != None:
                        serverBlock.append(result)

            # If we have any servers remaining in our server block, just send them over.
            if (len(serverBlock) != 0):
                SendServersToHeartbeat(serverBlock)

        print(Fore.MAGENTA + f"Sleeping for {int(sleeptime)} seconds..."  + Fore.RESET)
        time.sleep(int(sleeptime))

if (__name__ == "__main__"):
    MasterServer()

#TODO ctrl c handling
