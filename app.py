from flask import Flask,request
import requests
import yaml
import re
import mysql.connector
import threading 
import time, traceback
from flask_sslify import SSLify


TOKEN = '1840069135:AAFoi6wVoLtl2eSmZUWQGi_qEMG_ScmjICs'
URL= 'https://api.telegram.org/bot1840069135:AAFoi6wVoLtl2eSmZUWQGi_qEMG_ScmjICs/'
app = Flask(__name__)

sslify = SSLify(app)

db=yaml.load(open('db.yml'))

mydb = mysql.connector.connect(
  host=db['mysql_host'],
  user=db['mysql_user'],
  password=db['mysql_password'],
  database=db['mysql_db']
)

#проинициализируем курсор 
cursor=mydb.cursor()
#при каждом запуске бота сохраняем id последней проблемы
cursor.execute('SELECT * FROM problems ORDER BY id DESC LIMIT 1')		
last_problem_id=re.search("\d",str(cursor.fetchone()))[0]	

def send_message(chat_id, text):
    method = "sendMessage"
    token = TOKEN
    url = f"https://api.telegram.org/bot{token}/{method}"

    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data)


def checkUser(user_id,cur):
    cur.execute("SELECT status FROM users WHERE user_id = %s" % user_id)
    try:
        status = re.search("\d",str(cur.fetchone()))[0]
        if status == "1":
            return 1
        elif status == "0":
            return 0
    except:
        return -1
    

@app.route("/", methods=["GET", "POST"])
def update():
    if request.method == "POST":
         #print(request.json)
         chat_id = request.json["message"]["chat"]["id"]
         command = request.json["message"]["text"]
         cur = cursor
        #Команда подписки 
         if command == "/subscribe":
            if checkUser(chat_id,cur) == -1:
                cur.execute("INSERT INTO users(user_id, status) VALUES(%s,%s)", (chat_id,1))
                send_message(chat_id,'Вы успешно подписались')

            elif checkUser(chat_id,cur) == 0:
                cur.execute("UPDATE users SET status = '1' WHERE user_id = %s" % chat_id)
                send_message(chat_id,'С возвращением!')
            elif checkUser(chat_id,cur) == 1:
                send_message(chat_id,'Вы уже подписаны на уведомления')

        #Команда отписки 
         elif command == "/unsubscribe":
            if checkUser(chat_id,cur) == -1 or checkUser(chat_id,cur) == 0:
                send_message(chat_id,'Вы итак не подписаны')
            elif checkUser(chat_id,cur) == 1:
                cur.execute("UPDATE users SET status = '0' WHERE user_id = %s" % chat_id)    
                send_message(chat_id,'Вы успешно отписались от уведомлений')

        #Сохраняем изменения в базе
         mydb.commit()
    return {"browser?": True}





#Проверяем таблицу на наличие свежих проблем  

def checkNotify():
     cursor.execute('SELECT * FROM problems ORDER BY id DESC LIMIT 1')
     problem = cursor.fetchone()
     problem_id = re.search("\d",str(problem))[0]
     global last_problem_id
     #print(problem)
     #print(last_problem_id)
     mydb.commit()
     
     if problem_id != last_problem_id:
        last_problem_id=problem_id
        problem_desc = problem
        cursor.execute('SELECT user_id FROM users WHERE status = 1')
        Users = cursor.fetchall()
        message = ' Работник: %s\nПроблема: %s' % (problem_desc[1],problem_desc[2])
        for user in Users:
           send_message(user, message)

#Скрипт для выделенного потока 
def every(delay, task):
  next_time = time.time() + delay
  while True:
    time.sleep(max(0, next_time - time.time()))
    try:
      task()
    except Exception:
      traceback.print_exc()
      # in production code you might want to have this instead of course:
      # logger.exception("Problem while executing repetitive task.")
    # skip tasks if we are behind schedule:
    next_time += (time.time() - next_time) // delay * delay + delay


threading.Thread(target=lambda: every(180, checkNotify)).start()
#threading.Thread(target=lambda: app.run()).start()

if __name__ == '__main__':
    app.run()
   