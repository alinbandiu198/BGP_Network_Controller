from nornir import InitNornir  # importing the nornir  automation framework
from nornir_utils.plugins.functions import print_result , print_title # importing the print_result function 
from nornir_napalm.plugins.tasks import napalm_get # importing the napalm get functions 
from nornir_netmiko.tasks import netmiko_send_config , netmiko_send_command# importing the netmiko functions 
from nornir_jinja2.plugins.tasks import template_file # importing the jinja2 template file for creating configs
from nornir_napalm.plugins.tasks import napalm_configure
from nornir.core.filter import F
from nornir.core.exceptions import NornirExecutionError
import json 
import yaml 
import requests
from requests import ConnectionError 
from termcolor import colored
import schedule
from nornir.core.filter import F
import threading
import os 
import time
import subprocess
from napalm import get_network_driver
from netmiko import ConnectHandler
requests.packages.urllib3.disable_warnings()


with open ("hosts.yaml", "r") as f: 
    Devices = yaml.load(f, Loader=yaml.FullLoader)

nornir = InitNornir(
        config_file="config.yaml", dry_run=True, core={"raise_on_error": True})

headers = {'Content-Type': 'application/yang-data+json', #Defining the headers 
           'Accept': 'application/yang-data+json'}


def Automate_Interface_Description():
    driver = get_network_driver('ios')
    for x in range (1,6):
        iou = driver(Devices['R'+str(x)]['hostname'], 'alin', 'cisco')
        iou.open()
        
        lldp_neigh = iou.get_lldp_neighbors()
        for key in lldp_neigh:
            nr = key + ' R' + str(x)
            for y in range (1,6): 
                if x ==y:
                    #print(key)
                    #print(lldp_neigh[key])
                    net_connect = ConnectHandler(device_type='cisco_ios', host='1.1.1.'+str(x), username='alin',password='cisco',secret='cisco')
                    net_connect.enable()
                    host= lldp_neigh[key][0]['hostname']
                    port = lldp_neigh[key][0]['port']
                    cmds = [f'interface {key}', f'description Connecting to device {host}' + f' on remote port {port}']
                    cfg = net_connect.send_config_set(cmds)
                    print(colored("Pushing the following config to R" +str(x) , 'yellow') + '\n' + cfg )

#Automate_Interface_Description()


def Underlay_Monitor():
    
    err_list  = []
    ospf_lst = []
    error_handling = []
    
    try:
        #threading.Timer(5.0,Underlay_Monitor).start()
        core_routers = nornir.filter(F(groups__contains="core_group"))
    #print(core_routers.inventory.hosts.keys())
        results = core_routers.run(netmiko_send_command, command_string="show ip ospf neigh" ,use_textfsm=True)
        R = 0
        
        for key in results.keys():
            R = R +1
            response = results[key].result
        #print(type(response[0]))clear
        #print(len(response))
            print(colored('Checking OSPF on Router ' + str(R),'green') )
            nr_of_neigh = len(response)
            counter_neigh = 0
            for x in range(0,nr_of_neigh):
                counter_neigh = counter_neigh +1 
                OSPF_STATE = response[x].get('state')
                if nr_of_neigh != 3:
                    missing_neigh = 3 - nr_of_neigh
                    one = 'Router'+str(R) + ' is missing ' + str(missing_neigh) + ' Neighbor'
                    err_list.append(one)
                    break
                elif OSPF_STATE != 'FULL/  -':
                    two = 'ALERT!' + 'Router' + str(R) + ' is not in the FULL State with ' +response[x]['neighbor_id'] +' The state is ' + OSPF_STATE
                    err_list.append(two)
                    if OSPF_STATE == 'FULL/BDR':
                        three = 'Probabily there is an ospf network type missmatch....'
                        err_list.append(three)
                    if OSPF_STATE == 'EXSTART/  -':
                        four = 'Probabily there is an ospf mtu missmatch....'
                        err_list.append(four)
                    
                    if OSPF_STATE == 'EXCHANGE/  -':
                        five = 'Probabily there is an ospf mtu missmatch....'
                        err_list.append(five)




             
        if not err_list:
            ospf_lst.append('All Routers are running OSPF , everything is working corectly!')
            
        elif not ospf_lst:
            print(err_list)
            
        nornir.close_connections()
            
        


    except:  
        NornirExecutionError
        #error_handling.append('Oops!  , some device failed...')
        for ip in range(1,6):
            target = '1.1.1.'+str(ip)
            response =os.system("ping -c1 "+ target+ "> /dev/null")
            if response != 0: 
                error_handling.append('Critical!!! Device with ip  '+ target + ' does not respond')
                error_handling.append('Device management is down , fix this issue...')       
                
    return ospf_lst , err_list ,error_handling    


