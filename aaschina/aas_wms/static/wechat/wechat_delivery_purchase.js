/**
 * Created by luforn on 2017-7-14.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#delivery_purchase_pullrefresh',
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
    function aas_delivery_purchase_loading(){
        var deliverymask = mui.createMask();
        var loadimg = document.createElement('img'), maskEl = deliverymask[0];
        maskEl.removeEventListener('tap', arguments.callee);
        loadimg.setAttribute('src', '/aas_base/static/wechat/aas/images/loading.gif');
        loadimg.setAttribute('width', '50px');
        loadimg.setAttribute('height', '50px');
        loadimg.setAttribute('alt', '加载中.........');
        loadimg.setAttribute('style', "position:fixed;top:50%;left:50%;margin:-25px 0 0 -25px;");
        maskEl.appendChild(loadimg);
        deliverymask.show();
        return deliverymask;
    }

    var access_url = location.href;
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
                mui.ajax('/aaswechat/wms/deliverypurchaselabelscan',{
                    data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
                    dataType:'json', type:'post', timeout:10000,
                    headers:{'Content-Type':'application/json'},
                    success:function(data){
                        var dresult = data.result;
                        if (!dresult.success){
                            mui.toast(dresult.message);
                            return ;
                        }
                        var purchaseorderdiv = document.getElementById('purchaseorder');
                        var porder = purchaseorderdiv.getAttribute('porder');
                        if(porder=='' || porder==null){
                            purchaseorderdiv.setAttribute('porder', dresult.origin_order);
                            purchaseorderdiv.innerHTML = dresult.origin_order;
                        }else if(porder!=dresult.origin_order){
                            mui.toast('请仔细检查当前标签是否和其他标签是同一采购订单！');
                            return ;
                        }
                        var supplierdiv = document.getElementById('supplier');
                        var partnerid = parseInt(supplierdiv.getAttribute('partnerid'));
                        if(partnerid==0){
                            supplierdiv.setAttribute('partnerid', dresult.partner_id);
                            supplierdiv.innerHTML = dresult.partner_name;
                        }
                        var purchase_operations = document.getElementById('purchase_operations');
                        var operationli = document.createElement('li');
                        operationli.className = 'mui-table-view-cell aas-purchase-label';
                        operationli.setAttribute('labelid', dresult.label_id);
                        operationli.innerHTML = '<div class="mui-slider-right mui-disabled"><a class="mui-btn mui-btn-red">删除</a></div>' +
                            '<div class="mui-slider-handle">' +
                                '<div class="mui-table"> ' +
                                    '<div class="mui-table-cell mui-col-xs-6 mui-text-left">'+dresult.product_code+'</div>' +
                                    '<div class="mui-table-cell mui-col-xs-6 mui-text-right">'+dresult.product_lot+'</div>'+
                                '</div>' +
                                '<div class="mui-table"> ' +
                                    '<div class="mui-table-cell mui-col-xs-6 mui-text-left">'+dresult.label_name+'</div>' +
                                    '<div class="mui-table-cell mui-col-xs-6 mui-text-right">'+dresult.product_qty+'</div>'+
                                '</div>' +
                            '</div>';
                        purchase_operations.appendChild(operationli);
                    },
                    error:function(xhr,type,errorThrown){
                        console.log(type);
                    }
                });
            },
            fail: function(result){  mui.toast(result.errMsg); }
        });
    });

    //删除发货作业
    mui('#purchase_operations').on('tap', '.mui-btn', function(event) {
        var purchaseLi = this.parentNode.parentNode;
        mui.confirm('确认删除该条记录？', '清除上架', ['确认', '取消'], function(e) {
            if(e.index!=0){
                mui.swipeoutClose(purchaseLi);
                return ;
            }
            document.getElementById('purchase_operations').removeChild(purchaseLi);
        });
    });


    var delivery_purchase_flag = false;
    document.getElementById('action_deliver_done').addEventListener('tap',function(){
        if(delivery_purchase_flag){
            mui.toast('操作正在处理，请不要重复操作！');
            return ;
        }
        delivery_purchase_flag = true;
        var labellist = document.querySelectorAll('.aas-purchase-label');
        if(labellist==null||labellist==undefined||labellist.length<=0){
            mui.toast('请先添加需要退货的标签！');
            return ;
        }
        var labelids = [];
        mui.each(labellist, function(labelli){
            labelids.push(parseInt(labelli.getAttribute('labelid')));
        });
        var partnerid = parseInt(document.getElementById('supplier').getAttribute('partnerid'));
        var purchaseorder = document.getElementById('purchaseorder').getAttribute('porder');
        var params = {'partnerid': partnerid, 'purchaseorder': purchaseorder, 'labelids': labelids};
        var deliverymask = aas_delivery_purchase_loading();
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/deliverypurchasedone',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
            dataType:'json', type:'post', timeout:20000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                delivery_purchase_flag = false;
                deliverymask.close();
                var dresult = data.result;
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/wms');
            },
            error:function(xhr,type,errorThrown){
                delivery_purchase_flag = false;
                deliverymask.close();
                console.log(type);
            }
        });
    });


});
