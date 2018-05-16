/**
 * Created by luforn on 2017-7-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#delivery_sales_list_pullrefresh',
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
        var pullrefresh = document.getElementById('delivery_sales_list_pullrefresh');
        var salesindex = pullrefresh.getAttribute('salesindex');
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'salesindex': parseInt(salesindex)};
        mui.ajax('/aaswechat/wms/deliverysalesmore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: accessid}),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.salescount==0){
                    mui('#delivery_sales_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.salescount<20){
                    mui('#delivery_sales_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#delivery_sales_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('salesindex', dresult.salesindex);
                var delivery_sales_list = document.getElementById('delivery_sales_list');
                mui.each(dresult.deliverysales, function(index, dsales){
                    var li = document.createElement('li');
                    li.className = 'aas-delivery-sales mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>"+dsales.delivery_name+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-right'>"+dsales.partner_name+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('deliveryid', dsales.delivery_id);
                    delivery_sales_list.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}

mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-delivery-sales", function(){
        var salesid = this.getAttribute("deliveryid");
        mui.openWindow({'url': '/aaswechat/wms/deliverysalesdetail/'+salesid, 'id': 'deliverysalesdetail'});
    });

});