#Underlay_Monitor()
def BGP_Configuration():
    rezultat = []
    try:
        def config(task):
            r = task.run(task=template_file,
                        name="BGP configuration",
                        template="bgp_peerings.j2",
                        path=f"Jinja2/{task.host['protocol']}")

                    
            

            task.host["config"] =r.result.splitlines()

            
            task.run(task=netmiko_send_config,
                    name = "BGP peerings  configuration",
                    config_commands=task.host["config"])

        nornir.data.dry_run = False
        print_title("Performing some cool network automation !!!")

            
        result = nornir.run(task=config)
        print_result(result)
        
        rezultat.append('BGP configartion was succesful')
        return rezultat
    except:  
        NornirExecutionError
        rezultat.append('Cannot execute this , some device failed...')
        for ip in range(1,6):
            target = '1.1.1.'+str(ip)
            response =os.system("ping -c1 "+ target+ "> /dev/null")
            if response != 0: 
                rezultat.append('Failed '+ target)
                rezultat.append('Fix connection to this devices and try again ')
        return rezultat


#BGP_Configuration()
def Monitor_BGP_Peerings_Core():
    alert = []
    up_peers = []
    core_routers = nornir.filter(F(id="iou1"))
    result = core_routers.run(netmiko_send_command,command_string="show bgp summ" , use_textfsm=True)
    rr_routers = nornir.filter(F(role="RR"))
    rr_result = rr_routers.run(netmiko_send_command,command_string="show ip bgp summ", use_textfsm=True)
    neigh = []
    '''
    for key in rr_result.keys():
        response = rr_result[key].result
        
        for each in response:
            if each['router_id']=='1.1.1.5':
                print(each) 
                neigh.append('csr5')
            elif each['router_id']=='1.1.1.6':
                print(each)
                neigh.append('csr6')

    print(neigh)
    if neigh.count('csr5')!=5:
        alert.append(' Device with ID 5 (CSR5) is missing ' + str(5-neigh.count('csr5')) + ' neighbors')
    if neigh.count('csr6')!=5:
        alert.append(' Device with ID 6 (CSR6) is missing ' + str(5-neigh.count('csr5')) + ' neighbors')

    ''' 
     
               
              
    for key in result.keys():
        
        response = result[key].result
        new = response.strip()
    
        if new == '% BGP not active':
            print('ues')
            no_active = 'BGP is not active'
            alert.append(no_active)
            alert.append('Configuring BGP now...')
            time.sleep(5)
            
            BGP_Configuration()
            alert.append('BGP Configured')
            return alert
        else:
            for key in rr_result.keys():
                response = rr_result[key].result
        
                for each in response:
                    if each['router_id']=='1.1.1.5':
                        print(each) 
                        neigh.append('csr5')
                    elif each['router_id']=='1.1.1.6':
                        print(each)
                        neigh.append('csr6')

            print(neigh)
            if neigh.count('csr5')!=5:
                up_peers.append(' Device with ID 5 (CSR5) is missing ' + str(5-neigh.count('csr5')) + ' neighbors')
            if neigh.count('csr6')!=5:
                up_peers.append(' Device with ID 6 (CSR6) is missing ' + str(5-neigh.count('csr5')) + ' neighbors')

            
            #print(colored('*if no alerts are diplayed it means that all peers are up !','blue'))           
            for ip in range (5,7):  # Selecting the Core devices based on their IP address 

                url_CSR_RR = "https://"+ str(Devices['R'+str(ip)]['hostname'])+":443/restconf/data/Cisco-IOS-XE-bgp-oper:bgp-state-data/neighbors/neighbor" # Connecting using restconf to devices

                try:
                    response = requests.get(url_CSR_RR, auth = (Devices['R'+str(ip)]['username'],Devices['R'+str(ip)]['password']),headers=headers,verify=False)#storing the response  of Get operation
                except requests.ConnectionError:
                    err = 'Unable to connect to address https://1.1.1.'+str(ip)
                    alert.append(err)
                    print(alert)
                if response.status_code != 200:# checking the response codes 
                    alert.append('Login request failed. Status code is {}'.format(response.status_code))
                else:        
                    up_peers.append('Connecting to Router'+str(ip) + '.....Status code is '+str(response.status_code) + ' OK!')

                bgp_data =response.json() # Storing the respinse and display it in a json data format 
         
                if ip == 5: #Selecting the first device 
                    for index in bgp_data['Cisco-IOS-XE-bgp-oper:neighbor']: #checking the peering status 
                        CSR5_peers = index['neighbor-id']
                        Csr5_state = index['connection']['state']
                        notif_sent = index['bgp-neighbor-counters']['sent']['notifications']
                        notif_rec  = index['bgp-neighbor-counters']['received']['notifications']
                        connection_fail = index['connection']['reset-reason']
                        report = 'Router CSR5 is peering with ' +CSR5_peers + ' and the state is '+ Csr5_state # Checking to see if the peers are UP !! 
                        
                        if not 'established' in report: # If not an allert will pop up 
                            alert1='CSR5 ALERT!: '+' peer ' +  CSR5_peers + ' is DOWN and the status code is ' + Csr5_state + '\n' + 'the reason of failure is '+ connection_fail 
                            alert.append(alert1)
                            

                        else:
                            peers = 'CSR5 is peering with ' + CSR5_peers + ' for about ' + index['up-time'] + ' h/m/s'
                            up_peers.append(peers)
                        if notif_sent != 0 : 
                            notif1 = 'This device has sent ' + str(notif_sent) + ' notifications , please investigate furhter...'
                            alert.append(notif1)
                        elif notif_rec != 0: 
                            notif2 = 'This device has received ' + str(notif_rec) +' notifications , please investigate furhter'
                            alert.append(notif2)
                            
                if ip == 6: #doing the same thing for our second core device 
                    for index in bgp_data['Cisco-IOS-XE-bgp-oper:neighbor']:
                        CSR6_peers = index['neighbor-id']
                        Csr6_state = index['connection']['state']
                        notif_sent = index['bgp-neighbor-counters']['sent']['notifications']
                        notif_rec  = index['bgp-neighbor-counters']['received']['notifications']
                        connection_fail = index['connection']['reset-reason']
                        #peers_csr5 = bgp_data['Cisco-IOS-XE-bgp-oper:neighbor'][index]['neighbor-id']               
                        report = 'Router CSR6 is peering with ' +CSR6_peers + ' and the state is '+ Csr6_state
                        if not 'established' in report: 
                            alert2 = 'CSR6 ALERT!: '+' peer ' +  CSR6_peers + ' is DOWN and the status code is ' + Csr6_state + '\n' + 'the reason of failure is '+ connection_fail 
                            alert.append(alert2)
                            
                        else:
                            peers2 = 'CSR6 is peering with ' + CSR6_peers + ' for about ' + index['up-time'] + ' h/m/s'
                            up_peers.append(peers2)
                        if notif_sent != 0 : 
                            notif3 = 'This device has sent ' + str(notif_sent) + ' notifications , please investigate furhter...'
                            alert.append(notif3)
                        elif notif_rec != 0: 
                            notif4  = 'This device has received ' + str(notif_rec) +' notifications , please investigate furhter' 
                            alert.append(notif4)
    
    if not alert:
        return up_peers
    else:
        return alert
    


         
