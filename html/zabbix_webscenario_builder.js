angular.module('zabbix_webscenario_builder', [])
.filter('cut', function () {
        return function (value, wordwise, max, tail) {
            if (!value) return '';

            max = parseInt(max, 10);
            if (!max) return value;
            if (value.length <= max) return value;

            value = value.substr(0, max);
            if (wordwise) {
                var lastspace = value.lastIndexOf(' ');
                if (lastspace !== -1) {
                  //Also remove . and , so its gives a cleaner result.
                  if (value.charAt(lastspace-1) === '.' || value.charAt(lastspace-1) === ',') {
                    lastspace = lastspace - 1;
                  }
                  value = value.substr(0, lastspace);
                }
            }

            return value + (tail || ' …');
        };
    })
.controller('MainController', ['$scope', '$http', '$window', function($scope, $http, $window) {
    	$scope.appName = 'ZabbixWebScenarioBuilder';
    	$scope.requests = []
    	$scope.lock=false
    	$scope.showRequestParam = function(index) {
    	    console.log('show index ' + index)
    	    $scope.currentRequest = $scope.requests[index]
    	    console.log($scope.requests)
    	}
        $scope.clickStop = function() {
            $http({
                method: "POST",
                url: "/stop_recording",
                data: ''
            }).then(function(response) {
                $scope.lock=false;
                $scope.requests=response.data.requests;
                $scope.socket.close()
            }, function() {
                alert('Error in recording')
            });
        };
        $scope.clickRecord = function() {
            $http({
                method: "POST",
                url: "/start_recording",
                data: ''
            }).then(function() {
                $scope.lock=true
                $scope.socket = new WebSocket("ws://127.0.0.1:3130/");
                $scope.socket.onmessage = function(event) {
                    console.log(`[message] Data received from server: ${event.data}`);
                    obj = JSON.parse(event.data)
                    console.log(obj)
                    $scope.requests.push(obj)
                    $scope.$apply();

                };
                $scope.socket.onopen = function(e) {
                    console.log("[open] Connection established");
                    console.log("Sending to server");
                    $scope.socket.send("ZabbixWebScenarioEDI");
                };
                $scope.socket.onclose = function(event) {
                  if (event.wasClean) {
                    console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
                  } else {
                    console.log('[close] Connection died');
                  }
                };
                $scope.socket.onerror = function(error) {
                  console.log(`[error] ${error.message}`);
                };
            }, function() {
                alert('Error in recording')
            });
        };
        $scope.clickSendZabbix = function() {
            $scope.lock=true
            $http({
                method: "POST",
                url: "/push_zabbix",
                data: {
                    filter: $scope.searchTxt,
                    host_key: $scope.scenarioHostKey,
                    scenario_name: $scope.scenarioName,
                }
            }).then(function(response) {
                if(response.data.zapi_result.httptestids !== undefined) {
                    zabbix_url= response.data.zapi_host + '/httpconf.php?form=update&hostid=' + $scope.scenarioHostKey + '&httptestid='+response.data.zapi_result.httptestids[0]
                    $window.location.href = zabbix_url
                } else {
                    alert('Error while send to zabbix : ' + response.data.zapi_result)
                }
            }, function() {
                alert('Error in recording')
            });
        };
}]);