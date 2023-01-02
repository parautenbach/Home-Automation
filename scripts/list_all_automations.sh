#!/bin/bash

sed -nr 's/- alias.+"(.+)"/\1/p' * |sed -r "s/[ ']/_/g" |tr "[:upper:]" "[:lower:]" |sort |iconv -t ascii//translit |sed "s/'//g" |sed -r 's/^/- automation./g'
