import boto3
import json
import decimal
import time
import os
import random

from botocore.vendored import requests

headers = {'Content-Type': 'application/json'}
zapato = "👞"
sushi = "🍣"
keyboard = {"inline_keyboard": [[{"text": "Very bad", "callback_data": "0"}], [{"text": "Not that good", "callback_data": "1"}], [{"text": "It's ok", "callback_data": "2"}], [{"text": "So nice!", "callback_data": "3"}]]}
chatIdParaiso = os.environ['CHAT_PARAISO']
chatIdAdmin = os.environ['CHAT_ADMIN']
chatIdParaisoTest = os.environ['CHAT_PARAISO_TEST']
botToken = os.environ['BOT_TOKEN']
URL = "https://api.telegram.org/bot{}/".format(botToken)
qr_token = os.environ['QR_TOKEN']
precios_token = os.environ['PRECIOS_TOKEN']
table_name = os.environ['TABLE_NAME']
debug = os.environ['debug']

def lambda_handler(event, context):
    print(event)
    if 'checkoneminute' in event:
        checkOneMinute()
        return
    data = json.loads(event["body"])
    if 'message' in data:
        response = handleMessage(data)
        #response = "Algo salio mal, chequea la lista de comandos"
    elif 'callback_query' in data:
        response = handleCallbackQuery(data)
    else:
        response = {
            'statusCode': '200',
            'headers': headers
        }
    return response

def handleMessage(update):
    chatId = update['message']['chat']['id']
    print("chatId:" + str(chatId))
    if(debug=="true"):
        response = {
                'statusCode': '200',
                'headers': headers
                }
        return response
    if(str(chatId) != chatIdParaiso and str(chatId) != chatIdAdmin and str(chatId) != chatIdParaisoTest):
        response = {
                'statusCode': '200',
                'headers': headers
                }
        return response
    
    
    if 'text' in update['message']:
        sender = update['message']['from']
        text = update['message']['text']
        commands = text.split(" ")
        command = commands[0]
        command = command.split("@", 1)[0]
        print(text)
        status = estaPrendido()
        if status['prendido']=='false':
            if ('/prender' == command):
                switch('true')
                response = sendMessage(chatId,"Se prendio el morfi bot lambda")
            else:
                response = {
                'statusCode': '200',
                'headers': headers
                }
            return response
        if ('/abrir' == command):
            time =  text.split(" ",1)
            if len(time) < 2:
                message = "Tenes que especificar en cuantos minutos cerrar el pedido"
            else:
                message = abrirPedido(time[1])
            response = sendMessage(chatId,message)
        elif ('/cerrar' == command):
            message = cerrarPedido()
            response = sendMessage(chatId,message)
        elif ('/pedir' == command):
            pedido =  text.split(" ",1)
            if len(pedido) < 2:
                message = "Tenes que especificar que comida queres pedir"
            else:
                message = pedir(pedido[1],sender)
            response = sendMessage(chatId,message)
        elif ('/pedido' == command):
            message = mostrarPedido()
            response = sendMessage(chatId,message)
        elif ('/menu' == command):
            message = mostrarMenu()
            response = sendMessage(chatId,message)
        elif command == "/qr":
            response = sendPhoto(chatId,qr_token)
        elif command == "/precios":
            response = sendPhoto(chatId,precios_token)
        elif command == "/telefono":
            message = "El telefono es 4791-2900"
            response = sendMessage(chatId,message)
        elif command == "/mail":
            message = "El mail es paraisonaturalpedidos@gmail.com"
            response = sendMessage(chatId,message)    
        elif ('/apagar' == command):
            switch('false')
            response = sendMessage(chatId,"Se apago el morfi bot lambda")
        elif ('/mandarmail' == command):
            mandarMail()
            response = sendMessage(chatId,"Se mando el mail")
        elif command == "/prendido":
            prendido = estaPrendido()
            message = "Bot online = " + prendido['prendido'];
            response = sendMessage(chatId,message)    
        else:
            response = sendMessage(chatId,"de que estas hablando willys?")
        
    return response

def mandarMail():
    print("se esta mandando el mail")
    ses = boto3.client('ses')
    email_from = 'toti359@gmail.com'
    email_to = 'maxifwortman@gmail.com'
    email_cc = 'Email'
    emaiL_subject = 'Subject'
    email_body = 'Body'
    response = ses.send_email(
        Source = email_from,
        Destination={
            'ToAddresses': [
                email_to,
            ],
            'CcAddresses': [
                email_cc,
            ]
        },
        Message={
            'Subject': {
                'Data': emaiL_subject
            },
            'Body': {
                'Text': {
                    'Data': email_body
                }
            }
        }
    )
    print("se mando el mail")
    print(response)
    return

