/**
 * Created by luforn on 2017-10-7.
 */

mui.init({swipeBack:true});


mui.ready(function(){

    mui.ajax('/aaswechat/mes/scaninit',{
        data: JSON.stringify({
            jsonrpc: "2.0", method: 'call', params: {'access_url': location.href}, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
        }),
        dataType:'json', type:'post', timeout:10000,
        headers:{'Content-Type':'application/json'},
        success:function(data){
            wx.config(data.result);
            wx.ready(function(){});
            wx.error(function(res){});
        },
        error:function(xhr,type,errorThrown){ console.log(type); }
    });

    //注销
    document.getElementById('aas_mes_logout').addEventListener('tap', function(){
        window.location.replace('/web/session/logout?redirect='+location.href);
    });

    //投料
    document.getElementById('feeding').addEventListener('tap', function(){
        mui.openWindow({'url': '/aaswechat/mes/linefeeding', 'id': 'linefeeding'});
    });

    //生产工单
    document.getElementById('workorder').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描工单',
            scanType: ["qrCode"],
            success: function (result) {
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                mui.ajax('/aaswechat/mes/workorderscan',{
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'barcode': result.resultStr}, id: access_id }),
                    dataType:'json', type:'post', timeout:10000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        mui.openWindow({'url': '/aaswechat/mes/workticket/start/'+dresult.workticketid, 'id': 'workticketstart'});
                    },
                    error:function(xhr,type,errorThrown){ console.log(type);}
                });
            },
            fail: function (result) {mui.toast(result.errMsg);}
        });
    });

    //生产容器
    document.getElementById('container').addEventListener('tap', function(){
        mui.openWindow({'url': '/aaswechat/mes/container', 'id': 'workcontainer'});
    });

    //最终检查
    document.getElementById('finalinspection').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '终检扫描',
            scanType: ["qrCode"],
            success: function (result) {
                window.location.replace('/aaswechat/mes/finalinspection/'+result.resultStr);
            },
            fail: function (result) {mui.toast(result.errMsg);}
        });
    });

});