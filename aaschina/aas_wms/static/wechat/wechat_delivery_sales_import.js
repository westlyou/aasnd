/**
 * Created by Luforn on 2016-11-29.
 */

mui.init({swipeBack:true});

mui.ready(function(){

    //加载动画
    function aas_sales_import_loading(){
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
    document.getElementById('action_sales_import').addEventListener('tap', function(){
        if(import_flag){
            mui.toast('导入正在处理中，请不要重复操作！');
            return ;
        }
        import_flag = true;
        var sales_order = document.getElementById('sales_order').value;
        if(sales_order==null || sales_order==''){
            mui.toast('请输入销售发票号，销售发票号不能为空！');
            import_flag = false;
            return ;
        }
        var sales_params = {'order_name': sales_order};
        var sales_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var sales_import_mask = aas_sales_import_loading();
        mui.ajax('/aaswechat/wms/deliverysalesimportdone',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: sales_params, id: sales_accessid }),
            dataType:'json', type:'post', timeout:20000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                import_flag = false;
                sales_import_mask.close();
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/wms/deliverysalesdetail/'+dresult.salesid);
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                import_flag = false;
                sales_import_mask.close();
            }
        });
    });
});
