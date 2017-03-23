
# developed by Gabi Zapodeanu, TSA, GSS, Cisco Systems


# !/usr/bin/env python3


import requests
import json
import time
import base64
import requests.packages.urllib3

from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth  # for Basic Auth

# import all account info from xConnect_init.py file. Update the file with lab account info

from xConnect_init import SPARK_URL, SPARK_AUTH, ROOM_NAME, IT_ENG_EMAIL
from xConnect_init import EM_URL, EM_USER, EM_PASSW
from xConnect_init import PI_URL, PI_USER, PI_PASSW, WLAN_DEPLOY, WLAN_DISABLE, WIFI_SSID
from xConnect_init import CMX_URL, CMX_USER, CMX_PASSW

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # Disable insecure https warnings

PI_AUTH = HTTPBasicAuth(PI_USER, PI_PASSW)

CMX_AUTH = HTTPBasicAuth(CMX_USER, CMX_PASSW)


def pprint(json_data):
    """
    Pretty print JSON formatted data
    :param json_data:
    :return:
    """

    print(json.dumps(json_data, indent=4, separators=(' , ', ' : ')))


def get_EM_service_ticket():
    """
    Action:     create an authorization ticket required to access APIC-EM
    Call to:    APIC-EM - /ticket
    Input:      global variables: APIC-EM IP address, password and username
    Output:     ticket, if created
    """

    payload = {'username': EM_USER, 'password': EM_PASSW}
    url = EM_URL + '/ticket'
    header = {'content-type': 'application/json'}
    ticket_response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    if ticket_response is None:
        print('No data returned!')
    else:
        ticket_json = ticket_response.json()
        ticket = ticket_json['response']['serviceTicket']
        print('APIC-EM ticket: ', ticket)
        return ticket


def create_spark_room(room_name):
    """
    Action:     this function will create a Spark room with the title room name
    Call to:    Spark - /rooms
    Input:      the room name, global variable - Spark auth access token
    Output:     the Spark room Id
    """

    payload = {'title': room_name}
    url = SPARK_URL + '/rooms'
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    room_response = requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    room_json = room_response.json()
    room_number = room_json['id']
    print('Created Room with the name :  ', ROOM_NAME)
    return room_number


def find_spark_room_id(room_name):
    """
    Action:     this function will find the Spark room id based on the room name
    Call to:    Spark - /rooms
    Input:      the room name, global variable - Spark auth access token
    Output:     the Spark room Id
    """

    payload = {'title': room_name}
    room_number = None
    url = SPARK_URL + '/rooms'
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    room_response = requests.get(url, data=json.dumps(payload), headers=header, verify=False)
    room_list_json = room_response.json()
    room_list = room_list_json['items']
    for rooms in room_list:
        if rooms['title'] == room_name:
            room_number = rooms['id']
    return room_number


def add_spark_room_membership(room_Id, email_invite):
    """
    Action:     this function will add membership to the Spark room with the room Id
    Call to:    Spark - /memberships
    Input:      room Id and email address to invite, global variable - Spark auth access token
    Output:     none
    """

    payload = {'roomId': room_Id, 'personEmail': email_invite, 'isModerator': 'true'}
    url = SPARK_URL + '/memberships'
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    print("Invitation sent to :  ", email_invite)


def last_spark_room_message(room_Id):
    """
    Action:     this function will find the last message from the Spark room with the room Id
    Call to:    Spark - /messages
    Input:      room Id, global variable - Spark auth access token
    Output:     last room message and person email
    """

    url = SPARK_URL + '/messages?roomId=' + room_Id
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    response = requests.get(url, headers=header, verify=False)
    list_messages_json = response.json()
    list_messages = list_messages_json['items']
    last_message = list_messages[0]['text']
    last_person_email = list_messages[0]['personEmail']
    print('Last room message :  ', last_message)
    print('Last Person Email', last_person_email)
    return [last_message, last_person_email]


def post_spark_room_message(room_id, message):
    """
    Action:     this function will post a message to the Spark room with the room Id
    Call to:    Spark - /messages
    Input:      room Id and the message, global variable - Spark auth access token
    Output:     none
    """

    payload = {'roomId': room_id, 'text': message}
    url = SPARK_URL + '/messages'
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    requests.post(url, data=json.dumps(payload), headers=header, verify=False)
    print("Message posted :  ", message)


