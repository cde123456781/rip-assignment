"""
Title: Rip Assignment 2024
Author: Byrson Chen (32687456) Luke Morimoto (33883343)
Date: 22/04/2024
"""
import sys
import socket
import select
import time
import random


def file_parse(file_name: str):
    """Parses the file provided to extract router_id, input_ports, and outputs"""
    router_id = None
    input_ports = []
    outputs = []
    timers_output = None
    try:
        file = open(file_name, "r")
        line = file.readline()
    except FileNotFoundError:
        print("The file name provided as an argument could not be found")
        exit()
    except:
        print("An error occurred when opening the file")
        exit()

    while line:
        # Do some parsing
        if "router-id" in line:
            # Eg. Parsing: router-id 1
            router_id = line.split()[1]
            if (not router_id.isnumeric()):
                print("router-id in the config was not an integer")
                exit()
            else:
                router_id = int(router_id)
                if (router_id > 64000 or router_id < 1):
                    print("router-id in the config needs to be between 1 and 64000")
                    exit()
        elif "input-ports" in line:
            # Holds a string of comma separated input ports
            # Eg. input-ports 6110, 6201, 7345
            try:
                input_ports_string = line.split(" ", 1)[1]
            except:
                print("Line contains \"input-ports\" but no ports")
                exit()
            # Ports all need to be unique and be between 1024 and 64000 inclusive
            input_ports = input_ports_string.split(",")
            try:
                for i in range(len(input_ports)):
                    input_ports[i] = int(input_ports[i])
            except:
                print("Error parsing input ports")
                exit()

            for i in input_ports:
                if ((i > 64000 or i < 1024) or input_ports.count(i) > 1):
                    print("Invalid input port number was provided")
                    exit()
                
        elif "outputs" in line:
            # Holds a string of comma separated outputs
            # Eg. outputs 5000-1-1, 5002-5-4
            outputs_string = line.split(" ", 1)[1]
            outputs_triple = outputs_string.split(",")

            outputs_ports_list = []
            
            for i in outputs_triple:
                current_triple = i.split("-")
                if len(current_triple) != 3:
                    print("Error in outputs")
                    exit()
                try:
                    for j in range(3):
                        current_triple[j] = int(current_triple[j])
                except:
                    print("Provided outputs must be integers")
                    exit()
                
                if current_triple[0] > 64000 or current_triple[0] < 1024:
                    print("Output port out of range")
                    exit()
                if current_triple[2] > 64000 or current_triple[2] < 1:
                    print("Output router-id out of range")
                    exit()
                
                if current_triple[0] not in outputs_ports_list:
                    outputs_ports_list.append(current_triple[0])
                else:
                    print("Output ports are not all unique")
                    exit()

                outputs.append(current_triple)

        elif "timers" in line:
            timers_string = line.split(" ", 1)[1]

            try:
                timers_string = int(timers_string)
            except:
                print("Provided outputs must be integers")
                exit()
            if timers_string <= 0:
                print("Timer must be positive")
                exit()
            
            timers_output = [timers_string, timers_string*6, timers_string*4]



                           
        line = file.readline()


    file.close()

    if router_id is not None and input_ports and outputs:
        for i in outputs:
            if i[0] in input_ports:
                print("Output port cnanot be in input ports")
                exit()
        return (router_id, input_ports, outputs, timers_output)

    else:
        missing_params = []
        if router_id == None:
            missing_params.append("router-id")
        if not input_ports:
            missing_params.append("input-ports")
        if not outputs:
            missing_params.append("outputs")
        
        print("Missing params: {}".format(missing_params))
        exit()

def socket_bind(input_ports):
    sockets = []

    for i in input_ports:
        current_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        current_socket.bind(('127.0.0.1', i))
        sockets.append(current_socket)

    return sockets


def create_packet(router_id, routing_table):
    output_packet = bytearray()

    output_packet.append(2)
    output_packet.append(2)

    if router_id > 255:
        output_packet.append(router_id >> 8)
        output_packet.append(router_id - ((router_id >> 8) << 8))
    else:
        output_packet.append(0)
        output_packet.append(router_id) 
    
    for i in routing_table.keys():
        output_packet.append(0)
        output_packet.append(2)
        output_packet.append(0)
        output_packet.append(0)

        # router-id of the entry
        output_packet.append(0)
        output_packet.append(0)
        output_packet.append(i >> 8)
        output_packet.append(i - ((i >> 8) << 8))


        for j in range(8):
            output_packet.append(0)
        
        # metric of the entry

        for j in range(3):
            output_packet.append(0)

        output_packet.append(routing_table[i][1])

    return output_packet

def update_routing_table(sender_router_id, routing_table, rip_entries, outputs, sockets, router_id):
    table = routing_table.copy()


    if (sender_router_id not in table.keys()):
        neighbour_cost = 0
        for i in outputs:
            if i[2] == sender_router_id:
                neighbour_cost = i[1]

        if neighbour_cost == 0:
            #ie. sender is not a neighbour
            return table

        table[sender_router_id] = [sender_router_id, neighbour_cost, time.perf_counter(), time.perf_counter(), False]

    for i in rip_entries:
        if i[0] not in table.keys() and i[1] < 16:
            table[i[0]] = [sender_router_id, i[1] + table[sender_router_id][1], time.perf_counter(), time.perf_counter(), False]
        elif i[0] not in table.keys() and i[1] >= 16:
            continue
        elif i[0] == router_id:
            continue
        elif i[1] >= 16:
            if table[i[0]][1] < 16:
                table[i[0]][1] = 16
                table[i[0]][2] = time.perf_counter()
                packet = create_packet(router_id, table)
                send_packet(packet, sockets[0], outputs)
                
        else:
            current_cost = table[i[0]][1]
            current_output = None
            for j in outputs:
                if j[2] == sender_router_id:
                    current_output = j[1]
            if current_output == None:
                return table
            if current_cost > (current_output + i[1]):
                table[i[0]][0] = sender_router_id
                table[i[0]][1] = current_output + i[1]
                table[i[0]][2] = time.perf_counter()
                if current_output + i[1] < 16:
                    table[i[0]][4] = False
            elif current_cost == (current_output + i[1]):
                table[i[0]][2] = time.perf_counter()
                if current_cost < 16:
                    table[i[0]][4] = False

    return table

