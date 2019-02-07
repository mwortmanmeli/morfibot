import boto3
import json
import decimal
import time

from botocore.vendored import requests

debug = "false"
headers = {'Content-Type': 'application/json'}
zapato = "👞"
sushi = "🍣"
keyboard = {"inline_keyboard": [[{"text": "Very bad", "callback_data": "0"}], [{"text": "Not that good", "callback_data": "1"}], [{"text": "It's ok", "callback_data": "2"}], [{"text": "So nice!", "callback_data": "3"}]]}

def lambda_handler(event, context):
    print(event)
    print(context)
    # get http request from Telegram Server
    if 'checkoneminute' in event:
        checkOneMinute()
        return
    data = json.loads(event["body"])
    
    # response treating, add many update types as you want to handle. Here i handle only "message" and "callback_query"
    if 'message' in data:
        try:
            response = handleMessage(data)
        except:
            response = "Algo salio mal, chequea la lista de comandos"
    elif 'callback_query' in data:
        response = handleCallbackQuery(data)
    else:
        # Default response if we don't have anything to say.
        # 'statusCode': '200' means that we read the UPDATE, so Telegram wont
        # send it again. MUST HAVE
        response = {
            'statusCode': '200',
            'headers': headers
        }
    return response

def handleMessage(update):
    chatId = update['message']['chat']['id']
    if(debug=="true"):
        send_message("estoy configurando cosas, no me usen",chatId)
        return {
        'statusCode': 200
    }
    try:
        if 'text' in update['message']:
            sender = update['message']['from']
            text = update['message']['text']
            commands = text.split(" ")
            command = commands[0]
            command = command.split("@", 1)[0]
            print(command)
            #################### ADD YOUR CODE HERE!!!!!!!!!!!
            ###
            if ('/abrir' == command):
                time =  text.split(" ",1)[1]
                message = abrirPedido(time)
                response = sendMessage(chatId,message)
            elif ('/cerrar' == command):
                message = cerrarPedido()
                response = sendMessage(chatId,message)
            elif ('/pedir' == command):
                pedido =  text.split(" ",1)[1]
                message = pedir(pedido,sender)
                response = sendMessage(chatId,message)
            elif ('/pedido' == command):
                message = mostrarPedido()
                response = sendMessage(chatId,message)
            elif ('/menu' == command):
                message = mostrarMenu()
                response = sendMessage(chatId,message)
            elif command == "/qr":
                response = sendPhoto(chatId, "AgADAQAD-KcxG-3o4UY1xkPZuihZlyS8CjAABKRkOOQ2LGB4YuICAAEC")
            elif command == "/telefono":
                message = "El telefono es 4791-2900"
            else:
                response = sendMessage(chatId,"de que estas hablando willys?")
    except:
        message = "Algo salio mal, chequea la lista de comandos"
        response = sendMessage(chatId,message)
    return response

def checkOneMinute():
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "true" :
        if float(pedidoActual['closeTime']) < time.time():
            cerrarPedido()
            print("se cerro el pedido")


def abrirPedido(timeMinutes):
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "true" :
        return "Ya hay un pedido abierto"
    pedidoActual['open'] = 'true'
    pedidoActual['openTime'] = time.time()
    pedidoActual['closeTime'] = (time.time() + float(timeMinutes) * 60)
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
    saveToDynamo(pedido)
    return "El pedido se cerro. \n" + pedidoToString(pedidoActual)

def pedir(comida, sender):
    pedido = findPedido();
    pedidoActual = json.loads(pedido['pedidoActual'])
    if pedidoActual['open'] == "false" :
        return "No hay un pedido abierto"
    username = getUserName(sender)
    nuevoPedido = {"username":username,"pedido":comida}
    if 'pedidos' in pedidoActual:
        list = pedidoActual['pedidos'].append(nuevoPedido)
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
            'pedidoActual': {'S': pedido['pedidoActual']},
            'pedidos': {'S': pedido['pedidos']}
    }
    dynamo.put_item(TableName="Lambda", Item=item)


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
    response = dynamo.get_item(TableName='Lambda', Key={"id": {"S": "1"}})
    pedido = response['Item']
    print(pedido)
    return {
        'pedidoActual': pedido['pedidoActual']['S'],
        'pedidos': pedido['pedidos']['S']
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