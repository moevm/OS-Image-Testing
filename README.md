# OS-Image-Testing

Performance and Endurance Testing of OS images

Repository structure:

| Folder            |Description                               |
|-------------------|------------------------------------------|
| [docker](docker)  | Essential Docker-related files           |
| [docs](docs)      | Markdown documentation of the repository |
| [layers](layers)  | Layers content                           |
| [src](src)        | Source code and core development files   |
| [tests](tests)    | Image tests                              |

## Сборка Yocto образа через докер

### Базовая инициализация docker тома и последующая многоразовая сборка образа.

```
make docker
make docker-init-volumes
# Запуск QEMU в собранном docker образе
make docker-run-image
# Запуск тестирования QEMU через ptest-runner
make docker-test-image
```

Для добавления теста с использованием, например **stress-ng**, нужно зайти в папку tests, далее в папку endurance или performance, в зависимости от типа теста, затем добавить тест в папку тестируемой подсистемы, к которой относится тест и обновить соответствующий .bb файл.

Для добавления новой утилиты нужно обновить local.conf и прописать соответствующий рецепт, затем добавить пути до рецепта и зависимых файлов для всех вызываемых контейнеров в `Makefile`.
