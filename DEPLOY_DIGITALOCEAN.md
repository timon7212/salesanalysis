# 🚀 Деплой на Digital Ocean

## Шаг 1: Создание Droplet

1. Зайди на https://cloud.digitalocean.com/
2. Нажми **Create** → **Droplets**
3. Выбери конфигурацию:
   - **Image**: Ubuntu 24.04 LTS
   - **Size**: 
     - Минимум: **Basic** → **$12/mo** (2GB RAM, 1 CPU)
     - Рекомендуется: **Basic** → **$24/mo** (4GB RAM, 2 CPU) - для стабильной работы
   - **Datacenter**: Выбери ближайший регион (например, Frankfurt для России)
   - **Authentication**: SSH Key (добавь свой публичный ключ) ИЛИ Password
   - **Hostname**: `kommo-call-analyzer`

4. Нажми **Create Droplet**

---

## Шаг 2: Подключение к серверу

После создания скопируй IP-адрес и подключись:

```bash
ssh root@YOUR_DROPLET_IP
```

---

## Шаг 3: Установка Docker и Docker Compose

Выполни команды на сервере:

```bash
# Обновление пакетов
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose (уже включен в Docker)
docker compose version

# Установка git
apt install git -y
```

---

## Шаг 4: Клонирование проекта

```bash
cd /opt
git clone https://github.com/timon7212/salesanalysis.git
cd salesanalysis
```

---

## Шаг 5: Настройка переменных окружения

Создай `.env` файл:

```bash
nano .env
```

Вставь следующее (замени значения на свои):

```bash
# Admin
ADMIN_API_KEY=your-super-secret-admin-key-change-me

# Encryption
APP_ENCRYPTION_KEY=your-32-character-encryption-key!!!

# Database
DATABASE_URL=postgresql://kommo_user:kommo_password@postgres:5432/kommo_db
POSTGRES_USER=kommo_user
POSTGRES_PASSWORD=kommo_password
POSTGRES_DB=kommo_db

# Redis
REDIS_URL=redis://redis:6379/0

# Storage
STORAGE_MODE=local
LOCAL_STORAGE_PATH=/storage

# Kommo API
KOMMO_BASE_URL=https://YOUR_SUBDOMAIN.kommo.com
KOMMO_CLIENT_ID=your-client-id
KOMMO_CLIENT_SECRET=your-client-secret
KOMMO_REDIRECT_URI=http://YOUR_DROPLET_IP:3000/settings

# AssemblyAI (для транскрипции)
TRANSCRIBE_PROVIDER=assemblyai
ASSEMBLYAI_API_KEY=your-assemblyai-api-key

# OpenAI (для LLM анализа)
LLM_PROVIDER=openai
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL=gpt-4o-mini

# Upload limits
MAX_UPLOAD_MB=200
```

**Важно:**
- `ADMIN_API_KEY`: придумай сложный пароль (минимум 32 символа)
- `APP_ENCRYPTION_KEY`: создай случайный ключ 32 символа
- `KOMMO_REDIRECT_URI`: замени `YOUR_DROPLET_IP` на реальный IP сервера
- `ASSEMBLYAI_API_KEY`: получи на https://www.assemblyai.com/
- `LLM_API_KEY`: получи на https://platform.openai.com/api-keys

Сохрани: `Ctrl+X`, затем `Y`, затем `Enter`

---

## Шаг 6: Запуск приложения