#Monitor_BGP_Peerings_Core()

def Monitor_eBGP():
    info = []
    alert = []
    print('#######Checking the status of eBGP peers in Core network......########')
    print('#######eBGP routers in AS100 are Router Iou1 and Router Iou4:#########')
    print('*******If eBGP peers are down an alert message should pop up .....******')
    status = 'IOU1 Core Router eBGP edge report: '
    alert.append(status)
    info.append(status)
    iou1 = nornir.filter(id= "iou1")
    results = iou1.run(netmiko_send_command, command_string="show ip bgp summary" , use_textfsm=True)
    for key in results.keys():
        response = results[key].result # saving the result as a variable 
        for info in range (0,len(response)):
            if response[info]['neigh_as'] == str(Devices['R1']['data']['remote-asn']):
                print('checking the eBGP peering...')
                if response[info]['state_pfxrcd'] != '0':
                    
                    alerta = 'ALERT!'+ ' eBGP session have problems the state is ' + response[info]['state_pfxrcd']
                    alert.append(alerta)
                    def Fixing_EBGP():
                        print('Trying to resolve the eBGP peering issue ...')
                        if response[info]['state_pfxrcd'] == "Idle": 
                            print('Performing a ping to eBGP peer address...')
                            ping = iou1.run(netmiko_send_command, command_string="ping " + Devices['R1']['data']['epeers'][0])
                            for key in ping.keys():
                                resp = ping[key].result
                                if not "!!!" in resp: 
                                    print(colored("*******************************",'green'))
                                    print(colored('ALERT!: ','red') + 'I cannot ping eBGP peer , checking if a route exists..')
                                    route = iou1.run(netmiko_send_command, command_string="sh ip route " + Devices['R1']['data']['epeers'][0])
                                    for key in route.keys():
                                        resp = route[key].result
                                        if "% Subnet not in table" in resp:
                                            print('A route does not exists , trying to fix that...')
                                            config_cmd = ['conf t', 'ip route 1.1.1.7 255.255.255.255 Ethernet1/0 81.1.1.2']
                                            route_send = iou1.run(netmiko_send_config,config_commands=config_cmd)
                                            print('Route added ! ')
                    
                    print('Will you allow me to fix the problem?')
                    user = input()
                    if user == 'yes': 
                        Fixing_EBGP()
                    else: 
                        print('Ok , go to CLI then')

                                        


                else:
                    ok = 'The eBGP session with Customer 1 is up and healthy!'
                    info.append(ok)
    print(colored('Checking IOU4 eBGP Router...','yellow'))
    iou4 = nornir.filter(id= "iou4")
    
    results = iou4.run(netmiko_send_command, command_string="show ip bgp summary" , use_textfsm=True)
    for key in results.keys():
        response = results[key].result # saving the result as a variable 
        for info in range (0,len(response)):
            if response[info]['neigh_as'] == str(Devices['R4']['data']['remote-asn']):
                print('checking the eBGP peering...')
                if response[info]['state_pfxrcd'] != '0':
                    
                    print(colored('ALERT!','red')+ ' eBGP session have problems the state is ' + response[info]['state_pfxrcd'])
                else:
                    print('The eBGP session with Customer 2 is up and healthy!')

    for rtr in range(7,9):
        url_CSR = "https://"+ str(Devices['R'+str(rtr)]['hostname'])+":443/restconf/data/Cisco-IOS-XE-bgp-oper:bgp-state-data/neighbors/neighbor" # Connecting using restconf to devices
        print(colored('Connecting to CSR'+str(rtr) + ' and checking BGP....Asking for permission....','blue'))

        response = requests.get(url_CSR, auth = (Devices['R'+str(rtr)]['username'],Devices['R'+str(rtr)]['password']),headers=headers,verify=False)#storing the response  of Get operation
        time.sleep(5) # Allowing 5 sec in order to detect any changes
        if response.status_code != 200:# checking the response codes 
            print('Login request failed. Status code is {}'.format(response.status_code))
        else:        
            print('Connecting to Router CSR'+str(rtr) + '.....Status code is '+str(response.status_code) + ' OK!')
        bgp_data =response.json() # Storing the respinse and display it in a json data format 
        for index in bgp_data['Cisco-IOS-XE-bgp-oper:neighbor']: #checking the peering status 
            CSR7_peers = index['neighbor-id']
            Csr7_state = index['connection']['state']
            report = 'Router CSR7 is peering with ' +CSR7_peers + ' and the state is '+ Csr7_state # Checking to see if the peers are UP !! 
                
            if not 'established' in report: # If not an allert will pop up 
                alert1 = print(colored('CSR7 ALERT!:','red')+' peer ' +  CSR7_peers + ' is DOWN and the status code is ' + Csr7_state)
            #alert.append(alert1)
            else:
                peers = print('CSR'+str(rtr) + ' is peering with ' + CSR7_peers + ' for about ' + index['up-time'] + ' h/m/s')
            #up_peers.append(peers)
                    

#Monitor_eBGP()

def Connectivity_Test():
    print("Conducting a full ping test....:")
    print("\n")

    device = []

    for i in range  (1,9):
        targets = "1.1.1." + str(i)
        try:
            core = nornir.filter(F(groups__contains="core_group"))
            results = core.run(netmiko_send_command, command_string="ping " + targets + " source loop0")
            out = results.keys()
            
            for key in out:
                #print(key)
                response = results[key].result

                if not "!!!" in response: 
                    print(colored("*******************************",'green'))
                    fail  = key + " cannot ping " + targets 
                    device.append(fail)
                    route = nornir.filter(id=Devices[key]['data']['id'])
                    table = route.run(netmiko_send_command,command_string="show ip route " + str(targets),use_textfsm=True)
                    for each in table.keys():
                        ruta = table[each].result
                        issue = key + ' device report ' + str(ruta)
                        device.append(issue)

 

                  
        except NornirExecutionError:
            alrt = 'Alert! I cannot connect to all devices.....'
            device.append(alrt)
    if not device:
        device.append('Connectivity test was succesfull')  
    return device
    

#Connectivity_Test()

