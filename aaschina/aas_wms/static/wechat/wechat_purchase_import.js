/**
 * Created by Luforn on 2016-11-29.
 */

mui.init({swipeBack:true});

mui.ready(function(){

    //加载动画
    function aas_purchase_import_loading(){
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

    var import_flag = false;
    document.getElementById('action_purchase_import').addEventListener('tap', function(){
        if(import_flag){
            mui.toast('导入正在处理中，请不要重复操作！');
            return ;
        }
        import_flag = true;
        var purchase_order = document.getElementById('purchase_order').value;
        if(purchase_order==null || purchase_order==''){
            mui.toast('请输入采购订单号，采购订单号不能为空！');
            import_flag = false;
            return ;
        }
        var purchase_params = {'order_name': purchase_order};
        var purchase_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var purchase_import_mask = aas_purchase_import_loading();
        mui.ajax('/aaswechat/wms/purchaseimportdone',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: purchase_params, id: purchase_accessid }),
            dataType:'json', type:'post', timeout:20000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                import_flag = false;
                purchase_import_mask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/wms/purchasedetail/'+dresult.purchaseid);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                import_flag = false;
                purchase_import_mask.close();
            }
        });
    });
});