```bash
# Сборка и запуск всех контейнеров
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

**Ожидаемый результат:**
```
NAME            STATUS
kommo-web       Up
kommo-api       Up (healthy)
kommo-worker    Up
kommo-postgres  Up (healthy)
kommo-redis     Up (healthy)
```

---

## Шаг 7: Применение миграций БД

```bash
docker compose exec api alembic upgrade head
```

---

## Шаг 8: Открытие портов в Firewall

```bash
# Разрешить HTTP и HTTPS
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp  # Frontend
ufw allow 8000/tcp  # API (временно для тестирования)
ufw enable
```

---

## Шаг 9: Проверка работы

1. **Frontend**: http://YOUR_DROPLET_IP:3000
2. **API Health**: http://YOUR_DROPLET_IP:8000/health
3. **Login**: Используй `ADMIN_API_KEY` из `.env`

---

## Шаг 10: Настройка домена (опционально, но рекомендуется)

### 10.1. Купи домен (например, на Namecheap или Cloudflare)

### 10.2. Настрой DNS записи

Добавь A-записи:
- `kommo-analyzer.com` → IP вашего Droplet
- `api.kommo-analyzer.com` → IP вашего Droplet

### 10.3. Установи Nginx и SSL (Let's Encrypt)

```bash
# Установка Nginx
apt install nginx certbot python3-certbot-nginx -y

# Создай конфиг для фронтенда
nano /etc/nginx/sites-available/kommo-analyzer
```

Вставь:

```nginx
server {
    listen 80;
    server_name kommo-analyzer.com www.kommo-analyzer.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

server {
    listen 80;
    server_name api.kommo-analyzer.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активируй конфиг
ln -s /etc/nginx/sites-available/kommo-analyzer /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Получи SSL сертификаты
certbot --nginx -d kommo-analyzer.com -d www.kommo-analyzer.com
certbot --nginx -d api.kommo-analyzer.com
```

---

## 🔧 Полезные команды

### Просмотр логов
```bash
# Все логи
docker compose logs -f

# Только API
docker compose logs -f api

# Только Worker
docker compose logs -f worker
```

### Перезапуск сервисов
```bash
# Перезапуск всех контейнеров
docker compose restart

# Перезапуск одного сервиса
docker compose restart worker
```

### Обновление кода
```bash
cd /opt/salesanalysis
git pull origin main
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Очистка Docker
```bash
# Удалить неиспользуемые образы
docker system prune -a

# Удалить volumes (ВНИМАНИЕ: удалит данные БД!)
docker compose down -v
```

---

## 🛡️ Безопасность

1. **Измени пароли PostgreSQL** в `.env`
2. **Используй сложный `ADMIN_API_KEY`**
3. **Не публикуй `.env` в GitHub!**
4. **Настрой Firewall**:
   ```bash
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow ssh
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```
5. **После настройки Nginx закрой прямые порты 3000 и 8000**:
   ```bash
   ufw delete allow 3000/tcp
   ufw delete allow 8000/tcp
   ```

---

## 📊 Мониторинг

### Проверка использования ресурсов
```bash
# Память и CPU контейнеров
docker stats

# Диск
df -h

# Логи системы
journalctl -u docker -f
```

---

## 🆘 Troubleshooting

### Контейнер не запускается
```bash
docker compose logs api
docker compose logs worker
```

### База данных не подключается
```bash
docker compose exec postgres psql -U kommo_user -d kommo_db
```

### Worker не обрабатывает задачи
```bash
docker compose logs -f worker
docker compose exec worker celery -A app.celery_app inspect active
```

### Очистка и пересборка
```bash
docker compose down -v
docker system prune -a -f
docker compose build --no-cache
docker compose up -d
```

---

## 📝 Следующие шаги

1. ✅ Настрой Kommo интеграцию в UI `/settings`
2. ✅ Загрузи тестовый звонок
3. ✅ Проверь результаты анализа
4. ✅ Настрой автоматический бэкап БД
5. ✅ Добавь мониторинг (UptimeRobot, Grafana)

---

## 💰 Стоимость

**Минимальная конфигурация (~$30-40/месяц):**
- Digital Ocean Droplet: $12-24/mo
- AssemblyAI: ~$0.37 за час аудио
- OpenAI GPT-4o-mini: ~$0.15-0.60 за 1000 токенов

**Оптимизация затрат:**
- Используй `gpt-4o-mini` вместо `gpt-4` (в 20-30 раз дешевле)
- AssemblyAI берет оплату только за реально обработанные минуты

---

🎉 **Готово! Теперь у тебя полноценный сервер для анализа звонков!**

Если возникнут вопросы - пиши! 🚀

