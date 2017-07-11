/**
 * Created by Luforn on 2016-11-29.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#purchase_detail_pullrefresh',
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
    document.getElementById('action_purchase_receipt').addEventListener('tap', function(){
        var purchaseid = parseInt(document.getElementById('purchase_detail_pullrefresh').getAttribute('purchaseid'));
        mui.openWindow({'url': '/aaswechat/wms/purchasereceipt/'+purchaseid, 'id': 'purchasereceipt'});
    });
});