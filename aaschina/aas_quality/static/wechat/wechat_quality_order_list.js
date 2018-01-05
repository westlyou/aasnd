/**
 * Created by luforn on 2018-1-3.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#quality_order_list_pullrefresh',
        up: {
            auto: false,
            contentrefresh: '正在加载...',
            callback: pulluprefresh
        }
    }
});


function pulluprefresh(){
    mui.later(function(){
        var pullrefresh = document.getElementById('quality_order_list_pullrefresh');
        var orderindex = pullrefresh.getAttribute('orderindex');
        var temparams = {'orderindex': parseInt(orderindex)};
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/quality/ordermore', {
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: temparams, id: accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                var dresult = data.result;
                if (dresult.ordercount==0){
                    mui('#quality_order_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.ordercount<20){
                    mui('#quality_order_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#quality_order_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('orderindex', dresult.orderindex);
                var order_list = document.getElementById('quality_order_list');
                mui.each(dresult.orderlist, function(index, qorder){
                    var li = document.createElement('li');
                    li.className = 'aas-quality mui-table-view-cell';
                    li.setAttribute('orderid', qorder.order_id);
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                            "<div class='mui-table'> " +
                                "<div class='mui-table-cell mui-col-xs-8 mui-text-left'> " +
                                    "<div class='mui-ellipsis'>  "+qorder.order_name+" </div> " +
                                "</div> " +
                                "<div class='mui-table-cell mui-col-xs-4 mui-text-right'> " +
                                    "<div >  "+qorder.order_state+" </div> " +
                                "</div> " +
                            "</div>"+
                            "<div class='mui-table'> " +
                                "<div class='mui-table-cell mui-col-xs-8 mui-text-left'> " +
                                    "<div class='mui-ellipsis'>  "+qorder.product_code+" </div> " +
                                "</div> " +
                                "<div class='mui-table-cell mui-col-xs-4 mui-text-right'> " +
                                    "<div >  "+qorder.product_qty+" </div> " +
                                "</div> " +
                            "</div>"+
                        "</a>";
                    order_list.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) { console.log(type); }
        });
    }, 1000);
}


mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-quality", function(){
        var orderid = this.getAttribute("orderid");
        mui.openWindow({'url': '/aaswechat/quality/orderdetail/'+orderid, 'id': 'qualityorderdetail'});
    });

});