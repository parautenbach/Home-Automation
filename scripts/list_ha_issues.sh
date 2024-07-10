grep -ir http * |grep github |grep core |grep issues | grep -o 'https://github.com[^ ]*' | sort -t '/' -k7,7n | uniq
