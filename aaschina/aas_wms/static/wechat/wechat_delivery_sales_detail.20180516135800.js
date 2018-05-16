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

    //拣货清单
    var delivery_repicking_flag = false;
    document.getElementById('action_repicking').addEventListener('tap', function(){
        if (delivery_repicking_flag){
            mui.toast('操作正在处理中，请耐心等待！');
            return ;
        }
        delivery_repicking_flag = true;
        mui.confirm('确认要重新计算拣货清单吗？', '拣货清单', ['确认', '取消'], function(e) {
            if (e.index != 0) {
                delivery_repicking_flag = false;
                return;
            }
            var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
            var deliveryid = document.getElementById('delivery_sales_detail_pullrefresh').getAttribute('deliveryid');
            var params = {'deliveryid': parseInt(deliveryid)};
            var deliverymask = aas_delivery_sales_detail_loading();
            mui.ajax('/aaswechat/wms/deliveryrepicking',{
                data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: access_id}),
                dataType:'json', type:'post', timeout:20000,
                headers:{'Content-Type':'application/json'},
                success:function(data){
                    delivery_repicking_flag = false;
                    deliverymask.close();
                    var dresult = data.result;
                    if (!dresult.success){
                        mui.toast(dresult.message);
                        return ;
                    }
                    window.location.reload(true);
                },
                error:function(xhr,type,errorThrown){
                    delivery_repicking_flag = false;
                    deliverymask.close();
                    console.log(type);
                }
            });

        });
    });



});
