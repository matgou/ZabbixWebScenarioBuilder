# ZabbixWebScenarioBuilder v0.0.2

## Description

Website monitoring with zabbix is powerful, it can check availability of website by perform httpcheck.

But the UI to build Web-Scenario in Zabbix-Frontend is not easy to use. So ZabbixWebScenarioBuilder will record navigator http/https traffic and convert it to a Zabbix Webscenario.

## Install

### Init environment
To Init environment use virtualenv and pip by running the following command (this example is for Debian):
```
virtualenv --python=/usr/bin/python3 venv
. venv/bin/activate
pip -r requirement
```

### Create config.ini

ZabbixWebScenarioBuilder use a file named `config.ini`. You must init this file from `config.ini.template` :
```
cp config.ini.template config.ini
vi config.ini
```
|Section|  key             | description                                                 |
|------|------------------|-------------------------------------------------------------|
|ZABBIX| zabbix_host      | Base URL of zabbix (ex: https://zabbix.example.com/zabbix ) |
|ZABBIX| zabbix_user      | API user to log on zabbix                                   |
|ZABBIX| zabbix_password  | API password corresponding to user                          |
|ZABBIX| zabbix_hostid    | Id of host (or Template) to inject generated webscenario    |
|ZABBIX| zabbix_ignore_header | A list of extensions (end of url) of header to not put in webscenario |
| API  | recording_api_port | A listen port on host to display UI                       |
| API  | recording_api_websocket | A listen port on host to use for UI to fetch event via websocket|
|PROXY | port             | A listen port for local captive proxy                       |
|PROXY | proxy_ignore_ext | A list (comma separated) of all extension to not recording (ex: css) |

## Howto

#### Start application via main.py

```
  python main.py
```

On start application will create a proxy on localhost (127.0.0.1:3128) and open the EDI :
![Zabbix WebScenario EDI](https://github.com/matgou/zabbix_webscenario_builder/raw/main/documentation/EDI1.png)


### After clicking on "To Zabbix" button, scenario will be on Zabbix

![Zabbix WebScenario](https://github.com/matgou/zabbix_webscenario_builder/raw/main/documentation/zabbix_webscenario.png)