def delete_spark_room(room_id):
    """
    Action:     this function will delete the Spark room with the room Id
    Call to:    Spark - /rooms
    Input:      room Id, global variable - Spark auth access token
    Output:     none
    """

    url = SPARK_URL + '/rooms/' + room_id
    header = {'content-type': 'application/json', 'authorization': SPARK_AUTH}
    requests.delete(url, headers=header, verify=False)
    print("Deleted Spark Room :  ", ROOM_NAME)


def check_cmx_client(username):
    """
    Action:     this function will find out the WLC controller IP address for a client authenticated with the username
    Call to:    CMX - /api/location/v2/clients/?username={username}
    Input:      username, global variable - CMX_AUTH - HTTP Basic Auth
    Output:     WLC controller IP address
    """

    url = CMX_URL + 'api/location/v2/clients/?username=' + username
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, headers=header, auth=CMX_AUTH, verify=False)
    client_json = response.json()
    if not client_json:
        controller_ip_address = None
    else:
        controller_ip_address = client_json[0]['detectingControllers']
    return controller_ip_address


def get_controller_hostname(ip_address, ticket):
    """
    Action:     find out the hostname of the WLC controller
    Call to:    APIC-EM - network-device/ip-address/{ipAddress}
    Input:      WLC Controller IP address, APIC-EM ticket
    Output:     wireless controller hostname
    """

    url = EM_URL + '/network-device/ip-address/' + ip_address
    header = {'accept': 'application/json', 'X-Auth-Token': ticket}
    device_response = requests.get(url, headers=header, verify=False)
    device_json = device_response.json()
    hostname = device_json['response']['hostname']
    return hostname


def get_PI_device_Id(device_name):
    """
    Action:     find out the PI device Id using the device hostname
    Call to:    Prime Infrastructure - /webacs/api/v1/data/Devices, filtered using the Device Hostname
    Input:      device hostname, global variable - PI_Auth, HTTP basic auth
    Output:     PI device Id
    """

    url = PI_URL + '/webacs/api/v1/data/Devices?deviceName=' + device_name
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, headers=header, verify=False, auth=PI_AUTH)
    device_id_json = response.json()
    device_id = device_id_json['queryResponse']['entityId'][0]['$']
    return device_id


def deploy_PI_wlan_template(controller_name, template_name):
    """
    Action:     deploy a WLAN template to a wireless controller through job
    Call to:    Prime Infrastructure - /webacs/api/v1/op/wlanProvisioning/deployTemplate
    Input:      WLC Prime Infrastructure id, WLAN template name, global variable - PI_Auth, HTTP basic auth
    Output:     job number
    """

    param = {
        "deployWlanTemplateDTO": {
            "controllerName": controller_name,
            "templateName": template_name
        }
    }
    print(param)
    url = PI_URL + '/webacs/api/v1/op/wlanProvisioning/deployTemplate'
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.put(url, json.dumps(param), headers=header, verify=False, auth=PI_AUTH)
    job_json = response.json()
    job_name = job_json['mgmtResponse']['jobInformation']['jobName']
    print('job name: ', job_name)
    return job_name


def get_PI_job_status(job_name):
    """
    Action:     get PI job status
    Call to:    PI - /webacs/api/v1/data/JobSummary, filtered by the job name, will provide the job id
                A second call to /webacs/api/v1/data/JobSummary using the job id
    Input:      Prime Infrastructure job name, global variable - PI_Auth, HTTP basic auth
    Output:     job status
    """

    #  find out the PI job id using the job name

    url = PI_URL + '/webacs/api/v1/data/JobSummary?jobName=' + job_name
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, headers=header, verify=False, auth=PI_AUTH)
    job_id_json = response.json()
    job_id = job_id_json['queryResponse']['entityId'][0]['$']

    #  find out the job status using the job id

    url = PI_URL + '/webacs/api/v1/data/JobSummary/' + job_id
    header = {'content-type': 'application/json', 'accept': 'application/json'}
    response = requests.get(url, headers=header, verify=False, auth=PI_AUTH)
    job_status_json = response.json()
    #  print(json.dumps(job_status_json, indent=4, separators=(' , ', ' : ')))    # pretty print
    job_status = job_status_json['queryResponse']['entity'][0]['jobSummaryDTO']['resultStatus']
    return job_status