def sendMessageAsync(text, chat_id):
    url = URL + "sendMessage?text={}&chat_id={}".format(text, chat_id)
    requests.get(url)

def checkOneMinute():
    status = estaPrendido()
    if status['prendido']=='false':
        print("no prendido check one minute")
        return
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "true" :
        if float(pedidoActual['closeTime']) < time.time():
            pedidoCerrado = cerrarPedido()
            sendMessageAsync(pedidoCerrado,chatIdParaiso)
            return
        if float(pedidoActual['closeTime']) >= (time.time() + 10*60) and float(pedidoActual['closeTime']) <= (time.time() + 11*60):
            sendMessageAsync("el pedido cierra en 10 minutos" ,chatIdParaiso)
            return


def abrirPedido(timeMinutes):
    try:
        floatMinutes = float(timeMinutes) * 60
    except:
        return "El tiempo para cerrar el pedido debe ser un numero entero"
    if floatMinutes <= 0:
        return "El tiempo debe ser un numero positivo mayor que 0"
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "true" :
        return "Ya hay un pedido abierto"
    pedidoActual['open'] = 'true'
    pedidoActual['openTime'] = time.time()
    
        
    pedidoActual['closeTime'] = (time.time() + floatMinutes)
    pedidoActual['pedidos'] = []
    pedido['pedidoActual'] = json.dumps(pedidoActual)
    saveToDynamo(pedido)
    return "El pedido cierra en " + timeMinutes +" minutos"

def cerrarPedido():
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "false" :
        return "No hay un pedido abierto"
    pedidoActual['open'] = 'false'
    pedido['pedidoActual'] = json.dumps(pedidoActual)
    pedidoCerrado = "El pedido se cerro. \n" + pedidoToString(pedidoActual) 
    if len(pedidoActual['pedidos'])>0: 
        users = []
        for comida in pedidoActual['pedidos']:
            users.append(comida['username'])
        llama = random.choice(users)
        users.remove(llama)
        if(len(users)==0):
            busca = llama
        else:
            busca = ""
            userLen = len(users)
            for i in range(0,int((userLen-1)/4)+1):
                if i > 0:
                    busca = busca + ","
                user = random.choice(users)
                users.remove(user)
                busca = busca + user
        pedidoCerrado = pedidoCerrado + "Encargado de llamar o mandar el mail: " + llama + " \n" + "Va/n a buscar: " + busca
    saveToDynamo(pedido)
    return pedidoCerrado 

def pedir(comida, sender):
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "false" :
        return "No hay un pedido abierto"
    username = getUserName(sender)
    nuevoPedido = {"username":username,"pedido":comida}
    if 'pedidos' in pedidoActual:
        find = "false"
        for n, comidaPedida in enumerate(pedidoActual['pedidos']):
            if comidaPedida['username'] == username:
                pedidoActual['pedidos'][n] = nuevoPedido
                find = "true"
        if find =="false":
            pedidoActual['pedidos'].append(nuevoPedido)
    else:
        pedidos = [nuevoPedido]
        pedidoActual['pedidos'] = pedidos
    pedido['pedidoActual'] = json.dumps(pedidoActual)
    saveToDynamo(pedido)
    return "Registrado!"
    
def mostrarPedido():
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "false" :
        return "No hay un pedido abierto"
    return pedidoToString(pedidoActual)
    
def pedidoToString(pedido):
    str = "Pedidos: \n"
    if not pedido['pedidos']:
        str = "El pedido esta vacio"
    else:
        for pedidoObj in pedido['pedidos']:
            print(pedidoObj)
            str = str + pedidoObj['username'] + " - " + pedidoObj['pedido'] + "\n"
    return str
    

def saveToDynamo(pedido):
    dynamo = boto3.client('dynamodb')
    item = {
            'id': {'S': '1'},
            'pedidoActual': {'S': pedido['pedidoActual']}
    }
    dynamo.put_item(TableName=table_name, Item=item)

def switch(prendido):
    dynamo = boto3.client('dynamodb')
    item = {
            'id': {'S': '2'},
            'prendido': {'S': prendido}
    }
    dynamo.put_item(TableName=table_name, Item=item)


