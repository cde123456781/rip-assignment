import sys
import os
import socket

def file_parse(file_name: str):
    """Parses the file provided to extract router_id, input_ports, and outputs"""
    router_id = None
    input_ports = []
    outputs = []
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
            if (! router_id.isnumeric()):
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
                           
        line = file.readline()


    file.close()

    if router_id is not None and input_ports and outputs:
        return (router_id, input_ports, outputs)

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




def main():
    if len(sys.argv) > 2:
        print("This program only accepts 1 argument: The file name")
    elif len(sys.argv) == 1:
        print("This program requires the file name as an argument")
    else:
        file_name = sys.argv[1]
        router_id, input_ports, outputs = file_parse(file_name)

    sockets = socket_bind(input_ports)





main()