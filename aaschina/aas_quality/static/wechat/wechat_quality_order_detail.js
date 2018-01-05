/**
 * Created by luforn on 2018-1-4.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#order_detail_pullrefresh',
        down : {
          height:50,
          auto: false,
          contentdown : "下拉可以刷新",
          contentover : "释放立即刷新",
          contentrefresh : "正在刷新...",
          callback : function(){ mui.later(function(){ window.location.reload(true); }, 1000); }
        }
    }
});


mui.ready(function(){

    var access_url = location.href;
    var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
    mui.ajax('/aaswechat/quality/scaninit', {
        data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'access_url': access_url}, id: access_id}),
        dataType: 'json', type: 'post', timeout: 10000,
        headers: {'Content-Type': 'application/json'},
        success: function (data) {
            wx.config(data.result);
            wx.ready(function () {});
            wx.error(function (res) {});
        },
        error: function (xhr, type, errorThrown) { console.log(type);}
    });

    //全部合格
    document.getElementById('action_allqualified').addEventListener('tap', function(){
        mui.confirm('您确认所有未检测标签都合格？', '全部合格', ['确认', '取消'], function(e) {
            if(e.index!=0){
                return ;
            }
            action_allqualified();
        });
    });

    function action_allqualified(){
        var orderid = parseInt(document.getElementById('order_detail_pullrefresh').getAttribute('orderid'));
        var temparams = {'orderid': orderid};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/actionallqualified', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    }


    //全不合格
    document.getElementById('action_allunqualified').addEventListener('tap', function(){
        mui.confirm('您确认所有未检测标签都不合格？', '全不合格', ['确认', '取消'], function(e) {
            if(e.index!=0){
                return ;
            }
            action_allunqualified();
        });
    });

    function action_allunqualified(){
        var orderid = parseInt(document.getElementById('order_detail_pullrefresh').getAttribute('orderid'));
        var temparams = {'orderid': orderid};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/actionallunqualified', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    }


    //完成质检
    document.getElementById('action_done').addEventListener('tap', function(){
        var orderid = parseInt(document.getElementById('order_detail_pullrefresh').getAttribute('orderid'));
        var temparams = {'orderid': orderid};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/actionchecking', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                var daction = dresult.action;
                if(daction=='none'){
                    mui.confirm('您确认完成检测？', '完成检测', ['确认', '取消'], function(e) {
                        if(e.index!=0){
                            return ;
                        }
                        action_done(orderid);
                    });
                }else if(daction=='check'){
                    mui.confirm(dresult.message, '确认检测', ['确认', '取消'], function(e) {
                        if(e.index!=0){
                            return ;
                        }
                        action_done(orderid);
                    });
                }else if(daction=='split'){
                    mui.confirm(dresult.message, '不合格品拆分', ['确认', '取消'], function(e) {
                        if(e.index!=0){
                            return ;
                        }
                        window.location.replace('/aaswechat/quality/splitunqualified/'+orderid);
                    });
                }
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    });

    function action_done(orderid){
        var temparams = {'orderid': orderid};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/actiondone', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    }

    //扫描标签
    document.getElementById('scan_label').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描标签',
            scanType: ["qrCode"],
            success: function (result) {
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                var orderid = parseInt(document.getElementById('order_detail_pullrefresh').getAttribute('orderid'));
                var params = {'barcode': result.resultStr, 'orderid': orderid};
                mui.ajax('/aaswechat/quality/orderlabelscan',{
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
                    dataType:'json', type:'post', timeout:30000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        if(!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        window.location.replace('/aaswechat/quality/checkdetermine/'+dresult.rlabelid);
                    },
                    error:function(xhr,type,errorThrown){
                        console.log(type);
                    }
                });
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });


});