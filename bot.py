import logging
import os
from urllib.parse import urlparse, urlunparse, quote
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Configura o logging para vermos erros no console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ID do chat permitido ---
MEU_CHAT_ID = 476169897 

# --- Lista de domínios com paywall ---
PAYWALL_DOMAINS = {
    'bloomberg.com', 'correio.rac.com.br', 'nsctotal.com.br', 'economist.com', 
    'estadao.com.br', 'foreignpolicy.com', 'folha.uol.com.br', 'folha.com.br', 
    'gauchazh.clicrbs.com.br', 'zh.clicrbs.com.br', 'gazetadopovo.com.br', 
    'jota.info', 'jornalnh.com.br', 'nytimes.com', 'nyt.com', 'oglobo.globo.com', 
    'washingtonpost.com', 'exame.com', 'eltiempo.com', 'super.abril.com.br', 
    'veja.abril.com.br', 'quatrorodas.abril.com.br', 'uol.com.br', 'wsj.com', 
    'ft.com', 'gramophone.co.uk', 'folhadelondrina.com.br', 'wired.com', 
    'jornalvs.com.br', 'br18.com.br', 'diariopopular.com.br', 'haaretz.com', 
    'haaretz.co.il', 'diarinho.com.br', 'diariodaregiao.com.br', 
    'correio24horas.com.br', 'dgabc.com.br', 'crusoe.com.br', 'em.com.br', 
    'forbes.pl', 'forbes.com', 'newsweek.pl', 'seudinheiro.com', 
    'diariodecanoas.com.br', 'observador.pt', 'elpais.com', 'correiodopovo.com.br', 
    'technologyreview.com', 'revistagalileu.globo.com'
}

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

    # Mapeamento dos domínios de redes sociais
    REGRAS_SOCIAL = {
        'fixupx.com': ['twitter.com', 'x.com'],
        'fixtiktok.com': ['tiktok.com', 'vm.tiktok.com'],
        'ddinstagram.com': ['instagram.com'],
        'fxbsky.app': ['bsky.app']
    }

    for entity in message.entities:
        if entity.type == 'url':
            link_original = texto_original[entity.offset : entity.offset + entity.length]
            
            try:
                # Analisa o link para extrair o domínio de forma segura
                parsed_link = urlparse(link_original)
                domain_original = parsed_link.netloc.replace('www.', '')

                # 1. Checa se o domínio está na lista de PAYWALL
                if domain_original in PAYWALL_DOMAINS:
                    url_codificada = quote(link_original)
                    link_modificado = f"https://www.removepaywall.com/search?url={url_codificada}"
                    
                    texto_modificado = texto_modificado.replace(link_original, link_modificado)
                    links_alterados = True
                    continue # Pula para o próximo link, pois este já foi tratado

                # 2. Se não for paywall, checa as regras de redes sociais
                for novo_domain, dominios_antigos in REGRAS_SOCIAL.items():
                    if domain_original in dominios_antigos:
                        partes_do_link = parsed_link._replace(netloc=novo_domain)
                        link_modificado = urlunparse(partes_do_link)
                        
                        texto_modificado = texto_modificado.replace(link_original, link_modificado)
                        links_alterados = True
                        break # Pula para o próximo link

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
