import logging
import os
import random
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse, quote
from telegram import Update
from telegram.constants import ParseMode
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

# Mapeamento dos domínios de redes sociais
REGRAS_SOCIAL = {
    'fixupx.com': ['twitter.com', 'x.com'],
    'fixtiktok.com': ['tiktok.com', 'vm.tiktok.com'],
    'ddinstagram.com': ['instagram.com'],
    'fxbsky.app': ['bsky.app']
}

# --- Variáveis para o Cooldown do /acende ---
_last_acende_time = datetime.min
_acende_cooldown = timedelta(seconds=30)


# --- FUNÇÃO CENTRAL DE LÓGICA ---

def corrigir_links_automatico(texto_original, entities):
    """
    Função que processa links automaticamente baseado nas regras predefinidas.
    Retorna uma tupla: (texto_modificado, links_alterados, contem_paywall)
    """
    if not texto_original or not entities:
        return texto_original, False, False

    texto_modificado = texto_original
    links_alterados = False
    contem_paywall = False

    for entity in entities:
        if entity.type == 'url':
            link_original = texto_original[entity.offset : entity.offset + entity.length]
            
            try:
                parsed_link = urlparse(link_original)
                domain_original = parsed_link.netloc.replace('www.', '')

                # 1. Checa se o domínio termina com um dos domínios da lista de PAYWALL
                paywall_match_found = False
                for paywall_domain in PAYWALL_DOMAINS:
                    if domain_original.endswith(paywall_domain):
                        contem_paywall = True
                        url_removepaywall = f"https://www.removepaywall.com/search?url={quote(link_original)}"
                        texto_do_link = "🖕Vá se foder, paywall!🖕"
                        link_modificado = f'<a href="{url_removepaywall}">{texto_do_link}</a>'
                        
                        texto_modificado = texto_modificado.replace(link_original, link_modificado)
                        links_alterados = True
                        paywall_match_found = True
                        break

                if paywall_match_found:
                    continue

                # 2. Checa Redes Sociais
                for novo_domain, dominios_antigos in REGRAS_SOCIAL.items():
                    if domain_original in dominios_antigos:
                        partes_do_link = parsed_link._replace(netloc=novo_domain)
                        link_modificado = urlunparse(partes_do_link)
                        
                        texto_modificado = texto_modificado.replace(link_original, link_modificado)
                        links_alterados = True
                        break
            
            except Exception as e:
                logger.error(f"Erro ao processar o link {link_original}: {e}")
                continue

    return texto_modificado, links_alterados, contem_paywall


# --- HANDLERS DE COMANDOS E MENSAGENS ---

async def processa_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa automaticamente as mensagens de texto em busca de links."""
    message = update.message
    if message.chat_id != MEU_CHAT_ID:
        return

    texto_modificado, links_alterados, contem_paywall = corrigir_links_automatico(message.text, message.entities)

    if links_alterados:
        logger.info(f"Link(s) alterado(s) automaticamente para o usuário {message.from_user.name}")
        if contem_paywall:
            await message.reply_text(texto_modificado, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        else:
            await message.reply_text(texto_modificado, disable_web_page_preview=False)

async def comando_paywall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa o comando /paywall, funcionando em resposta a uma mensagem
    ou com um link na própria mensagem.
    """
    message = update.message
    # Prioriza a mensagem respondida; se não houver, usa a própria mensagem do comando.
    target_message = message.reply_to_message or message

    if not target_message.text or not target_message.entities:
        await message.reply_text("Cade o link, porra!?")
        return

    texto_original = target_message.text
    entities = target_message.entities
    link_modificado_final = None

    # Procura pelo primeiro link na mensagem alvo
    for entity in entities:
        if entity.type == 'url':
            link_original = texto_original[entity.offset : entity.offset + entity.length]
            
            # Gera o link do removepaywall para QUALQUER URL encontrada
            url_removepaywall = f"https://www.removepaywall.com/search?url={quote(link_original)}"
            texto_do_link = "🖕Vá se foder, paywall!🖕"
            link_modificado_final = f'<a href="{url_removepaywall}">{texto_do_link}</a>'
            
            break # Processa apenas o primeiro link encontrado

    if link_modificado_final:
        logger.info(f"Link(s) alterado(s) manualmente via /paywall por {message.from_user.name}")
        # Responde à mensagem que continha o link original, mas APENAS com o novo hiperlink
        await target_message.reply_text(
            link_modificado_final, 
            parse_mode=ParseMode.HTML, 
            disable_web_page_preview=True
        )
    else:
        await message.reply_text("Cade o link, porra!?")


