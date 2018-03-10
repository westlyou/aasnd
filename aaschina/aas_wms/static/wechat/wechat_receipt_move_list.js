/**
 * Created by luforn on 2018-3-10.
 */


mui.init({
    swipeBack:true,
    pullRefresh: {
        container: '#receipt_movelist_pullrefresh',
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
        var pullrefresh = document.body.querySelector('#receipt_movelist_pullrefresh');
        var productid = parseInt(pullrefresh.getAttribute('productid'));
        var moveindex = parseInt(pullrefresh.getAttribute('moveindex'));
        var searchkey = document.getElementById('move_search').value;
        var moveparams = {'productid': productid, 'moveindex': moveindex};
        if(searchkey!=null && searchkey!=''){
            moveparams['searchkey'] = searchkey;
        }
        var accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/receiptmovemore',{
            data: JSON.stringify({ jsonrpc: "2.0", method: 'call', params: moveparams, id: accessid }),
            dataType:'json', type:'post', timeout:10000,
            headers:{'Content-Type':'application/json'},
            success:function(data){
                var dresult = data.result;
                if (dresult.movecount==0){
                    mui('#receipt_movelist_pullrefresh').pullRefresh().endPullupToRefresh(true);
                    return ;
                }else if(dresult.movecount<20){
                    mui('#receipt_movelist_pullrefresh').pullRefresh().endPullupToRefresh(true);
                }else{
                    mui('#receipt_movelist_pullrefresh').pullRefresh().endPullupToRefresh(false);
                }
                pullrefresh.setAttribute('moveindex', dresult.moveindex);
                var tempmovelist = document.getElementById('movelist');
                mui.each(dresult.movelist, function(index, tmove){
                    var li = document.createElement('li');
                    li.className = 'aas-move mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+tmove.product_lot+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+tmove.product_qty+"</div>"+
                        "</div>"+
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+tmove.srclocation+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+tmove.destlocation+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('moveid', tmove.move_id);
                    tempmovelist.appendChild(li);
                });
            },
            error:function(xhr,type,errorThrown){ console.log(type); }
        });
    }, 1000);
}


mui.ready(function(){

    mui(".mui-content").on("tap", "li.aas-move", function(){
        var moveid = this.getAttribute("moveid");
        mui.openWindow({'url': '/aaswechat/wms/receiptmovedetail/'+moveid, 'id': 'movbedetail'});
    });

    // 搜索
    document.getElementById('move_search').addEventListener('keyup',function(event) {
        if (!event || event.keyCode != 13) {
            return;
        }
        var keyword = document.getElementById('move_search').value;
        if (keyword == null || keyword == '') {
            mui.toast('请输入请输入产品批次，搜索条件不能为空！');
            return;
        }
        var pullrefresh = document.getElementById('receipt_movelist_pullrefresh');
        var productid = parseInt(pullrefresh.getAttribute('productid'));
        var searchparams = {'productid': productid, 'searchkey': keyword};
        var search_accessid = Math.floor(Math.random() * 1000 * 1000 * 1000);
        mui.ajax('/aaswechat/wms/receiptmovesearch', {
            data: JSON.stringify({jsonrpc: "2.0", method: 'call', params: searchparams, id: search_accessid}),
            dataType: 'json', type: 'post', timeout: 10000,
            headers: {'Content-Type': 'application/json'},
            success: function (data) {
                mui('#receipt_movelist_pullrefresh').pullRefresh().endPullupToRefresh(true);
                var tempmovelist = document.getElementById('movelist');
                tempmovelist.innerHTML = '';
                var dresult = data.result;
                if(!dresult.success){
                    mui.toast(dresult.message);
                    return ;
                }
                pullrefresh.setAttribute('moveindex', dresult.moveindex);
                mui.each(dresult.movelist, function(index, tmove){
                    var li = document.createElement('li');
                    li.className = 'aas-move mui-table-view-cell';
                    li.innerHTML = "<a class='mui-navigate-right' style='padding-right:40px;' href='javascript:;'>" +
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+tmove.product_lot+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+tmove.product_qty+"</div>"+
                        "</div>"+
                        "<div class='mui-table'>" +
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-left'>"+tmove.srclocation+"</div>"+
                            "<div class='mui-table-cell mui-col-xs-6 mui-text-right'>"+tmove.destlocation+"</div>"+
                        "</div>"+
                        "</a>";
                    li.setAttribute('moveid', tmove.move_id);
                    tempmovelist.appendChild(li);
                });
            },
            error: function (xhr, type, errorThrown) {console.log(type);}
        });
    });

});
