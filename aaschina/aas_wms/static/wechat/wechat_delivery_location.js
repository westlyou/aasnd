/**
 * Created by luforn on 2017-12-20.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#delivery_location_pullrefresh',
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
    function aas_delivery_location_loading(){
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

    //删除标签
    mui('#delivery_labels').on('tap', '.mui-btn', function(event) {
        var li = this.parentNode.parentNode;
        mui.confirm('确认删除该标签？', '删除标签', ['确认', '取消'], function(e) {
            if(e.index!=0){
                mui.swipeoutClose(li);
                return ;
            }
            document.getElementById('delivery_labels').removeChild(li);
        });
    });

    //确认拣货
    document.getElementById('action_pick_confirm').addEventListener('tap', function(){
        mui.confirm('确认批量拣货？', '批量拣货', ['确认', '取消'], function(e) {
            if(e.index!=0){
                return ;
            }
            action_picking();
        });
    });

    var delivery_picking_flag = false;
    function action_picking(){
        if(delivery_picking_flag){
            mui.toast('操作正在处理，请不要重复操作！');
            return ;
        }
        delivery_picking_flag = true;
        var labellist = document.querySelectorAll('.aas-label');
        if(labellist==undefined || labellist==null || labellist.length<=0){
            mui.toast('未搜索到标签需要批量操作！');
            delivery_picking_flag = false;
            return ;
        }
        var dpullrefresh = document.getElementById('delivery_location_pullrefresh');
        var deliveryid = parseInt(dpullrefresh.getAttribute('deliveryid'));
        var dlineid = parseInt(dpullrefresh.getAttribute('dlineid'));
        var idstr = deliveryid+'-'+dlineid;
        var labelids = [];
        mui.each(labellist, function(index, tlabel){
            labelids.push(parseInt(tlabel.getAttribute('labelid')));
        });
        var access_id = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var pickparams = {'deliveryids': idstr, 'labelids': labelids};
        var deliverymask = aas_delivery_location_loading();
        mui.ajax('/aaswechat/wms/deliverylocationdone',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: pickparams, id: access_id}),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                deliverymask.close();
                delivery_picking_flag = false;
                var dresult = data.result;
                if (!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                mui.back();
            },
            error:function(xhr,type,errorThrown){
                console.log(type);
                deliverymask.close();
                delivery_picking_flag = false;
            }
        });

    }


});
