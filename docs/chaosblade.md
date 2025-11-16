# chaosblade

Chaosblade - платформа для хаос-инжиниринга. Типы доступных экспериментов:
* Operating System chaos
* Container Runtime chaos
* Kubernetes chaos
* JVM Application chaos
* Middleware chaos
* Cloud Platform chaos


## Operating System chaos

Эксперименты с хаосом в ОС затрагивают всю операционную систему, а не ограничиваются конкретными контейнерами или пространствами имён. Все эксперименты с ОС определяются в `chaosblade-os-spec` и выполняются через [локальный канал](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/2.3-execution-channels#local-execution-channel) или [канал SSH](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/2.3-execution-channels#ssh-remote-execution-channel).

Подробнее об экспериментах:
* [CPU](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.1-cpu-experiments) - увеличение нагрузки.
* [Memory](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.2-memory-experiments) - исчерпание памяти.
* [Network](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.3-network-experiments) - моделирование задержек, проблем с подключением, потерь пакетов, повреждения пакетов.
* [Disk](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.4-disk-experiments) - исчерпание дискового пространства и снижение производительности ввода/вывода.
* [Process](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.5-process-experiments) - моделирование сбоев процессов, зависания, конфликта ресурсов.
* [File System](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.6-file-system-experiments) - моделирование сбоев файловой системы путем манипулирования файлами и каталогами.
* [Advanced OS (systemd, system time, shell script execution, system call interception)](https://deepwiki.com/chaosblade-io/chaosblade-for-deepwiki/3.7-advanced-os-experiments)


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

2. Создать эксперимент. Эксперимент немедленно начинает выполняться и будет продолжаться до тех пор, пока не будет уничтожен явным образом или пока не истечет время ожидания `--timeout`.
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
