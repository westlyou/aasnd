/**
 * Created by luforn on 2018-3-5.
 */

mui.init({ swipeBack:true });

mui.ready(function(){

    mui.ajax('/aaswechat/quality/scaninit',{
        data: JSON.stringify({
            jsonrpc: "2.0", method: 'call',
            params: {'access_url': location.href}, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
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

    document.getElementById('oqcchecking').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描标签',
            scanType: ["qrCode"],
            success: function (result) {
                mui.openWindow({'url': '/aaswechat/quality/oqcchecking/label/'+result.resultStr, 'id': 'oqcchecking'});
            },
            fail: function (result) {mui.toast(result.errMsg);}
        });
    });
});
