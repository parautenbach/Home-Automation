# for ip in {1..254}; do
#   echo "Scanning 192.168.0.$ip..."
#   result=$(sudo nmap -sU -p 67 --script=dhcp-discover 192.168.0.$ip | grep "Server Identifier")
#   if [[ ! -z "$result" ]]; then
#     echo "DHCP Server found at 192.168.0.$ip"
#     echo "$result"
#   fi
# done

#####

sudo nmap -sU -p 67 --script=dhcp-discover 192.168.0.0/24
