/**
 * Created by luforn on 2018-4-28.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#attendance_pullrefresh',
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


    //加载动画
    function aas_attendance_loading(){
        var tempmask = mui.createMask();
        var loadimg = document.createElement('img'), maskEl = tempmask[0];
        maskEl.removeEventListener('tap', arguments.callee);
        loadimg.setAttribute('src', '/aas_base/static/wechat/aas/images/loading.gif');
        loadimg.setAttribute('width', '50px');
        loadimg.setAttribute('height', '50px');
        loadimg.setAttribute('alt', '加载中.........');
        loadimg.setAttribute('style', "position:fixed;top:50%;left:50%;margin:-25px 0 0 -25px;");
        maskEl.appendChild(loadimg);
        tempmask.show();
        return tempmask;
    }


    //切换产线
    document.getElementById('mesline').addEventListener('tap', function(){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aasmes/meslines', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: {}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if (dresult.meslines.length<=0){
                    mui.alert('请联系管理员，可能系统中还未设置产线信息！');
                    return ;
                }
                var linespicker = new mui.PopPicker();
                linespicker.setData(dresult.meslines);
                linespicker.show(function(items) {
                    var mesline = document.getElementById('mesline');
                    mesline.innerText = items[0].text;
                    mesline.setAttribute('meslineid', items[0].value);
                    localStorage.setItem('mesline_id', items[0].value);
                    localStorage.setItem('mesline_name', items[0].text);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    });

    //切换工位
    document.getElementById('workstation').addEventListener('tap', function(){
        var mesline = document.getElementById('mesline');
        var meslineid = parseInt(mesline.getAttribute('meslineid'));
        if(meslineid==0){
            mui.alert('您还未设置产线信息！');
            return ;
        }
        var temparams = {'meslineid': meslineid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aasmes/mesline/workstations', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: temparams, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if (dresult.workstations.length<=0){
                    mui.alert('系统中还未设置工位信息！');
                    return ;
                }
                var wspicker = new mui.PopPicker();
                wspicker.setData(dresult.workstations);
                wspicker.show(function(items) {
                    var workstation = document.getElementById('workstation');
                    workstation.innerText = items[0].text;
                    workstation.setAttribute('stationid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    });


    //切换设备
    document.getElementById('mequipment').addEventListener('tap', function(){
        var mesline = document.getElementById('mesline');
        var meslineid = parseInt(mesline.getAttribute('meslineid'));
        if(meslineid==0){
            mui.alert('您还未设置产线信息！');
            return ;
        }
        var workstation = document.getElementById('workstation');
        var stationid = parseInt(workstation.getAttribute('stationid'));
        if(stationid==0){
            mui.alert('您还未设置工位信息！');
            return ;
        }
        var temparams = {'meslineid': meslineid, 'workstationid': stationid};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aasmes/equipmentlist', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: temparams, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if (dresult.equipments.length<=0){
                    mui.alert('系统中还未设置工位设备信息！');
                    return ;
                }
                var eqpicker = new mui.PopPicker();
                eqpicker.setData(dresult.equipments);
                eqpicker.show(function(items) {
                    var mequipment = document.getElementById('mequipment');
                    mequipment.innerText = items[0].text;
                    mequipment.setAttribute('equipmentid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    });


    function setattendancedefaults(){
        var meslineid = localStorage.getItem('mesline_id');
        var meslinename = localStorage.getItem('mesline_name');
        if(meslineid==null || meslinename==null){
            return false;
        }
        var mesline = document.getElementById('mesline');
        mesline.setAttribute('meslineid', meslineid);
        mesline.innerText = meslinename;
    }

    setattendancedefaults();

    //单击扫描上料按钮

    document.getElementById('action_scan').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描上岗',
            scanType: ["qrCode"],
            success: function (result) {
                var barcode = result.resultStr;
                var memployee = document.getElementById('memployee');
                memployee.setAttribute('barcode', barcode);
                memployee.innerText = barcode;
                action_attendance(barcode);
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    var attend_flag = false;
    function action_attendance(barcode){
        if (attend_flag){
            mui.toast('操作正在执行，请耐心等待！');
            return ;
        }
        attend_flag = true;
        var mesline = document.getElementById('mesline');
        var meslineid = parseInt(mesline.getAttribute('meslineid'));
        var temparams = {'meslineid': meslineid, 'barcode': barcode};
        var stationid = parseInt(document.getElementById('workstation').getAttribute('stationid'));
        if(stationid > 0){
            temparams['workstationid'] = stationid;
        }
        var equipmentid = parseInt(document.getElementById('mequipment').getAttribute('equipmentid'));
        if(equipmentid > 0){
            temparams['equipmentid'] = equipmentid;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var tempmask = aas_attendance_loading();
        mui.ajax('/aaswechat/mes/attendance/scanning', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: temparams, id: access_id}),
            dataType: 'json', type: 'post', timeout: 30000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                attend_flag = false;
                tempmask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if(dresult.action=='working'){
                    if(dresult.message!=null && dresult.message!=''){
                        mui.toast(dresult.message);
                    }else{
                        mui.toast('您已上岗！');
                    }
                }else if(dresult.action=='leave'){
                    mui.toast('您已离岗！');
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }


});
