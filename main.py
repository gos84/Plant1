import machine
import ssd1306
from time import sleep_ms, sleep, time
import onewire
import ds18x20
import BME280
from umqttsimple import MQTTClient
import ubinascii
#import micropython
import network

#We start by setting up the OLED to be able to print information during startup

#OLED
i2cOLED = machine.I2C(-1, machine.Pin(22), machine.Pin(21), freq=500000)
display = ssd1306.SSD1306_I2C(128, 64, i2cOLED)
display.fill(0)
display.show()

#WIFI
def do_connect():
    import network
    sta_if = network.WLAN(network.STA_IF)       # Put modem on Station mode
    if not sta_if.isconnected():                # Check if already connected
        print('connecting to network...')
        display.fill(0)
        display.text("Connecting", 0, 0, 1)
        display.text("to WiFi...", 0, 10, 1)
        display.show()
        sta_if.active(True)                     # Activate network interface
        sta_if.connect('SSID', 'PASSWORD')     # Your WiFi Credential
        # Check if it is connected otherwise wait
        while not sta_if.isconnected():
            pass
        # Print the IP assigned by router
        print('network config:', sta_if.ifconfig())
        display.text("Connected!", 0, 20, 1)
        #IPaddr =  sta_if.ifconfig()[0])
        #display.text("IP: " +IPaddr, 0, 30, 1)
        display.show()

def http_get(url = 'http://detectportal.firefox.com/'):
    import socket                           # Used by HTML get request
    import time                             # Used for delay
    _, _, host, path = url.split('/', 3)    # Separate URL request
    addr = socket.getaddrinfo(host, 80)[0][-1]  # Get IP address of host
    s = socket.socket()                     # Initialise the socket
    s.connect(addr)                         # Try connecting to host address
    # Send HTTP request to the host with specific path
    s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))
    time.sleep(1)                           # Sleep for a second
    rec_bytes = s.recv(10000)               # Receve response
    print(rec_bytes)                        # Print the response
    s.close()                               # Close connection

do_connect() # WiFi Connection
http_get() # HTTP request


#MQTT declarations
mqtt_server = '192.168.1.91' # change to your MQTT-broker IP-adress
client_id = ubinascii.hexlify(machine.unique_id())
topic_pub_temp1 = b'sensors/plant1/soilhum'
topic_pub_temp2 = b'sensors/plant1/soiltemp'
topic_pub_temp3 = b'sensors/plant1/airtemp'
topic_pub_temp4 = b'sensors/plant1/airhum'
topic_pub_temp5 = b'sensors/plant1/airpres'
last_message = 0
message_interval = 1

def connect_mqtt():
  global client_id, mqtt_server
  #client = MQTTClient(client_id, mqtt_server)
  client = MQTTClient(client_id, mqtt_server, user='USERNAME', password='PASSWORD') # Change to your username and password
  client.connect()
  print('Connected to %s MQTT broker' % (mqtt_server))
  return client

def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  machine.reset()

# Connect to MQTT Broker
try:
  display.fill(0)
  display.text("Connecting to", 0, 0, 1)
  display.text("MQTT Broker...", 0, 10, 1)
  display.show()
  client = connect_mqtt()
except OSError as e:
  display.fill(0)
  display.text("Failed to connect", 0, 0, 1)
  display.text("Restarting...", 0, 10, 1)
  display.show()
  restart_and_reconnect()

display.fill(0)
display.text("Connected", 0, 0, 1)
display.show()

#Sensor declarations

#BME280
i2cBME = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=10000)


#Soil moisture sensor
adc = machine.ADC(machine.Pin(36))
adc.atten(machine.ADC.ATTN_11DB) # change attenuation to full range 3.3V
wet = 1080 # calibrate (lowest value with sensor in a glass of water)
dry = 2400 # kalibrera (highest value with sensor in air)
def scale_value(value, in_min, out_max, out_min):
  scaled_value = ((value - in_min) * 100) / (out_max - out_min) # set value the 0-100 %
  return scaled_value

#Soil temperature, ds18x20
ds_pin = machine.Pin(4)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
roms = ds_sensor.scan() #if more than 1 sensor is connected
#print('Found DS devices: ', roms)

#Start loop
while True:
    #check wifi connection
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        do_connect()
        sleep(1)
        try:
            display.fill(0)
            display.text("Connecting to", 0, 0, 1)
            display.text("MQTT Broker...", 0, 10, 1)
            display.show()
            client = connect_mqtt()
        except OSError as e:
            display.fill(0)
            display.text("Failed to connect", 0, 0, 1)
            display.text("Restarting...", 0, 10, 1)
            display.show()
            restart_and_reconnect()

    #jordfuktighet
    tmp = 0
    for y in range(0, 10): # average value of 10 readings during 1s
        tmp = tmp + adc.read()
        sleep_ms(100)
    moisture=tmp/10
    if moisture > dry: # sometimes the value would go outside the calibrated range
        moisture = dry
    if moisture < wet: # sometimes the value would go outside the calibrated range
        moisture = wet
    print('Soil Moisture: ', str(round(scale_value(moisture, dry, wet, dry))))
    ehum = str(round(scale_value(moisture, dry, wet, dry)))

#jordtemperatur
    ds_sensor.convert_temp()
    sleep_ms(750)
    for rom in roms:
        #print(rom)
        print('Soil Temperature: ', ("{0:.1f}").format(ds_sensor.read_temp(rom)))
        etemp = ("{0:.1f}").format(ds_sensor.read_temp(rom)) #only one sensor

#BME280
    bme = BME280.BME280(i2c=i2cBME)
    temp = ("{0:.1f}").format(bme.temperature)
    hum = ("{0:.1f}").format(bme.humidity)
    pres = ("{0:.1f}").format(bme.pressure)
    print('Air Temperature: ', temp)
    print('Air Humidity: ', hum)
    print('Air Pressure: ', pres)

#OLED
    display.fill(0)
    display.text("Jordfukt: " + ehum + " %", 0, 0, 1)
    display.text("Jordtemp: " + etemp + " C", 0, 10, 1)
    display.text("Lufttemp: " + temp + " C", 0, 30, 1)
    display.text("Luftfukt: " + hum + " %", 0, 40, 1)
    display.text("Ltryck: " + pres + " hPa", 0, 50, 1)
    display.show()

#MQTT publish
    if (time() - last_message) > message_interval:
        client.publish(topic_pub_temp1, ehum)
        client.publish(topic_pub_temp2, etemp)
        client.publish(topic_pub_temp3, temp)
        client.publish(topic_pub_temp4, hum)
        client.publish(topic_pub_temp5, pres)
        last_message = time()

#wait
    sleep(60)
