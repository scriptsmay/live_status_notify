# live_status_notify

## setup

```
# create dir
mkdir -p config

# download config
wget https://raw.githubusercontent.com/scriptsmay/live_status_notify/main/config/config.ini -O ./config/config.ini
wget https://raw.githubusercontent.com/scriptsmay/live_status_notify/main/config/URL_config.ini -O ./config/URL_config.ini
```

config your files as your own

## docker-compose setup

`docker-compose.yml` :

```
services:
  live-status-notify:
    image: ghcr.io/scriptsmay/live_status_notify:latest
    container_name: live-status-notify
    restart: always
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./backup_config:/app/backup_config
    environment:
      - TZ=Asia/Shanghai

```

## run

`docker-compose up -d`
