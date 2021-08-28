import a2s
import requests
import json
import time
import socket
from colorama import Fore
import sys
import signal
import asyncio

# Creators.TF Master Server
# Written by ZoNiCaL and edited by sapphonie.
# Purpose: Updates the Creators.TF database with the latest website information.

class Provider():
    """Object to store provider data in.
    
    Attributes:
        ID : int
            ID of this provider as pre-defined in the website database.
        servers : list
            This is the list of servers for this provider that are iterated
            over in the main logic loop.
        isCurrentlyPolling : bool
            Boolean to represent if this provider is currently having its
            servers being queried. Currently unused.
        timeSinceLastUpdate : int
            Unix timestamp presentation of the last time this provider made
            a request to the API for a list of servers from the database.
    """
    ID = -1
    servers = None
    isCurrentlyPolling = False
    timeSinceLastUpdate = -1
    
    def __init__(self, id):
        """
        Constructs all the necessary attributes for this class.

        Parameters:
            id : The ID of this provider as pre-defined in the website database.
        """
        self.ID = id

class CreatorsTFAPIError(BaseException):
    """Custom exception class to diagnose problems that specifically happen with the
    Creators.TF API. This could help diagnose problems later if needed.
    """
    pass

# Currently, we only care about a few providers in our network, that being
# Creators.TF, Balance Mod, Silly Events servers, and Creators.TF Vanilla+.
# For now, we don't have a way to grab providers dynamically, so we'll just
# hardcode them until we decide to flesh out providers more.
providers = [ Provider(15), Provider(1756), Provider(11919), Provider(78132) ]

# Time to sleep after running through all providers.
sleeptime = 10

# Import a config file that has our Master API key. This allows the website to
# recognize us when we make requests.
masterKey = ""

# There are 3600 seconds in an hour. Every hour, we'll query our providers again to
# get the latest servers from the database if they get updated for some reason.
hour = 3600

def GrabServersForProvider(providerID):
    """Grabs the servers from the Creators.TF Website database. Returns a list of dicts.
    
    providerID(s) are pre-defined in the website database. The request returns JSON data,
    and this function returns a list of dicts with server information."""

    requestURL = f"https://creators.tf/api/IServers/GServerList?provider={providerID}"
    # Make an API request to the website.
    try:
        req = requests.get(requestURL, timeout=5)    # Return a JSON object which we can iterate over.
        serverList = req.json()

        # If the API returned something that wasn't a SUCCESS, something went wrong
        # on the website-end, so we'll just skip this provider for now.
        if serverList["result"] != "SUCCESS":
            raise CreatorsTFAPIError(f"[{req.status_code}] API (GServerList) returned non-SUCCESS code.")

    # If we run into some sort of error making a request, we'll just skip this provider.
    except BaseException as e:
        print(f"[FAIL] Request failed for provider {providerID}: {e}")
    
    return serverList["servers"]

def OrganizeProviderServers(servers):
    """Spreads out servers by IP to be as far away from each other as possible. Returns a list.
    
    Takes a group of servers (list of dicts) and sorts them all into separate dicts by
    the first three characters of the IP address (e.g "eu1", "us.", "aus"). 
    
    Those dicts of grouped servers are then iterated to grab the first server, add it to the list
    of sorted servers, and then move to the next group.
    
    This repeats until no servers are left in the sorted groups. Returns a list."""

    serversByIP = {}

    for server in servers:
        # Grab the first three characters of our IP. This will help us
        # sort our servers into blocks, and we'll iterate over each block
        # when we query servers.
        serverIP = server["ip"]
        serverUniqueID = serverIP[0:3]
        if (serverUniqueID not in serversByIP):
            # Create a new list to put our servers in.
            serversByIP[serverUniqueID] = []

        # Add our server by IP to this list.
        serversByIP[serverUniqueID].append(server)

    # Grab our total amount of servers.
    total = 0
    for ID in serversByIP:
        total += len(serversByIP[ID])

    serversSorted = 0
    servers = []

    # Grab a server, one by one, from each region and remove it.
    # Lets say we have 6 unique IPs with the amount of servers being
    # 6, 6, 3, 3, 3, 4. Goto the first one, take the first server, and remove
    # it from the list and put it into our final sorted list. Goto the next
    # server list, pop the first one, add it to the final sorted list, repeat.

    # While the amount of the servers we've put into the list doesn't
    # match our full total.
    while serversSorted != total:
        for group in serversByIP:
            # If we don't have anymore servers in this group,
            # don't worry about it in the future by deleting it
            # from the dict.
            if len(serversByIP[group]) == 0:
                del serversByIP[group]
                break # Break the for loop here to prevent a RuntimeError.

            # Grab the very first server and "pop" it, removing it
            # from the list while grabbing it at the same time.
            server = serversByIP[group].pop(0)
            servers.append(server)

            serversSorted += 1

    # All the servers have been sorted, set this list for our provider.
    return servers

