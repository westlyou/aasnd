/**
 * Created by luforn on 2017-7-14.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#delivery_sales_detail_pullrefresh',
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
    function aas_delivery_sales_detail_loading(){
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


    //确认拣货
    var delivery_sales_deliver_flag = false;
    document.getElementById('action_delivery_done').addEventListener('tap', function(){
        if (delivery_sales_deliver_flag){
            mui.toast('操作正在处理中，请耐心等待！');
            return ;
        }
        delivery_sales_deliver_flag = true;
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var salesid = parseInt(document.getElementById('delivery_sales_detail_pullrefresh').getAttribute('salesid'));
        var params = {'salesid': salesid};
        var deliverymask = aas_delivery_sales_detail_loading();
        mui.ajax('/aaswechat/wms/deliverysalesdone',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id }),
            dataType:'json', type:'post', timeout:20000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                delivery_sales_deliver_flag = false;
                deliverymask.close();
                var dresult = data.result;
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                window.location.replace('/aaswechat/wms/deliverydetail/'+dresult.delivery_id);
            },
            error:function(xhr,type,errorThrown){
                delivery_sales_deliver_flag = false;
                deliverymask.close();
                console.log(type);
            }
        });
    });



});
