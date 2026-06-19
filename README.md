[![Latest Release](https://img.shields.io/github/v/release/sergius-dart/DrovaKeeneticDesktop)](https://github.com/sergius-dart/DrovaKeeneticDesktop/releases/latest)

# Drova Desktop

И так, доброе время уток, мы здесь будем настраивать Drova Desktop для работы без наших аккаунтов. 

Проект поддерживает выход из аккаунтов следующих лаунчеров:
+ Steam
+ EpicGames
+ Ea
+ BattleNet
+ Grypholink(Endfield - из игры)
+ BsgLauncher(Tarkov)
+ Wargaming(Tanki EU)
+ Lesta(Tanki RU)
+ Ubisoft

Проект НЕ ПОДДЕРЖИВАЕТ выход из Genshin Impact и других игр Hoyoverse! 

Нам понадобятся: 
+ Windows с последними обновлениями. Протестировано на win10 - 11 на свой страх и риск! 
+ Роутер/linux машина, прошитый OpenWrt или Debian (или свободная физическая Linux-машина), с python 3.11 (проверено и на Manjaro с python 3.13.4)

Никакие сетевые настройки создавать ненадо - надо установить либо на свободную физическую linux машину или создать виртуалку, которая будет следить за состоянием. 

# Подготовка Windows

## Установка WinGet

Зайдите в MSStore - и найдите там WinGet (Winget-AutoUpdate-aaS (Preview)) - установите если планируете устанавливать OBS. 

## Установка пароля

Работа приложения требует пароля на Windows - чтобы все работало вам надо установить и запомнить его - он потребуется далее. 

## Установка DrovaDesktop

Надо скачать последний релиз ( [![Latest Release](https://img.shields.io/github/v/release/sergius-dart/DrovaKeeneticDesktop)](https://github.com/sergius-dart/DrovaKeeneticDesktop/releases/latest) ) - drovadesktop.exe - и установить. Вас спросят 

+ пароль для Windows
+ SN для ShadowDefender(простите мне лень постоянно копировать его так что пользуйтесь)
+ ShadowDefender пароль ( придумать и запомнить )

После того как установка пройдет - надо сохранить конфиг, который установщик сгенерирует на рабочий стол - он понадобится для настройки проекта. Можете его скачать и ОБЯЗАТЕЛЬНО удалите с рабочего стола его - и из корзины тоже. Там хранятся ваши пароли! 

# Подготовка проекта

Следующая инструкция выполняется от `root` пользователя или с `sudo` на роутере или тачке с Linux. 

Для того чтобы начать, склонируйте данный репозиторий на роутер или тачку (протестировано на linux - но должно работать и на windows - но на windows вы сами создаете задачи для автозапуска).


Для debian вам надо установить python3 + pipx + git
```bash
apt install python3-full pipx git
```

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

Вам надо настроить env переменные - это можно сделать перенеся сохраненный файл, что сгенерировал установщик, либо заполнив самостоятельно. Описание файла:

```bash
WINDOWS_HOST=192.168.0.10 # ip адрес вашей тачки, на которой вы хотите развернуть Desktop
WINDOWS_LOGIN=Administrator # ваш локальный администратор - который должен быть залогинен и под кем будет заходить клиент
WINDOWS_PASSWORD=VeryStrongPassword # пароль от этого пользователя

SHADOW_DEFENDER_PASSWORD="ReallyVeryStrongPassword" # пароль от ShadowDefender - не оставляйте его без пароля! А то вам закоммитят все что натворили! 

OBS_REMOTE_URL="" # Здесь мы будем устанавливать url для стриминга. Стриминг пока не доделан - unstable опция!
```

После настройки теперь можно проверить, работает ли и верно ли указаны настройки. Залогиньтесь по VNC в ваш windows, откройте со своими credentials steam и Epic games - а так же желательно открыть ShadowDefender - чтобы увидеть что все ок.

Дальше выполняем команду на роутере:

```bash
poetry run drova_validate
```

либо так если вы не .env в NAME.env сделали

```bash
ENV_LOCATION=NAME.env poetry run drova_validate
```

Если написало `Ok!` - значит вы выставили `.env` верно и можно переходить к следующей части.

# Автозапуск

entware ( debian на keenetic ) - поддерживает только upstart - для этого есть скрипт `init.d/drova_poll` - мы его никуда перекладывать не будем - нам надо создать сервис, и вызывать его. 

## Entware(debian 13)

Если у вас не такой сетап - читайте и думайте, из коробки тогда не взлетит. Давайте создадим сервис `drova_socket.i9_3080ti`

Для этого мы создадим файл командой
```bash
touch /etc/init.d/drova_poll.i9_3080ti
chmod +x /etc/init.d/drova_poll.i9_3080ti
```

Дальше открываем его например в nano или удобном вам редакторе и вставляем такой контект: 
```bash
#!/bin/bash

ENV_LOCATION=/opt/drova-desktop/NAME.env

. /opt/drova-desktop/init.d/drova_poll "$@"
```

`ENV_LOCATION` - здесь находится ваш файл конфигурации, вместо NAME можно использовать то что вам удобно, но это должен быть путь до ваших настроек. Если у вас 1 компьютер, то можете NAME не указывать и тогда просто прописать `ENV_LOCATION=/opt/drova-desktop/.env` - по дефолту. Или ваще ничего не указывать. Тоже будет работать. 

Как только создали, проверье командой
```bash
/etc/init.d/drova_poll.i9_3080ti start
```

Ошибок быть не должно, если есть - надо возвращаться к настроке `ENV_LOCATION` или настройке `.env` - если вы использовали `NAME`

Чтобы протестировать конфигурацию можно выполнить команду в папке проекта
```bash
ENV_LOCATION=/opt/drova-desktop/NAME.env poetry run drova_validate
```

По классике вы должны увидеть `Ok!` если все ок. 

Удачи!

## Systemd (у вас виртуалки нормальная или физическая машина с нормальным дистрибутивом( написано для debian 12/13))

Для работы с systemd (если вы не на роутере а на отдельной тачке или виртуалке, где полноценная debian с systemd)

Делаем ссылку на сервис
```bash
ln -s /opt/drova-desktop/systemd/drova_poll@.service /etc/systemd/system/drova_poll@.service
```

Перезагружаем демоны systemd
```bash
systemctl daemon-reload
```

Создаем `.env` файлы для ваших тачек формата `NAME.env` - где вместо NAME то что вы хотите, например имя тачки. Для примера - если тачка называется i9_3080ti - то вы должны создать файл с настройками `i9_3080ti.env`

Прописываем настройки как в прошлом пункте, и проверяем командой (i9_3080ti заменяете на ваше имя)
```bash
ENV_LOCATION=i9_3080ti.env poetry run drova_validate
```

Если все ок - вы должны увидеть `Ok!`

Теперь можно запустить сервис командой - где вместо `NAME` подставить ваше имя ( уже подставлено i9_3080ti )
```bash
systemctl start drova_poll@i9_3080ti
```

Если ошибок не произошло - можно поставить в автозапуск ( подставьте ваше имя вместо i9_3080ti )
```bash
systemctl enable drova_poll@i9_3080ti
```

Удачи!