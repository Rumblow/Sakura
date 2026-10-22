import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image
import io

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync() # Sincroniza los comandos Slash
    print(f"Bot conectado como {bot.user}")

# Función auxiliar para superponer capas de imágenes
def superponer_vanities(base_path, vanity_paths):
    canvas = Image.open(base_path).convert("RGBA")
    
    for path in vanity_paths:
        layer = Image.open(path).convert("RGBA")
        canvas.paste(layer, (0, 0), layer) # Usa el canal alfa para transparencia
        
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# Comando Slash: /vanity_info
@bot.tree.command(name="vanity_info", description="Muestra la información de un cosmético.")
@app_commands.describe(nombre="Nombre del cosmético")
async def vanity_info(interaction: discord.Interaction, nombre: str):
    # Aquí consultarías tu Base de Datos. Ejemplo estático:
    embed = discord.Embed(
        title=f"✨ {nombre.title()}",
        description="Información general del cosmético en PokeMMO.",
        color=discord.Color.purple()
    )
    embed.add_field(name="Ranura", value="Espalda (Back)", inline=True)
    embed.add_field(name="Limitado", value="Sí", inline=True)
    embed.add_field(name="Obtención", value="Gift Shop / Comercio GTL", inline=False)
    
    await interaction.response.send_message(embed=embed)

bot.run("MI_TOKEN_AQUI")