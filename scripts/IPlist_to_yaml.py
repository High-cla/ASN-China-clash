with open("IP.China.txt", 'r') as f:
    iplist = f.readlines()

output = 'payload:\n'
for line in iplist:
    output += "  - " + line.strip() + "'\n"
with open('IP.China.yaml', 'w') as f:
    f.write(output)
