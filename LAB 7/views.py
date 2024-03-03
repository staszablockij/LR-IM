import json
import requests
import pymysql
import qrcode
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from myapp.credentials import TELEGRAM_API_URL, URL, HOSTDB, DBNAME, PORTDB, USERDB, PASSDB, TIMEOUT

timeout = TIMEOUT

# Встановлення з'єднання з базою даних
connection = pymysql.connect(
    charset="utf8mb4",
    connect_timeout=timeout,
    cursorclass=pymysql.cursors.DictCursor,
    db=DBNAME,
    host=HOSTDB,
    password=PASSDB,
    read_timeout=timeout,
    port=PORTDB,
    user=USERDB,
    write_timeout=timeout,
)

@csrf_exempt
def setwebhook(request):
    response = requests.post(TELEGRAM_API_URL + "setWebhook?url=" + URL).json()
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
    try:
        chat_id = update['message']['chat']['id']
        telegram_id = update['message']['from']['id']
        text = update['message'].get('text', '')

        if text == '/register':
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': 'Please send your contact:',
                'reply_markup': {
                    'keyboard': [
                        [
                            {
                                'text': 'My phone',
                                'request_contact': True
                            }
                        ]
                    ],
                    'resize_keyboard': True,
                    'one_time_keyboard': True,
                }
            })
        elif text == '/delete':
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': 'Are you sure you want to delete your data?',
                'reply_markup': {
                    'keyboard': [
                        [
                            {
                                'text': 'Yes'
                            },
                            {
                                'text': 'No'
                            }
                        ]
                    ],
                    'resize_keyboard': True,
                    'one_time_keyboard': True,
                }
            })
        elif text == 'Yes':
            success = delete_user_data(telegram_id)
            if success:
                send_message("sendMessage", {
                    'chat_id': chat_id,
                    'text': 'Your data has been successfully deleted.',
                    'reply_markup': {
                        'remove_keyboard': True,
                    }
                })
            else:
                send_message("sendMessage", {
                    'chat_id': chat_id,
                    'text': 'Failed to delete your data. Please try again later.',
                    'reply_markup': {
                        'remove_keyboard': True,
                    }
                })
        elif text == 'No':
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': 'Thank you for staying with us!',
                'reply_markup': {
                    'remove_keyboard': True,
                }
            })
        elif text == '/getmyid':
            send_user_qr(chat_id, telegram_id)
        elif 'contact' in update['message']:
            contact = update['message']['contact']
            phone_number = contact.get('phone_number', 'Номер телефону відсутній')
            name = contact.get('first_name', 'Ім\'я відсутнє')
            last_name = contact.get('last_name', 'Прізвище відсутнє')

            # Перевірка наявності користувача за номером телефону в базі даних
            user_id = check_user_existence(phone_number)

            if user_id:
                user_info = f'Користувач з номером телефону {phone_number} вже існує.\nID користувача: {user_id}'
            else:
                user_id = save_user_data(telegram_id, phone_number, name, last_name)
                user_info = f'Ви успішно зареєструвалися.\nID користувача: {user_id}\nТелефон: {phone_number}\nІм\'я: {name}\nПрізвище: {last_name}' 
                send_user_qr(chat_id, telegram_id)
                
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': user_info,
                'reply_markup': {
                    'remove_keyboard': True,
                }
            })

        else:
            send_message("sendMessage", {
                'chat_id': chat_id,
                'text': f'Ти сказав: {text}'
            })

    except Exception as e:
        send_message("sendMessage", {
            'chat_id': chat_id,
            'text': 'Щось пішло не так. Спробуйте ще раз.'
        })

def send_message(method, data):
    return requests.post(TELEGRAM_API_URL + method, json=data)

def check_user_existence(phone_number):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id FROM customers WHERE phone_number = %s"
            cursor.execute(sql, (phone_number,))
            result = cursor.fetchone()
            if result:
                return result['id']
            else:
                return None
    except Exception as e:
        print(f"Помилка при перевірці наявності користувача: {str(e)}")
        return None

def save_user_data(telegram_id, phone_number, name, last_name):
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO customers (telegram_id, phone_number, name, last_name) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (telegram_id, phone_number, name, last_name))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Помилка при збереженні даних користувача: {str(e)}")
        connection.rollback()
        return None

def delete_user_data(telegram_id):
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM customers WHERE telegram_id = %s"
            cursor.execute(sql, (telegram_id,))
            connection.commit()
            return True
    except Exception as e:
        print(f"Помилка при видаленні даних користувача: {str(e)}")
        connection.rollback()
        return False

def send_user_qr(chat_id, telegram_id):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id FROM customers WHERE telegram_id = %s"
            cursor.execute(sql, (telegram_id,))
            result = cursor.fetchone()
            if result:
                user_id = result['id']
                qr_data = f"User ID: {user_id}"
                qr_filename = f"user_{user_id}_qr.png"
                generate_qr_code(qr_data, qr_filename)
                send_document(chat_id, qr_filename)
            else:
                send_message("sendMessage", {
                    'chat_id': chat_id,
                    'text': 'Користувач не зареєстрований. Будь ласка, зареєструйтеся за допомогою команди /register.'
                })
    except Exception as e:
        print(f"Помилка при відправленні QR-коду користувачу: {str(e)}")

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

def send_document(chat_id, filename):
    url = f"{TELEGRAM_API_URL}sendDocument"
    files = {'document': open(filename, 'rb')}
    data = {'chat_id': chat_id}
    response = requests.post(url, files=files, data=data)
    if response.status_code == 200:
        print("Document sent successfully")
    else:
        print("Failed to send document")
