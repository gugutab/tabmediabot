import logging
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Configura o logging para vermos erros no console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- A LÓGICA DO SEU BOT COMEÇA AQUI ---

async def processa_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa todas as mensagens de texto em busca de links específicos."""
    message = update.message
    if not message or not message.text:
        return

    texto_original = message.text
    texto_modificado = texto_original
    links_alterados = False

    # Verifica se a mensagem contém links (URLs)
    if message.entities:
        for entity in message.entities:
            if entity.type == 'url':
                link_original = entity.get_text(texto_original)

                # --- Defina suas regras de substituição aqui ---
                if 'twitter.com' in link_original:
                    link_modificado = link_original.replace('twitter.com', 'x.com')
                    texto_modificado = texto_modificado.replace(link_original, link_modificado)
                    links_alterados = True
                elif 'seu-outro-site.com' in link_original:
                    # Adicione outras regras aqui se precisar
                    pass

    if links_alterados:
        logger.info(f"Link alterado para o usuário {message.from_user.name}")
        # Responde à mensagem original com o texto modificado
        await message.reply_text(texto_modificado, disable_web_page_preview=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem de boas-vindas quando o comando /start é executado."""
    await update.message.reply_text('Olá! Envie uma mensagem com um link do Twitter e eu vou corrigi-lo para você.')


def main() -> None:
    """Inicia o bot e fica escutando por mensagens."""
    # Pega o token de uma variável de ambiente para segurança
    TOKEN = os.getenv('TOKEN_TELEGRAM')
    if not TOKEN:
        logger.error("A variável de ambiente TOKEN_TELEGRAM não foi definida!")
        return

    # Cria a aplicação do bot
    application = Application.builder().token(TOKEN).build()

    # Adiciona os handlers (manipuladores)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processa_mensagem))

    logger.info("Bot iniciado e escutando...")
    # Inicia o bot
    application.run_polling()

if __name__ == '__main__':
    main()