def parse_packet(input_packet):
    rip_entries = []
    try:
        packet_len = len(input_packet)

        # Check header 
        if not (input_packet[0] == 2 and input_packet[1] == 2):
            return None

        sender_router_id = (input_packet[2] << 8) + input_packet[3]


        if (sender_router_id > 64000 or sender_router_id < 1):
            return None


        
        if (packet_len-4) % 20 != 0:
            return None
        
        for i in range((packet_len - 4) // 20):

            if not (input_packet[(20*i)+4] == 0 and input_packet[(20*i)+5] == 2):
                return None

            
            if not (input_packet[(20*i)+6] == 0 and input_packet[(20*i)+7] == 0):
                return None
            
            router_id = (input_packet[(20*i)+8] << 24) + (input_packet[(20*i)+9] << 16) + (input_packet[(20*i)+10] << 8) + input_packet[(20*i)+11]
            if not (router_id <= 64000 or router_id >= 1):
                return None

            
            if not (input_packet[(20*i)+12] == 0 and input_packet[(20*i)+13] == 0 and input_packet[(20*i)+14] == 0 and input_packet[(20*i)+15] == 0):
                return None

   
            
            if not (input_packet[(20*i)+16] == 0 and input_packet[(20*i)+17] == 0 and input_packet[(20*i)+18] == 0 and input_packet[(20*i)+19] == 0):
                return None

                                        
            metric = (input_packet[(20*i)+20] << 24) + (input_packet[(20*i)+21] << 16) + (input_packet[(20*i)+22] << 8) + input_packet[(20*i)+23]
            if metric > 0:
                if metric > 16: 
                    metric = 16
            rip_entries.append([router_id, metric])

        
        return (sender_router_id, rip_entries)
        


    
    except: 
        return None


def send_packet(packet, sending_socket, outputs):
    for i in outputs:
        sending_socket.sendto(packet, ("127.0.0.1", i[0]))



def print_routing_table(routing_table):
    print("--------------------------------Routing Table------------------------------")
    print("  Router ID  |   Next Hop   |    Cost    |   Timeout  |    Garbage Time")
    for i in routing_table.keys():
        router_id = i
        next_hop = routing_table[i][0]
        cost = routing_table[i][1]
        timeout = time.perf_counter() - routing_table[i][2]
        garbage_time = time.perf_counter() - routing_table[i][3]
        flag = routing_table[i][4]

        if flag:
            print("{:^12} | {:^12} | {:^10} | {:^10.2f} | {:^15.2f}".format(router_id, next_hop, cost, 0, garbage_time))
        else: 
            print("{:^12} | {:^12} | {:^10} | {:^10.2f} | {:^15.2f}".format(router_id, next_hop, cost, timeout, 0))

    print("---------------------------------------------------------------------------")


def main_loop(sockets, routing_table, router_id, outputs, timers):

    table = routing_table.copy()
    print_routing_table(table)
    while True:
        
        readable, writable, exceptional = select.select(sockets, [], sockets, 0.5)
        for current_socket in readable:
            current_packet = current_socket.recvfrom(1024)[0]
            result = parse_packet(current_packet)
            if result is not None:
                sender_router_id = result[0]
                rip_entries = result[1]
                table = update_routing_table(sender_router_id, table, rip_entries, outputs, sockets, router_id)
                print_routing_table(table)
        packet = create_packet(router_id, table)

        if time.perf_counter() - table[router_id][2] >= (random.uniform(0.8, 1.2) * timers[0]):
            
            send_packet(packet, sockets[0], outputs)
            table[router_id][2] = time.perf_counter()
        
        garbage_values = []

        for entry in table.keys():
            if entry != router_id:
                if (time.perf_counter() - table[entry][2] >= timers[1] or table[entry][1] >= 16) and not table[entry][4]:
                    table[entry][4] = True
                    table[entry][3] = time.perf_counter()
                    table[entry][1] = 16
                    send_packet(packet, sockets[0], outputs) #Triggered update
                if time.perf_counter() - table[entry][3] >= timers[2] and table[entry][4]:
                    send_packet(packet, sockets[0], outputs)
                    if table[entry][1] >= 16:
                        garbage_values.append(entry)
                    
        for garbage in garbage_values:
            table.pop(garbage)
        if len(garbage_values) > 0:
            print_routing_table(table)

def main():
    if len(sys.argv) > 2:
        print("This program only accepts 1 argument: The file name")
    elif len(sys.argv) == 1:
        print("This program requires the file name as an argument")
    else:
        file_name = sys.argv[1]
        router_id, input_ports, outputs, timers = file_parse(file_name)
        if timers == None:
            timers = [5, 30, 20]
        sockets = socket_bind(input_ports)
        routing_table = dict()
        routing_table[router_id] = [router_id, 0, time.perf_counter(), time.perf_counter(), False]

        main_loop(sockets, routing_table, router_id, outputs, timers)



main()