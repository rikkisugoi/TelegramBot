from telegram.ext import *
from telegram import *
import logging
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport
#from pprint import pprint
from datetime import datetime


#TOKEN='TOKEN_GENERATED_BY_BOTFATHER'
#REQUEST_KWARGS={
    #'proxy_url': 'PROXY_HERE',
    # Optional, if you need authentication:
    #'urllib3_proxy_kwargs': {
    #    'username': 'PROXY_USER',
    #    'password': 'PROXY_PASS',
    #}
#}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

INIT, TIPO_PESSOA, NUM_DOCUMENTO = range(3)
opcoes_menu = [[InlineKeyboardButton("Realizar consulta", callback_data='consultar'), InlineKeyboardButton("Não fazer nada", callback_data='null')]]
opcoes_tipo_pessoa = [[InlineKeyboardButton("Pessoa Física", callback_data='F'), InlineKeyboardButton("Pessoa Jurídica", callback_data='J')]]

dataAlertaMaisRecente = None
dataInadimplenciaMaisRecente = None



def start(bot, update):
    print('start')
    #reply_markup = ReplyKeyboardMarkup(keyboard=[[ KeyboardButton(text="Realizar Consulta"), KeyboardButton(text="Não fazer nada")]], one_time_keyboard=True)
    #bot.send_message(update.message.chat_id, 
    #             text="Olá! Escolha uma das opções:", 
    #             reply_markup=reply_markup)
    bot.send_message(update.message.chat_id, "Olá! Escolha uma opção:", reply_markup=InlineKeyboardMarkup(opcoes_menu))

    return INIT



def menuSelect(bot,update):
    print('menuSelect')
    query = update.callback_query
    
    if query.data == 'consultar':
        bot.send_message(query.message.chat_id,
                            text="Deseja consultar Pessoa Física ou Jurídica? \n" \
                            "Clique em um botão abaixo ou digite sua escolha.",
                            reply_markup=InlineKeyboardMarkup(opcoes_tipo_pessoa))
        return TIPO_PESSOA
    else:
        bot.send_message(query.message.chat_id,
                            text="Até a próxima. Se desejar iniciar o Bot novamente, pressione ou digite /start.")
        return ConversationHandler.END



def tipoPessoaSelect(bot,update, user_data):
    print('tipoPessoaSelect')

    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
        tipoSelecionado = update.callback_query.data
    if update.message:
        chat_id = update.message.chat_id
        tipoSelecionado = update.message.text.upper()
        if tipoSelecionado == 'F' \
        or tipoSelecionado == 'FISICA' or tipoSelecionado == 'FÍSICA' \
        or tipoSelecionado == 'PF' or tipoSelecionado == 'CPF' \
        or tipoSelecionado == 'PESSOA FISICA' or tipoSelecionado == 'PESSOA FÍSICA':
            tipoSelecionado = 'F'
        elif tipoSelecionado == 'J' \
        or tipoSelecionado == 'PJ' or tipoSelecionado == 'CNPJ' \
        or tipoSelecionado == 'JURIDICA' or tipoSelecionado == 'JURÍDICA' \
        or tipoSelecionado == 'PESSOA JURIDICA' or tipoSelecionado == 'PESSOA JURÍDICA':
            tipoSelecionado = 'J'
        
    if tipoSelecionado == 'F' or tipoSelecionado == 'J':
        user_data['tipo_pessoa'] = tipoSelecionado
        bot.send_message(chat_id,
                        text="Certo. Agora digite o número do documento (CPF ou CNPJ):")
        return NUM_DOCUMENTO
    else:
        bot.send_message(chat_id,
                        text="Opção inválida. Tente novamente.")
        bot.send_message(chat_id,
                        text="Deseja consultar Pessoa Física ou Jurídica? \n" \
                        "Clique em um botão abaixo ou digite sua escolha.",
                        reply_markup=InlineKeyboardMarkup(opcoes_tipo_pessoa))
        return TIPO_PESSOA



