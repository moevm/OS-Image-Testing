## Запуск LTP тестов

Просмотр наборов 
```
ls /opt/ltp/runtest
```

### Флаги runltp

- -f <suite_name> — выбрать набор (например, syscalls, fs, mm, ipc, timers, sched, net)

- -s <test_name> — выбрать конкретный тест в наборе

- -l <file_name> — лог LTP

- -o <file_name> — итоговый отчёт

- -p — «pretty» формат

- -q — тихий режим (скрывает промежуточные сообщения)

- -m N — остановиться после N FAIL

- -d <dir_name> — рабочая директория для временных файлов тестов

Просмотр отчета, который был записан через -о

```
tail -n 50 /tmp/ltp.out
```

### Пример
```
/opt/ltp/runltp -p -q \
  -l /tmp/ltp.log \
  -o /tmp/ltp.out \
  -f syscalls \
  -s getpid01
```
Где `-f syscalls` — запускает набор системных вызовов, `-s getpid01` — ровно один тест из набора, логи и отчёт складываются в /tmp/ltp.log и /tmp/ltp.out соответственно