#!/bin/bash

find . -type f -name "*.yaml" -exec sed -nr 's/- alias.+"(.+)"/\1/p' {} + |sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' |sed -r "s/[ ']/_/g" |tr "[:upper:]" "[:lower:]" |sort |iconv -t ascii//translit |sed "s/'//g" |sed -r 's/^/- automation./g'

