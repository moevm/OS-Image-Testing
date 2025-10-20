# Contributing

First of all thank you for your desire to contribute in that project.

## Development environment

You'll need to install and setup pre-commit hooks for checking style of source code, formatting it and checking types.

### Installing pre-commit on Ubuntu

Installing a `pre-commit` in the distribution:
```
sudo apt update
sudo apt install pre-commit
```

Installing a `pre-commit` script in the repository to automatically run check scripts when committing to a branch.
```
pre-commit install
```

### Self-checking a commit

Checks all the repository files:
```
pre-commit run --all-files
```
