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
    if(debug=="true"):
        send_message("estoy configurando cosas, no me usen",chat_id)
        return {
        'statusCode': 200
    }
    chatId = update['message']['chat']['id']
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