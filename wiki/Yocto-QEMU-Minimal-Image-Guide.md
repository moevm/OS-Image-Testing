# Сборка минимального образа Yocto и его запуск в QEMU

### Требования к узлу сборки:
* Не менее 90 ГБ свободного места на диске
* Минимум 8 ГБ оперативной памяти (рекомендуется 16 ГБ)
* Поддерживаемый дистрибутив Linux
  * https://docs.yoctoproject.org/ref-manual/system-requirements.html#supported-linux-distributions
* Git 1.8.3.1 или выше 
* tar 1,28 или выше 
* Python 3.8.0 или новее
* gcc 8.0 или выше
* GNU make 4.0 или выше


### Шаги

#### 1 - Установка зависимостей

```bash
sudo apt install build-essential chrpath cpio debianutils diffstat file gawk gcc git iputils-ping libacl1 liblz4-tool locales python3 python3-git python3-jinja2 python3-pexpect python3-pip python3-subunit socat texinfo unzip wget xz-utils zstd
```

#### 2 - Клонирование репозитория Yocto
```bash
git clone git://git.yoctoproject.org/poky
```

Далее необходимо определиться релизом. Их можно изучить по ссылке: https://wiki.yoctoproject.org/wiki/Releases.

Далее следует переключиться на ветку, соответсвующую выбранному релизу.

```bash
git checkout -t origin/styhead -b my-styhead
```

#### 3 - Инициализация среды сборки

```bash
cd poky
source oe-init-build-env
```

Помимо прочего, скрипт создаёт каталог сборки, который в данном случае является build и находится в исходном каталоге. После запуска скрипта текущим рабочим каталогом становится каталог сборки. После завершения сборки каталог сборки содержит все файлы, созданные во время сборки.

#### 4 - Просмотр конфигурационного файла 

Файл build/conf/local.conf предоставляет возможность управлять различными аспектами процесса сборки.

Например:
* настраивать производительность сборки, например, с помощью параметров BB_NUMBER_THREADS и PARALLEL_MAKE
* добавлять или исключать пакеты
* включить подробный вывод логов или настроить уровни отладки

В данном случае, можно убедиться, что указана правильная машина для эмуляции.

`
MACHINE ??= "qemux86-64"
`

#### 5 - Сборка минимального образа

```bash
bitbake core-image-minimal
```

**core-image-minimal** - минимальный образ, достаточный для загрузки устройства. Включает только самые необходимые компоненты для запуска системы.

_Сборка может занять несколько часов._

#### 6 - Запуск образа в QEMU

```bash
runqemu qemux86-64
```

Выйдите из QEMU, нажав на значок выключения или введя Ctrl-C в окне вывода QEMU, из которого вы запустили QEMU.
