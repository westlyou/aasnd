/**
 * Created by luforn on 2018-1-5.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#order_rejection_pullrefresh',
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
                    var labelprinter = document.getElementById('label_printer');
                    labelprinter.innerText = items[0].text;
                    labelprinter.setAttribute('printerid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    });

    document.getElementById('action_doprint').addEventListener('tap', function(){
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
        var labelidstr = document.getElementById('order_rejection_pullrefresh').getAttribute('labelids');
        if(labelidstr==undefined || labelidstr==null || labelidstr==''){
            mui.toast('未检测到需要打印的标签');
            return ;
        }
        var labelids = [];
        mui.each(labelidstr.split(','), function(index, tempid){
            labelids.push(parseInt(tempid));
        });
        var printparams = {'printerid': printerid, 'labelids': labelids};
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/printlabels', {
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

});
