# Server

## Установка и запуск

```bash
chmod +x install.sh
./install.sh
```

Скрипт установит зависимости и запустит сервер через `nohup` на порту 1488.

## Настройка

Отредактируй `config.py` перед запуском.

## Управление

```bash
# Остановить
pkill -f "python.*main.py"

# Лог
tail -f server.log

# Проверка
curl http://localhost:1488/health
```
