from telethon import TelegramClient, events, functions, types
import asyncio
from datetime import datetime, timedelta

api_id = '20925460'
api_hash = '1d97f11e65eeeb3df4528b965feeb157'
bot_token = '7208219154:AAEPZ0luO2R7QLUupfPmRVir4V4WUEGKXnM'

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Diccionario para almacenar la última actividad de cada usuario por grupo
last_activity = {}

# Username del canal de referencia
ref_channel_username = 'OLDMONEYCO'

# ID del creador del bot
creator_id = 5546251579

# Lista de IDs de usuarios con acceso a los comandos
authorized_ids = [creator_id]

# Función para formatear el tiempo transcurrido
def time_since(dt):
    now = datetime.now()
    diff = now - dt
    days, seconds = diff.days, diff.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if days > 0:
        return f"{days} día(s) atrás"
    elif hours > 0:
        return f"{hours} hora(s) atrás"
    elif minutes > 0:
        return f"{minutes} minuto(s) atrás"
    else:
        return "hace un momento"

# Función para verificar si el usuario tiene acceso a los comandos
def is_authorized(user_id):
    return user_id in authorized_ids

# Comando para agregar o eliminar usuarios autorizados usando tags o IDs
@client.on(events.NewMessage(pattern='/vaki (add|remove) (.+)'))
async def manage_access(event):
    if event.sender_id == creator_id:
        action, identifier = event.pattern_match.groups()
        try:
            if identifier.isdigit():
                user_id = int(identifier)
                user = await client.get_entity(user_id)
            else:
                user = await client.get_entity(identifier)
                user_id = user.id

            if action == 'add':
                if user_id not in authorized_ids:
                    authorized_ids.append(user_id)
                    await event.respond(f"{user.first_name} (@{user.username}) ahora tiene acceso a los comandos del bot.")
                else:
                    await event.respond(f"{user.first_name} (@{user.username}) ya tiene acceso a los comandos del bot.")
            elif action == 'remove':
                if user_id in authorized_ids and user_id != creator_id:
                    authorized_ids.remove(user_id)
                    await event.respond(f"{user.first_name} (@{user.username}) ya no tiene acceso a los comandos del bot.")
                else:
                    await event.respond(f"No se puede eliminar al creador del bot o {user.first_name} (@{user.username}) no tiene acceso a los comandos.")
        except Exception as e:
            await event.respond(f"No se pudo encontrar al usuario {identifier}. Error: {str(e)}")
    else:
        await event.respond("No tienes permiso para usar este comando.")

# Comando para activar el seguimiento de actividad
@client.on(events.NewMessage(pattern='/activate'))
async def activate(event):
    if is_authorized(event.sender_id):
        if event.is_group:
            chat_id = event.chat_id
            last_activity[chat_id] = {}
            await event.respond("El chequeo de actividad en este grupo ya está funcionando.")
        else:
            await event.respond("Este comando solo puede ser usado en grupos.")
    else:
        await event.respond("No tienes permiso para usar este comando.")

# Comando para mostrar la actividad de los miembros
@client.on(events.NewMessage(pattern='/activity'))
async def activity(event):
    if is_authorized(event.sender_id):
        if event.is_group:
            chat_id = event.chat_id
            if chat_id in last_activity:
                members_activity = last_activity[chat_id]
                if members_activity:
                    response = "Actividad de los miembros:\n"
                    for user_id, last_msg_time in members_activity.items():
                        user = await client.get_entity(user_id)
                        time_ago = time_since(last_msg_time)
                        response += f"{user.first_name} (@{user.username}): Último mensaje enviado el {last_msg_time} ({time_ago})\n"
                else:
                    response = "No se ha registrado actividad de los miembros aún."
            else:
                response = "El chequeo de actividad no está activado en este grupo."
            await event.respond(response)
        else:
            await event.respond("Este comando solo puede ser usado en grupos.")
    else:
        await event.respond("No tienes permiso para usar este comando.")

# Escuchar todos los mensajes para actualizar la última actividad
@client.on(events.NewMessage())
async def update_activity(event):
    if event.is_group:
        chat_id = event.chat_id
        user_id = event.sender_id
        if chat_id in last_activity:
            last_activity[chat_id][user_id] = datetime.now()

# Comando para reenviar un mensaje citado al canal de referencia
@client.on(events.NewMessage(pattern='/ref'))
async def forward_reference(event):
    if is_authorized(event.sender_id):
        if event.is_group:
            if event.is_reply:
                reply = await event.get_reply_message()
                try:
                    # Obtiene la entidad del canal de referencia usando el username
                    ref_channel = await client.get_entity(ref_channel_username)
                    # Reenvía el mensaje al canal de referencia
                    await client.forward_messages(ref_channel, reply)
                    await event.respond(f"Mensaje reenviado al canal de referencia {ref_channel_username}.")
                except Exception as e:
                    await event.respond(f"No se pudo reenviar el mensaje. Error: {str(e)}")
            else:
                await event.respond("Por favor, responde a un mensaje que desees reenviar al canal de referencia.")
        else:
            await event.respond("Este comando solo puede ser usado en grupos.")
    else:
        await event.respond("No tienes permiso para usar este comando.")

# Comando para crear una invitación y enviarla al MD del usuario
@client.on(events.NewMessage(pattern='/invite (\d+)'))
async def create_invite(event):
    if is_authorized(event.sender_id):
        try:
            usos = int(event.pattern_match.group(1))
            if event.is_group:
                chat_id = event.chat_id
                invite = await client(functions.messages.ExportChatInviteRequest(
                    peer=chat_id,
                    expire_date=None,  # No expiration
                    usage_limit=usos
                ))
                await client.send_message(event.sender_id, f"Tu invitación al grupo: {invite.link}")
                await event.respond("La invitación ha sido enviada a tu MD.")
            else:
                await event.respond("Este comando solo puede ser usado en grupos.")
        except Exception as e:
            await event.respond(f"No se pudo crear la invitación. Error: {str(e)}")
    else:
        await event.respond("No tienes permiso para usar este comando.")

# Función para revisar la actividad de los miembros y enviar advertencias
async def check_inactivity():
    while True:
        now = datetime.now()
        for chat_id, members in last_activity.items():
            for user_id, last_msg_time in members.items():
                if now - last_msg_time > timedelta(days=1):
                    user = await client.get_entity(user_id)
                    await client.send_message(chat_id, f"@{user.username} lleva 1 día sin tener actividad.")
        await asyncio.sleep(3600)  # Esperar una hora antes de volver a revisar

# Iniciar la tarea de revisar inactividad
with client:
    client.loop.create_task(check_inactivity())
    client.run_until_disconnected()
