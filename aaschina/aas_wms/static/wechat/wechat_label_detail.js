/**
 * Created by Luforn on 2016-11-10.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#label_detail_pullrefresh',
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

    mui('.mui-popover-bottom').on('tap', '#split_label', function(){
        var labelid = document.getElementById('label_detail_pullrefresh').getAttribute('labelid');
        window.location.replace('/aaswechat/wms/labelsplit/'+labelid);
    });

    mui('.mui-popover-bottom').on('tap', '#frozen_label', function(){
        var labelid = document.getElementById('label_detail_pullrefresh').getAttribute('labelid');
        var frozenparams = {'labelids': [labelid]};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/frozenlabels', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: frozenparams, id: access_id}),
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
            error: function (xhr, type, errorThrown) { console.log(type);}
        });
    });

    mui('.mui-popover-bottom').on('tap', '#unfrozen_label', function(){
        var labelid = document.getElementById('label_detail_pullrefresh').getAttribute('labelid');
        var unfrozenparams = {'labelids': [labelid]};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/unfrozenlabels', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: unfrozenparams, id: access_id}),
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
            error: function (xhr, type, errorThrown) { console.log(type);}
        });
    });


    mui('.mui-popover-bottom').on('tap', '#print_label', function(){
        mui('#label_detail_buttons').popover('toggle');
        var printerid = parseInt(document.getElementById('label_printer').getAttribute('printerid'));
        if (printerid==0){
            mui.toast('请先选择相应的标签打印名称！');
            return ;
        }
        var labelcount = parseInt(document.getElementById('labelcount').value);
        if(labelcount<=0){
            mui.toast('标签份数必须是一个大于0的整数！');
            return ;
        }
        var label_id = parseInt(document.getElementById('label_detail_pullrefresh').getAttribute('labelid'));
        var printparams = {'printerid': printerid, 'labelids': [label_id]};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/printlabels', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: printparams, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                var records = dresult.records;
                if(records.length<=0){
                    return ;
                }
                var printer = dresult.printer;
                var printurl = 'http://'+dresult.printurl;
                mui.each(records, function(index, record){
                    var params = {'label_name': printer, 'label_count': labelcount, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url: printurl, data: params,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                });
            },
            error: function (xhr, type, errorThrown) { console.log(type);}
        });
    });

    //切换打印标签名称
    document.getElementById('change_printer').addEventListener('tap', function(){
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/labelprinters', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: {}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                if (dresult.printers.length<=0){
                    mui.alert('请联系管理员，可能系统中还未配置打印机！');
                    return ;
                }
                var printerpicker = new mui.PopPicker();
                printerpicker.setData(dresult.printers);
                printerpicker.show(function(items) {
                    var labelprinter = document.getElementById('label_printer');
                    labelprinter.innerText = items[0].text;
                    labelprinter.setAttribute('printerid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    });

    //查看库存
    document.getElementById('showstocklist').addEventListener('tap',function(){
        var productid = document.getElementById('showstocklist').getAttribute('productid');
        mui.openWindow({'url': '/aaswechat/wms/product/stocklist/'+productid, 'id': 'productstocklist'});
    });

});