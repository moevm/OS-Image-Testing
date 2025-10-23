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

### 1. Клонирование репозитория

```bash
git clone https://github.com/moevm/OS-Image-Testing.git

cd OS-Image-Testing
```

### 2. Подключение open source слоёв

```bash
git submodule update --init --recursive
```

### 3. Базовая инициализация docker томов и последующая многоразовая сборка образа

```
# Инициализация docker образа и томов
make docker

# Запуск сборки образа
make docker-init-volumes

# Запуск QEMU в собранном docker образе
make docker-run-image

# Запуск тестирования QEMU через ptest-runner
make docker-test-image
```

Для добавления теста с использованием, например **stress-ng**, нужно зайти в папку layers/meta-image/tests/recipes-tests, далее в endurance-tests или performance-tests, в зависимости от типа теста, затем добавить тест в папку тестируемой подсистемы и обновить соответствующий .bb файл.

Для добавления новой утилиты нужно обновить local.conf и прописать соответствующий рецепт, затем добавить пути до рецепта и зависимых файлов для всех вызываемых контейнеров в `Makefile`.
