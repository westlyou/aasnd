/**
 * Created by luforn on 2017-12-27.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#product_stock_list_pullrefresh',
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

    document.getElementById('receiptlist').addEventListener('tap', function(){
        var productid = document.getElementById('product_stock_list_pullrefresh').getAttribute('productid');
        mui.openWindow({'url': '/aaswechat/wms/receiptmovelist/'+productid, 'id': 'stockreceiptlist'});
    });

    document.getElementById('deliverylist').addEventListener('tap', function(){
        var productid = document.getElementById('product_stock_list_pullrefresh').getAttribute('productid');
        mui.openWindow({'url': '/aaswechat/wms/deliverymovelist/'+productid, 'id': 'stockdeliverylist'});
    });

    mui("#stocklist").on("tap", "li.aas-stock", function(){
        var lotid = this.getAttribute('lotid');
        var locationid = this.getAttribute('locationid');
        var tempstr = locationid + '-' + lotid;
        mui.openWindow({'url': '/aaswechat/wms/product/stocklabels/'+tempstr, 'id': 'productstocklabels'});
    });


});
