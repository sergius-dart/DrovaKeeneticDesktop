# Drova Desktop

И так, доброе время уток, мы здесь будем настраивать Drova Desktop для работы без наших аккаунтов. 

Нам понадобятся: 
+ ShadowDefender ( активированный и защищенный паролем)
+ Роутер, прошитый OpenWrt или Debian( чтобы ловить подключение и исполнять команды ) с python 3.12
+ установленный на роутере socat
+ проброс всех портов кроме 7985 на таргете средствами роутера
+ Установленный openssh-server на Windows и добавленный в автозагрузку

## Подготовка

Для того чтобы начать, склонируйте данный репозиторий на роутер.

Установите poetry 
```bash
pipx install poetry
```

Скачайте проект в `/opt/drova-desktop/`
```bash
git clone https://github.com/sergius-dart/DrovaKeeneticDesktop.git /opt/drova-desktop/
```

Перейдите в папку проекта
```bash
cd /opt/drova-desktop/
```

Установите зависимости проекта

```bash
poetry install
```

После этого надо настроить env переменные. Выполните команду `cp .env.example .env` и редактируйте `.env` файл - там находятся настройки для скриптов, давайте их рассмотрим. 

```bash
DROVA_SOCKET_LISTEN=7985 # тот сокет, который мы будем слушать - на который будут приходить соединения от клиентов

WINDOWS_HOST=192.168.0.10 # ip адрес вашей тачки, на которой вы хотите развернуть Desktop
WINDOWS_LOGIN=Administrator # ваш локальный администратор - который должен быть залогинен и под кем будет заходить клиент
WINDOWS_PASSWORD=VeryStrongPassword # пароль от этого пользователя

SHADOW_DEFENDER_PASSWORD="ReallyVeryStrongPassword" # пароль от ShadowDefender - не оставляйте его без пароля! А то вам закоммитят все что натворили! 
SHADOW_DEFENDER_DRIVES="CDE" # здесь перечислите слитно все диски, на которых должен сработать ShadowDefender - в данном случае 3 диска: C, D и E - подразумевается что других нет. Если диск 1 - только C - оставляете только E
```

После настройки теперь можно проверить, работает ли и верно ли указаны настройки. Залогинтесь по VNC в ваш windows, откройте со своими credentials steam и epic games - а так же желательно открыть ShadowDefender - чтобы увидеть что все ок. 

Дальше выполняем команду на роутере:

```bash
poetry run python drova_validate
```

Если написало `Ok!` - значит вы выставили .env верно и можно переходить к следующей части

## Автозапуск

entware ( debian на keenetic ) - поддерживает только upstart - для этого есть скрипт `init.d/drova_socket` - мы его никуда перекладывать не будем - нам надо создать сервис, и вызывать его. 

### Entware(debian 13)

Если у вас не такой сетап - читайте и думайте, из коробки тогда не взлетит. Давайте создадим сервис `drova_socket.i9_3080ti`

Для этого мы создадим файл командой
```bash
touch /etc/init.d/drova_socket.i9_3080ti
chmod +x /etc/init.d/drova_socket.i9_3080ti
```

Дальше открываем его например в nano или удобном вам редакторе и вставляем такой контект: 
```bash
#!/bin/bash

ENV_LOCATION=/opt/drova-desktop/NAME.env

. /opt/drova-desktop/init.d/drova_socket "$@"
```

`ENV_LOCATION` - здесь находится ваш файл конфигурации, вместо NAME можно использовать то что вам удобно, но это должен быть путь до ваших настроек. Если у вас 1 компьютер, то можете NAME не указывать и тогда просто прописать `ENV_LOCATION=/opt/drova-desktop/.env` - по дефолту. Или ваще ничего не указывать. Тоже будет работать. 

Как только создали, проверье командой
```bash
/etc/init.d/drova_socket.i9_3080ti start
```

Ошибок быть не должно, если есть - надо возвращаться к настроке `ENV_LOCATION` или настройке `.env` - если вы использовали `NAME`

Чтобы протестировать конфигурацию можно выполнить команду в папке проекта
```bash
ENV_LOCATION=/opt/drova-desktop/NAME.env poetry run drova_validate
```

По классике вы должны увидеть `Ok!` если все ок. 

Удачи!

### Systemd 

Для работы с systemd ( если вы не на роутере а на отдельной тачке или виртуалке, где полноценная debian с systemd )

Делаем ссылку на сервис
```bash
ln -s /opt/drova-desktop/systemd/drova_socket@.service /etc/systemd/system/drova_socket@.service
```

Перезагружаем демоны systemd
```bash
systemctl daemon-reload
```

Создаем `.env` файлы для ваших тачек формата `NAME.env` - где вместо NAME то что вы хотите, например имя тачки. Для примера - если тачка называется i9_3080ti - то вы должны создать файл с настройками `i9_3080ti.env`

Прописываем настройки как в прошлом пункте, и проверяем командой 
```bash
ENV_LOCATION=NAME.env poetry run drova_validate
```

Если все ок - вы должны увидеть `Ok!`

Теперь можно запустить сервис командой - где вместо `NAME` подставить ваше имя
```bash
systemctl start drova_socket@NAME
```

Если ошибок не произошло - можно поставить в автозапуск
```bash
systemctl enable drova_socket@NAME
```

Удачи!