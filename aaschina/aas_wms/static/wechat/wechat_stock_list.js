/**
 * Created by luforn on 2017-7-10.
 */

mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#stock_list_pullrefresh',
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
        var pullrefresh = document.body.querySelector('#stock_list_pullrefresh');
        var stockindex = pullrefresh.getAttribute('stockindex');
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        var params = {'stockindex': parseInt(stockindex)};
        var keyword = document.getElementById('stock_search').value;
        if(keyword!=null && keyword!=''){
            params['skey'] = keyword;
        }
        mui.ajax('/aaswechat/wms/stockmore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: params, id: accessid}),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.stockcount==0){
                    mui('#stock_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.stockcount<20){
                    mui('#stock_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#stock_list_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('stockindex', dresult.stockindex);
                var stock_list = document.getElementById('stock_list');
                mui.each(dresult.stocklist, function(index, tstock){
                    var li = document.createElement('li');
                    li.className = 'aas-stock mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>"+tstock.product_code+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+tstock.product_qty+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+tstock.location_name+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('stockid', tstock.stock_id);
                    stock_list.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}

mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-stock", function(){
        var stockid = this.getAttribute("stockid");
        mui.openWindow({'url': '/aaswechat/wms/stockdetail/'+stockid, 'id': 'stockdetail'});
    });

    document.getElementById('stock_search').addEventListener('keyup',function(event) {
        if (!event || event.keyCode != 13) {
            return;
        }
        var keyword = document.getElementById('stock_search').value;
        if (keyword == null || keyword == '') {
            mui.toast('请输入产品编码或者库位名称！');
            return;
        }
        var search_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/stocksearch', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: {'skey': keyword}, id: search_accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                mui('#stock_list_pullrefresh').pullRefresh().endPullupToRefresh(true);
                var stock_list = document.getElementById('stock_list');
                stock_list.innerHTML = '';
                var titleli = document.createElement('li');
                titleli.className = 'mui-table-view-cell';
                titleli.innerHTML = "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>产品编码</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>产品数量</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>库位名称</div>"+
                        "</div>";
                stock_list.appendChild(titleli);
                var dresult = data.result;
                document.getElementById('stock_list_pullrefresh').setAttribute('stockindex', dresult.stockindex);
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                mui.each(dresult.stocklist, function(index, tstock){
                    var li = document.createElement('li');
                    li.className = 'aas-stock mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-left'>"+tstock.product_code+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+tstock.product_qty+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-4 mui-text-right'>"+tstock.location_name+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('stockid', tstock.stock_id);
                    stock_list.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) {console.log(type);}
        });
    });

});