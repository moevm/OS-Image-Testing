# SQLIOSim

SQLIOSim - приложение для имитации действий SQL Server на уровне дисковых операций. Его можно использовать для тестирования надежности и целостности дисковых подсистем.

Входит в стандартный набор программ при установке Microsoft SQL Server и связан с ним тем, что он имитирует выполнение его операций.

SQLIOSim заточен под Windows, но его можно использовать и в Linux (Red Hat, SUSE, Ubuntu).

Для осуществления моделирования операций ввода-вывода через графический интерфейс, необходимо запустить приложение по пути:

```
C:\Program Files\Microsoft SQL Server\MSSQLXX.<InstanceName>\MSSQL\Binn\SQLIOSIM.exe"
```

После [настройки конфигурации]((https://learn.microsoft.com/ru-ru/troubleshoot/sql/tools/sqliosim-utility-simulate-activity-disk-subsystem)) можно начать симуляцию.

Пример вывода из графического интерфейса:

```
 ********** Final Summary for file C:\temp\sqliosim.mdx **********
Target IO Duration (ms) = 100, Running Average IO Duration (ms) = 0, Number of times IO throttled = 89978, IO request blocks = 62
Reads = 200524, Scatter Reads = 336282, Writes = 7631, Gather Writes = 249396, Total IO Time (ms) = 43265879
DRIVE LEVEL: Sector size = 512, Cylinders = 31130, Media type = 12, Sectors per track = 63, Tracks per Cylinders = 255
DRIVE LEVEL: Read cache enabled = Yes, Write cache enabled = Yes
DRIVE LEVEL: Read count = 542111, Read time = 1684781, Write count = 502093, Write time = 42903603, Idle time = 50282, Bytes read = 55905911808, Bytes written = 69013877248, Split IO Count = 1204, Storage number = 3, Storage manager name = VOLMGR

********** Final Summary for file C:\temp\sqliosim.ldx **********
Target IO Duration (ms) = 100, Running Average IO Duration (ms) = 35, Number of times IO throttled = 301, IO request blocks = 9
Reads = 335, Scatter Reads = 0, Writes = 240280, Gather Writes = 0, Total IO Time (ms) = 1336325
DRIVE LEVEL: Sector size = 512, Cylinders = 31130, Media type = 12, Sectors per track = 63, Tracks per Cylinders = 255
DRIVE LEVEL: Read cache enabled = Yes, Write cache enabled = Yes
DRIVE LEVEL: Read count = 542116, Read time = 1684788, Write count = 502101, Write time = 42903604, Idle time = 50447, Bytes read = 55906038784, Bytes written = 69013914112, Split IO Count = 1204, Storage number = 3, Storage manager name = VOLMGR
```

* sqliosim.mdx - файл данных
* sqliosim.ldx - журнал транзакций
* sqliosim.log.xml - журнал ошибок

Возможен запуск через командную строку, для этого нужно указать путь до конфигурации и до места сохранения логов:

```
SQLIOSIM.COM -cfg C:\temp\sqliosim.cfg.ini -log C:\temp\sqliosim.log.xml
```

Будет сформирован файл с описанием всех событий во время тестирования и результатами. Пример вывода:

```
<ENTRY TYPE='INFO' TIME='02:57:30' DATE='11/08/25' TID='9080' User='Монитор' File='FileIO.cpp' Func='CLogicalFile::OutputSummary' HRESULT='' SYSTEXT=''>
<EXTENDED_DESCRIPTION>DRIVE LEVEL: Read count = 145369, Read time = 112396, Write count = 2698947, Write time = 1797779, Idle time = 2047373, Bytes read = 36437557760, Bytes written = 152289914880, Split IO Count = 857, Storage number = 3, Storage manager name = VOLMGR  </EXTENDED_DESCRIPTION>
</ENTRY>
```

Одновременно можно протестировать несколько томов дисков с помощью -dir, а также указать размеры файлов (МБ) и время выполнения (с):

```
SQLIOSIM.COM -cfg C:\temp\sqliosim.cfg.ini -log C:\temp\sqliosim.log.xml -dir "D:\sqliosim" -dir "F:\sqliosim" -size 500 -d 300
```
