#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1

if [ ! -x ".venv/bin/python" ]; then
    printf '%s\n' 'Bitte zuerst im Projektordner: python3.13 projekt.py einrichten'
    read -r -p 'Zum Schliessen Enter druecken. '
    exit 1
fi

if ! ".venv/bin/python" projekt.py anzeigen; then
    printf '%s\n' 'Die Visualisierung konnte nicht geoeffnet werden. Hinweise stehen oben.'
    read -r -p 'Zum Schliessen Enter druecken. '
    exit 1
fi
