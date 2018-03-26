/**
 * Created by luforn on 2017-12-13.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#container_detail_pullrefresh',
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
                    var containerprinter = document.getElementById('container_printer');
                    containerprinter.innerText = items[0].text;
                    containerprinter.setAttribute('printerid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    });

    //容器打印
    document.getElementById('print_container').addEventListener('tap', function(){
        mui('#container_detail_buttons').popover('toggle');
        var printerid = parseInt(document.getElementById('container_printer').getAttribute('printerid'));
        if (printerid==0){
            mui.toast('请先选择相应的标签打印名称！');
            return ;
        }
        var labelcount = parseInt(document.getElementById('labelcount').value);
        if(labelcount<=0){
            mui.toast('标签份数必须是一个大于0的整数！');
            return ;
        }
        var containerid = parseInt(document.getElementById('container_detail_pullrefresh').getAttribute('containerid'));
        var printparams = {'printerid': printerid, 'containerids': [containerid]};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/mes/printcontainers', {
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


    //清理容器
    /*document.getElementById('clean_container').addEventListener('tap', function(){
        mui('#container_detail_buttons').popover('toggle');
        mui.confirm('确认清理当前容器的库存清单？', '清理容器', ['确认', '取消'], function(e) {
            if (e.index != 0) {
                return;
            }
            action_clean();
        });
    });*/

    function action_clean(){
        var containerid = parseInt(document.getElementById('container_detail_pullrefresh').getAttribute('containerid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/mes/containerclean', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'containerids': [containerid]}, id: access_id}),
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
    }

});