async def comando_acende(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Implementa a lógica do 'rojão' com cooldown e variações aleatórias."""
    global _last_acende_time, _acende_cooldown
    message = update.message

    # Checa se é domingo (domingo = 6 na biblioteca datetime do Python)
    if datetime.now().weekday() == 6:
        await message.reply_text("Abaixo a escala 6x1!!!")
        return

    # Checa o cooldown
    time_since_last_use = datetime.utcnow() - _last_acende_time
    if time_since_last_use < _acende_cooldown:
        await message.reply_text("Calma porra!")
        return

    # Atualiza o tempo do último uso
    _last_acende_time = datetime.utcnow()

    # Define as sequências de mensagens (blocos)
    async def bloco1():
        await message.reply_text("pra pra")
        await asyncio.sleep(0.2)
        await message.reply_text("pra")
        await asyncio.sleep(0.1)
        await message.reply_text("pra")
        await asyncio.sleep(0.1)
        await message.reply_text("pra pra pra pra pra")
        await asyncio.sleep(0.4)
        await message.reply_text("POOOOOWW")

    async def bloco2():
        await message.reply_text("pra")
        await asyncio.sleep(0.2)
        await message.reply_text("pra pra pra")
        await asyncio.sleep(0.1)
        await message.reply_text("pra")
        await asyncio.sleep(0.1)
        await message.reply_text("...")
        await asyncio.sleep(0.6)
        await message.reply_text("POOOWW")

    async def bloco3():
        await message.reply_text("tra tra tra")
        await asyncio.sleep(0.3)
        await message.reply_text("tra tra")
        await asyncio.sleep(0.15)
        await message.reply_text("POW POW POW")
        await asyncio.sleep(0.5)
        await message.reply_text("BOOOOM")

    async def bloco4():
        await message.reply_text("pra")
        await asyncio.sleep(0.2)
        await message.reply_text("pra pra pra pra pra")
        await asyncio.sleep(0.1)
        await message.reply_text("pra pra pra")
        await asyncio.sleep(0.1)
        await message.reply_text("...")
        await asyncio.sleep(0.6)
        await message.reply_text("tssss...")

    async def bloco5():
        await message.reply_text("pra")
        await asyncio.sleep(0.2)
        await message.reply_text("pra pra...")
        await asyncio.sleep(0.6)
        await message.reply_text("pra pra pra")
        await asyncio.sleep(0.1)
        await message.reply_text("...")
        await asyncio.sleep(1.2)
        await message.reply_text("vai toma no cu")

    async def bloco6():
        await message.reply_text("pra")
        await asyncio.sleep(0.2)
        await message.reply_text("pra pra")
        await asyncio.sleep(0.1)
        await message.reply_text("pra pra pra")
        await asyncio.sleep(0.2)
        await message.reply_text("pra pra pra pra pra pra pra...")
        await asyncio.sleep(0.1)
        await message.reply_text("...")
        await asyncio.sleep(1.2)
        await message.reply_text("☭ revolução do proletariado já! ☭")

    async def bloco7():
        await message.reply_text("pra")
        await asyncio.sleep(0.2)
        await message.reply_text("psra para")
        await asyncio.sleep(0.1)
        await message.reply_text("pra pra pra pra pra ...")
        await asyncio.sleep(1.0)
        await message.reply_text("...")
        await asyncio.sleep(1.2)
        await message.reply_text("Não deita aí não Tio França!!!!!!!")
        await asyncio.sleep(0.6)
        await message.reply_text("🐂👨🏻‍🦲💥☠️")

    # Lista de blocos e suas probabilidades
    blocos = [bloco1, bloco2, bloco3, bloco4, bloco5, bloco6, bloco7]
    pesos = [25, 25, 25, 10, 5, 5, 5]

    # Escolhe um bloco baseado nos pesos e o executa
    bloco_escolhido = random.choices(blocos, weights=pesos, k=1)[0]
    await bloco_escolhido()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem de boas-vindas quando o comando /start é executado."""
    await update.message.reply_text('Olá! Envie uma mensagem com um link e eu vou corrigi-lo para você.')

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia o ID do chat atual."""
    chat_id = update.message.chat_id
    await update.message.reply_text(f"O ID deste chat é: {chat_id}")


def main() -> None:
    """Inicia o bot e fica escutando por mensagens."""
    TOKEN = os.getenv('TOKEN_TELEGRAM')
    if not TOKEN:
        logger.error("A variável de ambiente TOKEN_TELEGRAM não foi definida!")
        return

    application = Application.builder().token(TOKEN).build()

    # Adiciona os handlers (manipuladores)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", get_chat_id))
    application.add_handler(CommandHandler("paywall", comando_paywall))
    application.add_handler(CommandHandler("acende", comando_acende))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processa_mensagem))

    logger.info("Bot iniciado e escutando...")
    application.run_polling()

if __name__ == '__main__':
    main()
