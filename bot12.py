import requests
import qrcode
import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Configurações do bot e do grupo
BOT_TOKEN = '7842270901:AAEtmzkW6isjnladWZvdxgReTmk7x7ifg5A'  # Token do seu bot do Telegram
GRUPO_INVITE_LINK = 'https://t.me/+WlitJ3rLD49hMTFh'  # Link do grupo privado
VALOR_SERVICO = "1.00"  # Valor do serviço ou acesso
GN_CLIENT_ID = 'SEU_CLIENT_ID_GERENCIANET'  # ID do cliente da API do Gerencianet
GN_CLIENT_SECRET = 'SEU_CLIENT_SECRET_GERENCIANET'  # Segredo do cliente da API do Gerencianet
GN_PIX_WEBHOOK_SECRET = 'SEU_SEGREDO_WEBHOOK'  # Segredo para validar notificações de pagamento

# Endpoint para receber atualizações do bot (Webhooks do Telegram)
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    # Verificar se a mensagem contém o comando
    if 'message' in data and 'text' in data['message']:
        chat_id = data['message']['chat']['id']
        message_text = data['message']['text']
        
        if message_text == "/start":
            enviar_mensagem_start(chat_id)
        
        elif message_text == "/pagar":
            enviar_qr_pix(chat_id)
    
    return JSONResponse(content={'status': 'ok'})


# Função para enviar mensagem de boas-vindas com informações sobre o valor e o pagamento
def enviar_mensagem_start(chat_id):
    mensagem = (
        "Olá! Bem-vindo ao nosso bot.\n\n"
        "Para acessar o nosso grupo privado, é necessário realizar um pagamento via Pix.\n"
        f"💰 **Valor**: R$ {VALOR_SERVICO}\n\n"
        "Para iniciar o pagamento, utilize o comando `/pagar`.\n"
        "Após a confirmação do pagamento, você receberá o link para acessar o grupo exclusivo."
    )
    
    url = f'https://api.telegram.org/bot7842270901:AAEtmzkW6isjnladWZvdxgReTmk7x7ifg5A/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': mensagem,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        print("Mensagem de boas-vindas enviada com sucesso.")
    else:
        print(f"Erro ao enviar mensagem de boas-vindas: {response.text}")


# Função para gerar o QR code Pix e enviar ao usuário
def enviar_qr_pix(chat_id):
    # Gerar QR Code Pix via API do Gerencianet
    qr_code_pix, tx_id = gerar_qr_code_pix()
    
    if qr_code_pix:
        qr_code_path = gerar_qr_code(qr_code_pix)  # Gerar imagem do QR code
        enviar_qr_code(chat_id, qr_code_path)
        
        # Remover o arquivo QR code após o envio
        os.remove(qr_code_path)


# Função para gerar o QR code Pix no Gerencianet
def gerar_qr_code_pix():
    # Autenticar na API do Gerencianet
    auth_response = requests.post(
        'https://api.gerencianet.com.br/v1/authorize',
        auth=(GN_CLIENT_ID, GN_CLIENT_SECRET)
    )
    
    auth_data = auth_response.json()
    access_token = auth_data.get('access_token')

    # Criar cobrança Pix
    payload = {
        "calendario": {"expiracao": 3600},
        "valor": {"original": VALOR_SERVICO},  # Define o valor aqui
        "chave": "019.697.696-02",  # Chave Pix cadastrada no Gerencianet
        "infoAdicionais": [{"nome": "Produto", "valor": "Acesso ao grupo"}]
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    cobranca_response = requests.post(
        'https://api.gerencianet.com.br/v2/cob',
        headers=headers,
        data=json.dumps(payload)
    )
    cobranca_data = cobranca_response.json()
    
    # Obter QR code e txid
    qr_code_pix = cobranca_data.get('loc', {}).get('location')
    tx_id = cobranca_data.get('txid')
    return qr_code_pix, tx_id


# Função para gerar imagem do QR code
def gerar_qr_code(link):
    qr = qrcode.make(link)
    qr_code_path = 'qr_code_pix.png'
    qr.save(qr_code_path)
    return qr_code_path


# Função para enviar o QR code ao usuário no Telegram
def enviar_qr_code(chat_id, qr_code_path):
    url = f'https://api.telegram.org/bot7842270901:AAEtmzkW6isjnladWZvdxgReTmk7x7ifg5A/sendPhoto'
    
    with open(qr_code_path, 'rb') as photo:
        data = {
            'chat_id': chat_id,
            'caption': 'Use o QR code abaixo para efetuar o pagamento via Pix.'
        }
        files = {
            'photo': photo
        }
        
        response = requests.post(url, data=data, files=files)
    
    if response.status_code == 200:
        print('QR code enviado com sucesso')
    else:
        print(f'Erro ao enviar o QR code: {response.text}')


# Endpoint para receber notificações de pagamento Pix
@app.post("/webhook_pagamento")
async def webhook_pagamento(request: Request):
    data = await request.json()

    # Validar o segredo do webhook
    if data.get('secret') != GN_PIX_WEBHOOK_SECRET:
        return JSONResponse(content={'status': 'unauthorized'}, status_code=403)
    
    # Verificar se o pagamento foi concluído
    if data.get('status') == 'CONFIRMADO':  # Verifique o status correto com a documentação
        usuario_id = data.get('usuario_id')  # Capturar o ID do usuário que pagou
        enviar_link_grupo(usuario_id)  # Enviar o link do grupo ao usuário
    
    return JSONResponse(content={'status': 'success'})


# Função para enviar o link do grupo privado
def enviar_link_grupo(usuario_id):
    url = f'https://api.telegram.org/bot7842270901:AAEtmzkW6isjnladWZvdxgReTmk7x7ifg5A/sendMessage'
    mensagem = f'Aqui está o link para o grupo privado: {GRUPO_INVITE_LINK}'
    data = {
        'chat_id': usuario_id,
        'text': mensagem
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print('Link do grupo enviado com sucesso')
    else:
        print(f'Erro ao enviar o link do grupo: {response.text}')


# Rodar o servidor com o Uvicorn
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
