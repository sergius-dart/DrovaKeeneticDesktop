#!/bin/bash
echo "Black"
black .
echo "Isort"
isort .
echo "Pylint"
pylint drova_desktop_keenetic
echo "Mypy"
mypy drova_desktop_keenetic