/**
 * Created by luforn on 2017-7-11.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#purchase_list_pullrefresh',
        up: {
            auto: false,
            contentrefresh: '正在加载...',
            callback: pulldownrefresh
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


function pulldownrefresh(){
    mui.later(function(){
        var pullrefresh = document.body.querySelector('#purchase_list_pullrefresh');
        var purchaseindex = pullrefresh.getAttribute('purchaseindex');
        var purchase_params = {'purchaseindex': parseInt(purchaseindex)};
        var purchase_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/purchasemore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: purchase_params, id: purchase_accessid }),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.purchasecount==0){
                    mui('#purchase_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.purchasecount<15){
                    mui('#purchase_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#purchase_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('purchaseindex', dresult.purchaseindex);
                var purchase_list = document.getElementById('purchase_list');
                mui.each(dresult.purchases, function(index, purchase){
                    var li = document.createElement('li');
                    li.className = 'aas-purchase mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>"+purchase.order_name+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+purchase.partner_name+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('purchaseid', purchase.order_id);
                    purchase_list.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}



mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-purchase", function(){
        var purchaseid = this.getAttribute("purchaseid");
        mui.openWindow({'url': '/aaswechat/wms/purchasedetail/'+purchaseid, 'id': 'purchasedetail'});
    });

    //导入订单
    document.getElementById('action_purchase_import').addEventListener('tap', function(){
        mui.openWindow({'url': '/aaswechat/wms/purchaseimport', 'id': 'purchaseimport'});
    });

});