def consultar(bot,update, user_data):
    print('consultar')
    update.message.reply_text('Aguarde um momento. Sua consulta está sendo realizada.')

    user_data['num_documento'] = update.message.text
    session = Session()
    session.auth = HTTPBasicAuth('user', 'password')
    client = Client('https://homologacao.spc.org.br:443/spc6/remoting/ws/consulta/consultaWebService?WSDL', transport=Transport(session=session))
    result = client.service.consultar(13, user_data['tipo_pessoa'], user_data['num_documento'])
    print(result)
    #pprint(vars(result))
    #print(type(result.consumidor))
    #print(dir(result))

    alerta = result['alerta-documento']['resumo']['quantidade-total']
    data = result['alerta-documento']['resumo']['data-ultima-ocorrencia']
    compararDatas(data,'alerta')
    alerta += result['contra-ordem-documento-diferente']['resumo']['quantidade-total']
    data = result['contra-ordem-documento-diferente']['resumo']['data-ultima-ocorrencia']
    compararDatas(data,'alerta')       
    alerta += result['contra-ordem']['resumo']['quantidade-total']
    data = result['contra-ordem']['resumo']['data-ultima-ocorrencia']
    compararDatas(data,'alerta') 
    alerta += result['credito-concedido']['resumo']['quantidade-total']
    data = result['credito-concedido']['resumo']['data-ultima-ocorrencia']
    compararDatas(data,'alerta') 

    inadimplencia = result['spc']['resumo']['quantidade-total']
    data = result['spc']['resumo']['data-ultima-ocorrencia']
    compararDatas(data,'inadimplencia') 
    inadimplencia += result['cheque-lojista']['resumo']['quantidade-total']
    data = result['cheque-lojista']['resumo']['data-ultima-ocorrencia']
    compararDatas(data,'inadimplencia') 
    inadimplencia += result['ccf']['resumo']['quantidade-total']
    data = result['ccf']['resumo']['data-ultima-ocorrencia']
    compararDatas(data,'inadimplencia') 
    #inadimplencia += result['contumacia']['resumo']['quantidade-total']

    if user_data['tipo_pessoa'] == 'F':
        nomeConsumidor =result['consumidor']['consumidor-pessoa-fisica']['nome']
    elif user_data['tipo_pessoa'] == 'J':
        nomeConsumidor =result['consumidor']['consumidor-pessoa-juridica']['nome-comercial']        

    msgConsulta = ''
    if alerta > 0 and inadimplencia > 0:
        msgConsulta += 'Existe(m) {} registro(s) de alertas e {} registro(s) de inadimplência.'.format(inadimplencia, alerta)
    elif alerta > 0:
        msgConsulta += 'Existe(m) {} registro(s) de alertas.'.format(alerta)
    elif inadimplencia > 0:
        msgConsulta += 'Existe(m) {} registro(s) de inadimplência.'.format(inadimplencia)
    msgConsulta += '\nO documento consultado pertence a {}.'.format(nomeConsumidor)

    global dataAlertaMaisRecente
    global dataInadimplenciaMaisRecente
    if dataAlertaMaisRecente is not None:
        msgConsulta +=  '\nO último registro de alerta foi feito em {}'.format(dataAlertaMaisRecente)
    if dataInadimplenciaMaisRecente is not None:
        msgConsulta +=  '\nO último registro de inadimplência foi feito em {}'.format(dataInadimplenciaMaisRecente)

    bot.send_message(update.message.chat_id, text=msgConsulta)
    bot.send_message(update.message.chat_id,
                     text='Para mais informações, acesse o [site](https://servicos.spc.org.br/spc) ' \
                     'ou baixe o aplicativo, via [PlayStore](https://play.google.com/store/apps/details?id=org.spcbrasil.spcmobile) ' \
                     'ou [AppStore](https://itunes.apple.com/br/app/spc-mobile/id794394400?mt=8).',
                     parse_mode=ParseMode.MARKDOWN)   
    bot.send_message(update.message.chat_id, "Deseja algo mais?", reply_markup=InlineKeyboardMarkup(opcoes_menu))
    return INIT



def compararDatas(data, tipo):
    global dataAlertaMaisRecente
    global dataInadimplenciaMaisRecente

    if type(data) is datetime:
        if tipo == 'alerta':
            if dataAlertaMaisRecente is not None:  
                if data > dataAlertaMaisRecente:
                    dataAlertaMaisRecente = data
            else:
                dataAlertaMaisRecente = data
        elif tipo == 'inadimplencia':
            if dataInadimplenciaMaisRecente is not None:  
                if data > dataInadimplenciaMaisRecente:
                    dataInadimplenciaMaisRecente = data
            else:
                dataInadimplenciaMaisRecente = data
        


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)



def errorConversation(bot,update):
    print('error_conversation')
    bot.send_message(update.message.chat_id,
                    text="Erro. Encerrando chat.")
    return ConversationHandler.END



def main():
    #updater = Updater("TOKEN_GENERATED_BY_BOTFATHER", request_kwargs=REQUEST_KWARGS)
    updater = Updater("TOKEN_GENERATED_BY_BOTFATHER")
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            INIT: [CallbackQueryHandler(menuSelect),],

            TIPO_PESSOA: [CallbackQueryHandler(tipoPessoaSelect,
                                        pass_user_data=True),
                          MessageHandler(Filters.text,
                                        tipoPessoaSelect,
                                        pass_user_data=True),
                            ],

            NUM_DOCUMENTO: [MessageHandler(Filters.text,
                                           consultar,
                                           pass_user_data=True),
                           ],
        },

        fallbacks=[MessageHandler(Filters.text, errorConversation)]
        #fallbacks=[RegexHandler('^Done$', error_conversation)]
    )

    #dp.add_handler(CommandHandler("start", start))
    #updater.dispatcher.add_handler(CallbackQueryHandler(inlineButtonSelect))
    #dp.add_handler(CommandHandler("consulta", consultar, pass_args=True))
    print('main')
    dp.add_handler(conv_handler)

    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
