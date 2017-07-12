/**
 * Created by Luforn on 2016-11-15.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#receipt_detail_pullrefresh',
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

    //加载动画
    function aas_receipt_detail_loading(){
        var receiptmask = mui.createMask();
        var loadimg = document.createElement('img'), maskEl = receiptmask[0];
        maskEl.removeEventListener('tap', arguments.callee);
        loadimg.setAttribute('src', '/aas_base/static/wechat/aas/images/loading.gif');
        loadimg.setAttribute('width', '50px');
        loadimg.setAttribute('height', '50px');
        loadimg.setAttribute('alt', '加载中.........');
        loadimg.setAttribute('style', "position:fixed;top:50%;left:50%;margin:-25px 0 0 -25px;");
        maskEl.appendChild(loadimg);
        receiptmask.show();
        return receiptmask;
    }


    // 收货确认
    var receipt_confirming = false; //是否确认收货标识，正在处理时为true
    mui('.mui-popover-bottom').on('tap', '#action_confirm', function(){
        mui('#receipt_detail_buttons').popover('toggle');
        if(receipt_confirming){
            mui.toast('收货确认正在处理中，请不要重复操作！');
            return ;
        }
        receipt_confirming = true;
        var receiptid = parseInt(document.getElementById('receipt_detail_pullrefresh').getAttribute('receiptid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var receipt_confirm_mask = aas_receipt_detail_loading();
        mui.ajax('/aaswechat/wms/receiptconfirm', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: {'receiptid': receiptid}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                receipt_confirming = false;
                receipt_confirm_mask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){
                receipt_confirming = false;
                receipt_confirm_mask.close();
            }
        });
    });


    // 收货报检
    var quality_confirming = false; //是否确认收货标识，正在处理时为true
    mui('.mui-popover-bottom').on('tap', '#action_commitcheck', function(){
        mui('#receipt_detail_buttons').popover('toggle');
        if(quality_confirming){
            mui.toast('收货报检正在处理中，请不要重复操作！');
            return ;
        }
        quality_confirming = true;
        var receiptid = parseInt(document.getElementById('receipt_detail_pullrefresh').getAttribute('receiptid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var quality_confirm_mask = aas_receipt_detail_loading();
        mui.ajax('/aaswechat/wms/receiptcommitcheck', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: {'receiptid': receiptid}, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                quality_confirming = false;
                quality_confirm_mask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                quality_confirming = false;
                quality_confirm_mask.close();
            }
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
                    var receipt_printer = document.getElementById('receipt_printer');
                    receipt_printer.innerText = items[0].text;
                    receipt_printer.setAttribute('printerid', items[0].value);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    });




    // 标签打印
    var receipt_print_flag = false;
    mui('.mui-popover-bottom').on('tap', '#print_labels', function(){
        mui('#receipt_detail_buttons').popover('toggle');
        if(receipt_print_flag){
            mui.toast('操作正在处理，请耐心等待！');
            return ;
        }
        receipt_print_flag = true;
        var printerid = document.getElementById('receipt_printer').getAttribute('printerid');
        if (printerid==undefined || printerid==null || printerid=='' || printerid=='0'){
            receipt_print_flag = false;
            mui.toast('请先选择相应的标签打印机！');
            return ;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var receipt_print_mask = aas_receipt_detail_loading();
        var receiptid = parseInt(document.getElementById('receipt_detail_pullrefresh').getAttribute('receiptid'));
        var params = {'receiptid': receiptid, 'printerid': parseInt(printerid)};
        mui.ajax('/aaswechat/wms/receiptprintlabels', {
            data: JSON.stringify({jsonrpc: "2.0",method: 'call',params: params, id: access_id}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                receipt_print_flag = false;
                receipt_print_mask.close();
                var dresult = data.result;
                var records = dresult.records;
                if(records.length<=0){
                    return ;
                }
                var printer = dresult.printer;
                var printurl = 'http://'+dresult.printurl;
                mui.each(records, function(index, record){
                    var params = {'label_name':printer, 'label_count':1, 'label_content':record};
                    $.ajax({type:'post', dataType:'script', url: printurl, data: params,
                        success: function (result) { },
                        error:function(XMLHttpRequest,textStatus,errorThrown){}
                    });
                });
            },
            error:function(xhr,type,errorThrown){
                receipt_print_flag = false;
                receipt_print_mask.close();
                console.log(type);
            }
        });
    });


    //拆分生成收货标签
    mui('#receipt_lines').on('tap', '.aas-label-unrelated', function(){
        var lineid = parseInt(this.getAttribute('lineid'));
        mui.openWindow({'url': '/aaswechat/wms/receipt/lotlist/'+lineid, 'id': 'receiptlotlist'});
    });








});