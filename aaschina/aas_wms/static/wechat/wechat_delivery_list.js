/**
 * Created by luforn on 2017-7-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#delivery_list_pullrefresh',
        up: {
            auto: false,
            contentrefresh: '正在加载...',
            callback: pulluprefresh
        },
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

function pulluprefresh(){
    mui.later(function(){
        var pullrefresh = document.getElementById('delivery_list_pullrefresh');
        var deliveryindex = pullrefresh.getAttribute('deliveryindex');
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'deliveryindex': parseInt(deliveryindex)};
        mui.ajax('/aaswechat/wms/deliverymore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: accessid}),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.deliverycount==0){
                    mui('#delivery_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.deliverycount<20){
                    mui('#delivery_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#delivery_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('deliveryindex', dresult.deliveryindex);
                var delivery_list = document.getElementById('delivery_list');
                mui.each(dresult.deliverylist, function(index, dlist){
                    var li = document.createElement('li');
                    li.className = 'aas-delivery mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+dlist.delivery_name+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-3 mui-text-center'>"+dlist.delivery_type+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-3 mui-text-right'>"+dlist.state_name+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('deliveryid', dlist.delivery_id);
                    delivery_list.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}

mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-delivery", function(){
        var deliveryid = this.getAttribute("deliveryid");
        mui.openWindow({'url': '/aaswechat/wms/deliverydetail/'+deliveryid, 'id': 'deliverydetail'});
    });

});