def main():
    """
    A small number of APIs requests will create a new application to enable on-demand Wi-Fi guest networks.

    We will interact with Spark’s easy to use APIs to read room messages, and with CMX to locate users of our
    Application in the Enterprise network.
    APIC-EM device inventory accessed through APIs will identify the Wireless LAN Controllers.
    The Prime Infrastructure WLAN configuration APIs will ensure configuration will only be deployed
    to the user’s physical location.

    Simple script changes could create Hotspot networks based on schedule, incident response or social events.
    """

    # verify if Spark Room exists, if not create Spark Room, and add membership (optional)

    spark_room_id = find_spark_room_id(ROOM_NAME)
    if spark_room_id is None:
        spark_room_id = create_spark_room(ROOM_NAME)
        # add_spark_room_membership(spark_room_id, IT_ENG_EMAIL)
        print('- ', ROOM_NAME, ' -  Spark room created')
        post_spark_room_message(spark_room_id, 'To start HotSpot {Spark:Connect} enter  :  /E')
        post_spark_room_message(spark_room_id, 'Ready for input!')
        print('Instructions posted in the room')
    else:
        print('- ', ROOM_NAME, ' -  Existing Spark room found')
        post_spark_room_message(spark_room_id, 'To start HotSpot {Spark:Connect} enter  :  /E')
        post_spark_room_message(spark_room_id, 'Ready for input!')
    print('- ', ROOM_NAME, ' -  Spark room id: ', spark_room_id)

    # check for messages to identify the last message posted and the user's email who posted the message

    last_message = last_spark_room_message(spark_room_id)[0]

    while last_message == 'Ready for input!':
        time.sleep(5)
        last_message = last_spark_room_message(spark_room_id)[0]
        if last_message == '/E':
            last_person_email = last_spark_room_message(spark_room_id)[1]
            post_spark_room_message(spark_room_id, 'How long time do you need the HotSpot for? (in minutes) : ')
            time.sleep(10)
            if last_spark_room_message(spark_room_id)[0] == 'How long time do you need the HotSpot for? (in minutes) : ':
                timer = 30 * 60
            else:
                timer = int(last_spark_room_message(spark_room_id)[0]) * 60
        elif last_message != 'Ready for input!':
            post_spark_room_message(spark_room_id, 'I do not understand you')
            post_spark_room_message(spark_room_id, 'To start HotSpot {Spark:Connect} enter  :  /E')
            post_spark_room_message(spark_room_id, 'Ready for input!')
            last_message = 'Ready for input!'

    # CMX will use the email address to provide the wireless controller IP address
    # managing the AP the user is connected to.

    controller_IP_address = check_cmx_client(last_person_email)

    # if controller IP address not found, ask user to connect to WiFi

    if controller_IP_address is None:
        post_spark_room_message(spark_room_id, 'You are not connected to WiFi, please connect and try again!')
        controller_IP_address = '172.16.11.27'
    else:
        print('We found a WLC at your site, IP address: ', controller_IP_address)

    # create an APIC EM auth ticket

    EM_ticket = get_EM_service_ticket()

    # find the wireless controller hostname based on the management IP address provided by CMX

    controller_hostname = get_controller_hostname(controller_IP_address, EM_ticket)
    print('We found a WLC at your site, hostname: ', controller_hostname)

    # find the controller PI device Id using the WLC hostname

    PI_controller_device_id = get_PI_device_Id(controller_hostname)
    print('Controller PI device Id :  ', PI_controller_device_id)

    # deploy WLAN template to controller to enable the SparkConnect SSID, and get job status

    job_name_WLAN = deploy_PI_wlan_template(controller_hostname, WLAN_DEPLOY)
    time.sleep(20)    # required to give time to PI to deploy the template
    job_status = get_PI_job_status(job_name_WLAN)

    # post status update in Spark, an emoji, and the length of time the HotSpot network will be available

    post_spark_room_message(spark_room_id, 'HotSpot {Spark:Connect} ' + job_status)
    post_spark_room_message(spark_room_id, 'The HotSpot will be available for ' + str(int(timer / 60)) + ' minutes')
    post_spark_room_message(spark_room_id,  '  ' + '\U0001F44D')

    # timer required to maintain the HotSpot enabled, user provided

    time.sleep(timer)

    # disable WLAN via WLAN template, to be deployed to controller

    job_disable_WLAN = deploy_PI_wlan_template(controller_hostname, WLAN_DISABLE)

    post_spark_room_message(spark_room_id, 'HotSpot {Spark:Connect} has been disabled')
    post_spark_room_message(spark_room_id, 'Thank you for using our service')

    # delete Room - optional step, not required

    if input('Do you want to delete the {Spark:Connect} Spark Room ?  (y/n)  ') == 'y':
        delete_spark_room(spark_room_id)


if __name__ == '__main__':
    main()