async def QueryServer(serverID, serverInfo):
    """This function queries our server with A2S and returns a dict with all of the server information.
    
    A2S is the method for querying server information for Source Engine Servers, and by extension, TF2."""
    try:
        timeout = 3
        a2sInfoRequest = await a2s.ainfo(serverInfo, timeout)

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
    except asyncio.TimeoutError:
        print(Fore.RED + f"[TIMEOUT] {serverInfo}" + Fore.RESET)
    except socket.timeout:
        print(Fore.RED + f"[TIMEOUT] {serverInfo}" + Fore.RESET)
    except ConnectionRefusedError:
        print(Fore.RED + f"[REFUSED] {serverInfo}" + Fore.RESET)
    except socket.gaierror:
        print(Fore.RED + f"[NO SERVER] {serverInfo}" + Fore.RESET)
    except OSError:
        print(Fore.RED + f"[OS ERROR] {serverInfo}" + Fore.RESET)

async def SendServersToHeartbeat(servers):
    """Create a request to the Creators.TF API that updates server information in the database. No return."""

    print(Fore.YELLOW + f"[PENDING] Sending block of {len(servers)} servers to api/IServers/GHeartbeat..."  + Fore.RESET)
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

async def MasterServer():
    """The main logic loop. No return.
    
    This function starts by grabbing servers for each provider from the website database, and organises them.

    Until this program is killed, the loop will iterate over each provider. 
        - If an hour has passed since the last time the servers were retrieved from the database, it will
        grab the servers and organise them again.

    Each server in the list of servers for a provider are iterated over, and a request is made using A2S.
        - A2S is the method for querying server information for Source Engine Servers, and by extension, TF2.

    If a server IP (not including ports) has been requested in the last five attempts, the program will sleep for a second before making a
    request so servers aren't overloaded.
    
    On success, the information is stored and is added to a "block" of servers. If this block reaches 10 servers, they
    are packaged up and sent to the database with an API request.
    
    Once all providers have been iterated over, the loop sleeps for 10 seconds before restarting.
    """

    for provider in providers: 
        # Organize the servers for our providers.
        provider.servers = GrabServersForProvider(provider.ID)
        provider.servers = OrganizeProviderServers(provider.servers)
        provider.timeSinceLastUpdate = int(time.time())

    while True:
        # Grab our server list with an HTTP request.
        for provider in providers:
            # Has it been an hour and we need to do a check for new servers?
            if provider.timeSinceLastUpdate + hour < int(time.time()):
                print(Fore.YELLOW + f"[PENDING] Grabbing new server information for {provider.ID}."  + Fore.RESET)
                provider.servers = None

                # Grab and organize new servers.
                provider.servers = GrabServersForProvider(provider.ID)
                provider.servers = OrganizeProviderServers(provider.servers)

                provider.timeSinceLastUpdate = int(time.time())
                print(Fore.GREEN + f"[SUCCESS] Grabbed {len(provider.servers)} for {provider.ID}."  + Fore.RESET)
            
            provider.isCurrentlyPolling = True

            # We now have a list of servers. We're going to create blocks where we'll query
            # a block of servers and ship them off in a request. By default, we'll have
            # five servers in a block that we'll send off in a list. If we happen to have
            # less than five servers in a block because we've reached the end of a list for
            # a provider, that's alright, we'll send them anyways.
            serverBlock = []

            # If we've recently pinged this server with A2S, we'll add a delay
            # so we have the best chance of getting server information. Only the latest
            # four servers will be here.
            recentServers = []

            # Loop through all of our servers so we can query them.
            for server in provider.servers:
                serverUniqueID = server["ip"][0:3] # Grab the first three characters of the IP as a unique identifier.
                if serverUniqueID in recentServers:  # Add a delay of one second so we don't spam this IP too much.
                    print(Fore.YELLOW + f"[PENDING] Resting {server['ip']}:{server['port']} for one second."  + Fore.RESET)
                    await asyncio.sleep(1)

                # Okay, now lets send a query to the server asking for information.
                result = await QueryServer(server["id"], (server["ip"], server["port"]))

                # If we're already at 5 entires in our recent servers list,
                # remove the first one and add in this servers unique ID.
                if serverUniqueID not in recentServers:
                    recentServers.append(serverUniqueID)
                
                if len(recentServers) > 5:
                    recentServers.remove(recentServers[0])

                # Do we have a block of ten servers we can ship off?
                if (len(serverBlock) < 10): # No? Append the list.
                    if result != None:
                        serverBlock.append(result)
                else: # We already have a block of five servers, ship it off.
                    await SendServersToHeartbeat(serverBlock)
                    serverBlock.clear()
                    recentServers.clear()
                    # Add this server to the list afterwards as well.
                    if result != None:
                        serverBlock.append(result)

            # If we have any servers remaining in our server block, just send them over.
            if (len(serverBlock) != 0):
                await SendServersToHeartbeat(serverBlock)
                recentServers.clear()

            provider.isCurrentlyPolling = False

        print(Fore.MAGENTA + f"Sleeping for {int(sleeptime)} seconds..."  + Fore.RESET)
        await asyncio.sleep(int(sleeptime))
        recentServers.clear()

if (__name__ == "__main__"):
    """Main entry point for this application. 
    
    This loads a file (config.json) where it holds a special key to query the Creators.TF API
    and make special heartbeat requests."""
    try:
        config = json.load(open("config.json", 'r'))
        masterKey = config["key"]
    except Exception as e:
        print(f"Failed to load config and grab API key: {e}")
        quit()

    asyncio.run(MasterServer())

