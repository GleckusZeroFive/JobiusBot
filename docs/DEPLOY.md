# Деплой бота на VPS

Инструкция по развёртыванию JobiusBot на вашем VPS сервере.

## Быстрый деплой

### 1. Подключитесь к серверу

```bash
ssh user@your-server-ip
# Например: ssh root@178.173.250.115
```

### 2. Установите зависимости (если нужно)

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Python 3 и pip
sudo apt install -y python3 python3-pip python3-venv git

# Проверьте версию (нужен Python 3.9+)
python3 --version
```

### 3. Скопируйте проект на сервер

#### Вариант А: Через git (рекомендуется)

```bash
cd ~
git clone <URL_вашего_репозитория> JobiusBot
cd JobiusBot
```

#### Вариант Б: Через scp с локальной машины

```bash
# На вашем компьютере:
cd /home/gleckus/projects
scp -r JobiusBot user@your-server-ip:~/
```

### 4. Настройте .env файл

```bash
cd ~/JobiusBot
cp .env.example .env
nano .env
```

Вставьте ваши токены:
```
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
GROQ_API_KEY=ваш_ключ_от_groq
```

Сохраните: `Ctrl+X`, затем `Y`, затем `Enter`

### 5. Запустите бота

```bash
./start.sh
```

Готово! Бот запущен.

## Автозапуск при перезагрузке сервера

Создайте systemd service для автоматического запуска бота.

### 1. Создайте service файл

```bash
sudo nano /etc/systemd/system/jobiusbot.service
```

### 2. Вставьте следующее содержимое:

```ini
[Unit]
Description=JobiusBot - Telegram Job Search Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/JobiusBot
Environment="PATH=/home/YOUR_USERNAME/JobiusBot/venv/bin"
ExecStart=/home/YOUR_USERNAME/JobiusBot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**ВАЖНО:** Замените `YOUR_USERNAME` на ваше имя пользователя!

### 3. Активируйте service

```bash
# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите автозапуск
sudo systemctl enable jobiusbot

# Запустите сервис
sudo systemctl start jobiusbot

# Проверьте статус
sudo systemctl status jobiusbot
```

### 4. Полезные команды systemd

```bash
sudo systemctl start jobiusbot      # Запустить
sudo systemctl stop jobiusbot       # Остановить
sudo systemctl restart jobiusbot    # Перезапустить
sudo systemctl status jobiusbot     # Проверить статус
sudo journalctl -u jobiusbot -f     # Смотреть логи в реальном времени
sudo journalctl -u jobiusbot -n 100 # Последние 100 строк логов
```

## Обновление бота на сервере

### Если используете git:

```bash
cd ~/JobiusBot
./stop.sh                    # Остановить бота
git pull                     # Получить обновления
./start.sh                   # Запустить снова
```

### Если используете systemd:

```bash
cd ~/JobiusBot
sudo systemctl stop jobiusbot
git pull
sudo systemctl start jobiusbot
```

### Если обновились зависимости:

```bash
cd ~/JobiusBot
./stop.sh
source venv/bin/activate
pip install -r requirements.txt --upgrade
./start.sh
```

## Мониторинг

### Проверить статус бота:

```bash
./status.sh
```

### Посмотреть логи:

```bash
./logs.sh           # Последние 50 строк
./logs.sh 100       # Последние 100 строк
./logs.sh -f        # В реальном времени
./logs.sh -e        # Только ошибки
```

### Использование ресурсов:

```bash
# CPU и память
htop

# Место на диске
df -h

# Сетевые подключения
ss -tulpn | grep python
```

## Решение проблем

### Бот не запускается:

1. Проверьте логи: `./logs.sh -e`
2. Проверьте .env файл: `cat .env`
3. Проверьте права: `ls -la bot.py`
4. Проверьте Python: `python3 --version`

### Бот запущен, но не отвечает:

1. Проверьте токен в .env
2. Проверьте интернет-соединение: `ping -c 3 api.telegram.org`
3. Посмотрите логи: `./logs.sh -f`

### Несколько процессов бота:

```bash
./stop.sh    # Остановит все
./start.sh   # Запустит один
```

### Бот упал:

Если используете systemd с `Restart=always`, он автоматически перезапустится.

Если нет:
```bash
./restart.sh
```

## Безопасность

### 1. Создайте отдельного пользователя:

```bash
sudo adduser botuser
sudo su - botuser
```

### 2. Настройте firewall:

```bash
# Разрешите только SSH
sudo ufw allow ssh
sudo ufw enable
```

### 3. Не коммитьте .env в git:

Файл уже в .gitignore, но проверьте:
```bash
git status
# .env НЕ должен быть в списке изменений
```

### 4. Регулярно обновляйте систему:

```bash
sudo apt update && sudo apt upgrade -y
```

## Бэкап

### Создать бэкап:

```bash
cd ~
tar -czf jobiusbot-backup-$(date +%Y%m%d).tar.gz JobiusBot/
```

### Восстановить из бэкапа:

```bash
tar -xzf jobiusbot-backup-YYYYMMDD.tar.gz
cd JobiusBot
./start.sh
```
