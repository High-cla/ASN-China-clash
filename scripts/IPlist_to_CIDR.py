with open('IP.China.list', 'r') as f, open('IP.China.txt', 'w') as o:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        if ":" in line:
            new_line = "IP-CIDR6," + line + ",no-resolve\n"
        else:
            new_line = "IP-CIDR," + line + ",no-resolve\n"
        o.write(new_line)