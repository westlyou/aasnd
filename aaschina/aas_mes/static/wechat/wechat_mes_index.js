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
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描工位',
            scanType: ["qrCode"],
            success: function (result) {
                var barcode = result.resultStr;
                mui.openWindow({'url': '/aaswechat/mes/workstationfeeding/'+barcode, 'id': 'workstationfeeding'});
            },
            fail: function (result) {
                mui.toast(result.errMsg);
            }
        });
    });

});