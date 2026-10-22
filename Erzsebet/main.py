import discord
from discord.ext import commands
from discord import app_commands
import os
import pymupdf  # PyMuPDF para renderizar páginas de PDF
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configuración de intenciones
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

BASE_DIR = Path(__file__).resolve().parent
OUTFITS_DIR = BASE_DIR / "outfits"
MAGAZINES_DIR = BASE_DIR / "magazines"
EVENT_DURATION = timedelta(hours=2)

GUILD_ID = 1449529909289549987  # Reemplaza con la ID numérica de tu servidor de prueba (sin comillas)

@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        # Copia las firmas de los comandos al servidor específico
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ Sincronizados {len(synced)} comandos en el servidor {GUILD_ID}.")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

    print(f"🤖 Bot conectado exitosamente como {bot.user}")

# Comando /fit <jugador>
@bot.tree.command(name="fit", description="Muestra la foto del outfit de un jugador de PokeMMO.")
@app_commands.describe(jugador="Nombre del jugador en PokeMMO")
async def fit(interaction: discord.Interaction, jugador: str):
    nombre_normalizado = jugador.strip()
    ruta_imagen = next(
        (
            path
            for path in OUTFITS_DIR.iterdir()
            if path.is_file()
            and path.stem.casefold() == nombre_normalizado.casefold()
            and path.suffix.casefold() in {".png", ".jpg", ".jpeg"}
        ),
        None,
    )

    # Verificamos si la imagen del jugador existe en la carpeta
    if ruta_imagen is None:
        await interaction.response.send_message(
            f"❌ No encontré ningún outfit registrado para el jugador **{jugador}**.",
            ephemeral=True # Mensaje visible solo para quien usó el comando
        )
        return

    # Cargamos el archivo de la imagen para enviarlo a Discord
    file = discord.File(ruta_imagen, filename=ruta_imagen.name)

    # Creamos una tarjeta (Embed) estética
    embed = discord.Embed(
       title=f"✨ Outfit de {jugador.title()}",
        description=f"Mostrando la tarjeta de estilo de **{jugador}** en PokeMMO.",
        color=discord.Color.from_rgb(147, 112, 219) # Color púrpura/violeta
    )
    # Vinculamos la imagen adjunta con el Embed
    embed.set_image(url=f"attachment://{ruta_imagen.name}")
    embed.set_footer(text="PokeMMO Vanity Bot • Vanity Magazine")

    # Enviamos la respuesta con el Embed y el archivo adjunto
    await interaction.response.send_message(embed=embed, file=file)

# ==========================================
# SECCIÓN: VANITY MAGAZINE (EDICIONES & PDF)
# ==========================================

EDICIONES_MAGAZINE = {
    "edicion_1": {
        "titulo": "Vanity Magazine - Edición #1",
        "descripcion": "Primera edición oficial de la revista de modas de PokeMMO. ¡Descubre las últimas tendencias y análisis!",
        "foro_url": "https://forums.pokemmo.com/index.php?/topic/197886-vanity-megazine/", # Reemplaza con el link real de tu hilo
        "pdf_file": MAGAZINES_DIR / "edicion_1.pdf",
        "portada_file": MAGAZINES_DIR / "portadas" / "portada_principal.png"
    },
    "edicion_2": {
        "titulo": "Vanity Magazine - Edición #2",
        "descripcion": "Especial de tendencias de moda, entrevistas exclusivas a la comunidad.",
        "foro_url": "https://forums.pokemmo.com/index.php?/topic/197886-vanity-megazine/page/2/#findComment-2247155", # Reemplaza con el link real de tu hilo
        "pdf_file": MAGAZINES_DIR / "epok_interview" / "epok_interview.pdf",
        "portada_file": MAGAZINES_DIR / "epok_interview" / "page1_cover.png"
    }
}

