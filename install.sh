#!/bin/bash

# Telegram Complaint Server Installer

DOMAIN="reps.mooo.com"
EMAIL="admin@$DOMAIN"

echo "🔧 Установка сервера..."

# Обновление пакетов
apt update && apt upgrade -y

# Установка системных зависимостей
echo "📦 Установка системных пакетов..."
apt install -y python3 python3-pip python3-venv lsof certbot python3-certbot-nginx

# Создание виртуального окружения
echo "🐍 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
echo "📥 Установка Python пакетов..."
pip install --upgrade pip
pip install -r requirements.txt

# Проверка config.py
if [ ! -f "config.py" ]; then
    echo "❌ config.py не найден! Настройте его перед запуском."
    exit 1
fi

# Убийство процесса на порту 1488
echo "🛑 Остановка процесса на порту 1488..."
PID=$(lsof -t -i:1488 2>/dev/null)
if [ -n "$PID" ]; then
    echo "📍 Найден процесс: PID $PID"
    kill -9 $PID 2>/dev/null
    echo "⏳ Ожидание освобождения порта..."
    sleep 2

    while lsof -i:1488 >/dev/null 2>&1; do
        echo "⏳ Порт ещё занят, ждём..."
        sleep 1
    done
    echo "✅ Порт 1488 свободен"
else
    echo "✅ Порт 1488 свободен"
fi

# Остановка старых процессов сервера
pkill -f "python.*main.py" 2>/dev/null || true

# Получение SSL сертификата
echo "🔒 Получение SSL сертификата Let's Encrypt для $DOMAIN..."

# Проверка DNS
if ! dig +short $DOMAIN | grep -q .; then
    echo "❌ DNS запись для $DOMAIN не найдена!"
    echo "   Настройте A запись на IP этого сервера"
    exit 1
fi

# Остановка nginx если есть (для получения сертификата)
systemctl stop nginx 2>/dev/null || true

# Получение сертификата через standalone
certbot certonly --standalone \
    -d $DOMAIN \
    --email $EMAIL \
    --agree-tos \
    --non-interactive \
    --force-renewal

if [ $? -eq 0 ]; then
    echo "✅ SSL сертификат получен!"
    echo "📄 Сертификат: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "🔑 Ключ: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
else
    echo "❌ Ошибка получения сертификата!"
    echo "   Проверьте что порт 80 открыт и DNS настроен"
    exit 1
fi

# Запуск сервера через nohup
echo "🚀 Запуск сервера на порту 1488..."
nohup python main.py > server.log 2>&1 &

# Проверка запуска
sleep 2
if pgrep -f "python.*main.py" > /dev/null; then
    echo "✅ Сервер запущен!"
    echo "📄 Лог: server.log"
    echo "🌐 HTTPS: https://$DOMAIN"
    echo "🔍 Проверка: curl https://$DOMAIN/health"
else
    echo "❌ Ошибка запуска! Проверьте server.log"
    exit 1
fi
