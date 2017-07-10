/**
 * Created by luforn on 2017-7-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#receipt_line_detail_pullrefresh',
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
    function aas_receipt_line_detail_loading(){
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

    var access_url = location.href;
    var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
    mui.ajax('/aaswechat/wms/scaninit',{
        data: JSON.stringify({
            jsonrpc: "2.0", method: 'call', params: {'access_url': access_url}, id: Math.floor(Math.random() * 1000 * 1000 * 1000)
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


    //扫描库位
    document.getElementById('action_change_location').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描库位',
            scanType: ["qrCode"],
            success: function (result) {
                mui('#receipt_line_buttons').popover('toggle');
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                var params = {'barcode': result.resultStr};
                params['lineid'] = parseInt(document.getElementById('receipt_line_detail_pullrefresh').getAttribute('lineid'));
                mui.ajax('/aaswechat/wms/receiptlinelocationscan',{
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
                    dataType:'json', type:'post', timeout:10000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var push_location = document.getElementById('push_location');
                        push_location.innerHTML = dresult.location_name;
                        push_location.setAttribute('locationid', dresult.location_id);
                    },
                    error:function(xhr,type,errorThrown){
                        console.log(type);
                    }
                });
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    //扫描标签
    document.getElementById('action_scan_label').addEventListener('tap', function(){
        var push_location = document.getElementById('push_location');
        var location_id = push_location.getAttribute('locationid');
        if(location_id=='0' || location_id=='' || location_id==null){
            mui.alert('您还没有设置上架库位！');
            return ;
        }
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描标签',
            scanType: ["qrCode"],
            success: function (result) {
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                var params = {'barcode': result.resultStr};
                params['lineid'] = parseInt(document.getElementById('receipt_line_detail_pullrefresh').getAttribute('lineid'));
                mui.ajax('/aaswechat/wms/receiptlinelabelscan',{
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
                    dataType:'json', type:'post', timeout:10000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var receipt_operations = document.getElementById('receipt_operations');
                        var operationli = document.createElement('li');
                        operationli.className = 'mui-table-view-cell';
                        operationli.setAttribute('labelid', 'label_'+dresult.label_id);
                        operationli.setAttribute('operationid', dresult.operation_id);
                        operationli.innerHTML = '<div class="mui-slider-right mui-disabled"><a class="mui-btn mui-btn-red">删除</a></div>' +
                            '<div class="mui-slider-handle">' +
                                '<div class="mui-table"> ' +
                                    '<div class="mui-table-cell mui-col-xs-8 mui-text-left">'+dresult.label_name+'</div>' +
                                    '<div class="mui-table-cell mui-col-xs-4 mui-text-right">'+dresult.product_lot+'</div>'+
                                '</div>' +
                                '<div class="mui-table"> ' +
                                    '<div class="mui-table-cell mui-col-xs-8 mui-text-left">'+dresult.product_code+'</div>' +
                                    '<div class="mui-table-cell mui-col-xs-4 mui-text-right">'+dresult.product_qty+'</div>'+
                                '</div>' +
                            '</div>';
                        receipt_operations.appendChild(operationli);
                        document.getElementById('action_push_done').style.display = 'block';
                    },
                    error:function(xhr,type,errorThrown){
                        console.log(type);
                    }
                });
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    //删除未上架作业
    var receipt_delete_flag = false;
    mui('#receipt_operations').on('tap', '.mui-btn', function(event) {
        if(receipt_delete_flag){
            mui.toast('删除操作正在处理，请耐心等待！');
            return ;
        }
        receipt_delete_flag = true;
        var li = this.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除上架', ['确认', '取消'], function(e) {
            if(e.index!=0){
                mui.swipeoutClose(li);
                return ;
            }
            var operation_id = parseInt(li.getAttribute('operationid'));
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var receipt_delmask = aas_receipt_line_detail_loading();
            mui.ajax('/aaswechat/wms/receiptlineoperationdel',{
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'operation_id': operation_id}, id: access_id }),
                dataType:'json', type:'post', timeout:10000,
                headers:{'Content-Type':'application/json'},
                success:function(data){
                    var dresult = data.result;
                    receipt_delete_flag = false;
                    receipt_delmask.close();
                    if (!dresult.success){
                        mui.toast(dresult.message);
                        return ;
                    }
                    document.getElementById('receipt_operation').removeChild(li);
                    document.getElementById('receipt_doing_qty').innerHTML = dresult.doing_qty;
                },
                error:function(xhr,type,errorThrown){
                    console.log(type);
                    receipt_delete_flag = false;
                    receipt_delmask.close();
                }
            });
        });
    });

    //批量上架
    var push_all_flag = false;
    document.getElementById('action_push_all').addEventListener('tap', function(){
        if (push_all_flag){
            mui.alert('批量上架正在处理，请不要重复操作！');
            return ;
        }
        push_all_flag = true;
        var lineid = parseInt(document.getElementById('receipt_line_detail_pullrefresh').getAttribute('lineid'));
        var push_location = document.getElementById('push_location');
        var location_id = push_location.getAttribute('locationid');
        if(location_id=='0' || location_id=='' || location_id==null){
            push_all_flag = false;
            mui.alert('您还没有设置上架库位！');
            return ;
        }
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var receipt_pushall_mask = aas_receipt_line_detail_loading();
        mui.ajax('/aaswechat/wms/receiptlinepushall',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'lineid': lineid}, id: access_id }),
            dataType:'json', type:'post', timeout:20000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                push_all_flag = false;
                receipt_pushall_mask.close();
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                push_all_flag = false;
                receipt_pushall_mask.close();
            }
        });
    });

    //上架完成
    var push_done_flag = false;
    document.getElementById('action_push_done').addEventListener('tap', function(){
        if (push_done_flag){
            mui.alert('完成上架正在处理，请不要重复操作！');
            return ;
        }
        push_done_flag = true;
        var lineid = parseInt(document.getElementById('receipt_line_detail_pullrefresh').getAttribute('lineid'));
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var receipt_pushdone_mask = aas_receipt_line_detail_loading();
        mui.ajax('/aaswechat/wms/receiptlinepushdone',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'lineid': lineid}, id: access_id }),
            dataType:'json', type:'post', timeout:20000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                push_done_flag = false;
                receipt_pushdone_mask.close();
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.reload(true);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                push_done_flag = false;
                receipt_pushdone_mask.close();
            }
        });
    });



});
