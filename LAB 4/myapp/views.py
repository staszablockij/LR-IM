import json
import requests
from myapp.credentials import TELEGRAM_API_URL, URL
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

def setwebhook(request):
  response = requests.post(TELEGRAM_API_URL+ "setWebhook?url=" + URL).json()
  return HttpResponse(f"{response}")

@csrf_exempt
def telegram_bot(request):
  if request.method == 'POST':
    update = json.loads(request.body.decode('utf-8'))
    handle_update(update)
    return HttpResponse('ok')
  else:
    return HttpResponseBadRequest('Bad Request')

def handle_update(update):
  chat_id = update['message']['chat']['id']
  text = update['message']['text']
  send_message("sendMessage", {
    'chat_id': chat_id,
    'text': f'you said {text}'
  })

def send_message(method, data):
  return requests.post(TELEGRAM_API_URL + method, data)
