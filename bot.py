import logging
import os
from urllib.parse import urlparse, urlunparse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Configura o logging para vermos erros no console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MEU_CHAT_ID = 476169897 
# --- A LÓGICA DO SEU BOT COMEÇA AQUI ---

async def processa_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa todas as mensagens de texto em busca de links específicos."""
    message = update.message

    # --- FILTRO DE CHAT ID ---
    if message.chat_id != MEU_CHAT_ID:
        return # Ignora a mensagem se não for do chat permitido
        
    if not message or not message.text or not message.entities:
        return

    texto_original = message.text
    texto_modificado = texto_original
    links_alterados = False

    # Mapeamento dos domínios antigos para os novos
    REGRAS_DE_SUBSTITUICAO = {
        'fixupx.com': ['twitter.com', 'x.com'],
        'fixtiktok.com': ['tiktok.com', 'vm.tiktok.com'],
        'ddinstagram.com': ['instagram.com']
    }

    for entity in message.entities:
        if entity.type == 'url':
            link_original = texto_original[entity.offset : entity.offset + entity.length]
            
            try:
                # Analisa o link para extrair o domínio de forma segura
                parsed_link = urlparse(link_original)
                domain_original = parsed_link.netloc.replace('www.', '')

                # Verifica se o domínio está em alguma das nossas regras
                for novo_domain, dominios_antigos in REGRAS_DE_SUBSTITUICAO.items():
                    if domain_original in dominios_antigos:
                        # Remonta o link com o novo domínio, mantendo o resto da URL
                        partes_do_link = parsed_link._replace(netloc=novo_domain)
                        link_modificado = urlunparse(partes_do_link)
                        
                        # Substitui o link antigo pelo novo no texto completo da mensagem
                        texto_modificado = texto_modificado.replace(link_original, link_modificado)
                        links_alterados = True
                        break # Pula para a próxima entidade/link

            except Exception as e:
                logger.error(f"Erro ao processar o link {link_original}: {e}")
                continue

    if links_alterados:
        logger.info(f"Link(s) alterado(s) para o usuário {message.from_user.name}")
        # Responde à mensagem original com o texto modificado
        await message.reply_text(texto_modificado, disable_web_page_preview=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem de boas-vindas quando o comando /start é executado."""
    await update.message.reply_text('Olá! Envie uma mensagem com um link do Twitter, Instagram ou TikTok e eu vou corrigi-lo para você.')

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia o ID do chat atual."""
    chat_id = update.message.chat_id
    await update.message.reply_text(f"O ID deste chat é: {chat_id}")

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
    application.add_handler(CommandHandler("myid", get_chat_id))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processa_mensagem))

    logger.info("Bot iniciado e escutando...")
    # Inicia o bot
    application.run_polling()

if __name__ == '__main__':
    main()
