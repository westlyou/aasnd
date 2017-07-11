/**
 * Created by Luforn on 2016-11-15.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#receipt_list_pullrefresh',
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
        var pullrefresh = document.body.querySelector('#receipt_list_pullrefresh');
        var receiptindex = pullrefresh.getAttribute('receiptindex');
        var receipttype = pullrefresh.getAttribute('receipttype');
        var receipt_params = {'receipttype': receipttype, 'receiptindex': parseInt(receiptindex)};
        var keyword = document.getElementById('product_code_search').value;
        if(keyword!=null && keyword!=''){
            receipt_params['product_code'] = keyword;
        }
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/receiptmore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: receipt_params, id: accessid }),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.receiptcount==0){
                    mui('#receipt_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.receiptcount<15){
                    mui('#receipt_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#receipt_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('receiptindex', dresult.receiptindex);
                var receipt_list = document.getElementById('receipt_list');
                mui.each(dresult.receipts, function(index, receipt){
                    var li = document.createElement('li');
                    li.className = 'aas-receipt mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>"+receipt.receipt_name+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+receipt.receipt_state+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('receiptid', receipt.receipt_id);
                    receipt_list.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}


mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-receipt", function(){
        var receiptid = this.getAttribute("receiptid");
        mui.openWindow({'url': '/aaswechat/wms/receiptdetail/'+receiptid, 'id': 'receiptdetail'});
    });


    document.getElementById('product_code_search').addEventListener('keyup',function(event) {
        if (!event || event.keyCode != 13) {
            return;
        }
        var keyword = document.getElementById('product_code_search').value;
        if (keyword == null || keyword == '') {
            mui.toast('请输入产品编码，产品编码不能为空！');
            return;
        }
        var receipt_type = document.getElementById('receipt_list_pullrefresh').getAttribute('receipttype');
        var search_params = {'product_code': keyword, 'receipt_type': receipt_type};
        var search_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/receiptlistsearch', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: search_params, id: search_accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                mui('#receipt_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                var receipt_list = document.getElementById('receipt_list');
                receipt_list.innerHTML = '';
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                mui.each(dresult.receipts, function(index, receipt){
                    var li = document.createElement('li');
                    li.className = 'aas-receipt mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-8 mui-text-left'>"+receipt.receipt_name+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+receipt.receipt_state+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('receiptid', receipt.receipt_id);
                    receipt_list.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) {console.log(type);}
        });
    });

});