def sendMessage(chatId, text, replyId=0, replyMode=False):
    print('chatID = ' + str(chatId) + ', text = ' + text)
    if replyMode:
        response = {
            'statusCode': '200',
            'body': json.dumps(
                {'method': 'sendMessage', 'chat_id': chatId, 'text': text, 'reply_to_message_id': replyId}),
            'headers': headers
        }
    else:
        response = {
            'statusCode': '200',
            'body': json.dumps({'method': 'sendMessage', 'chat_id': chatId, 'text': text}),
            'headers': headers
        }
    return response

def findPedido():
    dynamo = boto3.client('dynamodb')
    response = dynamo.get_item(TableName=table_name, Key={"id": {"S": "1"}})
    pedido = response['Item']
    print(pedido)
    return {
        'pedidoActual': pedido['pedidoActual']['S']
    }


def estaPrendido():
    dynamo = boto3.client('dynamodb')
    response = dynamo.get_item(TableName=table_name, Key={"id": {"S": "2"}})
    prendido = response['Item']
    print(prendido)
    return {
        'prendido': prendido['prendido']['S'],   
    }



def getUserName(sender):
    name = "anonimo"
    if 'username' in sender:
        name = sender['username']
    elif 'first_name' in sender:
        name = sender['first_name']
    elif 'id' in sender:
        name = sender['id']
    print(name)
    return name

def mostrarMenu():
    menustr = ""
    menu = menuJson['menu']
    for categoria in menu:
        menustr = menustr + categoria['nombre'] + "\n"
        for plato in categoria['platos']:
            menustr = menustr + " - " + plato + "\n"
        if 'pastas' in categoria:
            for pasta in categoria['pastas']:
                menustr = menustr + " - " + pasta + "\n"
    return menustr

def sendPhoto(chatId, photo, replyId=0, replyMode=False):
    print('chatID = ' + str(chatId) + ', photo = ' + photo)
    if replyMode:
        response = {
            'statusCode': '200',
            'body': json.dumps(
                {'method': 'sendPhoto', 'chat_id': chatId, 'photo': photo, 'reply_to_message_id': replyId}),
            'headers': headers
        }
    else:
        response = {
            'statusCode': '200',
            'body': json.dumps({'method': 'sendPhoto', 'chat_id': chatId, 'photo': photo}),
            'headers': headers
        }
    return response



menuJson = {  
   "menu":[  
      {  
         'nombre':'Pastas',
         'platos':[  
            'Ñoquis',
            'Ravioles',
            'Tallarines',
            'Canelones'
         ],
         'salsas':[  
            'Fileto',
            'Bolognesa',
            'Blanca',
            'Crema',
            'Mixta',
            'Popeye'
         ]
      },
      {  
         'nombre':'Ensaladas',
         'platos':[  
            'Costa Brava (Tomate, Rúcula, Atún, Aceitunas, Huevo)',
            'Nicoise (Arroz, Tomate, Atún, Aceitunas, Huevo)',
            'Babilonia (Tomate, Rúcula, Blanco de Ave, Mozzarella)',
            'Multicolor (Tomate, Papa, Chaucha, Zanahoria, Remolacha, Huevo)',
            'Delicia (Tomate, Zanahoria, Choclo, Mozzarella, Albahaca)',
            'Capresse (Tomate, Mozzarella, Albahaca, Oliva, Pimienta en grano)',
            'A elección (Lechuga, Rúcula, Papa, Chaucha, Remolacha, Apio, Manzana, Zanahoria, Huevo, Tomate, Radicheta, Arveja)'
         ]
      },
      {  
         'nombre':'Frescos',
         'platos':[  
            'Salpicón de ave',
            'Arrollado de ave con ensalada rusa',
            'Matambre de ternera con ensalada rusa'
         ]
      },
      {  
         'nombre':'Pescados',
         'platos':[  
            'Brótola grillé con salsa tártara y vegetales',
            'Corvina al horno con papas panaderas',
            'Filet de merluza grillé o a la romana con guarnición'
         ]
      },
      {  
         'nombre':'Artesanales',
         'platos':[  
            'Milhojas de berenjena (Berenjenas, Queso, Zuchini, Tomate)',
            'Mozzarella in carroza (Tomate, Albahaca)',
            'Milanesa de pollo fiorentina (Verdura a la crema, Queso port salut)',
            '1/4 de pollo a la crema de queso con papas fritas',
            'Soufle vegetariano con crema de choclo y zanahoria',
            '1/2 bife de chorizon con guarnición',
            'Milanesa de pollo con guarnición',
            'Milanesa de ternera con guarnición',
            '1/4 de pollo grillé con guarnición',
            'Costillita de cerdo grillé con guarnición',
            'Bondiola de cerdo a la portuguesa con papas naturales o fritas'
         ]
      }
   ]
}