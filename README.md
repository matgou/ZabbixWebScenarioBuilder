# ZabbixWebScenarioBuilder v1.0

## Description

Website monitoring with zabbix is powerful, hit can check availability of website by perform httpcheck.

But the UI to build Web-Scenario in Zabbix-Frontend is not easy to use. So ZabbixWebScenarioBuilder will record http/https traffic and convert it to a Zabbix Webscenario.

## Install

### Init environment
To Init environment use virtualenv and pip by running the following command :
```
virtualenv venv
. venv/bin/activate
pip -r requirement
```

### Create config.ini

ZabbixWebScenarioBuilder use a file named `config.ini`. You must init this file from `config.ini.template` :
```
cp config.ini.template config.ini
vi config.ini
```

## Howto

### Step 1: Record HTTP traffic Scenario

This step will create a `/tmp/trace_httpoutput.dump` file containing all http/https request and response.

Start the captive proxy :
```
  venv/bin/mitmdump -p 3128 -w /tmp/trace_httpoutput.dump
```
Run chrome (while captive proxy running) and navigate on your application:
```
  chromium --proxy-server="127.0.0.1:3128" https://photos.kapable.info
```

#### On Chromium
Chrome can ask you to accept proxy certificate
![ValidateCert](https://github.com/matgou/zabbix_webscenario_builder/raw/main/documentation/chromium1.png)
![Step1](https://github.com/matgou/zabbix_webscenario_builder/raw/main/documentation/chromium2.png)
![Step2](https://github.com/matgou/zabbix_webscenario_builder/raw/main/documentation/chromium3.png)
![Step3](https://github.com/matgou/zabbix_webscenario_builder/raw/main/documentation/chromium4.png)

Finaly close navigator and captive proxy (Ctrl+C).

### Steap 2: Inject Scenario to Zabbix

Inject your WebScenario to zabbix
```
  python main.py /tmp/trace_httpoutput.dump SUPERVISION_SITE_PHOTOS
```

### Step 3: Check your scenario in zabbix

![Zabbix WebScenario](https://github.com/matgou/zabbix_webscenario_builder/raw/main/documentation/zabbix_webscenario.png)
