import json
import operator
import sqlite3
import random
import disnake
from disnake.ext import commands
from configparser import ConfigParser

intents = disnake.Intents.default()
intents.guilds = True
intents.presences = True

bot = commands.Bot(command_prefix='unused lol', intents=intents,
                   allowed_mentions=disnake.AllowedMentions(everyone=False, users=True, roles=False, replied_user=True))
guilds = [770428394918641694, 296802696243970049]

def getLang(inter, section, line):

    language = inter.locale

    languages = {
        'en-US':"translation/lang_en.ini",
        'en-GB':"translation/lang_en.ini",
        'ko':"translation/lang_ko.ini"
    }

    if language in languages:
        file = languages[language]
    else:
        file = languages['en-US']

    lang = ConfigParser()
    lang.read(file, encoding='utf-8')
    lineStr = lang.get(section, line)

    return lineStr

@bot.user_command(name='View Roles', guild_ids=guilds)
async def view_role_context(inter):
    await _roles(inter, type='Role', user=inter.target)

@bot.user_command(name='View Role Icons', guild_ids=guilds)
async def view_roleicon_context(inter):
    await _roles(inter, type='Icon', user=inter.target)

@bot.slash_command(description='Allows you to manage your active role, or view the roles of other users.', name='roles',
                   guild_ids=guilds)
async def roles(inter, member: disnake.Member = None, page:int=1):
    await _roles(inter, type='Role', user=member, page=page)


@bot.slash_command(description='Allows you to manage your active role icon, or view the role icons of other users.',
                   name='icons', guild_ids=guilds)
async def roleicons(inter, member: disnake.Member = None, page:int=1):
    await _roles(inter, type='Icon', user=member, page=page)


async def _roles(inter, type, returnEmbed = False,
                 user = False, page = 1, defer=True): # Lists a players' roles & role icons and allows them to choose between them.

    if page < 1:
        page = 1

    if not returnEmbed and defer:
        await inter.response.defer(ephemeral=True)

    if user:

        if isinstance(user, int):
            id = user
        else:
            id = user.id
            if id == inter.author.id:
                user = False
    else:
        id = inter.author.id
    roles, roleIcons = get_user_roles(id)
    guild = inter.guild

    true_items = []

    shortType = ''

    if type == 'Role':
        itemList = roles
        shortType = 'ro'
    else:
        itemList = roleIcons
        shortType = 'ri'

    for r in itemList:
        try:
            true_items.append(guild.get_role(r))
        except Exception as e:
            print(e)

    if page-1 > (len(true_items))/25:
        page = 1

    true_items_shortened = true_items[(page - 1)*25:(page * 25)]

    aList = []

    if not returnEmbed and not user:

        rarities = getLang(inter, 'Translation', 'RARITY_LIST').split(',')

        Menu = disnake.ui.Select()
        options = []
        for r in true_items_shortened:
            quality = random.choice(rarities)
            level = random.randint(0, 100)
            temp = disnake.SelectOption(label=r.name, value=f'{shortType}_{r.id}',
                                        description=getLang(inter, 'Translation', 'ITEM_RARITY').format(level, quality, r.name))
            options.append(temp)
        Menu.options = options
        Menu.custom_id = 'role_select'
        aList.append(Menu)
    else:
        Menu = None

    roleStrList = ''
    PageDown = None
    PageUp = None

    for i in true_items_shortened:
        roleStrList = f'{roleStrList}\n{i.mention}'
    if len(true_items) > len(true_items_shortened):
        roleStrList = f'{roleStrList}**({(page-1)*25}-{len(true_items_shortened)}/{len(true_items)})**'

        if true_items[-1] == true_items_shortened[-1] and len(true_items) > 25:
            pageDown = disnake.ui.Button(label='<-', custom_id=f'{shortType}_{page-1}', style=1)
            aList.append(pageDown)
        if true_items[0] == true_items_shortened[0] and len(true_items) > 25:
            pageUp = disnake.ui.Button(label='->', custom_id=f'{shortType}_{page+1}', style=1)
            aList.append(pageUp)

    if len(true_items) != 1:
        type_plural = getLang(inter, section='Translation', line=f'{type.upper()}_PLURAL')
    else:
        type_plural = getLang(inter, section='Translation', line=f'{type.upper()}')

    if id == 9:
        embTitle = getLang(inter, section='Translation', line='ROLES_LIST_BLACKLIST').format(len(true_items), type_plural)
    if user:
        embTitle = getLang(inter, section='Translation', line='ROLES_LIST_USER').format(user.name, len(true_items), type_plural)
    else:
        embTitle = getLang(inter, section='Translation', line='ROLES_LIST_INVOKER').format(len(true_items), type_plural)

    embed = disnake.Embed(title=embTitle, description=roleStrList, color=0xD8B400)
    if not returnEmbed:
        embed.set_footer(text=getLang(inter, section='Translation', line='ROLE_FOOTER_INFO').format(getLang(inter, section='Translation', line=f'{type.upper()}_PLURAL')))
    if len(true_items) != 0 and not returnEmbed and not user:
        embed.set_footer(text=getLang(inter, section='Translation', line='ROLE_FOOTER_DROPDOWN').format(getLang(inter, section='Translation', line=f'{type.upper()}')))

    if returnEmbed:
        return embed
    elif len(true_items) > 0 and not user:
        message = await inter.edit_original_message(components=aList, embed=embed)
    else:
        message = await inter.edit_original_message(embed=embed)