class MagazineView(discord.ui.View):
    def __init__(self, foro_url: str, pdf_path: str, titulo: str):
        super().__init__(timeout=None)
        self.pdf_path = pdf_path
        self.titulo = titulo

        self.add_item(discord.ui.Button(
            label="🌐 Ver en el Foro de PokeMMO",
            url=foro_url,
            style=discord.ButtonStyle.link
        ))

    @discord.ui.button(label="Descargar PDF", style=discord.ButtonStyle.primary, emoji="📥")
    async def download_pdf(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not os.path.exists(self.pdf_path):
            await interaction.response.send_message(
                "❌ El archivo PDF de esta edición no se encuentra disponible.",
                ephemeral=True
            )
            return

        file = discord.File(self.pdf_path, filename=Path(self.pdf_path).name)
        await interaction.response.send_message(
            content=f"📖 Aquí tienes el archivo PDF de **{self.titulo}**:",
            file=file,
            ephemeral=True
        )

# ==========================================
# FUNCIÓN PARA RENDERIZAR PDF A IMAGEN
# ==========================================
def pdf_a_imagen(pdf_path, numero_pagina=0):
    """ Convierte una página de un PDF a una imagen PNG en memoria """
    with pymupdf.open(pdf_path) as doc:
        if not 0 <= numero_pagina < doc.page_count:
            raise ValueError(f"Página fuera de rango: {numero_pagina}")
        pagina = doc.load_page(numero_pagina)
        pix = pagina.get_pixmap(dpi=150)
        img_bytes = io.BytesIO(pix.tobytes("png"))
    img_bytes.seek(0)
    return img_bytes

# ==========================================
# COMANDO /MAGAZINE
# ==========================================
@bot.tree.command(name="magazine", description="Muestra las ediciones de Vanity Magazine con su vista previa y foro.")
@app_commands.choices(edicion=[
    app_commands.Choice(name="Edición #1 - Lanzamiento", value="edicion_1"),
    app_commands.Choice(name="Edición #2 - Tendencias & Mercado", value="edicion_2"),
])
async def magazine(interaction: discord.Interaction, edicion: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)

    data = EDICIONES_MAGAZINE.get(edicion.value)

    if not data:
        await interaction.followup.send(
            "❌ No se encontró información para esta edición.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=f"✨ {data['titulo']}",
        description=data["descripcion"],
        color=discord.Color.from_rgb(186, 85, 211)
    )

    files_to_send = []

    # 1. Adjuntamos la miniatura de la portada si existe
    if data["portada_file"].is_file():
        filename_portada = data["portada_file"].name
        cover_file = discord.File(data["portada_file"], filename=filename_portada)
        files_to_send.append(cover_file)
        embed.set_thumbnail(url=f"attachment://{filename_portada}")

    # 2. Renderizamos la primera página del PDF como imagen y la mostramos en grande
    if data["pdf_file"].is_file():
        imagen_pdf_buffer = pdf_a_imagen(data["pdf_file"], numero_pagina=0)
        pdf_preview_file = discord.File(imagen_pdf_buffer, filename="preview_revista.png")
        files_to_send.append(pdf_preview_file)

        # Muestra la página del PDF en grande en el chat
        embed.set_image(url="attachment://preview_revista.png")

    embed.add_field(
        name="📖 Vista Previa Interactiva",
        value="Aquí tienes la vista previa de la revista directamente en el chat.",
        inline=False
    )
    embed.set_footer(text="Vanity Magazine • Editorial Oficial de PokeMMO")

    # Vista con el botón al foro de PokeMMO
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="🌐 Ver en el Foro de PokeMMO",
        url=data["foro_url"],
        style=discord.ButtonStyle.link
    ))

    await interaction.followup.send(embed=embed, files=files_to_send, view=view)

