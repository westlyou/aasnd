/**
 * Created by luforn on 2017-7-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#inventory_detail_pullrefresh',
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
    function aas_inventory_detail_loading(){
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

    //扫描标签
    document.getElementById('action_scan_label').addEventListener('tap', function(){
        wx.scanQRCode({
            needResult: 1,
            desc: '扫描标签',
            scanType: ["qrCode"],
            success: function (result) {
                var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
                var params = {'barcode': result.resultStr};
                params['inventory_id'] = parseInt(document.getElementById('inventory_detail_pullrefresh').getAttribute('inventoryid'));
                mui.ajax('/aaswechat/wms/inventorylabelscan',{
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
                    dataType:'json', type:'post', timeout:20000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var inventory_labels = document.getElementById('inventory_labels');
                        var labelli = document.createElement('li');
                        labelli.className = 'mui-table-view-cell';
                        labelli.setAttribute('ilabelid', dresult.ilabel_id);
                        labelli.innerHTML = '<div class="mui-slider-right mui-disabled"><a class="mui-btn mui-btn-red">删除</a></div>' +
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
                        inventory_labels.appendChild(labelli);
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
    var inventory_delete_flag = false;
    mui('#inventory_labels').on('tap', '.mui-btn', function(event) {
        if(inventory_delete_flag){
            mui.toast('删除操作正在处理，请耐心等待！');
            return ;
        }
        inventory_delete_flag = true;
        var li = this.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除上架', ['确认', '取消'], function(e) {
            if(e.index!=0){
                mui.swipeoutClose(li);
                return ;
            }
            var ilabelid = parseInt(li.getAttribute('ilabelid'));
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var inventory_delmask = aas_inventory_detail_loading();
            mui.ajax('/aaswechat/wms/inventorylabeldel',{
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: {'ilabel_id': ilabelid}, id: access_id }),
                dataType:'json', type:'post', timeout:20000,
                headers:{'Content-Type':'application/json'},
                success:function(data){
                    var dresult = data.result;
                    inventory_delete_flag = false;
                    inventory_delmask.close();
                    if (!dresult.success){
                        mui.toast(dresult.message);
                        return ;
                    }
                    document.getElementById('inventory_labels').removeChild(li);
                },
                error:function(xhr,type,errorThrown){
                    console.log(type);
                    inventory_delete_flag = false;
                    inventory_delmask.close();
                }
            });
        });
    });



});