@bot.slash_command(description='Assigns a role to a user.', name='giverole', guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def addrole(inter, member: disnake.abc.User, role: disnake.abc.Role):
    if role.name == '@everyone':
        await inter.response.send_message(getLang(inter, section='Translation', line=f'GIVE_ROLE_FAILED_EVERYONE'), ephemeral=True)
        return

    bl_role, trash = get_user_roles(9)
    if role.id in bl_role:
        await inter.response.send_message(getLang(inter, section='Translation', line=f'GIVE_ROLE_FAILED_BLACKLIST'), ephemeral=True),
        return

    await inter.response.send_message(getLang(inter, section='Translation', line=f'GIVE_ROLE_SUCCESS').format(member.mention, role.mention))
    database_update("add", user=member.id, role=role.id)


@bot.slash_command(description='Removes a role from a user.', name='removerole', guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def removerole(inter, member: disnake.abc.User, role: disnake.abc.Role):
    if role.name == '@everyone':
        await inter.response.send_message(getLang(inter, section='Translation', line=f'REMOVE_ROLE_FAILED_EVERYONE'), ephemeral=True)
        return
    if inter.locale == 'ko':
        tempF = getLang(inter, section='Translation', line='REMOVE_ROLE_SUCCESS').format(member.mention, role.mention)
    else:
        tempF = getLang(inter, section='Translation', line='REMOVE_ROLE_SUCCESS').format(role.mention, member.mention)
    await inter.response.send_message(tempF)
    database_update("remove", user=member.id, role=role.id)
    await member.remove_roles(role, reason=f'Role removed by {inter.author} ({inter.author.id})')


@bot.slash_command(description='Gives an icon to a user.', name='giveicon', guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def addroleicon(inter, member: disnake.abc.User, role: disnake.abc.Role):
    if role.name == '@everyone':
        await inter.response.send_message(getLang(inter, section='Translation', line=f'GIVE_ROLE_FAILED_EVERYONE'), ephemeral=True)
        return

    trash, bl_role = get_user_roles(9)
    if role.id in bl_role:
        await inter.response.send_message(getLang(inter, section='Translation', line=f'GIVE_ROLE_FAILED_BLACKLIST'),ephemeral=True)
        return

    await inter.response.send_message(getLang(inter, section='Translation', line=f'GIVE_ICON_SUCCESS').format(member.mention, role.mention))
    database_update("add", user=member.id, roleIcon=role.id)


@bot.slash_command(description='Removes an icon from a user.', name='removeicon', guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def removeroleicon(inter, member: disnake.abc.User, role: disnake.abc.Role):
    if role.name == '@everyone':
        await inter.response.send_message(getLang(inter, section='Translation', line=f'REMOVE_ROLE_FAILED_EVERYONE'), ephemeral=True)
        return
    if inter.locale == 'ko':
        tempF = getLang(inter, section='Translation', line='REMOVE_ROLE_SUCCESS').format(member.mention, role.mention)
    else:
        tempF = getLang(inter, section='Translation', line='REMOVE_ROLE_SUCCESS').format(role.mention, member.mention)
    await inter.response.send_message(tempF)
    database_update("remove", user=member.id, roleIcon=role.id)
    await member.remove_roles(role, reason=f'Role removed by {inter.author} ({inter.author.id})')


@bot.slash_command(description='Shows All Role Assignments', name='listroles', guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def listall(inter, role: disnake.Role = None):
    if role:
        return await list_specific_role(inter, role)

    await inter.response.defer()

    conn = sqlite3.connect('roles.db')
    cur = conn.cursor()

    sql = '''SELECT * FROM roles'''
    cur.execute(sql)

    items = cur.fetchall()
    allRoles = []
    allIcons = []

    for i in items:
        usr, temp1, temp2 = i
        member = await inter.guild.get_or_fetch_member(usr)
        if member is None:
            pass
        else:
            temp1 = json.loads(temp1)
            temp2 = json.loads(temp2)
            for t1 in temp1:
                allRoles.append(t1)
            for t2 in temp2:
                allIcons.append(t2)

    roleCount = {}
    iconCount = {}

    for rl in allRoles:
        if rl not in roleCount:
            roleCount[rl] = 0
        roleCount[rl] += 1

    for ri in allIcons:
        if ri not in iconCount:
            iconCount[ri] = 0
        iconCount[ri] += 1

    roleCount = sorted(roleCount.items(), key=operator.itemgetter(1), reverse=True)
    iconCount = sorted(iconCount.items(), key=operator.itemgetter(1), reverse=True)

    color = 0x000000
    color2 = 0x000000

    roleStr = ''
    roleIconStr = ''
    roleClr = False
    for i in roleCount:
        temprole = inter.guild.get_role(i[0])
        roleStr = f'{roleStr}\n{temprole.mention}: **{i[1]}**'
        if not roleClr:
            color = temprole.color
            roleClr = True

    roleClr = False

    for i in iconCount:
        temprole = inter.guild.get_role(i[0])
        roleIconStr = f'{roleIconStr}\n{inter.guild.get_role(i[0]).mention}: **{i[1]}**'
        if not roleClr:
            color2 = temprole.color
            roleClr = True

    embed = disnake.Embed(title=getLang(inter, 'Translation', 'LIST_ALL_ROLES'), description=roleStr)
    embed.color = color
    embed.set_footer(text=getLang(inter, 'Translation', 'LIST_ALL_ROLES_FOOTER'))
    embed2 = disnake.Embed(title=getLang(inter, 'Translation', 'LIST_ALL_ICONS'), description=roleIconStr)
    embed2.color = color2
    embed2.set_footer(text=getLang(inter, 'Translation', 'LIST_ALL_ICONS_FOOTER'))

    await inter.edit_original_message(embeds=[embed, embed2])


async def list_specific_role(inter, role):
    await inter.response.defer()
    conn = sqlite3.connect('roles.db')
    cur = conn.cursor()

    roleID = role.id

    sql = f'''SELECT * FROM roles WHERE role LIKE '%{roleID}%' OR roleicon LIKE '%{roleID}%' '''
    cur.execute(sql)

    items = cur.fetchall()
    userList = []
    if len(items) > 0:
        for i in items:
            user, trash1, trash2 = i
            userObj = await inter.guild.get_or_fetch_member(user)
            # print(userObj, user)
            if userObj:
                userList.append(userObj)
    allUserStr = ''
    if len(userList) > 0:
        for au in userList:
            allUserStr = f'{allUserStr}\n{au.name} ({au.mention})'
            if len(allUserStr) > 4000:
                allUserStr = f'{allUserStr}\n{getLang(inter, "Translation", "LIST_ALL_OVERFLOW").format((len(userList) - userList.index(au)))}'
                break
    else:
        allUserStr = getLang(inter, 'Translation', 'LIST_ROLE_RETURN_NONE')
    embed = disnake.Embed(title=getLang(inter, 'Translation', 'LIST_ROLE').format(role.name), description=allUserStr, color=role.color)
    await inter.edit_original_message(embed=embed)


@bot.slash_command(name='dongulate', description='Adds all valid roles to a user.', guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def dongulate(inter, user: disnake.User):
    roleIDs, roleIconIDs = get_user_roles(0)
    roles_to_add = []
    roleIcons_to_add = []

    masterRoles = {
        298698700719521795:298698201270059009, #Rhythm Maestro -> Sushi Maestro
        409552655623389185:409551428814635008, #Rhythm Master -> Sushi Master
        819428632447287296:517143533853868074, #Cafe Champion -> Cafe Regular
        517143533853868074:517143450391543818, #Cafe Regular -> Cafe Visitor
    }

    addedRoles = []

    userRoles = user.roles

    for r in userRoles:

        if r.id in masterRoles:
            role = inter.guild.get_role(masterRoles[r.id])
            if role not in userRoles:
                userRoles.append(role)

        if r.id in roleIDs:
            roles_to_add.append(r)
            addedRoles.append(r.id)
            database_update('add', user.id, role=r.id)
        if r.id in roleIconIDs:
            roleIcons_to_add.append(r)
            database_update('add', user.id, roleIcon=r.id)

    betarole = inter.guild.get_role(965347079708897350)
    await user.add_roles(betarole, reason='Dongulated.')
    await user.remove_roles(*roles_to_add, reason='All valid roles added to user inventory.')
    await user.remove_roles(*roleIcons_to_add, reason='All valid role icons added to user inventory.')
    await inter.response.send_message(getLang(inter, 'Translation', 'DONGULATE_SUCCESS').format(user.mention))


@bot.slash_command(name='blacklist', description='Adds a role to the blacklist, forbidding it from being assigned.',
                   guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def blacklist(inter, role: disnake.Role):
    roleIDs, roleIconIDs = get_user_roles(9)
    roleA, roleIconA = get_user_roles(0)
    if role.id in roleIDs or role.id in roleIconIDs:
        database_update('remove', 9, role=role.id)
        await inter.response.send_message(content=getLang(inter, 'Translation', 'BLACKLIST_REMOVE_SUCCESS').format(role.name),
                                          ephemeral=True)
    else:
        database_update('add', 9, role=role.id)
        await inter.response.send_message(getLang(inter, 'Translation', 'BLACKLIST_ADD_SUCCESS').format(role.name), ephemeral=True)
        if role.id in roleA:
            database_update("remove", 0, role=role.id)
        elif role.id in roleIconA:
            database_update("remove", 0, role=role.id)


@bot.slash_command(name='assignrole', description='Adds or removes a role from the Dongulatable roles.',
                   guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def assign_role(inter, role: disnake.Role):
    roleIDs, trash = get_user_roles(0)
    bl_r, trash = get_user_roles(9)
    if role.id in bl_r:
        await inter.response.send_message(content=getLang(inter, 'Translation', 'DONGULATE_ASSIGN_FAILED_BLACKLIST').format(role.name),
                                          ephemeral=True)
        return

    if role.id in roleIDs:
        database_update('remove', 0, role=role.id)
        await inter.response.send_message(content=getLang(inter, 'Translation', 'DONGULATE_ASSIGN_REMOVED_SUCCESS').format(role.name),
                                          ephemeral=True)
    else:
        database_update('add', 0, role=role.id)
        await inter.response.send_message(getLang(inter, 'Translation', 'DONGULATE_ASSIGN_ADDED_SUCCESS').format(role.name), ephemeral=True)


@bot.slash_command(name='viewblacklist', description='Lists all blacklisted roles and role icons.', guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def vw_bl(inter):
    user = 9
    await inter.response.defer()
    embed1 = await _roles(inter, 'Role', returnEmbed=True, user=user)
    embed2 = await _roles(inter, 'Icon', returnEmbed=True, user=user)
    await inter.edit_original_message(embeds=[embed1, embed2])


@bot.slash_command(name='show', description='Shows off your role inventory publicly!', guild_ids=guilds)
async def showoff(inter):
    await inter.response.defer()
    user = inter.author
    embed1 = await _roles(inter, 'Role', returnEmbed=True, user=user)
    embed2 = await _roles(inter, 'Icon', returnEmbed=True, user=user)
    await inter.edit_original_message(embeds=[embed1, embed2])

@bot.slash_command(name='assignicon', description='Adds or removes a role from the Dongulatable roles.',
                   guild_ids=guilds)
@commands.has_permissions(manage_roles=True)
async def assign_role_icon(inter, role: disnake.Role):
    trash, roleIconIDs = get_user_roles(0)
    bl_r, trash = get_user_roles(9)
    if role.id in bl_r:
        await inter.response.send_message(content=getLang(inter, 'Translation', 'DONGULATE_ASSIGN_FAILED_BLACKLIST').format(role.name),
                                          ephemeral=True)
        return
    if role.id in roleIconIDs:
        database_update('remove', 0, roleIcon=role.id)
        await inter.response.send_message(content=getLang(inter, 'Translation', 'DONGULATE_ASSIGN_REMOVED_SUCCESS_ICON').format(role.name),
                                          ephemeral=True)
    else:
        database_update('add', 0, roleIcon=role.id)
        await inter.response.send_message(getLang(inter, 'Translation', 'DONGULATE_ASSIGN_ADDED_SUCCESS_ICON').format(role.name), ephemeral=True)


@bot.listen("on_dropdown")
async def on_role_select(inter):
    if inter.data.custom_id == 'role_select':
        raw_id = inter.data.values[0]
        role_id = int(raw_id[3:])
        type = raw_id[:2]

        if type == 'ro':
            type = 'role'
        else:
            type = 'roleIcon'

        role = inter.guild.get_role(role_id)
        member = inter.author

        roleList = []

        roleIDs, roleIconIDs = get_user_roles(member.id)
        true_roles = []

        if type == 'role':
            true_roles = roleIDs
        else:
            true_roles = roleIconIDs

    for r in true_roles:
        roleList.append(inter.guild.get_role(r))

    try:
        roleList.remove(role)
    except Exception as e:
        await inter.send(embed=disnake.Embed(title=getLang(inter, 'Translation', 'EQUIP_ROLE_FAILED_BAD_ROLE_TITLE').format(role.name),
                                             description=getLang(inter, 'Translation', 'EQUIP_ROLE_FAILED_BAD_ROLE'),
                                             color=0x0e0e0e), ephemeral=True)
        return

    try:
        await member.add_roles(role, reason=f'Role Assignment by {member.name}')
    except disnake.Forbidden as e:
        await inter.response.send_message(
            getLang(inter, 'Translation', 'EQUIP_ROLE_FAILED_ERROR_GENERIC'),
            ephemeral=True)
        return

    try:
        await member.remove_roles(*roleList, reason=f'Role Assignment by {member.name}')
    except disnake.Forbidden as e:
        await inter.response.send_message(
            getLang(inter, 'Translation', 'REMOVE_ROLE_FAILED_ERROR_GENERIC'),
            ephemeral=True)
        return

    embed = disnake.Embed(title='Role Selected',
                          description=getLang(inter, 'Translation', 'EQUIP_ROLE_SUCCESS').format(role.mention),
                          color=role.color)
    await inter.response.send_message(embed=embed, ephemeral=True)

@bot.listen("on_button_click")
async def on_page_click(inter):
    custom_id = inter.data.custom_id
    if custom_id[0:2] == 'ro':
        longvariablethatdoesnothing, pageNo = custom_id.split("_")
        await _roles(inter, type='Role', page=int(pageNo))
        if custom_id[0:2] == 'ri':
            longvariablethatdoesnothing, pageNo = custom_id.split("_")
            await _roles(inter, type='Icon', page=int(pageNo))

def add_user_to_database(user):
    conn = sqlite3.connect('roles.db')
    cur = conn.cursor()

    blank = json.dumps([])

    sql = '''INSERT INTO roles(user, role, roleicon) VALUES(?, ?, ?)'''  # Adds new user, default has no roles.
    cur.execute(sql, [user, blank, blank])
    conn.commit()


def get_user_roles(user, skip=False):
    if user == 9:
        skip = True

    conn = sqlite3.connect('roles.db')
    cur = conn.cursor()

    sql = '''SELECT role, roleicon FROM roles WHERE user IS ?'''
    cur.execute(sql, [user])  # Gets all roles & role icons from the user.

    item = cur.fetchone()
    if not item:
        add_user_to_database(user)
        return get_user_roles(user)

    # user_roles = json.load()
    roles_str, roleIcons_str = item
    roles, roleIcons = json.loads(roles_str), json.loads(roleIcons_str)

    if not skip:
        bl, trash = get_user_roles(9)

        for i in roles:
            if i in bl:
                database_update('remove', user, role=i)
                roles.remove(i)
        for ix in roleIcons:
            if ix in bl:
                database_update('remove', user, role=ix)
                roleIcons.remove(ix)

        bl, trash = get_user_roles(9, skip=True)
        to_blacklist = False
        for i in roles:
            if i in bl:
                to_blacklist = True
        for ix in roleIcons:
            if ix in bl:
                to_blacklist = True

        if to_blacklist:
            database_update("none", user)

    return roles, roleIcons


def database_update(action, user, role=None, roleIcon=None):
    conn = sqlite3.connect('roles.db')
    cur = conn.cursor()

    sql = '''SELECT role, roleicon FROM roles WHERE user IS ?'''
    cur.execute(sql, [user])  # Gets all roles & role icons from the user.

    roles, roleIcons = get_user_roles(user, skip=True)

    if action == 'add':
        if role in roles or roleIcon in roleIcons:
            return 'User already has role!'
        if role:
            roles.append(role)
        if roleIcon:
            roleIcons.append(roleIcon)
    elif action == 'remove':
        if role:
            if role not in roles:
                return 'User does not have that role!'

            roles.remove(role)
        if roleIcon:
            if roleIcon not in roleIcons:
                return 'User does not have that role!'

            roleIcons.remove(roleIcon)
    else:
        return False

    sql2 = '''UPDATE roles SET role = ? WHERE user IS ?'''
    cur.execute(sql2, [json.dumps(roles), user])
    sql3 = '''UPDATE roles SET roleicon = ? WHERE user IS ? '''
    cur.execute(sql3, [json.dumps(roleIcons), user])
    conn.commit()


@bot.listen()
async def on_slash_command_error(ctx, error):
    if isinstance(error, disnake.ext.commands.MissingPermissions):
        await ctx.send(getLang(ctx, 'Translation', 'COMMAND_FAILED_BAD_PERMISSIONS'), ephemeral=True)
        return

    await ctx.send(
        getLang(ctx, 'Translation', 'COMMAND_FAILED_UNKNOWN_ERROR').format(error))
    print(error)

bot.run(open('token.txt', 'r').read())
