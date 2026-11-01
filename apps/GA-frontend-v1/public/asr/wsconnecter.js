/**
 * Copyright FunASR (https://github.com/alibaba-damo-academy/FunASR). All Rights
 * Reserved. MIT License  (https://opensource.org/licenses/MIT)
 */
/* 2021-2023 by zhaoming,mali aihealthx.com */

function WSConnecter(config) { //定义socket连接方法类
    var speechSokt;
    var connKeeperID;

    var msgHandle = config.msgHandle || config.onMessage || function(){};
    var stateHandle = config.stateHandle || function(){};
    var onClose = config.onClose || function(){};
    var onError = config.onError || function(){};
    var url = config.url || "ws://127.0.0.1:10095/";
    var mode = config.mode || "2pass";
    var useITN = config.useITN || false;
    var hotWords = config.hotWords || "";

    this.wsStart = function () {
        console.log("WSConnecter.wsStart called, connecting to:", url);

        if ('WebSocket' in window) {
            speechSokt = new WebSocket(url);
            speechSokt.onopen = function(e){
                console.log("WebSocket连接成功");
                // 发送初始配置
                var request = {
                    "chunk_size": [5, 10, 5],
                    "wav_name": "h5",
                    "is_speaking": true,
                    "chunk_interval": 10,
                    "itn": useITN,
                    "mode": mode,
                };

                if(hotWords){
                    request.hotwords = hotWords;
                }

                speechSokt.send(JSON.stringify(request));
                stateHandle(0); // 表示连接成功
            };

            speechSokt.onclose = function(e){
                console.log("WebSocket连接已关闭");
                onClose(e);
                stateHandle(1); // 表示连接关闭
            };

            speechSokt.onmessage = function(e){
                console.log("收到WebSocket消息");
                msgHandle(e);
            };

            speechSokt.onerror = function(e){
                console.error("WebSocket错误:", e);
                onError(e);
                stateHandle(2); // 表示连接错误
            };

            return 1; // 表示成功启动
        } else {
            alert('当前浏览器不支持WebSocket');
            return 0; // 表示启动失败
        }
    };

    // 定义停止与发送函数
    this.wsStop = function () {
        if(speechSokt != undefined) {
            console.log("WSConnecter.wsStop called");
            speechSokt.close();
            speechSokt = undefined;
        }
    };

    this.stop = function() {
        this.wsStop();
    };

    this.wsSend = function (oneData) {
        if(speechSokt == undefined) return false;
        if (speechSokt.readyState === 1) { // 0:CONNECTING, 1:OPEN, 2:CLOSING, 3:CLOSED
            speechSokt.send(oneData);
            return true;
        }
        return false;
    };

    this.sendData = function(data) {
        return this.wsSend(data);
    };

    this.getConnectState = function() {
        return speechSokt && speechSokt.readyState === 1;
    };
}

// 非常重要：将WSConnecter绑定到window对象上
window.WSConnecter = WSConnecter;
console.log("WSConnecter已定义并绑定到window对象");