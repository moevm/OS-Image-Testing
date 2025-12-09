# chaosblade

Chaosblade - платформа для хаос-инжиниринга. Он позволяет проводить контролируемые эксперименты с различными сбоями в системе для тестирования ее отказоустойчивости. Типы доступных систем для экспериментов:
* Operating System chaos
* Container Runtime chaos
* Kubernetes chaos
* JVM Application chaos
* Middleware chaos
* Cloud Platform chaos


## Operating System chaos

Эксперименты с хаосом в ОС затрагивают всю операционную систему, а не ограничиваются конкретными контейнерами или пространствами имён. Все эксперименты с ОС определяются в `chaosblade-os-spec` и выполняются через [локальный канал](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/2.3-execution-channels#local-execution-channel) или [канал SSH](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/2.3-execution-channels#ssh-remote-execution-channel).

Подробнее об экспериментах:
1. [CPU](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.1-cpu-experiments)
	* Доступные действия:
		* fullload (алиас fl, load) - создание нагрузки на процессор
	* Флаги:
		* `--cpu-percent` - процент загрузки процессора
		* `--cpu-count` -  количество случайно выбранных ядер процессора
		* `--cpu-list` - целевые ядра
		* `--climb-time` -  позволяет постепенно увеличивать нагрузку, начиная с 0% и доводя её до целевого значения в течение указанного времени (в секундах)
2. [Memory](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.2-memory-experiments)
	* Иммитируют сценарии нехватки памяти за счет выделения и использования памяти
	* Доступные действия:
		* load - создание нагрузки на память (выделение и удерживание)
	* Есть 2 режима работы (`--mode`):
		* `ram` - нагрузка на оперативную память
		* `cache` - нагрузка на кэш
	* Флаги определения размера памяти:
		* `--mem-percent` - процент от общего объема памяти
		* `--reserve` - объем памяти (в МБ), который должен быть свободным
		* Если есть `--mem-percent`, то оно имеет приоритет. Если есть только `--reserve`, то используется `--reserve`. В противном случае происходоит неявное вычисление размера.
	* Флаги:
		* `--include-buffer-cache` - при расчете процента использования памяти учитывается буферная и кэш-память в режиме `ram`.
		* `--rate` - скорость выделения памяти в режиме `ram` в МБ/с.
3. [Network](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.3-network-experiments)
	* Доступные действия:
		* `delay` - задержка в сети
		* `loss` - потеря пакетов
		* `duplicate` - дублирование пакетов
		* `corrupt` - повреждение пакетов
		* `reorder` - неправильный порядок пакетов, имитация проблем с сетевой маршрутизации
		* `drop` - блокировка сетевых пакетов по различным критериям
		* `dns` - управление разрешением dns
		* `dns_down` - делает разрешение dns недоступным
		* `occupy` - делает недоступным порт
	* Флаги:
		* `--interface` - указание интерфейса
		* `--destination-ip` - указание адреса(ов) назначения
		* `--exclude-ip` - исключение адреса(ов) назначения, если не задан `--destination-ip`
	* Флаги для `delay`:
		* `--time` - время задержки в мс
		* `--offset` - смещение/jitter в мс
	* Флаги для `loss`:
		* `--percent` - процент потери пакетов
	* Флаги для `duplicate`:
		* `--percent` - процент дублирования
	* Флаги для `corrupt`:
		* `--percent` - процент поврежденных пакетов
	* Флаги для `reorder`:
		* `--percent` - процент поврежденных пакетов
		* `--correlation` - корреляция с предыдущим пакетом
		* `--gap` - интервал между пакетами
		* `--time` - время задержки в мс (по умолчанию 10мс
		)
	* Флаги для `drop`:
		* `--source-ip` - адрес источника
		* `--destination-ip` - адрес получателя
		* `--source-port` - порт источника
		* `--destination-port` - порт получателя
		* `--string-pattern` - строка, содержащаяся в полезной нагрузке пакета
		* `--network-traffic` - направление движения (in/out)
	* Флаги для `dns`:
		* `--domain` - доменное имя
		* `--ip` - ip-адрес
	* Флаги для `dns_down`:
		* `--allow_domain` - список доменов, которые должны продолжать разрешаться
	* Флаги для `occupy`:
		* `--force` - принудительное завершение процесса через порт
		* `--port` - порт, который нужно занять
4. [Disk](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.4-disk-experiments)
	* Доступные действия:
		* fill - создание больших файлов для заполнения диска
		* burn - создание высокой загрузки на диск с помощью операций чтения/записи
	* Флаги для `fill`:
		* `--path` - путь к каталогу. По умолчанию `/`
		* `--size` - размер заполнения в МБ
		* `--percent` - процент заполнения дискового пространства
		* `--reserve` - сколько оставить свободным в МБ
		* Приоритет `percent > reserve > size`
		* `--retain-handle` - предотвращает удаление файла внешними процессами
	* Флаги для `burn`:
		* `--path` - путь к каталогу. По умолчанию `/`
		* `--size` - размер блока в МБ
		* `--read` - чтение (создает файл размером 600 МБ для чтения)
		* `--write` - запись (создает файл размером `--size`*10 МБ)
		* Необходимо указать хотя бы одно из `read` или `write` значений. Оба параметра можно включить одновременно
5. [Process](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.5-process-experiments)
	* Доступные действия:
		* kill - завершение процессов
		* stop - приостановка процессов
		* load - нагрузка путем запуска новых процессов
	* Флаги для `kill`, `stop`:
		* `--process` - процесс (точное совпадение)
		* `--process-cmd` - процесс (неточное совпадение)
		* `--count` - ограничение на количество затронутых процессов. 0 - без ограничений
		* `--signal` - сигнал. По умолчанию SIGTERM
		* `--exclude-process` - шаблон исключения
		* `--pid` - указание pid процесса
		* `--local-port` - выбор процесса на основе порта
		* `--ignore-not-found` - вернуть результат, даже если подходящих процессов нет
	* Флаги для `load`:
		* `--count` - количество процессов, которые будут запущены. 0 - без ограничений
		* `--user` - пользователь, от которого осуществляется запуск процессов. По умолчанию текущий пользователь
6. [File System](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.6-file-system-experiments) - моделирование сбоев файловой системы путем манипулирования файлами и каталогами.
	* Доступные действия:
		* append - добавление содержимого в файл
		* chmod - изменение прав доступа к файлам
		* add - создание новых файлов/каталогов
		* delete - удаление файлов/каталогов
		* move - перемещение файлов/каталогов
	* Флаги для `append`:
		* `--filepath` - путь к файлу
		* `--content` - содержимое для добавления
		* `--count` - количество добавлений
		* `--interval` - интервалмежду добавлениями (в секундах)
		* `--escape` - экранирование в `--content`
		* `--enable-base64` - в `--content` данные в base64
		* `--enable-backup` - создать резервную копию исходного файла для восстановления при завершении работы эксперимента
		* `--delete-file` - удаение файла при завершении работы эксперимента. Переопределяет `--enable-backup`
	* Флаги для `chmod`:
		* `--filepath` - путь к файлу
		* `--mark` - права доступа
	* Флаги для `add`:
		* `--filepath` - путь к файлу или каталогу для создания
		* `--directory` - указание создать директорию
		* `--content` - содержимое для записи при создании файла
		* `--enable-base64` - в `--content` данные в base64
		* `--auto-create-dir` - автоматическое создание родительских каталогов, если их нет
	* Флаги для `delete`:
		* `--filepath` - путь к файлу
		* `--force` - необратимое удаление
	* Флаги для `move`:
		* `--filepath` - путь к исходному файлу
		* `--target` - путь к целевому файлу
		* `--force` - перезаписать целевой файл, если он уже существует
		* `--auto-create-dir` - автоматическое создание родительских каталогов, если их нет


## Установка

1. Скачать
```
wget https://github.com/chaosblade-io/chaosblade/releases/download/v1.7.2/chaosblade-1.7.2-linux-amd64.tar.gz
```

2. Распаковать
```
tar -xzf chaosblade-1.7.2-linux-amd64.tar.gz
cd chaosblade-1.7.2/
```

3. Проверить установку
```
./blade version
```

## Пример команд
Подробнее о CLI [здесь](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/2.2-command-line-interface).

1. Проверка среды. Перед запуском экспериментов рекомендуется проверить, что в системе есть все зависимости.
```
blade check os cpu fullload
```

Вывод:
```
{"code":200,"success":true,"result":"[success] cpu fullload, success! `taskset` command exists"}
```

2. Создать эксперимент. Эксперимент немедленно начинает выполняться и будет продолжаться до тех пор, пока не будет уничтожен явным образом или пока не истечет время `--timeout`.
```
blade create cpu load --cpu-percent 20 --timeout 30
```

Вывод:

```
{"code":200,"success":true,"result":"4f222eee2051219b"}
```

`result` здесь указывает на `<experiment-id>`

3. Запросить информацию о конкретном эксперименте
```
blade status <experiment-id>
```

Вывод:

* во время работы
	```
	{
		"code": 200,
		"success": true,
		"result": {
			"Uid": "4f222eee2051219b",
			"Command": "cpu",
			"SubCommand": "fullload",
			"Flag": " --cpu-percent=20 --timeout=30",
			"Status": "Success",
			"Error": "",
			"CreateTime": "2025-11-16T15:49:08.565439457+03:00",
			"UpdateTime": "2025-11-16T15:49:08.686480503+03:00"
		}
	}
	```
* после истечения `timeout` или использования `destroy`
	```
	{
		"code": 200,
		"success": true,
		"result": {
			"Uid": "4f222eee2051219b",
			"Command": "cpu",
			"SubCommand": "fullload",
			"Flag": " --cpu-percent=20 --timeout=30",
			"Status": "Destroyed",
			"Error": "",
			"CreateTime": "2025-11-16T15:49:08.565439457+03:00",
			"UpdateTime": "2025-11-16T15:49:39.015493204+03:00"
		}
	}
	```

4. Эксперименты необходимо завершать вручную, если не задан `--timeout`, чтобы освободить ресурсы и вернуть систему в исходное состояние.
```
blade destroy <experiment-id>
```

Вывод:

```
{"code":200,"success":true,"result":"command: cpu fullload  --cpu-percent=20 --timeout=30, destroy time: 2025-11-16T15:49:39.015493204+03:00"}
```

5. Возможно просматривать информацию о статусе нескольких экспериментов с фильтрацией (`--type`, `--status`, `--target`, `--flag-filter`)

```
blade status --type create --flag-filter "timeout=10"
```

Вывод:
```
{
	"code": 200,
	"success": true,
	"result": [
		{
			"Uid": "69ff46fe079e5b5e",
			"Command": "cpu",
			"SubCommand": "fullload",
			"Flag": " --cpu-percent=20 --timeout=10",
			"Status": "Destroyed",
			"Error": "",
			"CreateTime": "2025-11-16T17:26:42.13752147+03:00",
			"UpdateTime": "2025-11-16T17:26:52.711820974+03:00"
		},
		{
			"Uid": "2425f39e20c3869a",
			"Command": "cpu",
			"SubCommand": "fullload",
			"Flag": " --timeout=10 --cpu-percent=20",
			"Status": "Destroyed",
			"Error": "",
			"CreateTime": "2025-11-16T15:21:47.505276784+03:00",
			"UpdateTime": "2025-11-16T15:21:58.125917793+03:00"
		}
	]
}
```