# ==========================================
# BASE DE DATOS LOCAL DE EVENTOS DE POKEMMO
# ==========================================
EVENTOS_POKEMMO = [
    {
        "id": "torneo_pvp_1",
        "nombre": "🏆 Torneo PvP OU - Pokeball Cup",
        "descripcion": "¡Demuestra tus habilidades en el formato OverUsed! Premios en yenes y objetos cosméticos.",
        "ubicación": "Kanto - Isla 4 (Canal 1)",
        "inicio": datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc), # Año, Mes, Día, Hora (UTC)
        "imagen_url": "https://i.imgur.com/example.png" # Opcional
    },
    {
        "id": "fashion_contest_1",
        "nombre": "✨ Concurso de Moda Vanity Magazine",
        "descripcion": "Especial de outfits temáticos. Se evaluará originalidad y combinación de colores.",
        "ubicación": "Unova - Ciudad Mayólica (Canal 4)",
        "inicio": datetime(2026, 10, 28, 22, 0, tzinfo=timezone.utc),
        "imagen_url": "https://i.imgur.com/example.png"
    }
]

# ==========================================
# COMANDO /EVENTOS (VER PRÓXIMOS EVENTOS)
# ==========================================
@bot.tree.command(name="eventos", description="Muestra los próximos eventos programados de PokeMMO.")
async def eventos(interaction: discord.Interaction):
    ahora = datetime.now(timezone.utc)

    embed = discord.Embed(
        title="📅 Próximos Eventos en PokeMMO",
        description="Aquí tienes la lista de actividades y torneos programados:",
        color=discord.Color.from_rgb(255, 215, 0) # Color dorado
    )

    for evento in EVENTOS_POKEMMO:
        inicio = evento["inicio"]
        fin = inicio + EVENT_DURATION
        # Convertimos la fecha a Timestamp de Discord para que cada usuario lo vea en su hora local
        timestamp_discord = f"<t:{int(inicio.timestamp())}:R>" # Muestra "En 2 días", "En 3 horas", etc.
        timestamp_fecha = f"<t:{int(inicio.timestamp())}:F>"

        # Verificamos si ya está sucediendo o si es futuro
        if inicio <= ahora < fin:
            estado = "🔴 **¡EN CURSO AHORA MISMO!**"
        elif ahora >= fin:
            estado = "✅ **Finalizado**"
        else:
            estado = f"⏳ Comienza: {timestamp_discord}"

        embed.add_field(
            name=f"📌 {evento['nombre']}",
            value=(
                f"📝 **Descripción:** {evento['descripcion']}\n"
                f"📍 **Ubicación:** {evento['ubicación']}\n"
                f"🕒 **Fecha:** {timestamp_fecha}\n"
                f"**Estado:** {estado}\n"
            ),
            inline=False
        )

    embed.set_footer(text="PokeMMO Vanity Bot • Mantente al tanto de la comunidad")
    await interaction.response.send_message(embed=embed)


# ==========================================
# COMANDO /CREAR_EVENTO_DISCORD (EVENTO NATIVO)
# ==========================================
@bot.tree.command(name="sincronizar_eventos", description="Crea los eventos nativos en la sección de eventos del servidor.")
@app_commands.default_permissions(administrator=True) # Solo administradores
async def sincronizar_eventos(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ Este comando solo funciona dentro de un servidor.", ephemeral=True)
        return

    creados = 0
    ahora = datetime.now(timezone.utc)
    eventos_existentes = await guild.fetch_scheduled_events()
    claves_existentes = {
        (evento.name, evento.start_time) for evento in eventos_existentes
    }

    for ev in EVENTOS_POKEMMO:
        # Solo creamos eventos que no hayan pasado aún
        clave_evento = (ev["nombre"], ev["inicio"])
        if ev["inicio"] > ahora and clave_evento not in claves_existentes:
            fin = ev["inicio"] + EVENT_DURATION

            # Crear evento en la interfaz de Discord
            await guild.create_scheduled_event(
                name=ev["nombre"],
                description=f"{ev['descripcion']}\n\n📍 Ubicación: {ev['ubicación']}",
                start_time=ev["inicio"],
                end_time=fin,
                entity_type=discord.EntityType.external,
                location=ev["ubicación"]
            )
            claves_existentes.add(clave_evento)
            creados += 1

    await interaction.response.send_message(
        f"✅ Se han publicado **{creados}** eventos en la pestaña de **Eventos del Servidor**.",
        ephemeral=True
    )

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Configura el token del bot en la variable de entorno DISCORD_TOKEN.")

bot.run(TOKEN)